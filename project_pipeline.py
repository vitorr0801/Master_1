"""Pipeline evolutivo do projeto completo (Sprints 1–4).

Este arquivo consolida a construção do projeto em sequência:
1. Sprint 1 — Heartbeat
2. Sprint 2 — Tarefa / ACK
3. Sprint 3 — Pedido de ajuda entre Masters
4. Sprint 4 — Relatório para o supervisor

Objetivo: manter a evolução do projeto em um único fluxo Python,
permitindo demonstração e validação incremental.
"""

import json
import sys
from typing import Dict, Any

from project_evolution import (
    build_heartbeat_response,
    build_task_response,
    build_status_response,
    build_ack_response,
    build_help_request,
    build_supervisor_report,
    serialize_payload,
    validate_evolution_payload,
)


def build_project_evolution() -> Dict[str, Any]:
    """Montagem do fluxo completo do projeto em quatro estágios."""
    heartbeat_payload = {"SERVER_UUID": "Master_A", "TASK": "HEARTBEAT"}
    heartbeat_response = build_heartbeat_response(heartbeat_payload)

    task_payload = build_task_response("Michel")
    status_payload = build_status_response("W-001", "OK")
    ack_payload = build_ack_response("W-001")

    request_help = build_help_request("MASTER_A", current_load=5, capacity=3, workers_needed=2)
    supervisor_report = build_supervisor_report(server_uuid="michel_1", role="master")

    evolution = {
        "stage": "sprint4_final",
        "sprint_1": {
            "input": heartbeat_payload,
            "output": heartbeat_response,
        },
        "sprint_2": {
            "task": task_payload,
            "status": status_payload,
            "ack": ack_payload,
        },
        "sprint_3": {
            "request_help": request_help,
            "response": {
                "type": "response_accepted",
                "request_id": request_help["request_id"],
                "payload": {
                    "workers_offered": 2,
                    "worker_details": [
                        {"id": "W-B1", "address": "127.0.0.1:6001"},
                        {"id": "W-B2", "address": "127.0.0.1:6002"},
                    ],
                },
            },
        },
        "sprint_4": {
            "supervisor": supervisor_report,
            "serialized": serialize_payload(supervisor_report),
        },
    }

    return evolution


def main() -> int:
    """Executa a demonstração do projeto completo."""
    evolution = build_project_evolution()

    if not validate_evolution_payload(
        {
            "stage": evolution["stage"],
            "heartbeat": evolution["sprint_1"]["input"],
            "task": evolution["sprint_2"]["task"],
            "negotiation": evolution["sprint_3"]["request_help"],
            "supervisor": evolution["sprint_4"]["supervisor"],
        }
    ):
        print("Falha na validação do fluxo evolutivo.", file=sys.stderr)
        return 1

    print(json.dumps(evolution, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
