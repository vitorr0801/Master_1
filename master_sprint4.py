# master.py
import json as _json
import os
import socket
import ssl
import threading
import time
import uuid
import datetime

try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from protocol import *
from network import *
from config import *

# ── Shared state (all access protected by _lock) ──────────────────────────────
_lock = threading.Lock()

task_queue = []          # [{"user": str}, ...]
local_workers = {}       # worker_uuid → socket
borrowed_workers = {}    # worker_uuid → {"conn": socket, "original_master": "ip:port"}
lent_workers = {}        # worker_uuid → {"conn": socket, "borrower": str}
busy_workers = set()     # worker_uuids currently executing a task
neighbor_conns = {}      # "ip:port" → socket  (M2M connection pool)

server_uuid = str(uuid.uuid4())
_user_counter = 0
_help_requested = False

# Sprint 4: task counters and uptime reference
_task_stats = {"completed": 0, "failed": 0}
_start_time  = time.time()

# Per-socket send locks to prevent concurrent writes from different threads
_socket_send_locks = {}
_ssl_mutex = threading.Lock()


def _log(tag, msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][{tag}] {msg}")


def _socket_lock(sock):
    sid = id(sock)
    with _ssl_mutex:
        if sid not in _socket_send_locks:
            _socket_send_locks[sid] = threading.Lock()
        return _socket_send_locks[sid]


def _safe_send(sock, data):
    with _socket_lock(sock):
        return send_message(sock, data)


def _remove_socket_lock(sock):
    with _ssl_mutex:
        _socket_send_locks.pop(id(sock), None)


# ── Sprint 2: Worker connection handler ───────────────────────────────────────

def handle_worker_connection(conn, addr, initial_msg=None):
    """
    Handles the full lifetime of one worker TCP connection.
    Supports Sprint 1 (heartbeat), Sprint 2 (task cycle),
    and Sprint 3 (register_temporary_worker from borrowed workers).
    """
    worker_uuid = None
    is_borrowed = False
    original_master = None
    registered = False

    def register(wid, orig=None):
        nonlocal worker_uuid, is_borrowed, original_master, registered
        worker_uuid = wid
        original_master = orig
        is_borrowed = bool(orig)
        registered = True
        with _lock:
            if is_borrowed:
                borrowed_workers[wid] = {"conn": conn, "original_master": orig}
                _log("MASTER", f"Worker EMPRESTADO: {wid} (origem: {orig})")
            else:
                local_workers[wid] = conn
                _log("MASTER", f"Worker LOCAL: {wid}")
            _log("MASTER", f"Locais: {len(local_workers)} | Emprestados: {len(borrowed_workers)}")

    def dispatch_task(wid):
        """Send QUERY or NO_TASK; if QUERY wait for STATUS then send ACK."""
        with _lock:
            if task_queue:
                task = task_queue.pop(0)
                user = task["user"]
                busy_workers.add(wid)
            else:
                task = None

        if task:
            _log("MASTER", f"QUERY → {wid} (user={user}, borrowed={is_borrowed})")
            _safe_send(conn, task_query(user))

            status_raw = receive_message_timeout(conn, 10)
            if status_raw:
                try:
                    sd = decode_message(status_raw)
                    status = sd.get("STATUS")
                    if status in ("OK", "NOK"):
                        _log("MASTER", f"STATUS {status} ← {wid}")
                        _safe_send(conn, task_ack(wid))
                        _log("MASTER", f"ACK → {wid} (borrowed={is_borrowed})")
                        with _lock:
                            if status == "OK":
                                _task_stats["completed"] += 1
                            else:
                                _task_stats["failed"] += 1
                    else:
                        _log("MASTER", f"STATUS inesperado de {wid}: {status_raw[:80]}")
                except Exception as e:
                    _log("MASTER", f"Erro ao parsear STATUS de {wid}: {e}")
            else:
                _log("MASTER", f"Timeout esperando STATUS de {wid}")
            with _lock:
                busy_workers.discard(wid)
        else:
            _safe_send(conn, task_no_task())

    def process(data):
        """Route one decoded message."""
        task_field = data.get("TASK")
        worker_field = data.get("WORKER")
        msg_type = data.get("type")

        # Sprint 1: heartbeat
        if task_field == "HEARTBEAT":
            _safe_send(conn, heartbeat_alive(server_uuid))

        # Sprint 2: work request (also serves as initial presentation)
        elif worker_field == "ALIVE":
            wid = data.get("WORKER_UUID")
            if not wid:
                _log("MASTER", f"ALIVE sem WORKER_UUID de {addr}")
                return
            orig = data.get("SERVER_UUID")
            if not registered:
                register(wid, orig)
            dispatch_task(wid)

        # Sprint 3: borrowed worker presenting itself
        elif msg_type == "register_temporary_worker":
            payload = data.get("payload", {})
            wid = payload.get("worker_id")
            orig = payload.get("original_master_address")
            if wid and orig:
                register(wid, orig)
                _log("MASTER", f"register_temporary_worker: {wid} pronto para tarefas")
            else:
                _log("MASTER", "register_temporary_worker: campos obrigatórios ausentes")

        elif msg_type is not None:
            _log("MASTER", f"Tipo desconhecido de {addr}: {msg_type} — ignorado")
        else:
            _log("MASTER", f"Mensagem não reconhecida de {addr}: {str(data)[:80]}")

    # Handle the first message that was already read by the router
    if initial_msg:
        process(initial_msg)

    # Main receive loop
    while True:
        raw = receive_message(conn)
        if not raw:
            break
        try:
            data = decode_message(raw)
        except Exception as e:
            _log("MASTER", f"JSON inválido de {addr}: {e}")
            continue
        process(data)

    # Cleanup
    with _lock:
        if worker_uuid:
            local_workers.pop(worker_uuid, None)
            borrowed_workers.pop(worker_uuid, None)
            busy_workers.discard(worker_uuid)
            _log("MASTER", f"Worker desconectado: {worker_uuid}")
            _log("MASTER", f"Locais: {len(local_workers)} | Emprestados: {len(borrowed_workers)}")
    _remove_socket_lock(conn)


# ── Sprint 3: Incoming M2M handler ────────────────────────────────────────────

def handle_m2m_connection(conn, addr, initial_msg):
    """Handles an incoming Master-to-Master connection."""
    def process(data):
        msg_type = data.get("type")
        request_id = data.get("request_id")
        _log("M2M-IN", f"type={msg_type} request_id={request_id} de {addr}")

        if msg_type == "request_help":
            payload = data.get("payload", {})
            requester_id = payload.get("master_id", "unknown")
            workers_needed = int(payload.get("workers_needed", 1))

            with _lock:
                my_load = len(task_queue)
                idle = [wid for wid in local_workers
                        if wid not in lent_workers and wid not in busy_workers]

            if my_load >= THRESHOLD or not idle:
                reason = "high_load" if my_load >= THRESHOLD else "no_workers_available"
                _log("M2M-IN", f"Recusando {requester_id}: {reason}")
                _safe_send(conn, m2m_response_rejected(request_id, reason))
            else:
                to_lend = idle[:workers_needed]
                my_addr = f"0.0.0.0:{MASTER_PORT}"
                worker_details = [{"id": wid, "address": my_addr} for wid in to_lend]
                _log("M2M-IN", f"Aceitando {requester_id}: emprestando {len(to_lend)} workers")
                _safe_send(conn, m2m_response_accepted(request_id, len(to_lend), worker_details))

                # The requester's server address (port is always MASTER_PORT per convention)
                requester_server_addr = f"{addr[0]}:{MASTER_PORT}"

                for wid in to_lend:
                    with _lock:
                        worker_conn = local_workers.get(wid)
                    if worker_conn:
                        _log("M2M-IN", f"command_redirect → {wid} ({requester_server_addr})")
                        _safe_send(worker_conn, m2m_command_redirect(requester_server_addr))
                        with _lock:
                            lent_workers[wid] = {"conn": worker_conn, "borrower": requester_id}

        elif msg_type == "notify_worker_returned":
            payload = data.get("payload", {})
            wid = payload.get("worker_id")
            if wid:
                with _lock:
                    lent_workers.pop(wid, None)
                _log("M2M-IN", f"Worker {wid} devolvido — Farm atualizada")
            else:
                _log("M2M-IN", "notify_worker_returned: worker_id ausente")

        elif msg_type is not None:
            _log("M2M-IN", f"Tipo desconhecido: {msg_type} — ignorado")

    process(initial_msg)

    # Keep connection open (pool) for follow-up messages from the same peer
    while True:
        raw = receive_message(conn)
        if not raw:
            break
        try:
            process(decode_message(raw))
        except Exception as e:
            _log("M2M-IN", f"Erro de parsing: {e}")

    _remove_socket_lock(conn)


# ── Connection router ─────────────────────────────────────────────────────────

# Message types that identify an incoming M2M connection
_M2M_TYPES = {
    "request_help", "response_accepted", "response_rejected",
    "command_redirect", "notify_worker_returned",
}


def handle_connection(conn, addr):
    raw = receive_message(conn)
    if not raw:
        conn.close()
        return
    try:
        data = decode_message(raw)
    except Exception as e:
        _log("MASTER", f"JSON inválido de {addr}: {e}")
        conn.close()
        return

    if data.get("type") in _M2M_TYPES:
        handle_m2m_connection(conn, addr, data)
    else:
        handle_worker_connection(conn, addr, initial_msg=data)

    try:
        conn.close()
    except Exception:
        pass


# ── Sprint 3: Outgoing M2M (saturation → request_help) ───────────────────────

def _get_neighbor_conn(neighbor):
    key = f"{neighbor['ip']}:{neighbor['port']}"
    with _lock:
        conn = neighbor_conns.get(key)
    if conn:
        return conn, key
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((neighbor["ip"], neighbor["port"]))
        s.settimeout(None)
        with _lock:
            neighbor_conns[key] = s
        _log("M2M-OUT", f"Conectado a {neighbor['master_id']} ({key})")
        return s, key
    except Exception as e:
        _log("M2M-OUT", f"Falha ao conectar com {neighbor['master_id']}: {e}")
        return None, key


def request_help_from_neighbors():
    global _help_requested
    with _lock:
        current_load = len(task_queue)

    workers_needed = max(1, current_load - THRESHOLD)

    if not NEIGHBOR_MASTERS:
        _help_requested = False
        return False

    results = {}
    results_lock = threading.Lock()

    def _ask_one(neighbor):
        conn, key = _get_neighbor_conn(neighbor)
        if not conn:
            return

        req_id = str(uuid.uuid4())
        msg = m2m_request_help(MASTER_ID, current_load, THRESHOLD, workers_needed, req_id)
        _log("M2M-OUT", f"request_help → {neighbor['master_id']} (rid={req_id})")

        if not _safe_send(conn, msg):
            with _lock:
                neighbor_conns.pop(key, None)
            _log("M2M-OUT", f"Falha ao enviar para {neighbor['master_id']}")
            return

        resp_raw = receive_message_timeout(conn, 5)
        if not resp_raw:
            _log("M2M-OUT", f"Timeout aguardando resposta de {neighbor['master_id']} — rid={req_id}")
            with _lock:
                neighbor_conns.pop(key, None)
            return

        try:
            resp = decode_message(resp_raw)
        except Exception as e:
            _log("M2M-OUT", f"Resposta inválida de {neighbor['master_id']}: {e}")
            return

        if resp.get("request_id") != req_id:
            _log("M2M-OUT", f"request_id mismatch de {neighbor['master_id']}")
            return

        rtype = resp.get("type")
        with results_lock:
            results[neighbor['master_id']] = rtype
        if rtype == "response_accepted":
            details = resp.get("payload", {}).get("worker_details", [])
            _log("M2M-OUT", f"{neighbor['master_id']} aceitou: {len(details)} worker(s) emprestado(s)")
        elif rtype == "response_rejected":
            reason = resp.get("payload", {}).get("reason", "unknown")
            _log("M2M-OUT", f"{neighbor['master_id']} recusou ({reason})")

    # Envia request_help apenas para os vizinhos permitidos (limite: MAX_NEIGHBOR_MASTERS)
    allowed = NEIGHBOR_MASTERS[:MAX_NEIGHBOR_MASTERS]
    threads = [threading.Thread(target=_ask_one, args=(n,), daemon=True)
               for n in allowed]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    accepted = any(v == "response_accepted" for v in results.values())
    if not accepted:
        _help_requested = False
    return accepted


def release_borrowed_workers():
    global _help_requested
    with _lock:
        to_release = list(borrowed_workers.items())

    for wid, info in to_release:
        conn = info["conn"]
        orig = info["original_master"]
        _log("MASTER", f"Liberando worker emprestado {wid} → {orig}")
        _safe_send(conn, m2m_command_release(orig))

        with _lock:
            borrowed_workers.pop(wid, None)

        # Notify the original master
        try:
            orig_ip, orig_port_str = orig.rsplit(":", 1)
            orig_port = int(orig_port_str)
        except Exception:
            continue

        key = f"{orig_ip}:{orig_port}"
        with _lock:
            m_conn = neighbor_conns.get(key)
        if not m_conn:
            try:
                m_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                m_conn.settimeout(5)
                m_conn.connect((orig_ip, orig_port))
                m_conn.settimeout(None)
                with _lock:
                    neighbor_conns[key] = m_conn
            except Exception as e:
                _log("MASTER", f"Falha ao notificar {orig}: {e}")
                continue
        _log("MASTER", f"notify_worker_returned → {orig} (worker={wid})")
        _safe_send(m_conn, m2m_notify_worker_returned(wid))

    with _lock:
        bcount = len(borrowed_workers)
    _log("MASTER", f"Locais: {len(local_workers)} | Emprestados: {bcount}")
    _help_requested = False


# ── Load monitor ──────────────────────────────────────────────────────────────

def monitor_load():
    global _help_requested
    while True:
        with _lock:
            qlen = len(task_queue)
            lcount = len(local_workers)
            bcount = len(borrowed_workers)

        _log("MONITOR",
             f"Fila={qlen} | Locais={lcount} | Emprestados={bcount} | Threshold={THRESHOLD}")

        if qlen > THRESHOLD and not _help_requested and NEIGHBOR_MASTERS:
            _log("MONITOR", "SATURAÇÃO — solicitando ajuda a vizinhos")
            _help_requested = True
            threading.Thread(target=request_help_from_neighbors, daemon=True).start()

        if qlen <= THRESHOLD:
            _help_requested = False

        if qlen < RELEASE_THRESHOLD and bcount > 0:
            _log("MONITOR", "Carga normalizada — devolvendo workers emprestados")
            threading.Thread(target=release_borrowed_workers, daemon=True).start()

        time.sleep(5)


# ── Request simulator ─────────────────────────────────────────────────────────

def simulate_requests():
    global _user_counter
    while True:
        with _lock:
            _user_counter += 1
            user = f"User_{_user_counter:04d}"
            task_queue.append({"user": user, "added_at": time.time()})
            qlen = len(task_queue)
        _log("SIM", f"Nova tarefa de {user} — fila: {qlen}")
        time.sleep(REQUEST_INTERVAL)


# ── Sprint 4: Supervisor metrics reporting ────────────────────────────────────

def _addr_to_peer_uuid(addr):
    """Resolve ip:port → master_id from config; fall back to the raw address."""
    for n in NEIGHBOR_MASTERS:
        if f"{n['ip']}:{n['port']}" == addr:
            return n["master_id"]
    return addr


def _build_performance_report():
    """Assemble the Sprint 4 performance_report payload from live state."""
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if _HAS_PSUTIL:
        cpu_pct      = _psutil.cpu_percent(interval=0.5)
        cpu_logical  = _psutil.cpu_count(logical=True)  or 1
        cpu_physical = _psutil.cpu_count(logical=False) or cpu_logical
        mem          = _psutil.virtual_memory()
        try:
            la = _psutil.getloadavg()
            load_1m, load_5m = round(la[0], 2), round(la[1], 2)
        except (AttributeError, OSError):
            # Windows: approximate with current CPU usage
            load_1m = round(cpu_pct / 100 * cpu_logical, 2)
            load_5m = load_1m
        try:
            disk_path = "C:\\" if os.name == "nt" else "/"
            disk = _psutil.disk_usage(disk_path)
            disk_total_gb = round(disk.total / 1024**3, 1)
            disk_free_gb  = round(disk.free  / 1024**3, 1)
            disk_pct      = round(disk.percent, 1)
        except Exception:
            disk_total_gb = disk_free_gb = disk_pct = 0.0
        uptime_s = int(time.time() - _psutil.boot_time())
        total_mb = int(mem.total     / 1024**2)
        avail_mb = int(mem.available / 1024**2)
        used_mb  = int(mem.used      / 1024**2)
        mem_pct  = round(mem.percent, 2)
    else:
        cpu_pct = cpu_logical = cpu_physical = 0
        load_1m = load_5m = 0.0
        uptime_s = int(time.time() - _start_time)
        total_mb = avail_mb = used_mb = 0
        mem_pct  = 0.0
        disk_total_gb = disk_free_gb = disk_pct = 0.0

    with _lock:
        w_total       = len(local_workers) + len(borrowed_workers)
        w_idle        = len([w for w in local_workers
                             if w not in busy_workers and w not in lent_workers])
        w_utilization = len(busy_workers)
        w_lent        = len(lent_workers)    # workers this node lent OUT
        w_received    = len(borrowed_workers) # workers this node received IN
        w_home        = len(local_workers)
        tasks_pending  = len(task_queue)
        tasks_running  = len(busy_workers)
        t_completed    = _task_stats["completed"]
        t_failed       = _task_stats["failed"]

        oldest_age = 0
        if task_queue:
            oldest_age = int(time.time() - task_queue[0].get("added_at", time.time()))

        bw_list = (
            [{"direction": "out", "peer_uuid": info.get("borrower", "unknown")}
             for info in lent_workers.values()] +
            [{"direction": "in",  "peer_uuid": _addr_to_peer_uuid(info.get("original_master", ""))}
             for info in borrowed_workers.values()]
        )

        neighbor_list = [
            {
                "server_uuid":    n["master_id"],
                "status":         "available" if f"{n['ip']}:{n['port']}" in neighbor_conns
                                  else "unavailable",
                "last_heartbeat": now_iso,
            }
            for n in NEIGHBOR_MASTERS
        ]

    return {
        "server_uuid":     SERVER_UUID,
        "hostname":        HOSTNAME,
        "role":            "master",
        "task":            "performance_report",
        "timestamp":       now_iso,
        "message_id":      str(uuid.uuid4()),
        "payload_version": "sprint4-monitor",
        "performance": {
            "system": {
                "uptime_seconds":  uptime_s,
                "load_average_1m": load_1m,
                "load_average_5m": load_5m,
                "cpu": {
                    "usage_percent":  cpu_pct,
                    "count_logical":  cpu_logical,
                    "count_physical": cpu_physical,
                },
                "memory": {
                    "total_mb":     total_mb,
                    "available_mb": avail_mb,
                    "percent_used": mem_pct,
                    "memory_used":  used_mb,
                },
                "disk": {
                    "total_gb":    disk_total_gb,
                    "free_gb":     disk_free_gb,
                    "percent_used": disk_pct,
                },
            },
            "farm_state": {
                "workers": {
                    "total_registered":        w_total,
                    "workers_utilization":     w_utilization,
                    "workers_alive":           w_total,
                    "workers_idle":            w_idle,
                    "workers_borrowed":        w_lent,
                    "workers_received":        w_received,
                    "workers_failed":          0,
                    "workers_home":            w_home,
                    "workers_available_capacity": w_idle,
                    "borrowed_workers":        bw_list,
                },
                "tasks": {
                    "tasks_pending":     tasks_pending,
                    "tasks_running":     tasks_running,
                    "tasks_completed":   t_completed,
                    "tasks_failed":      t_failed,
                    "oldest_task_age_s": oldest_age,
                },
            },
            "config_thresholds": {
                "max_task":            THRESHOLD,
                "warn_cpu_percent":    85,
                "warn_memory_percent": 85,
                "release_task":        RELEASE_THRESHOLD,
            },
            "neighbors": neighbor_list,
        },
    }


def build_monitor_report(server_uuid=None, role="master"):
    """Compatibility wrapper used by the Sprint 4 tests and runtime helpers."""
    payload = _build_performance_report()
    if server_uuid is not None:
        payload["server_uuid"] = server_uuid
    if role is not None:
        payload["role"] = role
    return payload


def _send_to_supervisor(payload):
    """Open TLS/TCP to supervisor, send JSON + \n, close — no response expected."""
    raw = (_json.dumps(payload) + "\n").encode("utf-8")
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((SUPERVISOR_HOST, SUPERVISOR_PORT), timeout=10) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=SUPERVISOR_SNI) as tls_sock:
                tls_sock.sendall(raw)
        _log("SUPERVISOR", f"Relatório enviado — msg_id={payload['message_id'][:8]}")
    except Exception as e:
        _log("SUPERVISOR", f"Falha ao enviar: {e}")


def supervisor_reporter():
    """Sprint 4: send performance_report to supervisor every SUPERVISOR_REPORT_INTERVAL s."""
    _log("SUPERVISOR", f"Iniciado — reportando a {SUPERVISOR_HOST}:{SUPERVISOR_PORT} "
                       f"a cada {SUPERVISOR_REPORT_INTERVAL}s")
    while True:
        time.sleep(SUPERVISOR_REPORT_INTERVAL)
        try:
            payload = _build_performance_report()
            print("\n" + "="*60)
            print("[SUPERVISOR] Estado interno no momento do relatório:")
            with _lock:
                print(f"  local_workers  : {list(local_workers.keys())}")
                print(f"  borrowed_workers: {list(borrowed_workers.keys())}")
                print(f"  busy_workers   : {list(busy_workers)}")
                print(f"  lent_workers   : {list(lent_workers.keys())}")
                print(f"  task_queue len : {len(task_queue)}")
            print("[SUPERVISOR] Payload que será enviado:")
            print(_json.dumps(payload, indent=2, ensure_ascii=False))
            print("="*60 + "\n")
            threading.Thread(target=_send_to_supervisor, args=(payload,), daemon=True).start()
        except Exception as e:
            _log("SUPERVISOR", f"Erro ao construir relatório: {e}")


# ── TCP server ────────────────────────────────────────────────────────────────

def start_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen()
    _log("MASTER", f"Iniciado | ID={MASTER_ID} | UUID={server_uuid} | Porta={port}")
    while True:
        try:
            conn, addr = server.accept()
            _log("MASTER", f"Nova conexão: {addr}")
            threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()
        except Exception:
            break


def start_master_services(port=MASTER_PORT):
    threading.Thread(target=monitor_load, daemon=True).start()
    threading.Thread(target=simulate_requests, daemon=True).start()
    threading.Thread(target=start_server, args=(port,), daemon=True).start()
    threading.Thread(target=supervisor_reporter, daemon=True).start()


if __name__ == "__main__":
    start_master_services(MASTER_PORT)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{LOG_SEPARATOR}")
        print("[MASTER] Encerrando com Ctrl+C...")
        print(LOG_SEPARATOR)
        import sys
        sys.exit(0)