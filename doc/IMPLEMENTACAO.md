# Implementação Técnica

---

## Stack de Tecnologias

### Linguagem e Runtime

- **Linguagem:** Python 3.7+
- **Runtime:** CPython
- **Executores:** ThreadPoolExecutor (stdlib)

### Bibliotecas Principais

```python
# Rede
socket      # TCP/IP nativo
ssl         # TLS/SSL para Supervisor
ssl         # TLS/SSL para Supervisor

# Serialização
json        # Formato de mensagens

# Concorrência
threading   # Threads (1 por conexão)
queue       # Filas thread-safe

# Monitoramento
psutil      # Coleta de métricas do sistema
uuid        # Geração de UUIDs
time        # Timing e delays
datetime    # Timestamps ISO-8601

# Logging
logging     # Logs estruturados
```

---

## Estrutura de Arquivos

```
Master_1/
├── Master.py                    # Master base (Sprint 1-2)
├── master_sprint3.py            # Master com M2M (Sprint 3)
├── master_sprint4.py            # Master com Supervisor (Sprint 4)
│
├── Worker.py                    # Worker base
├── worker_sprint2.py            # Worker com tarefas (Sprint 2)
├── worker_sprint4.py            # Worker com redirecionamento (Sprint 4)
│
├── protocol.py                  # Definições de payloads
├── network.py                   # Utilitários de rede
├── config.py                    # Configurações globais
│
├── test_*.py                    # Suite de testes
│
├── doc/                         # Documentação
│   ├── README.md
│   ├── 1_SPRINT_1_HEARTBEAT.md
│   ├── 2_SPRINT_2_TASK_CYCLE.md
│   ├── 3_SPRINT_3_MASTER_TO_MASTER.md
│   ├── 4_SPRINT_4_SUPERVISOR.md
│   ├── ARQUITETURA.md
│   ├── PROTOCOLO_DEFINIDO.md
│   ├── IMPLEMENTACAO.md
│   ├── TESTES.md
│   └── CONCLUSAO.md
│
└── Imagens/                     # Diagramas
    ├── Imagem1.png              # Heartbeat
    ├── Imagem2.png              # Task Cycle
    ├── Imagem3.png              # M2M
    └── Imagem4.png              # Supervisor
```

---

## Módulos Principais

### protocol.py

Centraliza todas as definições de mensagens.

```python
# Sprint 1
def heartbeat(server_uuid: str) -> dict
def heartbeat_alive(server_uuid: str) -> dict

# Sprint 2
def worker_alive(worker_uuid: str, original_master_uuid: str = None) -> dict
def task_query(user: str) -> dict
def task_no_task() -> dict
def task_status(status: str, worker_uuid: str) -> dict
def task_ack(worker_uuid: str) -> dict

# Sprint 3
def m2m_request_help(...) -> dict
def m2m_response_accepted(...) -> dict
def m2m_response_rejected(...) -> dict
def m2m_command_redirect(...) -> dict
def m2m_register_temporary_worker(...) -> dict
def m2m_command_release(...) -> dict
def m2m_notify_worker_returned(...) -> dict

# Encoding/Decoding
def encode_message(data: dict) -> bytes
def decode_message(data: bytes) -> dict
```

### network.py

Utilitários de rede reutilizáveis.

```python
class TCPServer:
    def __init__(self, host: str, port: int, handler: callable)
    def start(self)
    def stop(self)

class TCPClient:
    def __init__(self, host: str, port: int, timeout: int = 5)
    def connect(self)
    def send(self, data: dict)
    def receive(self) -> dict
    def close(self)

class ConnectionPool:
    def __init__(self, max_connections: int = 100)
    def get(self, key: str) -> TCPClient
    def put(self, key: str, conn: TCPClient)
    def remove(self, key: str)
```

### config.py

Configurações centralizadas.

```python
# Identidade
MASTER_ID = "michel_1"
WORKER_ID_PREFIX = "W-"

# Rede
MASTER_HOST = "0.0.0.0"
MASTER_PORT = 5000
SUPERVISOR_HOST = "nuted-ia.dev"
SUPERVISOR_PORT = 443

# Timing
HEARTBEAT_INTERVAL = 30      # segundos
HEARTBEAT_TIMEOUT = 5        # segundos
M2M_TIMEOUT = 5              # segundos
REPORT_INTERVAL = 10         # segundos

# Capacidade
CAPACITY = 100               # Max tarefas pendentes
SATURATION_THRESHOLD = 100   # Quando pedir ajuda
RELEASE_THRESHOLD = 60       # Quando devolver Workers

# Logging
LOG_LEVEL = logging.INFO
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
```

---

## Classes Principais

### Classe MasterP2P

**Responsabilidades:**
- Gerenciar Farm
- Distribui tarefas
- Monitorar saturação
- Negociar com vizinhos
- Coletar métricas

**Estrutura:**

```python
class MasterP2P:
    def __init__(self, master_id, host, port):
        # Identidade
        self.master_id = master_id
        self.host = host
        self.port = port
        
        # Estado
        self.workers = {}                  # Workers locais
        self.borrowed_workers = {}         # Workers emprestados
        self.pending_tasks = queue.Queue() # Fila de tarefas
        
        # Config
        self.capacity = CAPACITY
        self.saturation_threshold = SATURATION_THRESHOLD
        self.release_threshold = RELEASE_THRESHOLD
        
        # Comunicação
        self.neighbors = {}                # Masters vizinhos
        self.master_connections = {}       # Pool M2M
        self.pending_requests = {}         # Requests em aberto
        
        # Métricas
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Sincronização
        self.lock = threading.RLock()
    
    def handle_worker_connection(self, conn, addr):
        """Thread: Trata conexão de Worker"""
        
    def saturation_monitor(self):
        """Thread: Monitora e negocia"""
        
    def metrics_collector(self):
        """Thread: Coleta e envia relatórios"""
        
    def detect_saturation(self) -> bool:
        """Verifica se está saturado"""
        
    def send_request_help(self, neighbor_id: str):
        """Envia pedido para vizinho"""
```

### Classe WorkerWithRedirect

**Responsabilidades:**
- Conectar ao Master
- Solicitar tarefas
- Processar tarefas
- Reportar status
- Suportar redirecionamento

**Estrutura:**

```python
class WorkerWithRedirect:
    def __init__(self, worker_id, master_host, master_port):
        self.worker_id = worker_id
        self.master_host = master_host
        self.master_port = master_port
        self.original_master = None
        self.sock = None
    
    def connect(self) -> bool:
        """Conecta ao Master"""
        
    def send_alive(self) -> dict:
        """Fase 1: Apresentação"""
        
    def process_task(self, task: dict) -> bool:
        """Fase 2-3: Processa e reporta"""
        
    def handle_command_redirect(self, payload: dict):
        """Processa redirecionamento"""
        
    def work_loop(self):
        """Loop principal"""
```

### Classe SupervisorClient

**Responsabilidades:**
- Coletar métricas
- Construir relatórios
- Enviar para Supervisor
- Gerenciar conexão TLS

**Estrutura:**

```python
class SupervisorClient:
    def __init__(self, server_uuid, master_id):
        self.server_uuid = server_uuid
        self.master_id = master_id
    
    def collect_system_metrics(self) -> dict:
        """Coleta CPU, memória, disco"""
        
    def collect_farm_state(self, master) -> dict:
        """Coleta estado da farm"""
        
    def build_performance_report(self, master) -> dict:
        """Constrói relatório completo"""
        
    def send_report(self, master):
        """Envia via TLS ao Supervisor"""
        
    def start_reporting(self, master, interval=10):
        """Inicia thread de coleta periódica"""
```

---

## Padrões de Design

### 1. Observer Pattern (Monitoramento)

```python
# Master monitora saturação
class SaturationObserver:
    def on_saturation(self, master):
        """Dispara negociação"""
        pass

# Implementações
class NegotiationObserver(SaturationObserver):
    def on_saturation(self, master):
        self.request_help(master)
```

### 2. Connection Pool Pattern (M2M)

```python
class ConnectionPool:
    def get_or_create(self, neighbor_id):
        if neighbor_id not in self.connections:
            self.connections[neighbor_id] = TCPClient(...)
        return self.connections[neighbor_id]
```

### 3. Producer-Consumer Pattern (Tarefas)

```python
# Producer: Simula chegada de tarefas
while True:
    task = generate_task()
    task_queue.put(task)

# Consumer: Master distribui tarefas
while True:
    task = task_queue.get(timeout=1)
    if task:
        send_to_worker(task)
```

### 4. Thread-per-Connection Pattern (Workers)

```python
server = TCPServer(host, port, handler_callback)
while True:
    conn, addr = server.accept()
    thread = Thread(target=handler_callback, args=(conn, addr))
    thread.start()
```

---

## Concorrência

### Threads por Component

```python
# Master
Main Thread
├─ TCPServer.accept() - bloqueante
│  └─ Handler Threads (N)
│     └─ Process message from Worker
│
Monitor Thread
├─ Timer: 2s
├─ Check saturation
└─ Send request_help if needed

Reporting Thread
├─ Timer: 10s
├─ Collect metrics
└─ Send to Supervisor

# Worker
Main Thread
├─ Connect to Master
└─ work_loop()
   ├─ send_alive()
   ├─ receive_task()
   ├─ process_task()
   └─ send_status()
```

### Sincronização

**Estruturas thread-safe:**

```python
# Queue (thread-safe nativa)
self.pending_tasks = queue.Queue()

# RLock para dicts
self.lock = threading.RLock()
with self.lock:
    self.workers[worker_id] = ...

# Timeout em locks (evitar deadlock)
if self.lock.acquire(timeout=1):
    try:
        # operação
    finally:
        self.lock.release()
else:
    log.warning("Lock timeout")
```

---

## Tratamento de Erros

### JSON Parsing

```python
try:
    message = json.loads(data)
except json.JSONDecodeError as e:
    log.error(f"JSON inválido: {e}")
    # Descartar mensagem, continuar
    return
```

### Network Errors

```python
try:
    sock.connect((host, port))
except socket.timeout:
    log.error("Connection timeout")
    return False
except Exception as e:
    log.error(f"Connection failed: {e}")
    return False
finally:
    if sock:
        sock.close()
```

### Validation Errors

```python
def validate_payload(payload, required_fields):
    missing = [f for f in required_fields if f not in payload]
    if missing:
        log.error(f"Missing fields: {missing}")
        raise ValueError(f"Missing: {missing}")
```

---

## Performance Considerations

### Otimizações

1. **Connection Pooling**
   - Reutilizar conexões M2M
   - Reduzir overhead de TCP handshake

2. **Buffer Size**
   - 1024 bytes por recv (balanço entre latência e throughput)

3. **Task Queue**
   - Usar Queue nativa (thread-safe e otimizada)

4. **Logging**
   - Usar logging (assincrono) ao invés de print()

5. **Timeouts**
   - Prevenir threads penduradas

### Limites Observados

```
Por Master (single instance):
├─ Workers: ~500 (FD limit)
├─ TPS: ~100 (CPU-bound)
├─ Latência: ~50ms (network)

Cluster (múltiplos Masters):
├─ Total Workers: ~50k
├─ Total TPS: ~10k
└─ Observabilidade: Real-time (<10s)
```

---

## Logging

### Estratégia

```python
import logging

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)

logger = logging.getLogger(__name__)

# Uso
logger.info("[MASTER] Aguardando conexões em %s:%d", HOST, PORT)
logger.debug("[WORKER] Enviando ALIVE com UUID %s", worker_uuid)
logger.warning("[MASTER] Saturado: carga %d > capacidade %d", load, cap)
logger.error("[ERROR] JSON inválido: %s", e)
```

### Eventos Registrados

```
[INFO] Master iniciado
[INFO] Worker conectado
[INFO] Tarefa distribuída
[INFO] Status recebido
[WARNING] Saturação detectada
[WARNING] Timeout na negociação
[ERROR] JSON inválido
[ERROR] Conexão falhou
[DEBUG] Payload recebido: {...}
```

---

## Deployment

### Variáveis de Ambiente

```bash
export MASTER_ID="michel_1"
export MASTER_PORT=5000
export SUPERVISOR_HOST="nuted-ia.dev"
export SUPERVISOR_PORT=443
```

### Inicialização

```bash
# Terminal 1: Master A
python master_sprint4.py

# Terminal 2: Master B
MASTER_ID=michel_2 MASTER_PORT=6000 python master_sprint4.py

# Terminal 3-N: Workers
python worker_sprint4.py
```

### Monitoramento

```bash
# Ver logs em tempo real
tail -f master.log

# Ver conexões ativas
netstat -an | grep ESTABLISHED

# Ver uso de memória
ps aux | grep python
```

---

**Versão da Implementação:** 1.0  
**Última Atualização:** 2026-06-17  
**Status:** Produção
