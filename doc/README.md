# Documentação do Projeto: P2P com Balanceamento de Carga Dinâmico

**Disciplina:** Arquitetura de Sistemas Distribuídos  
**Professor:** Prof. Michel Junio Ferreira Rosa  
**Data:** 2026-06-17

---

## 📋 Índice

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Sprints Implementadas](#sprints-implementadas)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Protocolo de Comunicação](#protocolo-de-comunicação)
5. [Implementação](#implementação)
6. [Testes e Validação](#testes-e-validação)
7. [Conclusões](#conclusões)

---

## Visão Geral do Projeto

Este projeto implementa um **sistema distribuído autônomo** que demonstra o conceito de **balanceamento de carga horizontal** através de uma arquitetura **P2P (Peer-to-Peer)**.

### Objetivo Principal

Desenvolver um sistema onde nós Masters gerenciam Workers de forma autônoma, detectam saturação de carga e, ao atingirem um limiar crítico, negociam dinamicamente o empréstimo de Workers de Masters vizinhos usando um **protocolo de consenso robusto**.

### Desafio Central

Garantir a **autonomia entre sistemas** desenvolvidos por diferentes equipes, permitindo que se interconectem e colaborem sem conhecimento prévio da implementação interna, apenas do protocolo de comunicação.

---

## Sprints Implementadas

| Sprint | Foco | Status |
|--------|------|--------|
| **Sprint 1** | Mecanismo de Heartbeat (Worker ↔ Master) | ✅ Concluída |
| **Sprint 2** | Comunicação de Tarefas e Ciclo Completo | ✅ Concluída |
| **Sprint 3** | Protocolo Master-to-Master e Redirecionamento | ✅ Concluída |
| **Sprint 4** | Apresentação Final e Supervisor de Métricas | ✅ Concluída |

---

## Arquitetura do Sistema

### Componentes Principais

```
┌─────────────────────────────────────────┐
│      Sistema Distribuído P2P             │
├─────────────────────────────────────────┤
│                                           │
│  ┌─── Master A ─────────┐   ┌─── Master B ───────┐
│  │                       │   │                     │
│  │  ┌──────────────────┐ │   │ ┌──────────────────┐│
│  │  │   Farm A         │ │   │ │   Farm B         ││
│  │  │ ┌─ W1 ─┐ ┌─ W2 ─┐│ │   │ │┌─ W3 ─┐ ┌─ W4 ─┐││
│  │  │ └─────┘ └─────┘│ │   │ │└─────┘ └─────┘││
│  │  └──────────────────┘ │   │ └──────────────────┘│
│  │                       │   │                     │
│  │  ┌──────────────────┐ │   │ ┌──────────────────┐│
│  │  │  Negociação M2M  │─┼───┼─│  Negociação M2M  ││
│  │  └──────────────────┘ │   │ └──────────────────┘│
│  └───────────────────────┘   └─────────────────────┘
│           │                              │
│           └──────────────────────────────┘
│         (Master-to-Master Communication)
│
└─────────────────────────────────────────┘
```

### Entidades

1. **Master Node**
   - Gerencia uma Farm de Workers
   - Monitora carga de requisições
   - Detecta saturação
   - Negocia com vizinhos
   - Redireciona Workers dinamicamente

2. **Worker Node**
   - Executa tarefas atribuídas
   - Suporta redirecionamento
   - Mantém heartbeat com Master
   - Reporta status de execução

3. **Protocolo de Comunicação**
   - **Sprint 1-2:** JSON via TCP (delimitador `\n`)
   - **Sprint 3:** Mensagens M2M com `type` e `request_id`
   - **Sprint 4:** Relatórios de métricas para Supervisor

---

## Protocolo de Comunicação

### Camadas de Comunicação

1. **Camada Worker-Master** (Sprints 1-2)
   - Heartbeat: verificação de disponibilidade
   - Task Cycle: solicitação, entrega e confirmação de tarefas

2. **Camada Master-Master** (Sprint 3)
   - Request Help: solicitação de recursos
   - Response: aceitação ou rejeição
   - Redirecionamento: comando para Workers
   - Devolução: retorno de Workers

3. **Camada Supervisor** (Sprint 4)
   - Performance Reports: métricas do cluster
   - Dashboard: visualização em tempo real

### Estrutura de Mensagem

```json
{
  "type": "tipo_da_mensagem",
  "request_id": "uuid_unico",
  "payload": {
    "dados_especificos": "..."
  }
}
```

---

## Implementação

### Arquivos Principais

| Arquivo | Responsabilidade |
|---------|------------------|
| `protocol.py` | Definição de payloads e encoding/decoding |
| `Master.py` | Servidor Master base (Sprints 1-2) |
| `master_sprint3.py` | Master com negociação M2M (Sprint 3) |
| `master_sprint4.py` | Master com supervisor (Sprint 4) |
| `Worker.py` | Cliente Worker base |
| `worker_sprint2.py` | Worker com suporte a tarefas |
| `worker_sprint4.py` | Worker com suporte a redirecionamento |
| `config.py` | Configurações globais |
| `network.py` | Utilitários de rede |

### Fluxo de Execução

1. **Inicialização**
   - Masters iniciam servidores TCP
   - Workers conectam aos Masters
   - Heartbeats começam

2. **Operação Normal**
   - Workers solicitam tarefas
   - Masters distribuem tarefas
   - Workers reportam status

3. **Detecção de Saturação**
   - Master monitora fila de tarefas
   - Se `current_load > capacity` → iniciar negociação

4. **Negociação e Redirecionamento**
   - Master A envia `request_help` para Master B
   - Master B responde com `response_accepted`
   - Master B envia `command_redirect` a Workers
   - Workers se reconectam ao Master A

5. **Liberação de Workers**
   - Quando carga normaliza
   - Master A envia `command_release`
   - Workers retornam ao Master original

---

## Testes e Validação

### Testes Implementados

- `test_master_imports.py` - Verificação de módulos
- `test_sprint3.py` - Protocolo M2M
- `test_sprint4_modules.py` - Integração Sprint 4
- `test_sprint4_supervisor.py` - Comunicação com Supervisor
- `test_dashboard_integration.py` - Visualização no Dashboard

### Cenários Validados

1. ✅ Heartbeat worker-master
2. ✅ Ciclo de tarefas completo
3. ✅ Detecção de saturação
4. ✅ Negociação M2M (aceita/rejeita)
5. ✅ Redirecionamento de Workers
6. ✅ Retorno de Workers
7. ✅ Envio de métricas para Supervisor
8. ✅ Visualização no Dashboard

---

## Conclusões

### Conquistas

1. **Comunicação Robusta**: Implementação de protocolo JSON com delimitação segura
2. **Distribuição de Carga**: Sistema de detecção e balanceamento automático
3. **Autonomia**: Masters operam independentemente com negociação consensual
4. **Observabilidade**: Dashboard em tempo real do cluster
5. **Interoperabilidade**: Protocolo padrão para comunicação entre equipes

### Desafios Superados

- Concorrência com threads/AsyncIO
- Sincronização entre Masters
- Tratamento de falhas de conexão
- Histerese para evitar oscilações

### Lições Aprendidas

- Importância de protocolo bem definido
- Necessidade de timeout em comunicação distribuída
- Valor da detecção de saturação com histerese
- Monitoramento essencial para debug

---

## Para Mais Detalhes

- [Visão Geral do Projeto](./0_VISAO_GERAL.md)
- [Sprint 1 - Heartbeat](./1_SPRINT_1_HEARTBEAT.md)
- [Sprint 2 - Task Cycle](./2_SPRINT_2_TASK_CYCLE.md)
- [Sprint 3 - Master-to-Master](./3_SPRINT_3_MASTER_TO_MASTER.md)
- [Sprint 4 - Supervisor](./4_SPRINT_4_SUPERVISOR.md)
- [Protocolo Completo](./PROTOCOLO_DEFINIDO.md)
- [Arquitetura Detalhada](./ARQUITETURA.md)
- [Implementação Técnica](./IMPLEMENTACAO.md)
- [Testes e Validação](./TESTES.md)

---

**Documentação Gerada:** 2026-06-17  
**Versão:** 1.0
