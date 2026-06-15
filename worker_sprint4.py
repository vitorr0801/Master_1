# worker.py
import socket
import time
import uuid
import threading
import random
import shutil
import datetime

from protocol import *
from network import *
from config import *
import master_sprint4  # ← Master B não pede ajuda a ninguém

ELECTION_PORT = 5005
WORKER_HEARTBEAT_INTERVAL = 10

# ── Identity & addressing ─────────────────────────────────────────────────────
worker_id = str(uuid.uuid4())

my_ip = "127.0.0.1"              # This worker's IP — use 127.0.0.1 for local testing
current_master_ip = "127.0.0.1"  # Master IP — 127.0.0.1 local, ou IP real da máquina do master
current_master_port = MASTER_PORT

# Sprint 3: track original master when borrowed
original_master_ip = None
original_master_port = None
original_master_uuid = None   # learned from heartbeat response
current_master_uuid = None    # learned from heartbeat response
is_borrowed = False

# ── Connection state ──────────────────────────────────────────────────────────
sock = None
sock_lock = threading.Lock()   # protects concurrent sends on sock

hosting_master = False
in_election = False
heartbeat_fails = 0
election_bids = {}


def _log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][WORKER {worker_id[:8]}] {msg}")


def get_free_disk_space():
    return shutil.disk_usage("/").free


def process_task(user):
    _log(f"Processando tarefa de {user}...")
    time.sleep(random.uniform(1, max(1, TASK_PROCESS_TIME)))
    _log(f"Tarefa de {user} concluida")


# ── Connection helpers ────────────────────────────────────────────────────────

def connect_to_master(ip, port):
    global sock
    _log(f"Conectando ao master {ip}:{port}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, port))
        s.settimeout(None)
        with sock_lock:
            sock = s
        _log(f"Conectado ao master {ip}:{port}")
        return True
    except Exception as e:
        _log(f"Falha ao conectar: {e}")
        return False


def _close_sock():
    global sock
    with sock_lock:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
            sock = None


def _recv_timeout(timeout=5):
    """Receive one message from current sock with timeout."""
    s = sock
    if not s:
        return None
    return receive_message_timeout(s, timeout)


# ── Sprint 1 + 2 + 3: Main work cycle ────────────────────────────────────────

def work_cycle():
    """
    Single thread that drives the full worker protocol:
      Sprint 1: periodic HEARTBEAT / ALIVE check
      Sprint 2: ALIVE → QUERY/NO_TASK → STATUS → ACK
      Sprint 3: react to command_redirect and command_release
    """
    global sock, is_borrowed, current_master_uuid, original_master_uuid
    global original_master_ip, original_master_port, current_master_ip, current_master_port
    global in_election, heartbeat_fails

    # Start with last_heartbeat = now so the first thing we do is a work request,
    # not a heartbeat (per Sprint 2: first message after connect is ALIVE).
    last_heartbeat = time.time()

    while True:
        if in_election:
            time.sleep(1)
            continue

        if sock is None:
            time.sleep(2)
            _log(f"Reconectando ao master {current_master_ip}:{current_master_port}...")
            if connect_to_master(current_master_ip, current_master_port):
                heartbeat_fails = 0
                last_heartbeat = time.time()
            continue

        now = time.time()

        # ── Sprint 1: Heartbeat (every WORKER_HEARTBEAT_INTERVAL seconds) ────
        if now - last_heartbeat >= WORKER_HEARTBEAT_INTERVAL:
            _log(f"Enviando HEARTBEAT para {current_master_ip}")
            master_id_to_send = current_master_uuid or current_master_ip
            with sock_lock:
                ok = send_message(sock, heartbeat(master_id_to_send))
            if not ok:
                _on_conn_lost()
                continue

            raw = _recv_timeout(5)
            if raw:
                try:
                    data = decode_message(raw)
                    if data.get("TASK") == "HEARTBEAT" and data.get("RESPONSE") == "ALIVE":
                        current_master_uuid = data.get("SERVER_UUID", current_master_uuid)
                        _log(f"HEARTBEAT: ALIVE (master_uuid={current_master_uuid})")
                        last_heartbeat = time.time()
                        heartbeat_fails = 0
                        continue
                except Exception:
                    pass
            # Heartbeat failed
            heartbeat_fails += 1
            _log(f"HEARTBEAT falhou ({heartbeat_fails}/{MAX_HEARTBEAT_FAILS})")
            if heartbeat_fails >= MAX_HEARTBEAT_FAILS:
                _log("Master offline — iniciando eleicao")
                start_election()
            continue

        # ── Sprint 2: Work request (ALIVE) ────────────────────────────────────
        orig_uuid = original_master_uuid if is_borrowed else None
        alive_msg = worker_alive(worker_id, orig_uuid)

        with sock_lock:
            ok = send_message(sock, alive_msg)
        if not ok:
            _on_conn_lost()
            continue

        raw = _recv_timeout(5)
        if raw is None:
            # Timeout waiting for response from master
            time.sleep(2)
            continue

        try:
            data = decode_message(raw)
        except Exception as e:
            _log(f"JSON invalido do master: {e}")
            time.sleep(1)
            continue

        task = data.get("TASK")
        msg_type = data.get("type")

        if task == "NO_TASK":
            time.sleep(2)

        elif task == "QUERY":
            user = data.get("USER", "unknown")
            process_task(user)

            # Report result
            with sock_lock:
                send_message(sock, task_status("OK", worker_id))

            # Wait for ACK
            ack_raw = _recv_timeout(5)
            if ack_raw:
                try:
                    ack = decode_message(ack_raw)
                    if ack.get("STATUS") == "ACK":
                        _log(f"ACK recebido para tarefa de {user}")
                    else:
                        _log(f"Resposta inesperada no lugar do ACK: {ack_raw[:80]}")
                except Exception:
                    pass
            else:
                _log("Timeout esperando ACK")

        elif task == "HEARTBEAT" and data.get("RESPONSE") == "ALIVE":
            # Heartbeat response arrived in work-cycle slot — accept it
            current_master_uuid = data.get("SERVER_UUID", current_master_uuid)
            last_heartbeat = time.time()
            heartbeat_fails = 0

        # ── Sprint 3: Redirect command ────────────────────────────────────────
        elif msg_type == "command_redirect":
            payload = data.get("payload", {})
            new_addr = payload.get("new_master_address", "")
            _log(f"command_redirect recebido → {new_addr}")

            # Save original master info before disconnecting
            original_master_ip = current_master_ip
            original_master_port = current_master_port
            original_master_uuid = current_master_uuid

            _close_sock()

            try:
                new_ip, new_port_str = new_addr.rsplit(":", 1)
                new_port = int(new_port_str)
            except Exception as e:
                _log(f"Endereco invalido em command_redirect '{new_addr}': {e}")
                # Fall back to original master
                connect_to_master(original_master_ip, original_master_port)
                is_borrowed = False
                continue

            is_borrowed = True
            current_master_uuid = None  # unknown until first heartbeat on new master

            if connect_to_master(new_ip, new_port):
                current_master_ip = new_ip
                current_master_port = new_port
                orig_addr = f"{original_master_ip}:{original_master_port}"
                reg_msg = m2m_register_temporary_worker(worker_id, orig_addr)
                with sock_lock:
                    send_message(sock, reg_msg)
                _log(f"register_temporary_worker enviado (origem={orig_addr})")
                # Reset heartbeat timer so we do work requests first
                last_heartbeat = time.time()
            else:
                _log("Falha ao conectar ao novo master — retornando ao original")
                is_borrowed = False
                connect_to_master(original_master_ip, original_master_port)
                current_master_uuid = original_master_uuid

        # ── Sprint 3: Release command ─────────────────────────────────────────
        elif msg_type == "command_release":
            payload = data.get("payload", {})
            orig_addr = payload.get("original_master_address", "")
            _log(f"command_release recebido → retornando para {orig_addr}")

            _close_sock()
            is_borrowed = False

            try:
                orig_ip, orig_port_str = orig_addr.rsplit(":", 1)
                orig_port = int(orig_port_str)
            except Exception:
                orig_ip = original_master_ip or current_master_ip
                orig_port = original_master_port or current_master_port

            if connect_to_master(orig_ip, orig_port):
                current_master_ip = orig_ip
                current_master_port = orig_port
                current_master_uuid = original_master_uuid
                original_master_ip = None
                original_master_port = None
                original_master_uuid = None
                _log(f"Reconectado ao master original {orig_ip}:{orig_port}")
                last_heartbeat = time.time()
            else:
                _log(f"Falha ao reconectar ao master original {orig_ip}:{orig_port}")

        elif msg_type is not None:
            _log(f"Tipo desconhecido do master: {msg_type} — ignorado")
        else:
            _log(f"Mensagem nao reconhecida: {str(data)[:80]}")


def _on_conn_lost():
    global heartbeat_fails
    _close_sock()
    heartbeat_fails += 1
    _log(f"Conexao perdida ({heartbeat_fails}/{MAX_HEARTBEAT_FAILS})")
    if heartbeat_fails >= MAX_HEARTBEAT_FAILS:
        _log("Limite de falhas — iniciando eleicao")
        start_election()
    else:
        time.sleep(2)


# ── Election (legacy: worker → master election on master failure) ─────────────

def start_election():
    global in_election, election_bids, hosting_master, current_master_ip, heartbeat_fails

    in_election = True
    election_bids.clear()
    my_space = get_free_disk_space()
    _log(f"Eleicao iniciada! Espaco livre: {my_space / (1024**3):.2f} GB")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    bid_msg = encode_message(election_bid(worker_id, my_space, my_ip, MASTER_PORT))
    for _ in range(3):
        udp_sock.sendto(bid_msg, ("<broadcast>", ELECTION_PORT))
        time.sleep(0.5)

    _log(f"Aguardando respostas por {ELECTION_TIMEOUT}s...")
    time.sleep(ELECTION_TIMEOUT)

    winner_id = worker_id
    max_space = my_space
    winner_ip = my_ip
    for pid, info in election_bids.items():
        if info["space"] > max_space:
            max_space, winner_id, winner_ip = info["space"], pid, info["ip"]
        elif info["space"] == max_space and pid > winner_id:
            winner_id, winner_ip = pid, info["ip"]

    if winner_id == worker_id:
        _log("EU VENCI A ELEICAO! Tornando-me Master...")
        hosting_master = True
        vic_msg = encode_message(election_victory(worker_id, my_ip, MASTER_PORT))
        udp_sock.sendto(vic_msg, ("<broadcast>", ELECTION_PORT))
        master_sprint4.start_master_services(MASTER_PORT)
        time.sleep(1.5)
        current_master_ip = my_ip
        if connect_to_master(current_master_ip, MASTER_PORT):
            heartbeat_fails = 0
    else:
        _log(f"Vencedor: {winner_id} ({winner_ip}) — conectando...")

    in_election = False
    udp_sock.close()


def listen_election_messages():
    global current_master_ip, heartbeat_fails
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    udp_sock.bind(("", ELECTION_PORT))

    while True:
        data, addr = udp_sock.recvfrom(2048)
        if hosting_master:
            continue
        try:
            msg = decode_message(data.decode())
            if msg.get("type") == "ELECTION_BID":
                election_bids[msg["worker_id"]] = {"space": msg["free_space"], "ip": msg["ip"]}
            elif msg.get("type") == "ELECTION_VICTORY":
                _log(f"Novo Master reconhecido: {msg['ip']}")
                current_master_ip = msg["ip"]
                heartbeat_fails = 0
                if connect_to_master(current_master_ip, current_master_port):
                    _log("Conectado ao novo master")
        except Exception:
            pass


# ── Startup ───────────────────────────────────────────────────────────────────

_log(f"Worker iniciado: {worker_id}")

threading.Thread(target=listen_election_messages, daemon=True).start()
threading.Thread(target=work_cycle, daemon=True).start()

if not connect_to_master(current_master_ip, current_master_port):
    _log("Master nao encontrado na inicializacao — iniciando eleicao")
    start_election()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\n{LOG_SEPARATOR}")
    print("[WORKER] Encerrando...")
    print(LOG_SEPARATOR)