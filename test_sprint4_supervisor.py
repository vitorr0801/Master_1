import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import sprint4_supervisor_client as supervisor


class TestSprint4Supervisor(unittest.TestCase):
    def test_build_performance_report_contains_required_fields(self):
        payload = supervisor.build_performance_report(
            server_uuid="michel_1",
            role="master",
            task="performance_report",
        )

        self.assertEqual(payload["server_uuid"], "michel_1")
        self.assertEqual(payload["role"], "master")
        self.assertEqual(payload["task"], "performance_report")
        self.assertIn("performance", payload)
        self.assertIn("system", payload["performance"])
        self.assertIn("farm_state", payload["performance"])
        self.assertIn("config_thresholds", payload["performance"])
        self.assertIn("neighbors", payload["performance"])

    def test_payload_is_json_serializable(self):
        payload = supervisor.build_performance_report(server_uuid="michel_1")
        json.dumps(payload)

    def test_validate_payload_accepts_expected_structure(self):
        payload = supervisor.build_performance_report(server_uuid="michel_1")
        self.assertTrue(supervisor.validate_payload(payload))

    def test_default_server_uuid_matches_professor_example(self):
        payload = supervisor.build_performance_report()
        self.assertEqual(payload["server_uuid"], "michel_1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
