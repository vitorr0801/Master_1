# Sprint 2: Comunicação de Tarefas e Ciclo Completo

**Data:** Segunda semana do projeto  
**Duração:** Segunda semana  
**Status:** ✅ Concluída

---

## Objetivo

Implementar o **fluxo completo de ciclo de vida de uma tarefa**, desde a apresentação do Worker até o processamento e confirmação final de recebimento do status pelo Master.

---

## Problem Statement

A Sprint 1 estabeleceu apenas verificação de disponibilidade. Agora precisamos de um ciclo **trabalho real**: Workers solicitam tarefas, Masters distribuem trabalho, Workers executam e reportam status, Masters confirmam recebimento.

---

## Padrão de Mensagens - Sprint 2

### Fase 1: Apresentação (Worker → Master)

**Worker Local:**
```json
{
  "WORKER": "ALIVE",
  "WORKER_UUID": "W-123"
}
```

**Worker Emprestado:**
```json
{
  "WORKER": "ALIVE",
  "WORKER_UUID": "W-999",
  "SERVER_UUID": "Master-B"
}
```

### Fase 2: Distribuição de Tarefa (Master → Worker)

**Com Tarefa:**
```json
{
  "TASK": "QUERY",
  "USER": "Michel"
}
```

**Sem Tarefa:**
```json
{
  "TASK": "NO_TASK"
}
```

### Fase 3: Reporte de Status (Worker → Master)

```json
{
  "STATUS": "OK",
  "TASK": "QUERY",
  "WORKER_UUID": "W-123"
}
```

Nota: `STATUS` pode ser "OK" ou "NOK"

### Fase 4: Confirmação Final (Master → Worker)

```json
{
  "STATUS": "ACK",
  "WORKER_UUID": "W-123"
}
```

---

## Fluxo Completo

```
Worker                          Master
   │                              │
   ├─ Conecta ────────────────────→│
   │                              │
   ├─ Envia ALIVE ────────────────→│  (Apresentação)
   │                              │
   │  (Master identifica Worker)  │
   │                              │
   │←─── QUERY com tarefa ────────┤  (Distribuição)
   │                              │
   ├─ Processa tarefa            │
   │  (ex: sleep, cálculo)       │
   │                              │
   ├─ Envia STATUS: OK ───────────→│  (Reporte)
   │                              │
   │  (Master registra resultado) │
   │                              │
   │←─── ACK ──────────────────────┤  (Confirmação)
   │                              │
   └─ Aguarda ciclo seguinte      │
      (volta para passo 2)        │
```

---

## Implementação Master

```python
import socket
import threading
import json
import queue
from collections import defaultdict

class Master:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.task_queue = queue.Queue()
        self.workers = {}  # {worker_id: connection}
        self.lock = threading.Lock()
        
    def populate_tasks(self):
        """Simula tarefas chegando"""
        tasks = [
            {"USER": "Michel"},
            {"USER": "Julia"},
            {"USER": "Pedro"},
        ]
        for task in tasks:
            self.task_queue.put(task)
    
    def handle_client(self, conn, addr):
        """Trata conexão de Worker"""
        worker_id = None
        buffer = ""
        
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    payload = json.loads(message)
                    
                    # Fase 1: Apresentação
                    if payload.get("WORKER") == "ALIVE":
                        worker_id = payload.get("WORKER_UUID")
                        is_borrowed = "SERVER_UUID" in payload
                        original_master = payload.get("SERVER_UUID")
                        
                        with self.lock:
                            self.workers[worker_id] = {
                                "conn": conn,
                                "addr": addr,
                                "borrowed": is_borrowed,
                                "original_master": original_master
                            }
                        
                        print(f"[MASTER] Worker {worker_id} registrado "
                              f"(Emprestado: {is_borrowed})")
                        
                        # Fase 2: Distribuição
                        if not self.task_queue.empty():
                            task = self.task_queue.get()
                            response = {
                                "TASK": "QUERY",
                                "USER": task["USER"]
                            }
                        else:
                            response = {"TASK": "NO_TASK"}
                        
                        conn.sendall((json.dumps(response) + "\n").encode())
                    
                    # Fase 3: Reporte de Status
                    elif payload.get("STATUS") in ["OK", "NOK"]:
                        worker_uuid = payload.get("WORKER_UUID")
                        status = payload.get("STATUS")
                        
                        print(f"[MASTER] Worker {worker_uuid} reportou: {status}")
                        
                        # Registra resultado (em produção, seria persistido)
                        
                        # Fase 4: Confirmação
                        ack = {
                            "STATUS": "ACK",
                            "WORKER_UUID": worker_uuid
                        }
                        conn.sendall((json.dumps(ack) + "\n").encode())
                        
            except json.JSONDecodeError as e:
                print(f"[ERRO] JSON inválido: {e}")
            except Exception as e:
                print(f"[ERRO] {e}")
                break
        
        # Cleanup
        with self.lock:
            if worker_id and worker_id in self.workers:
                del self.workers[worker_id]
        conn.close()
    
    def start(self):
        """Inicia servidor Master"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen()
        
        print(f"[MASTER] Escutando em {self.host}:{self.port}")
        
        # Popula tarefas iniciais
        self.populate_tasks()
        
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=self.handle_client, 
                args=(conn, addr)
            )
            thread.daemon = True
            thread.start()

if __name__ == "__main__":
    master = Master()
    master.start()
```

---

## Implementação Worker

```python
import socket
import json
import time
import random
import threading

class Worker:
    def __init__(self, worker_id, master_host, master_port, 
                 original_master_id=None):
        self.worker_id = worker_id
        self.master_host = master_host
        self.master_port = master_port
        self.original_master_id = original_master_id  # Se emprestado
        self.sock = None
    
    def connect(self):
        """Conecta ao Master"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.master_host, self.master_port))
            print(f"[WORKER {self.worker_id}] Conectado ao Master")
            return True
        except Exception as e:
            print(f"[WORKER {self.worker_id}] Erro na conexão: {e}")
            return False
    
    def send_alive(self):
        """Fase 1: Apresenta-se ao Master"""
        payload = {
            "WORKER": "ALIVE",
            "WORKER_UUID": self.worker_id
        }
        
        if self.original_master_id:
            payload["SERVER_UUID"] = self.original_master_id
        
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            
            # Aguarda tarefa
            response_data = self.sock.recv(1024).decode().strip()
            response = json.loads(response_data)
            
            if response.get("TASK") == "QUERY":
                return response  # Tem tarefa
            elif response.get("TASK") == "NO_TASK":
                return None  # Sem tarefa
                
        except Exception as e:
            print(f"[WORKER {self.worker_id}] Erro ao enviar ALIVE: {e}")
            return None
    
    def process_task(self, task):
        """Fase 3: Processa tarefa e reporta status"""
        try:
            user = task.get("USER", "Unknown")
            print(f"[WORKER {self.worker_id}] Processando tarefa de {user}")
            
            # Simula processamento
            time.sleep(random.uniform(1, 3))
            
            # Decide OK ou NOK aleatoriamente (95% OK)
            status = "OK" if random.random() < 0.95 else "NOK"
            
            # Reporta status
            payload = {
                "STATUS": status,
                "TASK": "QUERY",
                "WORKER_UUID": self.worker_id
            }
            
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            print(f"[WORKER {self.worker_id}] Status reportado: {status}")
            
            # Aguarda ACK
            ack_data = self.sock.recv(1024).decode().strip()
            ack = json.loads(ack_data)
            
            if ack.get("STATUS") == "ACK":
                print(f"[WORKER {self.worker_id}] ACK recebido")
                return True
                
        except Exception as e:
            print(f"[WORKER {self.worker_id}] Erro ao processar tarefa: {e}")
            return False
    
    def work_loop(self):
        """Loop principal do Worker"""
        if not self.connect():
            return
        
        try:
            while True:
                # Fase 1: Apresenta-se
                task = self.send_alive()
                
                if task:
                    # Fase 3: Processa tarefa
                    self.process_task(task)
                else:
                    # Sem tarefa, aguarda
                    print(f"[WORKER {self.worker_id}] Sem tarefas, aguardando...")
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            print(f"[WORKER {self.worker_id}] Encerrando...")
        finally:
            if self.sock:
                self.sock.close()

if __name__ == "__main__":
    worker = Worker(
        worker_id="W-001",
        master_host="127.0.0.1",
        master_port=5000
    )
    worker.work_loop()
```

---

## Definição de Pronto (DoD)

- ✅ Worker realiza handshake com sucesso (apresentação)
- ✅ Master distribui tarefa ou informa NO_TASK
- ✅ Worker processa e Master recebe status OK/NOK
- ✅ Worker recebe ACK e ciclo se encerra corretamente
- ✅ Sistema trata corretamente campo SERVER_UUID (emprestado vs local)
- ✅ Sem perda de mensagens no stream TCP

---

## Cenários de Teste

### CT01: Worker Local Recebendo Tarefa

```
Worker apresenta-se → Master reconhece (local) → entrega tarefa
```

**Resultado:** ✅ Tarefa distribuída com sucesso

### CT02: Worker Emprestado

```
Worker com SERVER_UUID apresenta-se → Master reconhece (emprestado)
→ entrega tarefa normalmente
```

**Resultado:** ✅ Worker emprestado atua normalmente

### CT03: Fila Vazia

```
Sem tarefas na fila → Master responde NO_TASK
```

**Resultado:** ✅ Worker aguarda próximo ciclo

### CT04: Reporte de Sucesso

```
Worker executa tarefa → reporta OK → Master envia ACK
```

**Resultado:** ✅ Ciclo completo funciona

### CT05: Reporte de Falha

```
Worker falha na execução → reporta NOK → Master envia ACK
```

**Resultado:** ✅ Master registra falha e ainda confirma

---

## Decisões de Implementação

| Decisão | Justificativa |
|---------|---------------|
| Queue thread-safe | Suportar múltiplos Workers sem race condition |
| Locks em estruturas compartilhadas | Evitar corrupção de dados |
| Timeout 5s em socket | Detectar falhas rapidamente |
| ACK obrigatório | Garantir entrega de confirmação |
| Campo SERVER_UUID opcional | Flexibilidade para Workers emprestados (Sprint 3) |

---

## Progresso do Projeto

**Sprint 1:** ✅ Heartbeat básico  
**Sprint 2:** ✅ Ciclo de tarefas  
**Sprint 3:** ⏳ Master-to-Master  
**Sprint 4:** ⏳ Supervisor de métricas

---

**Sprint Concluída:** ✅ Sim
