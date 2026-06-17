# Arquitetura Completa do Sistema

---

## Visão Geral Arquitetônica

```
┌─────────────────────────────────────────────────────────────────┐
│                  CLUSTER DISTRIBUÍDO P2P                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────┐      ┌──────────────────────────┐ │
│  │      MASTER A            │◄────►│      MASTER B            │ │
│  │  ┌────────────────────┐  │      │  ┌────────────────────┐ │ │
│  │  │  Server Socket     │  │      │  │  Server Socket     │ │ │
│  │  │  (5000)            │  │      │  │  (6000)            │ │ │
│  │  └────────────────────┘  │      │  └────────────────────┘ │ │
│  │  ┌────────────────────┐  │      │  ┌────────────────────┐ │ │
│  │  │  Farm A            │  │      │  │  Farm B            │ │ │
│  │  │ ┌─W1─┐ ┌─W2─┐     │  │      │  │ ┌─W3─┐ ┌─W4─┐     │ │ │
│  │  │ └───┘ └───┘     │  │      │  │ └───┘ └───┘     │ │ │
│  │  └────────────────────┘  │      │  └────────────────────┘ │ │
│  │  ┌────────────────────┐  │      │  ┌────────────────────┐ │ │
│  │  │  Task Queue        │  │      │  │  Task Queue        │ │ │
│  │  │  ┌──────────┐      │  │      │  │  ┌──────────┐      │ │ │
│  │  │  │ Tarefas  │      │  │      │  │  │ Tarefas  │      │ │ │
│  │  │  └──────────┘      │  │      │  │  └──────────┘      │ │ │
│  │  └────────────────────┘  │      │  └────────────────────┘ │ │
│  │  ┌────────────────────┐  │      │  ┌────────────────────┐ │ │
│  │  │  Monitoramento     │  │      │  │  Monitoramento     │ │ │
│  │  │  - Saturação       │  │      │  │  - Saturação       │ │ │
│  │  │  - Carga           │  │      │  │  - Carga           │ │ │
│  │  └────────────────────┘  │      │  └────────────────────┘ │ │
│  └──────────────────────────┘      └──────────────────────────┘ │
│           │              │ P2P via Socket TCP │             │   │
│           │              └─────────────────────┘             │   │
│           │                                                   │   │
│           └───────────────────────┬─────────────────────────┘   │
│                                   │                              │
│                           (TLS/TCP 443)                          │
│                                   │                              │
└───────────────────────────────────┼──────────────────────────────┘
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │   Supervisor         │
                        │   nuted-ia.dev:443   │
                        │                      │
                        │  - Recebe relatórios │
                        │  - Agrega métricas   │
                        │  - Armazena histórico│
                        └──────────┬───────────┘
                                   │
                              (HTTP GET)
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Dashboard Web      │
                        │   (Browser)          │
                        │                      │
                        │ - Topologia cluster  │
                        │ - Gráficos CPU/MEM   │
                        │ - Status Workers     │
                        │ - Filas tarefas      │
                        │ - Alertas             │
                        └──────────────────────┘
```

---

## Componentes

### 1. Master Node (master_sprint4.py)

**Responsabilidades:**
- Gerenciar Farm de Workers (locais e emprestados)
- Escutar conexões de Workers (servidor TCP)
- Distribuir tarefas para Workers ociosos
- Monitorar carga e detectar saturação
- Negociar empréstimo de Workers com vizinhos
- Coletar e enviar métricas ao Supervisor

**Estrutura de Dados:**

```python
class MasterP2P:
    # Identidade
    master_id: str
    host: str
    port: int
    
    # Capacidade e limiares
    capacity: int                # Max tarefas
    saturation_threshold: int    # Quando pedir ajuda
    release_threshold: int       # Quando devolver Workers
    
    # Estado
    workers: dict                # Workers locais
    borrowed_workers: dict       # Workers emprestados
    pending_tasks: queue.Queue   # Tarefas aguardando
    
    # Comunicação M2M
    neighbors: dict              # Masters vizinhos
    master_connections: dict     # Pool de conexões
    pending_requests: dict       # Requests em aberto
    
    # Métricas
    tasks_completed_count: int
    tasks_failed_count: int
```

**Thread Principal:**
1. Servidor TCP escutando conexões
2. Processar mensagens de Workers
3. Monitor de saturação (a cada 2s)
4. Coleta e envio de métricas (a cada 10s)

### 2. Worker Node (worker_sprint4.py)

**Responsabilidades:**
- Conectar ao Master (cliente TCP)
- Solicitar tarefas periodicamente
- Processar tarefas (simular trabalho)
- Reportar status de conclusão
- Suportar redirecionamento para outro Master

**Fluxo de Vida:**

```
┌────────────┐
│   Iníciar  │
└─────┬──────┘
      │
      ▼
┌─────────────────┐
│ Conectar Master │
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Enviar ALIVE         │ (Apresentação)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐     ┌──────────────────┐
│ Receber QUERY/NO_TASK│────►│ Processar/Aguardar│
└────────┬─────────────┘     └──────────────────┘
         │
         ▼
┌──────────────────────┐
│ Enviar STATUS        │ (OK/NOK)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Receber ACK          │
└────────┬─────────────┘
         │
         ▼
    (Loop)
```

### 3. Protocol Layer

**Estrutura de Mensagens:**

```
Worker-Master (Sprint 1-2):
├─ HEARTBEAT: {"SERVER_UUID": "...", "TASK": "HEARTBEAT"}
├─ ALIVE: {"WORKER": "ALIVE", "WORKER_UUID": "..."}
├─ QUERY: {"TASK": "QUERY", "USER": "..."}
├─ NO_TASK: {"TASK": "NO_TASK"}
├─ STATUS: {"STATUS": "OK|NOK", "TASK": "QUERY", "WORKER_UUID": "..."}
└─ ACK: {"STATUS": "ACK", "WORKER_UUID": "..."}

Master-Master (Sprint 3):
├─ request_help: {"type": "request_help", "request_id": "...", "payload": {...}}
├─ response_accepted: {"type": "response_accepted", "request_id": "...", ...}
├─ response_rejected: {"type": "response_rejected", "request_id": "...", ...}
├─ command_redirect: {"type": "command_redirect", "request_id": "...", ...}
├─ register_temporary_worker: {"type": "register_temporary_worker", "request_id": "...", ...}
├─ command_release: {"type": "command_release", "request_id": "...", ...}
└─ notify_worker_returned: {"type": "notify_worker_returned", "request_id": "...", ...}

Master-Supervisor (Sprint 4):
└─ performance_report: {
    "server_uuid": "...",
    "performance": {...},
    "farm_state": {...},
    "config_thresholds": {...},
    "neighbors": [...]
  }
```

**Características de Protocolo:**
- Formato: JSON
- Delimitador: `\n` (newline)
- Encoding: UTF-8
- Case Sensitivity: CAIXA ALTA para campos de controle (HEARTBEAT, QUERY, etc)
- Timeout: 5 segundos em chamadas síncronas
- Correlação: UUID v4 para request_id em M2M

### 4. Network Layer

**Componentes:**

```python
# network.py
├─ encode_message(data) → bytes
├─ decode_message(data) → dict
├─ TCPServer(host, port)
├─ TCPClient(host, port)
└─ ConnectionPool(max_connections)
```

**Features:**
- Pool de conexões reutilizáveis
- Timeout configurável
- Tratamento de desconexões
- Bufferização de mensagens incompletas

### 5. Supervisor de Métricas

**Endpoints:**

```
POST https://nuted-ia.dev:443/
  ↓ (TLS/TCP, sem HTTP)
  └─ Recebe JSON de performance_report

GET https://nuted-ia.dev/supervisor/dashboard/
  └─ Retorna HTML do Dashboard
```

**Funcionalidades:**
- Agregação de múltiplos Masters
- Cálculo de médias e máximos
- Detecção de anomalias
- Geração de alertas
- Histórico de dados

---

## Fluxos Principais

### Fluxo 1: Heartbeat (Sprint 1)

```
┌─────────────────────────────────────────┐
│ Worker                                   │
├─────────────────────────────────────────┤
│ 1. Timer: esperar 30s                    │
│ 2. Conectar ao Master (TCP)              │
│ 3. Enviar HEARTBEAT (JSON + \n)         │
│ 4. Esperar resposta (timeout 5s)        │
│ 5. Validar RESPONSE = ALIVE              │
│ 6. Log: "Master UP"                      │
│ 7. Fechar conexão                        │
│ 8. Volta ao passo 1                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Master                                   │
├─────────────────────────────────────────┤
│ 1. Escutar socket (porta 5000)           │
│ 2. Aceitar conexão (thread por cliente)  │
│ 3. Ler mensagem até \n                   │
│ 4. Parse JSON                            │
│ 5. Validar campos obrigatórios           │
│ 6. Se TASK = HEARTBEAT:                 │
│    └─ Construir response ALIVE           │
│    └─ Enviar response + \n               │
│ 7. Fechar conexão                        │
│ 8. Volta ao passo 1                      │
└─────────────────────────────────────────┘
```

### Fluxo 2: Ciclo de Tarefas (Sprint 2)

```
┌────────────────────────────┐     ┌────────────────────────────┐
│ Worker                     │     │ Master                     │
├────────────────────────────┤     ├────────────────────────────┤
│ 1. Conectar                │────►│ 1. Aceitar conexão         │
│                            │     │                            │
│ 2. Enviar ALIVE            │────►│ 2. Registrar Worker        │
│    com WORKER_UUID         │     │                            │
│                            │     │ 3. Buscar tarefa na fila   │
│ 4. Receber QUERY/NO_TASK   │◄────│ 4. Enviar resposta         │
│                            │     │                            │
│ 5a. Se QUERY:              │     │ 5a. Se houver tarefa:      │
│   └─ Processar tarefa      │     │    └─ Enviar QUERY         │
│   └─ Simular (sleep)       │     │                            │
│                            │     │ 5b. Se sem tarefa:         │
│ 5b. Se NO_TASK:            │     │    └─ Enviar NO_TASK       │
│   └─ Aguardar (2s)         │     │                            │
│                            │     │                            │
│ 6. Enviar STATUS (OK/NOK)  │────►│ 6. Receber e registrar     │
│                            │     │    resultado               │
│ 7. Receber ACK             │◄────│ 7. Enviar ACK              │
│                            │     │                            │
│ 8. Volta ao passo 2        │     │ 8. Volta ao passo 2        │
└────────────────────────────┘     └────────────────────────────┘
```

### Fluxo 3: Negociação P2P (Sprint 3)

```
┌──────────────────┐        ┌──────────────────┐
│ Master A         │        │ Master B         │
│ (Saturado)       │        │ (Com capacidade) │
├──────────────────┤        ├──────────────────┤
│ 1. Monitor       │        │                  │
│    deteta:       │        │                  │
│    load > cap    │        │                  │
│                  │        │                  │
│ 2. Abre conexão  │───────►│ 1. Aceita conexão│
│    com B         │        │                  │
│                  │        │ 2. Recebe        │
│ 3. Envia         │───────►│    request_help  │
│    request_help  │        │                  │
│ (request_id: U1) │        │ 3. Valida carga  │
│                  │        │    própria       │
│ 4. Aguarda resp  │        │                  │
│    (timeout 5s)  │        │ 4. Avalia Workers│
│                  │        │    ociosos       │
│                  │◄───────│ 5. Envia         │
│ 5. Recebe        │        │    response_     │
│    response_     │        │    accepted      │
│    accepted      │        │ (request_id: U1) │
│ (request_id: U1) │        │                  │
│                  │        │ 6. Para cada W:  │
│                  │        │    Envia         │
│                  │        │    command_      │
│                  │        │    redirect      │
│                  │        │    (request_id:  │
│                  │        │     U2)          │
│                  │        │                  │
│                  │        │ 7. W desconecta  │
│                  │        │    de B          │
│                  │        │                  │
│ 6. Worker novo   │◄───────│ 8. W conecta em A│
│    conecta       │        │    enviando      │
│                  │        │    register_temp │
│ 7. Registra W    │        │                  │
│    como          │        │                  │
│    emprestado    │        │                  │
│                  │        │                  │
│ 8. W começa      │        │                  │
│    ciclo Sprint2 │        │                  │
│    com SERVER_UUID        │                  │
│                  │        │                  │
│ (Depois...)      │        │                  │
│                  │        │                  │
│ 9. Monitor:      │        │                  │
│    load < rel    │        │                  │
│                  │        │                  │
│ 10. Envia        │───────►│ Envia            │
│     command_     │        │ notify_worker_   │
│     release      │        │ returned         │
│     para W       │        │                  │
│                  │        │                  │
│ 11. W desconecta │        │                  │
│     de A         │        │                  │
│                  │        │ 11. W reconecta  │
│                  │◄───────│ em B             │
│                  │        │ normalmente      │
└──────────────────┘        └──────────────────┘
```

### Fluxo 4: Relatórios ao Supervisor (Sprint 4)

```
┌─────────────────────────┐
│ Master                  │
├─────────────────────────┤
│ 1. Timer: 10s           │
│ 2. Coletar métricas:    │
│    - CPU               │
│    - Memória           │
│    - Disco             │
│    - Workers           │
│    - Tarefas           │
│ 3. Construir JSON      │
│ 4. Abrir socket TLS    │
│    para Supervisor     │
│ 5. Conectar            │
│    nuted-ia.dev:443    │
│ 6. Enviar JSON         │
│ 7. Fechar conexão      │
│ 8. Volta ao passo 1    │
└─────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Supervisor (nuted-ia.dev)    │
├──────────────────────────────┤
│ 1. Receber JSON via TLS      │
│ 2. Parse e validar           │
│ 3. Armazenar no DB           │
│ 4. Atualizar agregações      │
│ 5. Dashboard faz GET         │
│    periodicamente            │
│ 6. Dashboard atualiza gráfcos│
└──────────────────────────────┘
```

---

## Concorrência e Sincronização

### Threading

**Master Node:**
```
Main Thread (Thread 1)
├─ Server TCP (accept)
│  └─ spawn Handler Thread por cliente
│
Worker Handler Threads (N)
├─ Ler mensagem
├─ Parse JSON
└─ Processar comando

Monitor Thread (Thread M)
├─ Timer 2s
├─ Verificar saturação
└─ Negociar se necessário

Reporting Thread (Thread R)
├─ Timer 10s
└─ Enviar relatórios
```

### Sincronização

**Estruturas compartilhadas:**

```python
# Protected by lock
self.workers: dict              # RLock
self.borrowed_workers: dict     # RLock
self.pending_tasks: Queue       # Thread-safe por padrão
self.pending_requests: dict     # RLock
```

**Estratégia:**
- Queue thread-safe para tarefas
- RLock (Reentrant Lock) para dicts
- Timeout em locks para evitar deadlock
- Minimal critical sections

---

## Tratamento de Falhas

### Falhas Detectadas

| Falha | Detector | Ação |
|-------|----------|------|
| Worker não conecta | Master | Não registra, retry próximo ciclo |
| Master não responde | Worker | Timeout 5s, reconectar próximo ciclo |
| Tarefa falha | Worker | Reportar NOK, Master registra |
| Vizinho não responde | Master A | Timeout 5s, tentar próximo vizinho |
| Worker emprestado cai | Master A | Registra como falhado, tenta devolver |
| Conexão cai durante M2M | Ambos | Retry com backoff exponencial |

### Recuperação

```python
# Exemplo: Retry com backoff
max_retries = 3
backoff = 1  # segundos

for attempt in range(max_retries):
    try:
        socket.connect(...)
        break
    except:
        if attempt < max_retries - 1:
            time.sleep(backoff)
            backoff *= 2  # Exponential backoff
        else:
            raise
```

---

## Escalabilidade

### Horizontal

- **Masters:** Adicionar novos Masters e registrar como vizinhos
- **Workers:** Cada Master pode gerenciar centenas de Workers
- **Tarefas:** Distribuídas por fila em cada Master

### Vertical

- **Threads:** Uma por conexão de Worker (escalável até limite de FD)
- **Memória:** Tarefas processadas incrementalmente
- **CPU:** Processamento distribuído entre Masters

### Limites

```
Por Master:
├─ Max Workers: ~500 (limite de file descriptors / threads)
├─ Max Tarefas/Fila: ~10k (limite de memória)
├─ Max Vizinhos: ~50 (limite prático)
├─ Max TPS (tarefas/seg): ~100 (CPU-bound)

Cluster:
├─ Max Masters: ~100 (escalabilidade de rede)
├─ Max Workers Total: ~50k
├─ Max TPS Cluster: ~10k tarefas/s
```

---

## Segurança

### Validações

- **JSON Parsing:** Strict, falha em JSON inválido
- **Campos Obrigatórios:** Requeridos, não ignorados
- **Case Sensitivity:** Validação exata
- **Timeouts:** Evita deadlock
- **Rate Limiting:** Não implementado (futuro)

### TLS/SSL

```
Master → Supervisor:
├─ TLS 1.2+
├─ SNI: nuted-ia.dev
├─ Certificado validado
└─ Sem HTTP, apenas socket TCP
```

---

## Evolução Futura

### Melhorias Possíveis

1. **Persistência:** Salvar tarefas em DB
2. **Replicação:** Masters em standby
3. **Consensus:** Raft/Paxos para decisões
4. **Elasticity:** Escalaling automático
5. **Observability:** Distributed tracing
6. **Security:** Autenticação/Autorização
7. **Load Balancing:** Round-robin avançado
8. **Fault Tolerance:** Circuit breaker pattern

---

**Versão:** 1.0  
**Última Atualização:** 2026-06-17
