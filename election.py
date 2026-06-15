"""
election.py
===========
Módulo de eleição de master por consenso entre workers.

Fluxo:
1. Worker detecta 4 falhas consecutivas de heartbeat → chama start_election()
2. start_election() abre um servidor TCP temporário na ELECTION_SERVER_PORT
   e faz broadcast para todos os peers conhecidos anunciando sua candidatura
   com o espaço livre em disco.
3. Cada worker que recebe um announce responde com seu próprio announce.
4. Após o período de coleta (ELECTION_COLLECT_TIME), o worker com maior
   free_disk é eleito por consenso local — cada worker chega à mesma
   conclusão independentemente (não há troca de votos explícita, o critério
   é determinístico).
5. Se o worker local for o eleito, ele chama become_master().
6. Todos os workers (incluindo o novo master) reconectam ao novo IP:porta.
"""

import socket
import threading
import shutil
import time
import json

from protocol import (
    election_announce, election_result, i_am_master,
    encode_message, decode_message
)
from config import (
    LOG_SEPARATOR, ELECTION_SERVER_PORT, ELECTION_MASTER_PORT,
    HEARTBEAT_FAIL_THRESHOLD
)

# Tempo que cada worker espera coletando announces antes de decidir (segundos)
ELECTION_COLLECT_TIME = 5


def get_free_disk_bytes():
    """Retorna o espaço livre em disco em bytes."""
    usage = shutil.disk_usage("/")
    return usage.free


def _listen_for_announces(my_id, my_ip, collect_time):
    """
    Abre um servidor TCP temporário na ELECTION_SERVER_PORT e coleta
    announces de outros workers durante `collect_time` segundos.
    Retorna uma lista de candidatos: [{"worker_id", "free_disk", "ip", "port"}]
    """
    candidates = []
    lock = threading.Lock()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", ELECTION_SERVER_PORT))
    except OSError:
        print(f"[ELECTION] Porta {ELECTION_SERVER_PORT} já em uso — continuando sem servidor local")
        return candidates

    server.listen(20)
    server.settimeout(collect_time + 1)

    print(f"[ELECTION] Servidor de eleição ouvindo na porta {ELECTION_SERVER_PORT}")

    deadline = time.time() + collect_time

    def handle_conn(conn):
        try:
            conn.settimeout(2)
            raw = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                raw += chunk
                if b"\n" in raw:
                    break
            if raw:
                msg = json.loads(raw.decode().split("\n")[0])
                if msg.get("type") == "election_announce":
                    with lock:
                        candidates.append({
                            "worker_id": msg["worker_id"],
                            "free_disk": msg["free_disk"],
                            "ip": msg["ip"],
                            "port": msg["port"]
                        })
                        print(f"[ELECTION] Candidato recebido: {msg['worker_id']} "
                              f"({msg['free_disk'] // (1024**3)} GB livres)")
        except Exception as e:
            print(f"[ELECTION] Erro ao processar announce: {e}")
        finally:
            conn.close()

    while time.time() < deadline:
        try:
            conn, _ = server.accept()
            threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()
        except socket.timeout:
            break
        except Exception:
            break

    server.close()
    return candidates


def _broadcast_announce(my_announce, peer_ips):
    """
    Envia o announce do worker local para todos os peers conhecidos.
    Usa conexão TCP direta na ELECTION_SERVER_PORT de cada peer.
    """
    payload = encode_message(my_announce)

    def send_to(ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((ip, ELECTION_SERVER_PORT))
            s.sendall(payload)
            s.close()
            print(f"[ELECTION] Announce enviado para {ip}")
        except Exception as e:
            print(f"[ELECTION] Não foi possível contatar {ip}: {e}")

    threads = [threading.Thread(target=send_to, args=(ip,), daemon=True)
               for ip in peer_ips]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3)


def _decide_winner(candidates):
    """
    Critério determinístico: maior free_disk.
    Em caso de empate, menor worker_id (string) vence.
    Retorna o dicionário do candidato vencedor.
    """
    return max(candidates, key=lambda c: (c["free_disk"], -ord(c["worker_id"][0])))


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def start_election(worker_id, my_ip, peer_ips, on_elected_as_master, on_new_master_found):
    """
    Inicia o processo de eleição.

    Parâmetros
    ----------
    worker_id            : str  — UUID deste worker
    my_ip                : str  — IP deste worker (visível pelos peers)
    peer_ips             : list — IPs dos outros workers conhecidos
    on_elected_as_master : callable() — chamado se este worker for eleito master
    on_new_master_found  : callable(ip, port) — chamado com o IP/porta do novo master
    """

    print(LOG_SEPARATOR)
    print("[ELECTION] Iniciando eleição de novo master")
    print(f"[ELECTION] Worker local: {worker_id}")
    print(f"[ELECTION] Peers conhecidos: {peer_ips}")
    print(LOG_SEPARATOR)

    free_disk = get_free_disk_bytes()
    my_announce = election_announce(
        worker_id=worker_id,
        free_disk_bytes=free_disk,
        ip=my_ip,
        port=ELECTION_MASTER_PORT
    )

    print(f"[ELECTION] Meu espaço livre: {free_disk // (1024**3)} GB")

    # Inicia o servidor de coleta em paralelo ao broadcast
    collect_thread_result = []

    def collect():
        result = _listen_for_announces(worker_id, my_ip, ELECTION_COLLECT_TIME)
        collect_thread_result.append(result)

    t_collect = threading.Thread(target=collect, daemon=True)
    t_collect.start()

    # Pequeno delay para o servidor subir antes do broadcast
    time.sleep(0.3)

    _broadcast_announce(my_announce, peer_ips)

    # Aguarda coleta terminar
    t_collect.join(timeout=ELECTION_COLLECT_TIME + 2)

    # Inclui o próprio worker como candidato
    candidates = collect_thread_result[0] if collect_thread_result else []
    candidates.append({
        "worker_id": worker_id,
        "free_disk": free_disk,
        "ip": my_ip,
        "port": ELECTION_MASTER_PORT
    })

    print(LOG_SEPARATOR)
    print(f"[ELECTION] Total de candidatos: {len(candidates)}")
    for c in candidates:
        print(f"  {c['worker_id']} — {c['free_disk'] // (1024**3)} GB livres")

    winner = _decide_winner(candidates)

    print(f"[ELECTION] Vencedor: {winner['worker_id']}")
    print(f"  IP: {winner['ip']}  Porta: {winner['port']}")
    print(LOG_SEPARATOR)

    if winner["worker_id"] == worker_id:
        print("[ELECTION] Este worker foi eleito MASTER!")
        on_elected_as_master()
    else:
        print(f"[ELECTION] Novo master é {winner['worker_id']} em {winner['ip']}:{winner['port']}")
        on_new_master_found(winner["ip"], winner["port"])