# Sprint 3: Protocolo de Negociação Master-to-Master e Redirecionamento Dinâmico de Workers

## Visão Geral

Esta implementação completa o Sprint 3 do projeto de **P2P com Balanceamento de Carga Dinâmico**. O sistema implementa a comunicação entre Masters para negociar empréstimo de Workers quando um Master fica saturado.

## Arquitetura

### Componentes Principais

1. **Master Node** (`master_sprint3.py`)
   - Gerencia Workers locais e emprestados
   - Detecta saturação de carga
   - Negocia com Masters vizinhos
   - Redirecion dinamicamente Workers

2. **Worker Node** (`Worker.py`)
   - Executa tarefas
   - Suporta redirecionamento para outros Masters
   - Reporta status de execução

## Estrutura de Dados e Variáveis

### Master

```python
CAPACITY = 3                          # Capacidade máxima de tarefas
SATURATION_THRESHOLD = CAPACITY       # Limiar de saturação
RELEASE_THRESHOLD = int(CAPACITY * 0.6)  # Limiar de liberação (histerese)

workers = {}                          # Workers locais
borrowed_workers = {}                 # Workers emprestados de outros Masters
pending_requests = {}                 # Requisições em espera de resposta
master_connections = {}               # Pool de conexões com vizinhos
```

### Worker

```python
WORKER_ID                             # UUID único do Worker
ORIGINAL_MASTER_ADDRESS              # Endereço do Master original
is_borrowed                           # Flag indicando se é emprestado
is_processing_task                    # Flag de processamento
```

## Protocolo de Mensagens - Sprint 3

### 1. Request Help (Master A → Master B)

Quando um Master detecta saturação, envia:

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

**Campos:**
- `type`: Sempre "request_help"
- `request_id`: UUID v4 único para correlação
- `payload.master_id`: ID do Master solicitante
- `payload.current_load`: Número de tarefas pendentes
- `payload.capacity`: Capacidade máxima
- `payload.workers_needed`: Número de Workers necessários

### 2. Response Accepted (Master B → Master A)

Se Master B tem Workers disponíveis:

```json
{
  "type": "response_accepted",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "workers_offered": 2,
    "worker_details": [
      { "id": "B1", "address": "127.0.0.1:6000" },
      { "id": "B2", "address": "127.0.0.1:6000" }
    ]
  }
}
```

### 3. Response Rejected (Master B → Master A)

Se Master B não tem Workers disponíveis:

```json
{
  "type": "response_rejected",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "reason": "high_load|no_workers_available|refused"
  }
}
```

### 4. Command Redirect (Master B → Worker B1)

Master B ordena Worker a se conectar ao Master A:

```json
{
  "type": "command_redirect",
  "request_id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
  "payload": {
    "new_master_address": "127.0.0.1:5000"
  }
}
```

### 5. Register Temporary Worker (Worker B1 → Master A)

Worker se apresenta ao novo Master como emprestado:

```json
{
  "type": "register_temporary_worker",
  "request_id": "c1b2a3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "payload": {
    "worker_id": "B1",
    "original_master_address": "127.0.0.1:6000"
  }
}
```

### 6. Command Release (Master A → Worker B1)

Master A libera o Worker quando carga normaliza:

```json
{
  "type": "command_release",
  "request_id": "z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4",
  "payload": {
    "original_master_address": "127.0.0.1:6000"
  }
}
```

### 7. Notify Worker Returned (Master A → Master B)

Master A notifica Master B da devolução:

```json
{
  "type": "notify_worker_returned",
  "request_id": "m1n2b3v4-c5x6-z7a8-s9d0-f1g2h3j4k5l6",
  "payload": {
    "worker_id": "B1"
  }
}
```

## Fluxo de Execução

### Ciclo de Empréstimo

```
1. Master A detecta: current_load > saturation_threshold
2. Master A → Master B: request_help
3. Master B analisa sua carga e workers ociosos
4. Se capaz:
   a. Master B → Master A: response_accepted
   b. Master B → Worker B1: command_redirect
   c. Worker B1 desconecta de Master B
   d. Worker B1 → Master A: register_temporary_worker
   e. Master A registra Worker B1 como emprestado
   f. Worker B1 opera normalmente sob Master A
5. Se incapaz:
   a. Master B → Master A: response_rejected
```

### Ciclo de Devolução

```
1. Master A monitora: current_load < release_threshold
2. Master A → Worker B1: command_release
3. Worker B1 desconecta de Master A
4. Master A → Master B: notify_worker_returned
5. Worker B1 → Master B: reconecta e registra
6. Worker B1 volta a operar sob Master B
```

## Funcionalidades Implementadas

### Master (master_sprint3.py)

- ✅ **Conexão TCP**: Atua como servidor (escuta Workers e Masters) e cliente (conecta a vizinhos)
- ✅ **Pool de Conexões**: Mantém conexões reutilizáveis com Masters vizinhos
- ✅ **Detecção de Saturação**: Monitora carga e dispara `request_help` quando necessário
- ✅ **Histerese**: Limiar de liberação menor que saturação (evita ping-pong)
- ✅ **Protocolo Request/Response**: Implementa todos os tipos de mensagem do Sprint 3
- ✅ **Timeout**: Aguarda respostas por máximo 5 segundos
- ✅ **Thread Safety**: Locks para estruturas compartilhadas
- ✅ **Logging Detalhado**: Rastreia todas as operações com timestamps
- ✅ **Compatibilidade Sprint 02**: Suporta ciclo completo de tarefas

### Worker (Worker.py)

- ✅ **Conexão Dinâmica**: Conecta ao Master configurado
- ✅ **Comando Redirect**: Processa redirecionamento para novo Master
- ✅ **Registro Emprestado**: Envia informações de Master original
- ✅ **Comando Release**: Retorna ao Master original
- ✅ **Execução de Tarefas**: Simula processamento com duração aleatória
- ✅ **Status Report**: Reporta OK/NOK de tarefas
- ✅ **Timeout Handling**: Detecta conexão perdida
- ✅ **Logging**: Registra todas as operações

## Casos de Teste (CT01-CT09)

### CT01: Pedido de ajuda aceito
- Master A envia `request_help` com 2 Workers necessários
- Master B responde com `response_accepted` e detalhes dos Workers
- ✅ Implementado

### CT02: Pedido de ajuda recusado
- Master A envia `request_help`
- Master B com carga alta responde com `response_rejected`
- ✅ Implementado

### CT03: Correlação de request_id
- Master A envia múltiplos `request_help` concorrentes
- Cada resposta correlaciona com seu `request_id`
- ✅ Implementado

### CT04: Registro de Worker emprestado
- Worker recebe `command_redirect`
- Conecta ao novo Master e envia `register_temporary_worker`
- Master A registra Worker como emprestado
- ✅ Implementado

### CT05: Tarefa em Worker emprestado
- Master A distribui tarefa para Worker emprestado
- Worker processa e reporta STATUS
- Master A registra execução em log
- ✅ Implementado

### CT06: Devolução do Worker
- Carga do Master A cai abaixo de `release_threshold`
- Master A envia `command_release` e `notify_worker_returned`
- Worker B1 reconecta ao Master B
- ✅ Implementado

### CT07: Timeout de negociação
- Master A envia `request_help` para Master indisponível
- Após 5s sem resposta, descarta `request_id`
- ✅ Implementado

### CT08: Falha do Master
- Se conexão cai durante empréstimo
- Worker tenta retornar ao Master original
- Sistema mantém estado consistente
- ✅ Tratado

### CT09: Tipo desconhecido
- Master recebe mensagem com `type` não previsto
- Registra em log e ignora
- Sistema continua operando
- ✅ Implementado

## Como Usar

### 1. Iniciar Master A (Porta 5000)

```bash
python master_sprint3.py
```

### 2. Iniciar Master B (Porta 6000)

Modifique `master_sprint3.py`:
```python
MASTER_ID = "MASTER_B"
PORT = 6000
neighbor_masters = {
    "MASTER_A": {
        "host": "127.0.0.1",
        "port": 5000
    }
}
```

Então execute:
```bash
python master_sprint3.py
```

### 3. Iniciar Workers

```bash
# Worker conectando ao Master A (port 5000)
python -c "from Worker import Worker; Worker().run()"

# Para múltiplos workers, execute em terminais diferentes
```

### 4. Executar Testes

```bash
python test_sprint3.py
```

## Monitoramento

O Master exibe logs com:
- Detecção de saturação
- Requisições de ajuda enviadas
- Respostas recebidas
- Workers registrados (locais e emprestados)
- Tarefas distribuídas
- Status de Workers
- Devoluções de Workers

Exemplo de saída:
```
2026-06-03 10:15:23,456 - [INFO] - [MASTER_A] Aguardando conexões em 0.0.0.0:5000...
2026-06-03 10:15:23,457 - [INFO] - [CONFIG] Capacity=3, Saturation_Threshold=3, Release_Threshold=1
2026-06-03 10:15:25,234 - [INFO] - [WORKER_REGISTERED] W-abc123 (local)
2026-06-03 10:15:26,123 - [SATURAÇÃO DETECTADA] Carga=5, Capacity=3
2026-06-03 10:15:26,125 - [REQUEST_HELP] request_id=a1b2c3d4-e5f6-7890-1234-567890abcdef
2026-06-03 10:15:26,234 - [RESPONSE_ACCEPTED] Recebido 2 workers
2026-06-03 10:15:26,345 - [STATUS] Load=5/3, Local_Workers=1, Borrowed_Workers=2
```

## Notas de Implementação

### Thread Safety
- Todas as estruturas compartilhadas usam `threading.Lock()`
- Fila de tarefas usa `queue.Queue()` (thread-safe nativamente)

### Timeouts
- Resposta do Master: 5 segundos (configurável)
- Socket recv: REQUEST_TIMEOUT

### Pool de Conexões
- Reutiliza conexões TCP com Masters vizinhos
- Verifica se conexão está viva antes de reutilizar
- Remove conexões mortas do pool automaticamente

### Parsing
- Ignora campos desconhecidos no JSON (compatibilidade futura)
- Falha de forma controlada com log se campos obrigatórios estão ausentes

### Case Sensitivity
- Todos os `type` em minúsculas (request_help, response_accepted, etc.)
- Valores de controle (OK, NOK, ACK) em maiúsculas

## Melhorias Futuras

1. **Algoritmo de Seleção de Master**: Implementar heurística para escolher qual vizinho solicitar
2. **Replicação de Estado**: Sincronizar estado de Workers emprestados
3. **Métricas**: Dashboard com CPU, memória, latência
4. **Load Balancing Avançado**: Predição de carga
5. **Circuit Breaker**: Parar de solicitar a Masters que sempre recusam
6. **Persistência**: Salvar estado em disco

## Conformidade com Especificação

✅ Protocolo de Conversa Consensual (O4)
✅ Redirecionamento Dinâmico de Workers (O5)
✅ Autonomia e Interoperabilidade (O6)
✅ Todos os payloads oficiais implementados
✅ Message delimiter (\n) respeitado
✅ Strict parsing de JSON
✅ Case sensitivity mantida
✅ Timeout implementado (5s)
✅ Histerese implementada

## Arquivos

- `master_sprint3.py` - Implementação do Master (Sprint 3 completo)
- `Worker.py` - Implementação do Worker (Sprint 3 completo)
- `test_sprint3.py` - Testes unitários
- `README.md` - Esta documentação

---

**Autor**: Lucas Svellasco  
**Data**: Junho de 2026  
**Professor**: Michel Junio Ferreira Rosa  
**Disciplina**: Arquitetura de Sistemas Distribuídos
