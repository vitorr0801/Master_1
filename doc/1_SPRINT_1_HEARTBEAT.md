# Sprint 1: Mecanismo de Heartbeat

**Data:** Sprint Inicial  
**Duração:** Primeira semana do projeto  
**Status:** ✅ Concluída

---

## Objetivo

Estabelecer a comunicação base entre Worker e Master através de **verificação periódica de disponibilidade** (heartbeat) usando mensagens JSON via TCP.

---

## Problem Statement

Para que um sistema distribuído funcione com confiabilidade, é necessário que clientes (Workers) possam verificar continuamente se seus servidores (Masters) estão ativos e respondendo. Esta Sprint implementa o mecanismo fundamental de heartbeat.

---

## Arquitetura da Sprint 1

### Componentes

```
Worker (Cliente TCP)  ←→  Master (Servidor TCP)
   │                          │
   └─ Conecta                 └─ Escuta porta 5000
   └─ Envia HEARTBEAT        └─ Recebe HEARTBEAT
   └─ Aguarda resposta       └─ Responde ALIVE
   └─ Verifica se está UP    └─ Mantém conexão
```

### Fluxo de Comunicação

```
Worker                          Master
   │                              │
   ├─ Conecta em TCP ────────────→│
   │                              │
   ├─ Envia {"TASK": "HEARTBEAT"}→│
   │                              │
   │   (Worker aguarda 5s)        │
   │                              │
   │←──── {"RESPONSE": "ALIVE"} ──┤
   │                              │
   ├─ Registra: UP                │
   │                              │
   └─ Aguarda 30s para próximo    │
                                  │
      (Ciclo se repete)
```

---

## Padrão de Mensagem - Sprint 1

### Worker → Master (Heartbeat Request)

```json
{
  "SERVER_UUID": "Master_A",
  "TASK": "HEARTBEAT"
}
```

### Master → Worker (Heartbeat Response)

```json
{
  "SERVER_UUID": "Master_A",
  "TASK": "HEARTBEAT",
  "RESPONSE": "ALIVE"
}
```

### Características

- **Formato:** JSON
- **Terminador:** Newline (`\n`) após cada mensagem
- **Timeout:** 5 segundos
- **Intervalo:** 30 segundos entre verificações
- **Port:** 5000

---

## Implementação

### Master (Servidor)

```python
import socket
import threading
import json

HOST = "0.0.0.0"
PORT = 5000

def handle_client(conn, addr):
    """Trata conexão de um cliente (Worker)"""
    buffer = ""
    
    while True:
        data = conn.recv(1024).decode()
        if not data:
            break
        
        buffer += data
        
        # Processa mensagens completas (delimitadas por \n)
        while "\n" in buffer:
            message, buffer = buffer.split("\n", 1)
            
            try:
                payload = json.loads(message)
                
                if payload.get("TASK") == "HEARTBEAT":
                    # Responde com ALIVE
                    response = {
                        "SERVER_UUID": payload.get("SERVER_UUID"),
                        "TASK": "HEARTBEAT",
                        "RESPONSE": "ALIVE"
                    }
                    conn.sendall((json.dumps(response) + "\n").encode())
                    
            except json.JSONDecodeError:
                print(f"[ERRO] JSON inválido de {addr}")
    
    conn.close()

def start_server():
    """Inicia servidor Master"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    
    print(f"[MASTER] Escutando em {HOST}:{PORT}")
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
```

### Worker (Cliente)

```python
import socket
import json
import time

MASTER_HOST = "127.0.0.1"
MASTER_PORT = 5000
MASTER_ID = "Master_A"

def send_heartbeat():
    """Envia heartbeat para Master"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 segundos de timeout
        sock.connect((MASTER_HOST, MASTER_PORT))
        
        # Prepara mensagem
        payload = {
            "SERVER_UUID": MASTER_ID,
            "TASK": "HEARTBEAT"
        }
        
        # Envia
        sock.sendall((json.dumps(payload) + "\n").encode())
        
        # Aguarda resposta
        response_data = sock.recv(1024).decode()
        response = json.loads(response_data.strip())
        
        if response.get("RESPONSE") == "ALIVE":
            print(f"[WORKER] {MASTER_ID} está UP")
            return True
        else:
            print(f"[WORKER] Resposta inesperada: {response}")
            return False
            
    except socket.timeout:
        print(f"[WORKER] Timeout: {MASTER_ID} não respondeu")
        return False
    except Exception as e:
        print(f"[WORKER] Erro: {e}")
        return False
    finally:
        sock.close()

def heartbeat_loop():
    """Loop contínuo de heartbeats"""
    while True:
        send_heartbeat()
        time.sleep(30)  # Aguarda 30 segundos

if __name__ == "__main__":
    heartbeat_loop()
```

---

## Definição de Pronto (DoD)

A entrega da Sprint 1 foi considerada concluída quando:

- ✅ Worker consegue abrir conexão TCP com Master
- ✅ Master recebe JSON e identifica comando HEARTBEAT
- ✅ Worker recebe confirmação "ALIVE" e imprime em log
- ✅ Conexão é mantida sem travar os processos
- ✅ Ciclo se repete a cada 30 segundos

---

## Testes Executados

### Teste de Conectividade

```bash
# Terminal 1: Master
python Master.py

# Terminal 2: Worker
python Worker.py

# Output esperado:
# [MASTER] Escutando em 0.0.0.0:5000
# [WORKER] Master_A está UP
# [WORKER] Master_A está UP
# ...
```

### Teste de Timeout

- Desligar Master enquanto Worker está rodando
- Worker deve reportar timeout após 5 segundos
- Worker deve tentar reconectar no próximo ciclo

### Teste de Parsing

- Enviar JSON inválido
- Master deve ignorar sem derrubar
- Continuar respondendo a mensagens válidas

---

## Decisões de Implementação

| Decisão | Justificativa |
|---------|---------------|
| TCP ao invés de UDP | Garantir entrega e ordem das mensagens |
| Delimitador `\n` | Identificar fim de mensagem em stream TCP |
| JSON | Formato padrão, legível, extensível |
| Timeout 5s | Detectar falha rapidamente |
| Intervalo 30s | Monitoramento contínuo sem overhead |

---

## Desafios e Soluções

### Desafio 1: Parsing de Stream TCP

**Problema:** TCP é um stream, não é orientado a mensagens. Múltiplos JSONs podem chegar juntos.

**Solução:** Implementar buffer com delimitador `\n`. Processar mensagens completas quando encontrar `\n`.

### Desafio 2: Timeout de Conexão

**Problema:** Worker pode ficar pendurado indefinidamente aguardando resposta.

**Solução:** Usar `socket.settimeout(5)` para abortar após 5 segundos.

### Desafio 3: Concorrência

**Problema:** Master precisa atender múltiplos Workers simultaneamente.

**Solução:** Usar threads (uma por conexão) com `ThreadingTCPServer`.

---

## Lições Aprendidas

1. **Importância da delimitação de mensagens** em protocolos TCP
2. **Timeouts são essenciais** para evitar deadlocks
3. **Threads permite escalabilidade** de conexões simultâneas
4. **JSON é versátil** e suporta extensões futuras

---

## Próximas Passos

A Sprint 2 usará a infraestrutura do heartbeat para implementar um **ciclo completo de tarefas**, onde Workers não apenas verificam se o Master está vivo, mas também solicitam trabalho e reportam resultados.

---

**Sprint Concluída:** ✅ Sim  
**Data de Conclusão:** Semana 1 do projeto
