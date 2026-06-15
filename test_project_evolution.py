import json
import unittest

from project_evolution import (
    build_heartbeat_response,
    build_task_response,
    build_help_request,
    build_supervisor_report,
    validate_evolution_payload,
)


class TestProjectEvolution(unittest.TestCase):
    def test_heartbeat_pipeline(self):
        payload = {"SERVER_UUID": "Master_A", "TASK": "HEARTBEAT"}
        response = build_heartbeat_response(payload)
        self.assertEqual(response["TASK"], "HEARTBEAT")
        self.assertEqual(response["RESPONSE"], "ALIVE")

    def test_task_pipeline_query_and_ack(self):
        task = build_task_response("Michel")
        self.assertEqual(task["TASK"], "QUERY")
        self.assertEqual(task["USER"], "Michel")

        ack = {"STATUS": "ACK", "WORKER_UUID": "W-001"}
        self.assertEqual(ack["STATUS"], "ACK")

    def test_help_request_and_report(self):
        help_request = build_help_request("MASTER_A", 5, 3, 2)
        self.assertEqual(help_request["type"], "request_help")
        self.assertEqual(help_request["payload"]["master_id"], "MASTER_A")

        report = build_supervisor_report(server_uuid="michel_1")
        self.assertEqual(report["task"], "performance_report")
        self.assertIn("performance", report)

    def test_validate_evolution_payload_accepts_full_flow(self):
        payload = {
            "stage": "sprint4",
            "heartbeat": {"SERVER_UUID": "Master_A", "TASK": "HEARTBEAT"},
            "task": {"TASK": "QUERY", "USER": "Michel"},
            "negotiation": {"type": "request_help", "request_id": "x", "payload": {"master_id": "A"}},
            "supervisor": build_supervisor_report(server_uuid="michel_1"),
        }
        self.assertTrue(validate_evolution_payload(payload))


if __name__ == "__main__":
    unittest.main(verbosity=2)
