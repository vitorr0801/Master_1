"""Monitor da Sprint 4 para envio periódico de métricas ao supervisor.

Este módulo é independente das sprints 1–3 e oferece uma forma simples de:
1. gerar um payload de performance baseado no sistema local;
2. enviar esse payload ao supervisor em TLS/TCP;
3. repetir o envio em intervalos configuráveis.

Uso:
    python sprint4_monitor.py --once
    python sprint4_monitor.py --interval 10
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from typing import Optional

from sprint4_supervisor_client import build_performance_report, send_report, validate_payload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sprint4_monitor")

RUNNING = True


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor da Sprint 4")
    parser.add_argument("--server-uuid", default=None, help="Identificador do nó no cluster")
    parser.add_argument("--role", default="master", help="Papel do nó (master/worker)")
    parser.add_argument("--host", default="nuted-ia.dev", help="Host do supervisor")
    parser.add_argument("--port", type=int, default=443, help="Porta do supervisor")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo em segundos entre envios")
    parser.add_argument("--once", action="store_true", help="Envia uma única mensagem e encerra")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout do socket em segundos")
    return parser.parse_args(argv)


def build_report(server_uuid: Optional[str], role: str) -> dict:
    payload = build_performance_report(server_uuid=server_uuid, role=role)
    if not validate_payload(payload):
        raise ValueError("Payload inválido gerado pelo monitor da Sprint 4")
    return payload


def send_once(server_uuid: Optional[str], role: str, host: str, port: int, timeout: int) -> bool:
    payload = build_report(server_uuid, role)
    logger.info("Enviando payload para o supervisor: %s", payload["message_id"])
    ok = send_report(payload, host=host, port=port, tls=True, sni=host, timeout=timeout)
    logger.info("Resultado do envio: %s", "OK" if ok else "FALHA")
    return ok


def run_forever(server_uuid: Optional[str], role: str, host: str, port: int, interval: int, timeout: int) -> None:
    global RUNNING

    def handle_signal(signum, _frame):
        global RUNNING
        RUNNING = False
        logger.info("Sinal recebido (%s). Encerrando monitor da Sprint 4.", signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Monitor da Sprint 4 iniciado. Intervalo=%ss host=%s:%s", interval, host, port)

    try:
        while RUNNING:
            try:
                send_once(server_uuid, role, host, port, timeout)
            except Exception as exc:
                logger.error("Erro ao enviar métricas: %s", exc)
            time.sleep(interval)
    finally:
        logger.info("Monitor da Sprint 4 encerrado.")


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    try:
        if args.once:
            ok = send_once(args.server_uuid, args.role, args.host, args.port, args.timeout)
            return 0 if ok else 1

        run_forever(args.server_uuid, args.role, args.host, args.port, args.interval, args.timeout)
        return 0
    except KeyboardInterrupt:
        logger.info("Execução interrompida pelo usuário.")
        return 130
    except Exception as exc:
        logger.error("Falha crítica do monitor: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
