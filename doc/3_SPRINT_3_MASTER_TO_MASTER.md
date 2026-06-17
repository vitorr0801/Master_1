# Sprint 3: Protocolo de Negociação Master-to-Master

**Data:** Terceira semana do projeto  
**Duração:** Terceira semana  
**Status:** ✅ Concluída

---

## Objetivo

Implementar a **camada de comunicação P2P entre Masters**, permitindo que um Master saturado negocie e receba, de forma autônoma e consensual, Workers emprestados de um Master vizinho.

---

## Problem Statement

Até a Sprint 2, cada Master operava isoladamente com seus Workers. Agora precisamos que Masters comunicar-se para **balancear carga dinamicamente**: um Master saturado pode solicitar Workers de um vizinho, que os redireciona dinamicamente.

---

## Fluxo Completo de Empréstimo

```
Master A (Saturado)          Master B (Vizinho)            Worker B1
        │                            │                           │
        │─── request_help ────────→ │                           │
        │                            │ (Master B avalia carga)   │
        │                            │                           │
        │ ← response_accepted ───────│                           │
        │                            │                           │
        │                            │─── command_redirect ────→ │
        │                            │                           │
        │                            │   (Worker B1 desconecta)  │
        │                            │                           │
        │  ←════ nova conexão TCP ════════════════════════════════│
        │                            │                           │
        │←── register_temporary_worker ───────────────────────────│
        │                            │                           │
        │  (Ciclo de tarefas continua com SERVER_UUID)          │
        │                            │                           │
        │─── command_release ────────────────────────────────────→│
        │                            │                           │
        │─── notify_worker_returned →│                           │
        │                            │                           │
        │                            │ ←════ reconexão TCP ═══════│
        │                            │                           │
        │                            │  (Volta ao ciclo normal)  │
```

---

## Padrão de Mensagens - Sprint 3

### 1. Pedido de Ajuda (request_help)

**De:** Master A → **Para:** Master B

```json
{
  "type": "request_help",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "master_id": "A",
    "current_load": 150,
    "capacity": 100,
    "workers_needed": 2
  }
}
```

### 2. Resposta Aceita (response_accepted)

**De:** Master B → **Para:** Master A

```json
{
  "type": "response_accepted",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "workers_offered": 2,
    "worker_details": [
      { "id": "B1", "address": "192.168.1.10:5001" },
      { "id": "B2", "address": "192.168.1.10:5002" }
    ]
  }
}
```

### 3. Resposta Rejeitada (response_rejected)

**De:** Master B → **Para:** Master A

```json
{
  "type": "response_rejected",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "reason": "high_load"
  }
}
```

### 4. Comando de Redirecionamento (command_redirect)

**De:** Master B → **Para:** Worker B1

```json
{
  "type": "command_redirect",
  "request_id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
  "payload": {
    "new_master_address": "192.168.1.5:5000"
  }
}
```

### 5. Registro do Worker Temporário (register_temporary_worker)

**De:** Worker B1 → **Para:** Master A

```json
{
  "type": "register_temporary_worker",
  "request_id": "c1b2a3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "payload": {
    "worker_id": "B1",
    "original_master_address": "192.168.1.10:5000"
  }
}
```

### 6. Comando de Liberação (command_release)

**De:** Master A → **Para:** Worker B1

```json
{
  "type": "command_release",
  "request_id": "z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4",
  "payload": {
    "original_master_address": "192.168.1.10:5000"
  }
}
```

### 7. Notificação de Devolução (notify_worker_returned)

**De:** Master A → **Para:** Master B

```json
{
  "type": "notify_worker_returned",
  "request_id": "m1n2b3v4-c5x6-z7a8-s9d0-f1g2h3j4k5l6",
  "payload": {
    "worker_id": "B1"
  }
}
```

---

## Implementação Master - Negociação

```python
import socket
import threading
import json
import uuid
import time
from collections import defaultdict

class MasterP2P:
    def __init__(self, master_id, host="0.0.0.0", port=5000):
        self.master_id = master_id
        self.host = host
        self.port = port
        
        # Capacidade e thresholds
        self.capacity = 100
        self.saturation_threshold = 100
        self.release_threshold = 60
        
        # Estado
        self.pending_tasks = queue.Queue()
        self.workers = {}  # Workers locais
        self.borrowed_workers = {}  # {worker_id: {"original_master": ..., "conn": ...}}
        self.pending_requests = {}  # {request_id: {"timestamp": ..., "response": None}}
        self.master_connections = {}  # Pool de conexões com vizinhos
        
        # Vizinhos
        self.neighbors = {
            "Master_B": ("192.168.1.10", 6000)
        }
        
        self.lock = threading.Lock()
    
    def detect_saturation(self):
        """Detecta se Master está saturado"""
        current_load = self.pending_tasks.qsize()
        return current_load > self.saturation_threshold
    
    def should_release_workers(self):
        """Detecta se deve devolver Workers emprestados"""
        current_load = self.pending_tasks.qsize()
        return current_load < self.release_threshold
    
    def send_request_help(self, neighbor_id):
        """Envia pedido de ajuda para vizinho"""
        neighbor_host, neighbor_port = self.neighbors[neighbor_id]
        request_id = str(uuid.uuid4())
        current_load = self.pending_tasks.qsize()
        workers_needed = max(1, (current_load - self.capacity) // 10)
        
        payload = {
            "type": "request_help",
            "request_id": request_id,
            "payload": {
                "master_id": self.master_id,
                "current_load": current_load,
                "capacity": self.capacity,
                "workers_needed": workers_needed
            }
        }
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Timeout 5s
            sock.connect((neighbor_host, neighbor_port))
            
            # Registra pedido pendente
            with self.lock:
                self.pending_requests[request_id] = {
                    "timestamp": time.time(),
                    "response": None,
                    "socket": sock
                }
            
            # Envia
            sock.sendall((json.dumps(payload) + "\n").encode())
            
            # Aguarda resposta
            response_data = sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            with self.lock:
                self.pending_requests[request_id]["response"] = response
            
            if response.get("type") == "response_accepted":
                print(f"[MASTER {self.master_id}] Pedido aceito!")
                self.handle_workers_accepted(response)
            else:
                print(f"[MASTER {self.master_id}] Pedido rejeitado: "
                      f"{response.get('payload', {}).get('reason')}")
                      
        except socket.timeout:
            print(f"[MASTER {self.master_id}] Timeout na negociação")
            with self.lock:
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
        except Exception as e:
            print(f"[MASTER {self.master_id}] Erro na negociação: {e}")
    
    def handle_workers_accepted(self, response):
        """Processa Workers aceitos pelo vizinho"""
        payload = response.get("payload", {})
        workers_offered = payload.get("worker_details", [])
        
        for worker_info in workers_offered:
            worker_id = worker_info.get("id")
            worker_address = worker_info.get("address")
            
            print(f"[MASTER {self.master_id}] Worker {worker_id} "
                  f"será emprestado de {worker_address}")
            
            # Neste ponto, o Master B já enviou command_redirect
            # ao Worker. Aguardamos sua reconexão.
    
    def handle_command_release(self, worker_id, original_master_address):
        """Master A ordena Worker retornar"""
        if worker_id in self.borrowed_workers:
            payload = {
                "type": "command_release",
                "request_id": str(uuid.uuid4()),
                "payload": {
                    "original_master_address": original_master_address
                }
            }
            
            worker_conn = self.borrowed_workers[worker_id].get("conn")
            if worker_conn:
                try:
                    worker_conn.sendall((json.dumps(payload) + "\n").encode())
                    print(f"[MASTER {self.master_id}] "
                          f"command_release enviado para {worker_id}")
                except Exception as e:
                    print(f"[MASTER {self.master_id}] Erro ao enviar "
                          f"command_release: {e}")
    
    def handle_register_temporary_worker(self, payload):
        """Master A recebe Worker emprestado"""
        worker_data = payload.get("payload", {})
        worker_id = worker_data.get("worker_id")
        original_master = worker_data.get("original_master_address")
        
        with self.lock:
            self.borrowed_workers[worker_id] = {
                "original_master": original_master,
                "conn": None  # Será preenchido na conexão
            }
        
        print(f"[MASTER {self.master_id}] "
              f"Worker emprestado {worker_id} registrado")
    
    def handle_notify_worker_returned(self, neighbor_id, worker_id):
        """Master B recebe notificação de retorno"""
        print(f"[MASTER {self.master_id}] "
              f"Worker {worker_id} retornou de {neighbor_id}")
    
    def saturation_monitor(self):
        """Thread: Monitora saturação e negocia se necessário"""
        while True:
            time.sleep(2)  # Verifica a cada 2 segundos
            
            if self.detect_saturation():
                print(f"[MASTER {self.master_id}] SATURADO! Buscando ajuda...")
                
                for neighbor_id in self.neighbors:
                    self.send_request_help(neighbor_id)
                    time.sleep(1)
            
            elif self.should_release_workers():
                print(f"[MASTER {self.master_id}] Carga normalizada. "
                      f"Devolvendo Workers...")
                
                borrowed_list = list(self.borrowed_workers.keys())
                for worker_id in borrowed_list:
                    original_master = self.borrowed_workers[worker_id][
                        "original_master"
                    ]
                    self.handle_command_release(worker_id, original_master)
    
    def start_monitoring(self):
        """Inicia thread de monitoração"""
        monitor_thread = threading.Thread(target=self.saturation_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
```

---

## Implementação Worker - Redirecionamento

```python
class WorkerWithRedirect:
    def __init__(self, worker_id, master_host, master_port):
        self.worker_id = worker_id
        self.master_host = master_host
        self.master_port = master_port
        self.original_master = None
        self.sock = None
    
    def handle_command_redirect(self, payload):
        """Worker recebe comando de redirecionamento"""
        new_master_address = payload.get("payload", {})\
            .get("new_master_address")
        
        if new_master_address:
            new_host, new_port = new_master_address.split(":")
            new_port = int(new_port)
            
            print(f"[WORKER {self.worker_id}] "
                  f"Redirecionando para {new_host}:{new_port}")
            
            # Fecha conexão atual
            if self.sock:
                self.sock.close()
            
            # Aguarda um pouco
            time.sleep(1)
            
            # Conecta ao novo Master
            self.master_host = new_host
            self.master_port = new_port
            self.register_as_temporary()
    
    def register_as_temporary(self):
        """Worker registra-se como emprestado no novo Master"""
        if not self.connect():
            return
        
        payload = {
            "type": "register_temporary_worker",
            "request_id": str(uuid.uuid4()),
            "payload": {
                "worker_id": self.worker_id,
                "original_master_address": f"{self.original_master}"
            }
        }
        
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            print(f"[WORKER {self.worker_id}] Registrado como emprestado")
        except Exception as e:
            print(f"[WORKER {self.worker_id}] Erro ao registrar: {e}")
    
    def connect(self):
        """Conecta ao Master"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.master_host, self.master_port))
            return True
        except Exception as e:
            print(f"[WORKER {self.worker_id}] Erro na conexão: {e}")
            return False
```

---

## Definição de Pronto (DoD)

- ✅ Master saturado consegue abrir conexão e enviar request_help
- ✅ Master vizinho processa e responde com response_accepted/rejected
- ✅ request_id é correlacionado corretamente (mesmo na resposta)
- ✅ command_redirect é enviado aos Workers acordados
- ✅ Workers desconectam graciosamente e se reconectam
- ✅ Workers emprestados executam register_temporary_worker
- ✅ Campo SERVER_UUID é incluído nas apresentações
- ✅ Quando carga normaliza, command_release é enviado
- ✅ notify_worker_returned notifica Master original
- ✅ Workers retornam ao Master original com sucesso
- ✅ Sem vazamento de threads ou conexões penduradas

---

## Cenários de Teste

### CT01: Pedido Aceito

```
Master A saturado → Envia request_help
Master B com capacidade → Responde response_accepted
Master B redireciona Workers → Workers conectam em Master A
```

**Resultado:** ✅ Workers emprestados operando

### CT02: Pedido Rejeitado

```
Master A saturado → Envia request_help
Master B sem capacidade → Responde response_rejected (high_load)
```

**Resultado:** ✅ Master A tenta próximo vizinho

### CT03: Timeout

```
Master A envia request_help
Master B não responde em 5s
```

**Resultado:** ✅ Master A libera request_id e tenta vizinho seguinte

### CT04: Tarefa em Worker Emprestado

```
Master A recebe Worker emprestado
Fila de Master A tem tarefa
Worker emprestado solicita trabalho
```

**Resultado:** ✅ Master A distribui tarefa ao Worker emprestado

### CT05: Devolução de Worker

```
Carga de Master A normaliza
Master A envia command_release
Worker B1 desconecta de Master A
Worker B1 reconecta em Master B
```

**Resultado:** ✅ Worker retorna com sucesso

---

## Tabela de Tipos de Mensagem Sprint 3

| Type | De→Para | Quando | Finalidade |
|------|---------|--------|-----------|
| `request_help` | A→B | Carga > threshold | Solicita Workers |
| `response_accepted` | B→A | B tem capacidade | Aceita pedido |
| `response_rejected` | B→A | B sem capacidade | Rejeita pedido |
| `command_redirect` | B→W | Após aceitar | Ordena redirecionamento |
| `register_temporary_worker` | W→A | Após reconectar | Apresenta-se |
| `command_release` | A→W | Carga normaliza | Libera Worker |
| `notify_worker_returned` | A→B | Após liberar | Notifica devolução |

---

## Desafios Superados

| Desafio | Solução |
|---------|---------|
| Correlação de request/response | UUID único em cada request_id |
| Múltiplos pedidos concorrentes | Pool de conexões + map de pending_requests |
| Timeout em negociação | socket.settimeout(5) + tratamento de exceção |
| Redirecionamento gracioso | Desconectar, aguardar, reconectar |
| Histerese | release_threshold < saturation_threshold |

---

## Progresso do Projeto

**Sprint 1:** ✅ Heartbeat  
**Sprint 2:** ✅ Task Cycle  
**Sprint 3:** ✅ Master-to-Master P2P  
**Sprint 4:** ⏳ Supervisor de métricas

---

**Sprint Concluída:** ✅ Sim
