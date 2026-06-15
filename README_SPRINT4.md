# Sprint 4 — Apresentação Final e Supervisão do Cluster

## Visão geral

Esta é a quarta etapa do projeto de P2P com balanceamento de carga dinâmico. A Sprint 4 não substitui as anteriores: ela consolida a evolução do sistema desde o mecanismo básico de monitoramento até a etapa final de supervisão, observabilidade e apresentação do cluster.

## Evolução das Sprints 1, 2 e 3

### Sprint 1 — Heartbeat e disponibilidade do Master
- O sistema começa com comunicação TCP entre Worker e Master.
- O Worker envia um payload de verificação com TASK = HEARTBEAT.
- O Master responde com RESPONSE = ALIVE.
- Objetivo: garantir disponibilidade e conexão base.

### Sprint 2 — Ciclo de tarefas e apresentação de Workers
- O Worker se apresenta ao Master com WORKER = ALIVE e WORKER_UUID.
- O Master distribui tarefas da fila (QUERY) ou informa NO_TASK.
- O Worker processa a tarefa e retorna STATUS = OK/NOK.
- O Master envia ACK para fechar o ciclo.
- Objetivo: validar o fluxo completo de execução de tarefas.

### Sprint 3 — Negociação entre Masters e redirecionamento de Workers
- Um Master saturado pode pedir ajuda a um vizinho usando request_help.
- O vizinho responde com response_accepted ou response_rejected.
- Workers podem ser redirecionados dinamicamente.
- O sistema passa a tratar empréstimo, devolução e registro temporário de Workers.
- Objetivo: adicionar balanceamento dinâmico e interoperabilidade entre nós.

### Sprint 4 — Supervisão, métricas e apresentação final
- O projeto agora deve enviar métricas do nó para um supervisor externo.
- O objetivo é demonstrar o estado real do cluster em tempo real.
- O sistema deve reportar desempenho, carga, workers, tarefas e vizinhos.
- Objetivo: fechar a apresentação final com observabilidade e monitoramento.

---

## Objetivo da Sprint 4

A Sprint 4 tem como foco a apresentação final do projeto, incluindo:

1. Coleta de métricas do nó (CPU, memória, disco, uptime, filas e workers).
2. Envio das métricas em formato JSON via conexão TLS/TCP.
3. Integração com o supervisor do professor.
4. Visualização dos dados por meio do dashboard.

Essa etapa transforma o projeto de um protótipo funcional para um sistema observável e demonstrável em ambiente de avaliação.

---

## O que deve ser implementado

### 1. Coleta de métricas do nó
O sistema deve gerar um payload com informações de:
- server_uuid
- hostname
- role
- task
- timestamp
- message_id
- payload_version
- performance.system
- performance.farm_state
- performance.config_thresholds
- performance.neighbors

### 2. Envio ao supervisor
O envio deve ocorrer por:
- host: nuted-ia.dev
- porta: 443
- protocolo: TLS sobre TCP
- SNI: nuted-ia.dev

Importante:
- não usar HTTP;
- não usar endpoint REST;
- apenas abrir conexão, enviar o JSON e encerrar a conexão.

### 3. Compatibilidade com as sprints anteriores
A Sprint 4 deve continuar respeitando:
- a arquitetura Master/Worker;
- os protocolos já definidos nas sprints anteriores;
- os conceitos de carga, workers emprestados e balanceamento;
- a lógica de conexão TCP/JSON já utilizada no projeto.

---

## Payload de referência para Sprint 4

O payload do supervisor deve seguir a estrutura abaixo, com foco em métricas de desempenho e estado do cluster:

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
          { "direction": "in", "peer_uuid": "michel_2" }
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
}
```

---

## Checklist da Sprint 4

### Implementação
- [ ] Gerar métricas do sistema em tempo real
- [ ] Montar payload JSON completo
- [ ] Enviar via TLS/TCP para o supervisor
- [ ] Garantir que a conexão seja aberta, enviada e encerrada sem esperar resposta
- [ ] Integrar os dados do Master e dos Workers

### Observabilidade
- [ ] Exibir carga da CPU, memória e disco
- [ ] Mostrar quantidade de workers ativos, ociosos e emprestados
- [ ] Registrar tarefas pendentes, executando e concluídas
- [ ] Exibir vizinhos e estado da rede

### Apresentação
- [ ] Preparar demonstração do fluxo completo das Sprints 1–4
- [ ] Relacionar cada sprint com a evolução do sistema
- [ ] Apresentar o dashboard como prova funcional do projeto

---

## Como esta Sprint complementa as anteriores

A Sprint 4 é a etapa de fechamento do projeto:
- Sprint 1 mostrou que o sistema consegue se comunicar;
- Sprint 2 mostrou que o sistema consegue processar tarefas;
- Sprint 3 mostrou que o sistema consegue equilibrar carga e negociar entre Masters;
- Sprint 4 mostra que o sistema também consegue ser monitorado, medido e apresentado para validação.

Em outras palavras: a evolução do projeto vai de comunicação simples, para execução de tarefas, para balanceamento distribuído e, por fim, para observabilidade e apresentação final.

---

## Recomendação para a entrega

Para a apresentação, o ideal é organizar a explicação em quatro blocos:
1. Funcionamento básico do heartbeat.
2. Distribuição de tarefas entre Workers.
3. Negociação e empréstimo de Workers entre Masters.
4. Monitoramento e dashboard da Sprint 4.

Esse formato deixa clara a evolução do trabalho e facilita a explicação para o professor.
