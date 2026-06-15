"""Implementação evolutiva do projeto completo (Sprints 1–4).

Este módulo reúne os blocos básicos das quatro sprints em uma única
linha de evolução: heartbeat, tarefas, negociação Master-to-Master e
monitoramento final para supervisor.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def build_heartbeat_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta de heartbeat da Sprint 1."""
    return {
        "SERVER_UUID": payload.get("SERVER_UUID", "Master_A"),
        "TASK": "HEARTBEAT",
        "RESPONSE": "ALIVE",
    }


def build_task_response(user: str, task_type: str = "QUERY") -> Dict[str, Any]:
    """Resposta de tarefa da Sprint 2."""
    return {"TASK": task_type, "USER": user}


def build_status_response(worker_uuid: str, status: str = "OK") -> Dict[str, Any]:
    """Resposta de status da Sprint 2."""
    return {"STATUS": status, "TASK": "QUERY", "WORKER_UUID": worker_uuid}


def build_ack_response(worker_uuid: str) -> Dict[str, Any]:
    """ACK final da Sprint 2."""
    return {"STATUS": "ACK", "WORKER_UUID": worker_uuid}


def build_help_request(master_id: str, current_load: int, capacity: int, workers_needed: int) -> Dict[str, Any]:
    """Pedido de ajuda da Sprint 3."""
    return {
        "type": "request_help",
        "request_id": str(uuid.uuid4()),
        "payload": {
            "master_id": master_id,
            "current_load": current_load,
            "capacity": capacity,
            "workers_needed": workers_needed,
        },
    }


def build_supervisor_report(server_uuid: str = "michel_1", role: str = "master") -> Dict[str, Any]:
    """Payload de monitoramento da Sprint 4."""
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "server_uuid": server_uuid,
        "hostname": f"{server_uuid}.farm.local",
        "role": role,
        "task": "performance_report",
        "timestamp": now,
        "message_id": str(uuid.uuid4()),
        "payload_version": "sprint4-monitor",
        "performance": {
            "system": {
                "uptime_seconds": 0,
                "load_average_1m": 0.0,
                "load_average_5m": 0.0,
                "cpu": {"usage_percent": 0.0, "count_logical": 1, "count_physical": 1},
                "memory": {"total_mb": 0, "available_mb": 0, "percent_used": 0.0, "memory_used": 0},
                "disk": {"total_gb": 0.0, "free_gb": 0.0, "percent_used": 0.0},
            },
            "farm_state": {
                "workers": {
                    "total_registered": 0,
                    "workers_utilization": 0,
                    "workers_alive": 0,
                    "workers_idle": 0,
                    "workers_borrowed": 0,
                    "workers_received": 0,
                    "workers_failed": 0,
                    "workers_home": 0,
                    "workers_available_capacity": 0,
                    "borrowed_workers": [],
                },
                "tasks": {
                    "tasks_pending": 0,
                    "tasks_running": 0,
                    "tasks_completed": 0,
                    "tasks_failed": 0,
                    "oldest_task_age_s": 0,
                },
            },
            "config_thresholds": {"max_task": 100, "warn_cpu_percent": 85, "warn_memory_percent": 85, "release_task": 60},
            "neighbors": [],
        },
    }


def validate_evolution_payload(payload: Dict[str, Any]) -> bool:
    """Valida um payload evolutivo contendo as etapas das quatro sprints."""
    if not isinstance(payload, dict):
        return False

    required = ["stage", "heartbeat", "task", "negotiation", "supervisor"]
    if any(field not in payload for field in required):
        return False

    heartbeat = payload.get("heartbeat")
    task = payload.get("task")
    negotiation = payload.get("negotiation")
    supervisor = payload.get("supervisor")

    if not isinstance(heartbeat, dict) or heartbeat.get("TASK") != "HEARTBEAT":
        return False
    if not isinstance(task, dict) or task.get("TASK") not in ("QUERY", "NO_TASK"):
        return False
    if not isinstance(negotiation, dict) or negotiation.get("type") not in ("request_help", "response_accepted", "response_rejected"):
        return False
    if not isinstance(supervisor, dict) or supervisor.get("task") != "performance_report":
        return False

    return True


def serialize_payload(payload: Dict[str, Any]) -> str:
    """Serializa o payload com delimitador newline, como previsto no projeto."""
    return json.dumps(payload) + "\n"
