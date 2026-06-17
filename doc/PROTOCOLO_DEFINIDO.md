# Protocolo Completo Definido

---

## Visão Geral

Este documento consolida **todas as definições de mensagens** utilizadas no projeto, organizadas por camada e sprint.

---

## Convenções

### Formato de Mensagem

```json
{
  "campo_obrigatorio": "valor",
  "campo_opcional": "valor"
}
```

### Terminador

- **Delimitador:** `\n` (newline)
- **Encoding:** UTF-8
- **Exemplo:** `{"TASK": "HEARTBEAT"}\n`

### Regras de Parsing

1. Campos desconhecidos são **ignorados**
2. Campos obrigatórios **faltantes causam rejeição**
3. **Case-sensitive** para valores de controle (HEARTBEAT, QUERY, etc)
4. Invalid JSON → **logar e descartar mensagem**

---

## Camada 1: Worker ↔ Master (Sprint 1-2)

### 1.1 Heartbeat

**Sprint:** 1  
**Direção:** Worker → Master  
**Tipo:** Verificação de disponibilidade

#### Request (Worker → Master)

```json
{
  "SERVER_UUID": "Master_A",
  "TASK": "HEARTBEAT"
}
```

**Campos:**
- `SERVER_UUID` (obrigatório, string): ID do Master
- `TASK` (obrigatório, string): "HEARTBEAT"

#### Response (Master → Worker)

```json
{
  "SERVER_UUID": "Master_A",
  "TASK": "HEARTBEAT",
  "RESPONSE": "ALIVE"
}
```

**Campos:**
- `SERVER_UUID` (obrigatório, string): ID do Master
- `TASK` (obrigatório, string): "HEARTBEAT"
- `RESPONSE` (obrigatório, string): "ALIVE"

**Características:**
- Timeout: 5 segundos
- Intervalo: 30 segundos
- Port: 5000

---

### 1.2 Task Cycle

**Sprint:** 2  
**Direção:** Worker ↔ Master (bidirecional)  
**Tipo:** Ciclo completo de trabalho

#### Fase 1: Apresentação (Worker → Master)

**Request (Worker Local)**

```json
{
  "WORKER": "ALIVE",
  "WORKER_UUID": "W-123"
}
```

**Campos:**
- `WORKER` (obrigatório, string): "ALIVE"
- `WORKER_UUID` (obrigatório, string): UUID único do Worker

**Request (Worker Emprestado)**

```json
{
  "WORKER": "ALIVE",
  "WORKER_UUID": "W-999",
  "SERVER_UUID": "Master-B"
}
```

**Campos adicionais:**
- `SERVER_UUID` (opcional, string): Master de origem (se emprestado)

#### Fase 2: Distribuição de Tarefa (Master → Worker)

**Response (Tem Tarefa)**

```json
{
  "TASK": "QUERY",
  "USER": "Michel"
}
```

**Campos:**
- `TASK` (obrigatório, string): "QUERY"
- `USER` (obrigatório, string): Identificador do usuário

**Response (Sem Tarefa)**

```json
{
  "TASK": "NO_TASK"
}
```

**Campos:**
- `TASK` (obrigatório, string): "NO_TASK"

#### Fase 3: Reporte de Status (Worker → Master)

**Request**

```json
{
  "STATUS": "OK",
  "TASK": "QUERY",
  "WORKER_UUID": "W-123"
}
```

**Campos:**
- `STATUS` (obrigatório, string): "OK" ou "NOK"
- `TASK` (obrigatório, string): "QUERY"
- `WORKER_UUID` (obrigatório, string): UUID do Worker

#### Fase 4: Confirmação (Master → Worker)

**Response (ACK)**

```json
{
  "STATUS": "ACK",
  "WORKER_UUID": "W-123"
}
```

**Campos:**
- `STATUS` (obrigatório, string): "ACK"
- `WORKER_UUID` (obrigatório, string): UUID do Worker

---

## Camada 2: Master ↔ Master (Sprint 3)

### Estrutura Base de M2M

**Todas as mensagens M2M seguem:**

```json
{
  "type": "tipo_mensagem",
  "request_id": "uuid-unico",
  "payload": {
    "dados_especificos": "..."
  }
}
```

**Campos base:**
- `type` (obrigatório, string): tipo de mensagem (minúsculas)
- `request_id` (obrigatório, string): UUID v4 para rastreio
- `payload` (obrigatório, object): dados específicos

---

### 2.1 Request Help

**Direção:** Master A → Master B  
**Quando:** Master A detecta saturação (load > threshold)  
**Timeout:** 5 segundos

#### Request

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

**Payload:**
- `master_id` (obrigatório, string): ID do Master solicitante
- `current_load` (obrigatório, int): Tarefas pendentes atuais
- `capacity` (obrigatório, int): Capacidade máxima
- `workers_needed` (obrigatório, int): Número de Workers desejados

---

### 2.2 Response Accepted

**Direção:** Master B → Master A  
**Quando:** Master B tem Workers ociosos  
**request_id:** Idêntico ao request_help original

#### Response

```json
{
  "type": "response_accepted",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "workers_offered": 2,
    "worker_details": [
      {
        "id": "B1",
        "address": "192.168.1.10:5001"
      },
      {
        "id": "B2",
        "address": "192.168.1.10:5002"
      }
    ]
  }
}
```

**Payload:**
- `workers_offered` (obrigatório, int): Número de Workers ofertados
- `worker_details` (obrigatório, array): Lista de Workers com endereços

---

### 2.3 Response Rejected

**Direção:** Master B → Master A  
**Quando:** Master B não tem capacidade  
**request_id:** Idêntico ao request_help original

#### Response

```json
{
  "type": "response_rejected",
  "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "payload": {
    "reason": "high_load"
  }
}
```

**Payload:**
- `reason` (obrigatório, string): Motivo da rejeição
  - `"high_load"` - Master B tem carga alta
  - `"no_workers_available"` - Sem Workers ociosos
  - `"refused"` - Recusou por outro motivo

---

### 2.4 Command Redirect

**Direção:** Master B → Worker B1  
**Quando:** Após response_accepted

#### Command

```json
{
  "type": "command_redirect",
  "request_id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
  "payload": {
    "new_master_address": "192.168.1.5:5000"
  }
}
```

**Payload:**
- `new_master_address` (obrigatório, string): "ip:port" do novo Master

**Ação do Worker:**
1. Desconectar do Master B
2. Aguardar 1s
3. Conectar ao novo endereço (Master A)
4. Enviar register_temporary_worker

---

### 2.5 Register Temporary Worker

**Direção:** Worker B1 → Master A  
**Quando:** Worker se reconecta após command_redirect

#### Request

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

**Payload:**
- `worker_id` (obrigatório, string): ID do Worker
- `original_master_address` (obrigatório, string): "ip:port" do Master de origem

**Master A então:**
- Registra Worker como emprestado
- Próximas mensagens ALIVE incluem SERVER_UUID do Master original

---

### 2.6 Command Release

**Direção:** Master A → Worker B1  
**Quando:** Carga de Master A normaliza (load < release_threshold)

#### Command

```json
{
  "type": "command_release",
  "request_id": "z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4",
  "payload": {
    "original_master_address": "192.168.1.10:5000"
  }
}
```

**Payload:**
- `original_master_address` (obrigatório, string): "ip:port" do Master original

**Ação do Worker:**
1. Desconectar de Master A
2. Reconectar ao Master B (original_master_address)
3. Enviar ALIVE normalmente (sem SERVER_UUID)

---

### 2.7 Notify Worker Returned

**Direção:** Master A → Master B  
**Quando:** Após command_release

#### Notification

```json
{
  "type": "notify_worker_returned",
  "request_id": "m1n2b3v4-c5x6-z7a8-s9d0-f1g2h3j4k5l6",
  "payload": {
    "worker_id": "B1"
  }
}
```

**Payload:**
- `worker_id` (obrigatório, string): ID do Worker devolvido

**Master B então:**
- Remove Worker do registro de "emprestado"
- Disponibiliza Worker para futuras negociações

---

## Camada 3: Master → Supervisor (Sprint 4)

### 3.1 Performance Report

**Direção:** Master → Supervisor  
**Quando:** A cada 10 segundos  
**Protocolo:** TLS/TCP (não HTTP)  
**Port:** 443  
**Host:** nuted-ia.dev

#### Payload Completo

```json
{
  "server_uuid": "michel_1",
  "hostname": "michel_1.farm.local",
  "role": "master",
  "task": "performance_report",
  "timestamp": "2026-06-08T12:34:56Z",
  "message_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "payload_version": "sprint4-monitor",
  
  "performance": {
    "system": {
      "uptime_seconds": 12345,
      "load_average_1m": 3.20,
      "load_average_5m": 2.50,
      "cpu": {
        "usage_percent": 85.42,
        "count_logical": 8,
        "count_physical": 4
      },
      "memory": {
        "total_mb": 16384,
        "available_mb": 8192,
        "percent_used": 62.18,
        "memory_used": 8000
      },
      "disk": {
        "total_gb": 512.0,
        "free_gb": 250.0,
        "percent_used": 45.0
      }
    }
  },
  
  "farm_state": {
    "workers": {
      "total_registered": 6,
      "workers_utilization": 4,
      "workers_alive": 6,
      "workers_idle": 2,
      "workers_borrowed": 1,
      "workers_received": 1,
      "workers_failed": 0,
      "workers_home": 5,
      "workers_available_capacity": 2,
      "borrowed_workers": [
        { "direction": "out", "peer_uuid": "michel_2" },
        { "direction": "in",  "peer_uuid": "michel_2" }
      ]
    },
    "tasks": {
      "tasks_pending": 42,
      "tasks_running": 4,
      "tasks_completed": 150,
      "tasks_failed": 3,
      "oldest_task_age_s": 312
    }
  },
  
  "config_thresholds": {
    "max_task": 100,
    "warn_cpu_percent": 85,
    "warn_memory_percent": 85,
    "release_task": 60
  },
  
  "neighbors": [
    {
      "server_uuid": "michel_2",
      "status": "available",
      "last_heartbeat": "2026-06-08T12:34:56Z"
    }
  ]
}
```

**Campos Obrigatórios:**
- `server_uuid` - ID único do Master
- `hostname` - Nome DNS
- `role` - "master" (fixo)
- `task` - "performance_report" (fixo)
- `timestamp` - ISO-8601 com Z (UTC)
- `message_id` - UUID v4
- `payload_version` - Versão do schema
- `performance` - Seção de métricas de sistema
- `farm_state` - Seção de estado da farm
- `config_thresholds` - Limites configurados
- `neighbors` - Lista de vizinhos

---

## Tabela de Compatibilidade

### Versões do Protocolo

| Versão | Sprint | Feature |
|--------|--------|---------|
| 1.0 | 1 | Heartbeat |
| 1.1 | 2 | Task Cycle |
| 2.0 | 3 | Master-to-Master |
| 3.0 | 4 | Supervisor |

### Compatibilidade Retroativa

- ✅ Sprint 1 → Sprint 2: Adiciona campos (backward compatible)
- ✅ Sprint 2 → Sprint 3: Novo type "type" em M2M (não afeta W2M)
- ✅ Sprint 3 → Sprint 4: Adiciona campos de coleta (não afeta M2M)

---

## Exemplos Práticos

### Exemplo 1: Ciclo Completo de Tarefa

```
Worker conecta e envia:
{"WORKER": "ALIVE", "WORKER_UUID": "W-001"}\n

Master responde:
{"TASK": "QUERY", "USER": "Michel"}\n

Worker processa (simula trabalho) e envia:
{"STATUS": "OK", "TASK": "QUERY", "WORKER_UUID": "W-001"}\n

Master confirma:
{"STATUS": "ACK", "WORKER_UUID": "W-001"}\n

Worker loop: Volta ao passo 1
```

### Exemplo 2: Negociação com Empréstimo

```
Master A detecta saturação e envia:
{
  "type": "request_help",
  "request_id": "req-123",
  "payload": {
    "master_id": "A",
    "current_load": 150,
    "capacity": 100,
    "workers_needed": 2
  }
}\n

Master B responde:
{
  "type": "response_accepted",
  "request_id": "req-123",
  "payload": {
    "workers_offered": 2,
    "worker_details": [
      {"id": "W3", "address": "10.0.0.2:5001"},
      {"id": "W4", "address": "10.0.0.2:5002"}
    ]
  }
}\n

Master B envia para Worker W3:
{
  "type": "command_redirect",
  "request_id": "redir-456",
  "payload": {
    "new_master_address": "10.0.0.1:5000"
  }
}\n

Worker W3 reconecta e envia:
{
  "type": "register_temporary_worker",
  "request_id": "reg-789",
  "payload": {
    "worker_id": "W3",
    "original_master_address": "10.0.0.2:5000"
  }
}\n

Master A agora recebe de W3 com:
{"WORKER": "ALIVE", "WORKER_UUID": "W3", "SERVER_UUID": "B"}\n
```

---

## Status Codes

### Valores de `STATUS`

| Valor | Significado | Enviado por |
|-------|-----------|-----------|
| "OK" | Tarefa concluída com sucesso | Worker |
| "NOK" | Tarefa falhou na execução | Worker |
| "ACK" | Confirmação de recebimento | Master |
| "ALIVE" | Resposta de heartbeat | Master |

---

## Timeouts

| Operação | Timeout | Ação após timeout |
|----------|---------|------------------|
| Heartbeat | 5s | Considerar Master DOWN |
| Task Request | 5s | Reconectar |
| M2M Response | 5s | Tentar próximo vizinho |
| Report Send | 5s | Log + retry próximo ciclo |

---

## Notas de Versioning

- Campos novos em payload = backward compatible
- Mudanças em `type` = quebra compatibilidade
- Campos removidos = quebra compatibilidade
- Valores diferentes para campos existentes = compatível se parsing tolera

---

**Versão do Protocolo:** 3.0  
**Última Atualização:** 2026-06-17  
**Status:** Final
