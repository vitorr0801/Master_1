"""Módulo de Sprint 4 para envio de métricas ao supervisor do cluster.

Este módulo fornece:
- geração de payload JSON de desempenho;
- validação do payload;
- envio seguro via TLS/TCP ao supervisor.

Ele foi implementado de forma isolada para não alterar os arquivos da Sprint 3
já existentes, mantendo a evolução do projeto em Python separado.
"""

import json
import os
import socket
import ssl
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - fallback seguro
    psutil = None


DEFAULT_SUPERVISOR_HOST = "nuted-ia.dev"
DEFAULT_SUPERVISOR_PORT = 443
DEFAULT_TLSSNI = "nuted-ia.dev"
DEFAULT_PAYLOAD_VERSION = "sprint4-monitor"
DEFAULT_SERVER_UUID = "michel_1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _collect_system_metrics() -> Dict[str, Any]:
    """Coleta métricas do sistema com fallback seguro se o psutil não estiver disponível."""
    system = {
        "uptime_seconds": 0,
        "load_average_1m": 0.0,
        "load_average_5m": 0.0,
        "cpu": {
            "usage_percent": 0.0,
            "count_logical": 1,
            "count_physical": 1,
        },
        "memory": {
            "total_mb": 0,
            "available_mb": 0,
            "percent_used": 0.0,
            "memory_used": 0,
        },
        "disk": {
            "total_gb": 0.0,
            "free_gb": 0.0,
            "percent_used": 0.0,
        },
    }

    if psutil is not None:
        try:
            boot_time = psutil.boot_time()
            system["uptime_seconds"] = max(0, int(time.time() - boot_time))
            system["cpu"]["usage_percent"] = _safe_float(psutil.cpu_percent(interval=None))
            logical = psutil.cpu_count(logical=True) or 1
            physical = psutil.cpu_count(logical=False) or 1
            system["cpu"]["count_logical"] = logical
            system["cpu"]["count_physical"] = physical

            mem = psutil.virtual_memory()
            system["memory"]["total_mb"] = _safe_int(mem.total / (1024 * 1024))
            system["memory"]["available_mb"] = _safe_int(mem.available / (1024 * 1024))
            system["memory"]["percent_used"] = _safe_float(mem.percent)
            system["memory"]["memory_used"] = _safe_int(mem.used / (1024 * 1024))

            disk = psutil.disk_usage('/')
            system["disk"]["total_gb"] = _safe_float(disk.total / (1024 ** 3))
            system["disk"]["free_gb"] = _safe_float(disk.free / (1024 ** 3))
            system["disk"]["percent_used"] = _safe_float(disk.percent)
        except Exception:
            # mantém os valores padrão em caso de falha de coleta
            pass

    return system


def _default_farm_state() -> Dict[str, Any]:
    return {
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
    }


def _default_config_thresholds() -> Dict[str, Any]:
    return {
        "max_task": 100,
        "warn_cpu_percent": 85,
        "warn_memory_percent": 85,
        "release_task": 60,
    }


def _default_neighbors() -> list:
    return []


def build_performance_report(
    server_uuid: Optional[str] = None,
    hostname: Optional[str] = None,
    role: str = "master",
    task: str = "performance_report",
    payload_version: str = DEFAULT_PAYLOAD_VERSION,
    performance: Optional[Dict[str, Any]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Constrói um payload de métricas para o supervisor.

    Se performance não for fornecido, usa dados do sistema com fallback seguro.
    """
    server_uuid = server_uuid or os.getenv("SERVER_UUID", DEFAULT_SERVER_UUID)
    hostname = hostname or os.getenv("HOSTNAME", socket.gethostname())

    report = {
        "server_uuid": server_uuid,
        "hostname": hostname,
        "role": role,
        "task": task,
        "timestamp": _utc_now(),
        "message_id": str(uuid.uuid4()),
        "payload_version": payload_version,
        "performance": {
            "system": _collect_system_metrics(),
            "farm_state": performance.get("farm_state", _default_farm_state()) if performance else _default_farm_state(),
            "config_thresholds": performance.get("config_thresholds", _default_config_thresholds()) if performance else _default_config_thresholds(),
            "neighbors": performance.get("neighbors", _default_neighbors()) if performance else _default_neighbors(),
        },
    }

    if performance and "system" in performance:
        report["performance"]["system"] = performance["system"]

    if extra_fields:
        report.update(extra_fields)

    return report


def validate_payload(payload: Dict[str, Any]) -> bool:
    """Valida o payload mínimo exigido pela Sprint 4.

    Retorna True quando os campos obrigatórios existem e o formato está consistente.
    """
    required_top = ["server_uuid", "hostname", "role", "task", "timestamp", "message_id", "payload_version", "performance"]
    if not isinstance(payload, dict):
        return False

    if any(field not in payload for field in required_top):
        return False

    performance = payload.get("performance")
    if not isinstance(performance, dict):
        return False

    required_perf = ["system", "farm_state", "config_thresholds", "neighbors"]
    if any(field not in performance for field in required_perf):
        return False

    system = performance.get("system")
    if not isinstance(system, dict) or not isinstance(system.get("cpu"), dict) or not isinstance(system.get("memory"), dict) or not isinstance(system.get("disk"), dict):
        return False

    farm_state = performance.get("farm_state")
    if not isinstance(farm_state, dict) or not isinstance(farm_state.get("workers"), dict) or not isinstance(farm_state.get("tasks"), dict):
        return False

    return True


def send_report(
    payload: Dict[str, Any],
    host: str = DEFAULT_SUPERVISOR_HOST,
    port: int = DEFAULT_SUPERVISOR_PORT,
    tls: bool = True,
    sni: Optional[str] = None,
    timeout: int = 10,
) -> bool:
    """Envia o payload para o supervisor.

    O comportamento é seguro e não bloqueia a execução principal do projeto:
    abre socket, envia JSON e encerra a conexão. Se o envio falhar, retorna False.
    """
    if not validate_payload(payload):
        raise ValueError("Payload inválido para o supervisor da Sprint 4.")

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        if tls:
            context = ssl.create_default_context()
            wrapped = context.wrap_socket(sock, server_hostname=sni or host)
            wrapped.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            wrapped.close()
        else:
            sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            sock.close()
        return True
    except Exception:
        return False


def main(argv: Optional[list[str]] = None) -> int:
    """Entrada CLI simples para teste rápido do módulo.

    Exemplo:
        python sprint4_supervisor_client.py
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    server_uuid = argv[0] if argv else os.getenv("SERVER_UUID", "master_local")
    role = argv[1] if len(argv) > 1 else "master"

    payload = build_performance_report(server_uuid=server_uuid, role=role)
    print(json.dumps(payload, indent=2))

    ok = send_report(payload)
    print("\nSTATUS_ENVIO:", "OK" if ok else "FALHA")
    return 0 if ok or True else 1


if __name__ == "__main__":
    raise SystemExit(main())
