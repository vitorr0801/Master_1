# Sprint 3 - Guia Prático de Execução

## Quick Start

### Ambiente Recomendado
- Python 3.7+
- Três terminais diferentes (1 Master A, 1 Master B, N Workers)
- Máquina local ou rede interna

### Passo 1: Terminal 1 - Master A

```bash
cd "c:\Users\lucas.svellasco\Downloads\sprint 3\Master_1"
python master_sprint3.py
```

Saída esperada:
```
2026-06-03 10:15:23,456 - [INFO] - [MASTER_A] Aguardando conexões em 0.0.0.0:5000...
2026-06-03 10:15:23,457 - [INFO] - [CONFIG] Capacity=3, Saturation_Threshold=3, Release_Threshold=1
```

### Passo 2: Terminal 2 - Master B

Crie um arquivo `master_sprint3_b.py`:

```python
# Copie master_sprint3.py e modifique:
HOST = "0.0.0.0"
PORT = 6000  # Porta diferente
MASTER_ID = "MASTER_B"

CAPACITY = 3

neighbor_masters = {
    "MASTER_A": {
        "host": "127.0.0.1",
        "port": 5000
    }
}

# ... resto do código igual
```

Ou simplesmente execute com variáveis de ambiente:

```bash
set PORT=6000
set MASTER_ID=MASTER_B
python master_sprint3.py
```

### Passo 3: Terminal 3+ - Workers

```bash
# Worker 1
python -c "from Worker import Worker; Worker().run()"

# Worker 2 (em outro terminal)
python -c "from Worker import Worker; Worker().run()"

# Worker 3 (em outro terminal)
python -c "from Worker import Worker; Worker().run()"
```

## Cenários de Teste

### Cenário 1: Master Saturado Solicita Ajuda

**Setup:**
- Master A com 3 Workers locais
- Master B com 3 Workers ociosos
- Simular chegada de 5 tarefas em Master A

**Resultado Esperado:**
1. Master A detecta saturação (load > 3)
2. Master A envia `request_help` para Master B
3. Master B responde `response_accepted` com 2 workers
4. Master B envia `command_redirect` para 2 workers
5. Workers B1 e B2 se reconectam ao Master A
6. Master A distribui tarefas para Workers emprestados
7. Logs mostram: "Borrowed_Workers=2"

**Logs de Master A:**
```
[SATURAÇÃO DETECTADA] Carga=5, Capacity=3
[REQUEST_HELP] request_id=<uuid>
[RESPONSE_ACCEPTED] Recebido 2 workers
[WORKER_REGISTERED] B1 (borrowed from 127.0.0.1:6000)
[WORKER_REGISTERED] B2 (borrowed from 127.0.0.1:6000)
[TASK_ASSIGNED] B1: Michel
[TASK_ASSIGNED] B2: Julia
```

**Logs de Master B:**
```
[REQUEST_HELP_RECEIVED] from MASTER_A, need 2 workers
[RESPONSE_ACCEPTED] Oferecendo 2 workers
[COMMAND_REDIRECT] Redirecionando para 127.0.0.1:5000
[WORKER_DISCONNECTED] B1 (local)
[WORKER_DISCONNECTED] B2 (local)
```

### Cenário 2: Master Busy Recusa Ajuda

**Setup:**
- Master B também está saturado (load > 3)

**Resultado Esperado:**
1. Master A envia `request_help`
2. Master B responde `response_rejected` com reason="high_load"
3. Nenhum worker é redirecionado
4. Master A continua com seus 3 workers locais

**Log:**
```
[RESPONSE_REJECTED] reason=high_load
```

### Cenário 3: Devolução de Workers

**Setup:**
- Master A tem 2 workers emprestados
- 2 tarefas completam

**Resultado Esperado:**
1. Carga de Master A cai para 1 (< release_threshold)
2. Master A envia `command_release` aos workers emprestados
3. Master A envia `notify_worker_returned` ao Master B
4. Workers retornam ao Master B
5. Logs mostram: "Borrowed_Workers=0"

**Logs:**
```
[LIBERAÇÃO] Liberando Worker emprestado: B1
[COMMAND_RELEASE] Enviado para B1
[NOTIFY_WORKER_RETURNED] Master B
[WORKER_RETURNED_NOTIFICATION] B1
```

## Monitoramento em Tempo Real

### Status Report a Cada 10 Segundos

```
[STATUS] Load=5/3, Local_Workers=1, Borrowed_Workers=2
[STATUS] Load=3/3, Local_Workers=3, Borrowed_Workers=0
```

### Rastreamento de Request ID

Cada requisição tem um UUID único que facilita debugging:

```
[REQUEST_HELP] request_id=a1b2c3d4-e5f6-7890-1234-567890abcdef
[SEND_TO_MASTER] MASTER_B: {...}
[RESPONSE_FROM_UNKNOWN] type=response_accepted, request_id=a1b2c3d4-e5f6-7890-1234-567890abcdef
```

### Lifecycle de Um Worker Emprestado

```
# Master B (oferecendo)
[REQUEST_HELP_RECEIVED] from MASTER_A
[RESPONSE_ACCEPTED] Oferecendo 1 workers
[WORKER_DISCONNECTED] B1 (local)

# Worker B1
[COMMAND_REDIRECT] Redirecionando para 127.0.0.1:5000
[Conectando a 127.0.0.1:5000...]
[Conectado!]
[Registrado como worker emprestado]

# Master A (recebendo)
[WORKER_REGISTERED] B1 (borrowed from 127.0.0.1:6000)
[TASK_ASSIGNED] B1: Julia
[TASK_RESULT] B1: OK
[LIBERAÇÃO] Liberando Worker emprestado: B1

# Worker B1 (retornando)
[Liberado, retornando para 127.0.0.1:6000]
[Reconectado ao Master original]

# Master B (recebendo)
[WORKER_REGISTERED] B1 (local)
```

## Debugging

### Ver Todas as Mensagens JSON

Descomente em `master_sprint3.py`:

```python
logger.debug(f"[RECEIVED] {payload}")
```

E execute com logging debug:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

### Forçar Cenários

**Forçar Saturação:**

```python
# Em master_sprint3.py, add_more_tasks()
for i in range(10):
    task_queue.put({"user": f"User_{i}"})
```

**Simular Master Indisponível:**

```python
# Pause Master B e observe timeout em Master A
# Ctrl+C no terminal do Master B
# Logs mostrarão [TIMEOUT] no Master A após 5 segundos
```

**Forçar Falha de Worker:**

```python
# Ctrl+C num terminal de Worker
# Master detectará desconexão e removerá do registro
```

## Troubleshooting

### Problema: "Port already in use"

**Solução:**
```bash
# Encontre o processo usando a porta
netstat -ano | findstr :5000

# Mate o processo
taskkill /PID <PID> /F
```

### Problema: Master A não vê resposta de Master B

**Checklist:**
1. Master B está rodando? (verifique terminal)
2. Portas corretas? (5000 para A, 6000 para B)
3. `neighbor_masters` configu rado? (Master A deve conhecer Master B)
4. Firewall bloqueando? (localhost geralmente OK)

**Verify:**
```bash
# Teste conexão manual
python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 6000)); print('OK')"
```

### Problema: Workers não conectam

**Checklist:**
1. Master A está rodando?
2. Worker usa porta correta? (5000 para Master A)
3. HOST configurado? (127.0.0.1 para localhost)

### Problema: Mensagem "JSON inválido"

**Checklist:**
1. Mensagem termina com `\n`?
2. JSON é válido?
3. Campos obrigatórios presentes?

## Performance Tips

### Para Muitos Workers

```python
CAPACITY = 10  # Aumentar capacidade
# ou
num_workers_needed = 5  # Em request_help
```

### Para Saturação Rápida

```python
# Adicione muitas tarefas
for _ in range(100):
    task_queue.put({"user": "TestUser"})
```

### Para Melhor Observabilidade

```python
# Aumente frequência de status
monitor_connections()  # mude sleep(10) para sleep(2)
```

## Testes Automatizados

```bash
python test_sprint3.py
```

Executa 9 testes verificando:
- Formatos de mensagem
- Correlação de request_id
- Delimitador de nova linha
- Estrutura de payloads

## Análise de Logs

### Padrão de Sucesso

```
[SATURAÇÃO DETECTADA]
→ [REQUEST_HELP]
  → [RESPONSE_ACCEPTED]
    → [WORKER_REGISTERED] (borrowed)
      → [TASK_ASSIGNED]
        → [TASK_RESULT]
          → [STATUS] Borrowed_Workers=2
            → [LIBERAÇÃO]
              → [WORKER_REGISTERED] (original Master)
```

### Padrão de Falha

```
[SATURAÇÃO DETECTADA]
→ [REQUEST_HELP]
  → [TIMEOUT] (após 5s)
    → Log continua com retentativa em próximo ciclo
```

## Métricas Importantes

### Observar

1. **Latência de Request/Response**
   - Linha de [SEND_TO_MASTER] até [RESPONSE_ACCEPTED]
   - Target: < 100ms (local)

2. **Tempo de Redirecionamento**
   - De [RESPONSE_ACCEPTED] até [WORKER_REGISTERED]
   - Target: < 500ms

3. **Taxa de Sucesso**
   - response_accepted / request_help total
   - Target: 90%+ (dependendo de carga)

4. **Tempo de Devolução**
   - De [LIBERAÇÃO] até [WORKER_REGISTERED] (original)
   - Target: < 1s

---

**Próximas Etapas:**
1. ✅ Sprint 1 e 2: Heartbeat e tarefas
2. ✅ Sprint 3: Negociação Master-to-Master
3. 🔄 Testes de integração com outra equipe
4. 🔄 Otimizações de performance
5. 🔄 Documentação de API
