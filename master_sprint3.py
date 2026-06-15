import socket
import threading
import json
import queue
import uuid
import time
import logging
import os
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 5000
MASTER_ID = "MASTER_A"

CAPACITY = 3
SATURATION_THRESHOLD = CAPACITY  # Threshold para saturação
RELEASE_THRESHOLD = int(CAPACITY * 0.6)  # 60% da capacidade para liberação (histerese)
REQUEST_TIMEOUT = 5  # segundos

# Estruturas de dados thread-safe
workers = {}  # Workers locais: {worker_id: {addr, status}}
borrowed_workers = {}  # Workers emprestados: {worker_id: {addr, original_master_address}}
pending_requests = {}  # Requisições pendentes: {request_id: {master_id, response_received, socket}}
master_connections = {}  # Pool de conexões com Masters vizinhos

workers_lock = threading.Lock()
borrowed_workers_lock = threading.Lock()
pending_requests_lock = threading.Lock()
master_connections_lock = threading.Lock()

neighbor_masters = {
    "MASTER_B": {
        "host": "127.0.0.1",
        "port": 6000
    }
}

SUPERVISOR_HOST = os.getenv("SUPERVISOR_HOST", "nuted-ia.dev")
SUPERVISOR_PORT = int(os.getenv("SUPERVISOR_PORT", "443"))
SUPERVISOR_TLS = True
SUPERVISOR_INTERVAL_SECONDS = int(os.getenv("SUPERVISOR_INTERVAL_SECONDS", "10"))

# Fila thread-safe
task_queue = queue.Queue()

def current_load():
    """Retorna número de tarefas pendentes na fila"""
    return task_queue.qsize()

def get_available_workers():
    """Retorna número de workers ociosos"""
    with workers_lock:
        return len(workers)

def get_borrowed_workers_list():
    """Retorna lista de workers emprestados"""
    with borrowed_workers_lock:
        return list(borrowed_workers.values())


def monitor_load():
    """Monitora carga e dispara pedidos de ajuda se necessário"""
    while True:
        load = current_load()
        
        if load > SATURATION_THRESHOLD:
            logger.info(f"[SATURAÇÃO DETECTADA] Carga={load}, Capacity={SATURATION_THRESHOLD}")
            request_help()
        
        # Verificar se deve liberar workers emprestados
        if load < RELEASE_THRESHOLD:
            release_borrowed_workers()
        
        time.sleep(2)

def release_borrowed_workers():
    """Libera workers emprestados quando a carga normaliza"""
    with borrowed_workers_lock:
        if not borrowed_workers:
            return
        
        workers_to_release = list(borrowed_workers.items())
    
    for worker_id, worker_info in workers_to_release:
        logger.info(f"[LIBERAÇÃO] Liberando Worker emprestado: {worker_id}")
        release_worker(worker_id, worker_info)

def release_worker(worker_id, worker_info):
    """Envia comando de liberação para um worker emprestado"""
    try:
        original_master_addr = worker_info.get("original_master_address")
        
        # command_release para o Worker
        command = {
            "type": "command_release",
            "request_id": str(uuid.uuid4()),
            "payload": {
                "original_master_address": original_master_addr
            }
        }
        
        # Aqui você enviaria para o worker (via sua conexão registrada)
        logger.info(f"[COMMAND_RELEASE] Enviado para {worker_id}: {command}")
        
        # notify_worker_returned para o Master original
        original_master = parse_master_from_address(original_master_addr)
        notify_command = {
            "type": "notify_worker_returned",
            "request_id": str(uuid.uuid4()),
            "payload": {
                "worker_id": worker_id
            }
        }
        
        send_to_master(original_master, notify_command)
        
        # Remove do registro de emprestados
        with borrowed_workers_lock:
            if worker_id in borrowed_workers:
                del borrowed_workers[worker_id]
                logger.info(f"[BORROWED_WORKERS] Removido: {worker_id}, Restantes: {len(borrowed_workers)}")
    
    except Exception as e:
        logger.error(f"[ERRO AO LIBERAR] Worker {worker_id}: {e}")

# Inicializa tarefas
task_queue.put({"user": "Michel"})
task_queue.put({"user": "Julia"})
task_queue.put({"user": "Carlos"})
task_queue.put({"user":"Ana"})
task_queue.put({"user":"Pedro"})
task_queue.put({"user":"Maria"})
task_queue.put({"user":"Lucas"})
task_queue.put({"user":"Joao"})

def get_or_create_master_connection(master_id, host, port):
    """Obtém ou cria conexão com um Master vizinho (pool de conexões)"""
    conn_key = f"{host}:{port}"
    
    with master_connections_lock:
        if conn_key in master_connections:
            sock = master_connections[conn_key]
            try:
                # Verifica se a conexão ainda está ativa
                sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                return sock
            except:
                # Conexão morta, remove do pool
                del master_connections[conn_key]
    
    # Cria nova conexão
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(REQUEST_TIMEOUT)
        sock.connect((host, port))
        
        with master_connections_lock:
            master_connections[conn_key] = sock
        
        logger.info(f"[MASTER_CONNECTION] Nova conexão com {conn_key}")
        return sock
    
    except Exception as e:
        logger.error(f"[ERRO CONEXÃO] Não consegui conectar em {conn_key}: {e}")
        return None

def parse_master_from_address(address):
    """Extrai master_id a partir de endereço ip:port"""
    # Procura nos vizinhos
    for master_id, info in neighbor_masters.items():
        addr = f"{info['host']}:{info['port']}"
        if addr == address:
            return master_id
    return None

def send_to_master(master_id, message):
    """Envia mensagem para um Master vizinho"""
    if master_id not in neighbor_masters:
        logger.error(f"[ERRO] Master {master_id} não encontrado na lista de vizinhos")
        return False
    
    master_info = neighbor_masters[master_id]
    host = master_info["host"]
    port = master_info["port"]
    
    sock = get_or_create_master_connection(master_id, host, port)
    if not sock:
        return False
    
    try:
        msg_str = json.dumps(message) + "\n"
        sock.sendall(msg_str.encode())
        logger.info(f"[SEND_TO_MASTER] {master_id}: {message}")
        return True
    
    except Exception as e:
        logger.error(f"[ERRO AO ENVIAR] para {master_id}: {e}")
        # Remove conexão do pool
        with master_connections_lock:
            conn_key = f"{host}:{port}"
            if conn_key in master_connections:
                del master_connections[conn_key]
        return False

def handle_response(master_id, response_data):
    """Processa resposta de um Master"""
    msg_type = response_data.get("type")
    request_id = response_data.get("request_id")
    
    logger.info(f"[RESPONSE_FROM_{master_id}] type={msg_type}, request_id={request_id}")
    
    with pending_requests_lock:
        if request_id not in pending_requests:
            logger.warning(f"[AVISO] request_id {request_id} não encontrado")
            return
        
        pending_requests[request_id]["response_received"] = True
        pending_requests[request_id]["response_data"] = response_data
    
    if msg_type == "response_accepted":
        handle_response_accepted(response_data)
    elif msg_type == "response_rejected":
        handle_response_rejected(response_data)

def handle_response_accepted(response_data):
    """Processa resposta aceita: inicia redirecionamento de workers"""
    workers_offered = response_data.get("payload", {}).get("worker_details", [])
    logger.info(f"[RESPONSE_ACCEPTED] Recebido {len(workers_offered)} workers")
    
    for worker_detail in workers_offered:
        worker_id = worker_detail.get("id")
        worker_address = worker_detail.get("address")
        logger.info(f"[WORKER_OFFERED] {worker_id} em {worker_address}")

def handle_response_rejected(response_data):
    """Processa resposta rejeitada"""
    reason = response_data.get("payload", {}).get("reason", "unknown")
    logger.warning(f"[RESPONSE_REJECTED] reason={reason}")

def request_help():
    """Envia pedido de ajuda para um Master vizinho"""
    request_id = str(uuid.uuid4())
    
    load = current_load()
    workers_needed = max(1, load - CAPACITY)
    
    msg = {
        "type": "request_help",
        "request_id": request_id,
        "payload": {
            "master_id": MASTER_ID,
            "current_load": load,
            "capacity": CAPACITY,
            "workers_needed": workers_needed
        }
    }
    
    logger.info(f"[REQUEST_HELP] request_id={request_id}, workers_needed={workers_needed}")
    
    # Registra a requisição como pendente
    with pending_requests_lock:
        pending_requests[request_id] = {
            "master_id": None,
            "response_received": False,
            "response_data": None,
            "timestamp": time.time()
        }
    
    # Envia para todos os vizinhos em thread separada
    for master_id in neighbor_masters.keys():
        threading.Thread(
            target=send_request_help_to_master,
            args=(master_id, msg, request_id),
            daemon=True
        ).start()

def send_request_help_to_master(master_id, message, request_id):
    """Envia request_help para um master específico com timeout"""
    send_to_master(master_id, message)
    
    # Aguarda resposta com timeout
    start_time = time.time()
    while time.time() - start_time < REQUEST_TIMEOUT:
        with pending_requests_lock:
            if request_id in pending_requests:
                req_info = pending_requests[request_id]
                if req_info.get("response_received"):
                    logger.info(f"[RESPONSE_RECEIVED] de {master_id}")
                    return
        time.sleep(0.1)
    
    # Timeout
    logger.warning(f"[TIMEOUT] Nenhuma resposta de {master_id} em {REQUEST_TIMEOUT}s")
    with pending_requests_lock:
        if request_id in pending_requests:
            del pending_requests[request_id]


def handle_client(conn, addr):
    """Manipula conexões de clientes (Workers, outros Masters, etc)"""
    logger.info(f"[CLIENT_CONNECTED] {addr}")
    
    buffer = ""
    worker_id = None  # Para rastrear qual worker está usando esta conexão
    is_borrowed = False  # Se é um worker emprestado
    
    try:
        while True:
            data = conn.recv(1024).decode()
            
            if not data:
                break
            
            buffer += data
            
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                
                try:
                    payload = json.loads(message)
                    logger.debug(f"[RECEIVED] {payload}")
                    
                    msg_type = payload.get("type")
                    
                    # ==========================================
                    # REQUEST_HELP - De outro Master
                    # ==========================================
                    if msg_type == "request_help":
                        handle_request_help(conn, payload)
                    
                    # ==========================================
                    # RESPONSE_ACCEPTED / RESPONSE_REJECTED
                    # ==========================================
                    elif msg_type in ["response_accepted", "response_rejected"]:
                        handle_response("UNKNOWN", payload)  # TODO: Identificar qual master
                    
                    # ==========================================
                    # COMMAND_REDIRECT - Worker redirect
                    # ==========================================
                    elif msg_type == "command_redirect":
                        handle_command_redirect(conn, payload)
                    
                    # ==========================================
                    # REGISTER_TEMPORARY_WORKER - Worker emprestado registrando
                    # ==========================================
                    elif msg_type == "register_temporary_worker":
                        response_worker = handle_register_temporary_worker(conn, addr, payload)
                        worker_id = response_worker
                        is_borrowed = True
                        conn.sendall(
                            (json.dumps({"status": "registered"}) + "\n").encode()
                        )
                    
                    # ==========================================
                    # NOTIFY_WORKER_RETURNED
                    # ==========================================
                    elif msg_type == "notify_worker_returned":
                        handle_notify_worker_returned(payload)
                    
                    # ==========================================
                    # WORKER ALIVE (Sprint 02)
                    # ==========================================
                    elif payload.get("WORKER") == "ALIVE":
                        worker_uuid = payload.get("WORKER_UUID")
                        server_uuid = payload.get("SERVER_UUID")  # Master original (se emprestado)
                        
                        # Registra worker local
                        if not server_uuid:
                            with workers_lock:
                                workers[worker_uuid] = {"addr": addr, "conn": conn}
                            logger.info(f"[WORKER_REGISTERED] {worker_uuid} (local)")
                        else:
                            # Worker emprestado
                            with borrowed_workers_lock:
                                borrowed_workers[worker_uuid] = {
                                    "addr": addr,
                                    "conn": conn,
                                    "original_master_address": server_uuid
                                }
                            logger.info(f"[WORKER_REGISTERED] {worker_uuid} (borrowed from {server_uuid})")
                        
                        worker_id = worker_uuid
                        
                        # Responde com tarefa ou NO_TASK
                        if not task_queue.empty():
                            task = task_queue.get()
                            response = {
                                "TASK": "QUERY",
                                "USER": task["user"]
                            }
                            logger.info(f"[TASK_ASSIGNED] {worker_uuid}: {task['user']}")
                        else:
                            response = {
                                "TASK": "NO_TASK"
                            }
                            logger.info(f"[NO_TASK] para {worker_uuid}")
                        
                        conn.sendall(
                            (json.dumps(response) + "\n").encode()
                        )
                    
                    # ==========================================
                    # TASK STATUS (OK/NOK) - Sprint 02
                    # ==========================================
                    elif payload.get("STATUS") in ["OK", "NOK"]:
                        worker_uuid = payload.get("WORKER_UUID")
                        status = payload.get("STATUS")
                        
                        logger.info(f"[TASK_RESULT] {worker_uuid}: {status}")
                        
                        response = {
                            "STATUS": "ACK",
                            "WORKER_UUID": worker_uuid
                        }
                        
                        conn.sendall(
                            (json.dumps(response) + "\n").encode()
                        )
                    
                    else:
                        # Tipo desconhecido - ignora (compatibilidade com extensões futuras)
                        logger.warning(f"[UNKNOWN_TYPE] {msg_type}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"[JSON_ERROR] {e}: {message}")
    
    except Exception as e:
        logger.error(f"[ERROR] {e}")
    
    finally:
        # Cleanup
        if worker_id:
            if is_borrowed:
                with borrowed_workers_lock:
                    if worker_id in borrowed_workers:
                        del borrowed_workers[worker_id]
                        logger.info(f"[WORKER_DISCONNECTED] {worker_id} (borrowed)")
            else:
                with workers_lock:
                    if worker_id in workers:
                        del workers[worker_id]
                        logger.info(f"[WORKER_DISCONNECTED] {worker_id} (local)")
        
        conn.close()
        logger.info(f"[CONNECTION_CLOSED] {addr}")

def handle_request_help(conn, payload):
    """Processa pedido de ajuda de outro Master"""
    request_id = payload.get("request_id")
    master_id = payload.get("payload", {}).get("master_id")
    workers_needed = payload.get("payload", {}).get("workers_needed", 1)
    
    logger.info(f"[REQUEST_HELP_RECEIVED] from {master_id}, need {workers_needed} workers")
    
    available = get_available_workers()
    
    if available >= workers_needed:
        # Aceita o pedido
        response = {
            "type": "response_accepted",
            "request_id": request_id,
            "payload": {
                "workers_offered": min(available, workers_needed),
                "worker_details": [
                    {
                        "id": f"W-{MASTER_ID}-{i}",
                        "address": f"{HOST}:{PORT}"
                    }
                    for i in range(min(available, workers_needed))
                ]
            }
        }
        logger.info(f"[RESPONSE_ACCEPTED] Oferecendo {len(response['payload']['worker_details'])} workers")
    else:
        # Recusa o pedido
        reason = "high_load" if current_load() > CAPACITY else "no_workers_available"
        response = {
            "type": "response_rejected",
            "request_id": request_id,
            "payload": {
                "reason": reason
            }
        }
        logger.info(f"[RESPONSE_REJECTED] reason={reason}")
    
    conn.sendall(
        (json.dumps(response) + "\n").encode()
    )

def handle_command_redirect(conn, payload):
    """Processa comando de redirecionamento (recebido por um Worker)"""
    new_master_address = payload.get("payload", {}).get("new_master_address")
    logger.info(f"[COMMAND_REDIRECT] Redirecionando para {new_master_address}")
    # O Worker deve encerrar a conexão e conectar ao novo Master
    # Isso é tratado no lado do Worker

def handle_register_temporary_worker(conn, addr, payload):
    """Processa registro de um Worker emprestado"""
    worker_id = payload.get("payload", {}).get("worker_id")
    original_master_address = payload.get("payload", {}).get("original_master_address")
    
    logger.info(f"[REGISTER_TEMPORARY] {worker_id} from {original_master_address}")
    
    with borrowed_workers_lock:
        borrowed_workers[worker_id] = {
            "addr": addr,
            "conn": conn,
            "original_master_address": original_master_address
        }
        logger.info(f"[BORROWED_WORKERS] Registrado: {worker_id}, Total: {len(borrowed_workers)}")
    
    return worker_id

def handle_notify_worker_returned(payload):
    """Processa notificação de devolução de Worker"""
    worker_id = payload.get("payload", {}).get("worker_id")
    logger.info(f"[WORKER_RETURNED_NOTIFICATION] {worker_id}")

def monitor_connections():
    """Monitora e loga estado das conexões e workers"""
    while True:
        time.sleep(10)  # A cada 10 segundos
        
        with workers_lock:
            local_count = len(workers)
        
        with borrowed_workers_lock:
            borrowed_count = len(borrowed_workers)
        
        load = current_load()
        
        logger.info(
            f"[STATUS] Load={load}/{CAPACITY}, "
            f"Local_Workers={local_count}, "
            f"Borrowed_Workers={borrowed_count}"
        )

def start_server():
    """Inicia o servidor Master"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    
    logger.info(f"[MASTER_{MASTER_ID}] Aguardando conexões em {HOST}:{PORT}...")
    logger.info(f"[CONFIG] Capacity={CAPACITY}, Saturation_Threshold={SATURATION_THRESHOLD}, Release_Threshold={RELEASE_THRESHOLD}")
    
    # Inicia thread de monitoramento de carga
    threading.Thread(
        target=monitor_load,
        daemon=True,
        name="MonitorLoad"
    ).start()
    
    # Inicia thread de monitoramento de conexões
    threading.Thread(
        target=monitor_connections,
        daemon=True,
        name="MonitorConnections"
    ).start()

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True,
                name=f"ClientHandler-{addr}"
            ).start()
    
    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] Master recebeu sinal de interrupção")
    
    finally:
        server.close()
        logger.info("[SHUTDOWN] Servidor encerrado")

if __name__ == "__main__":
    start_server()