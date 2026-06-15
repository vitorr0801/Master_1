import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import sprint4_supervisor_client as supervisor


class TestDashboardIntegration(unittest.TestCase):
    def test_build_dashboard_payload_includes_required_fields(self):
        payload = supervisor.build_performance_report(server_uuid="michel_1", role="master")

        self.assertEqual(payload["server_uuid"], "michel_1")
        self.assertEqual(payload["role"], "master")
        self.assertEqual(payload["task"], "performance_report")
        self.assertIn("performance", payload)
        self.assertIn("farm_state", payload["performance"])
        self.assertIn("workers", payload["performance"]["farm_state"])
        self.assertIn("tasks", payload["performance"]["farm_state"])
        self.assertTrue(supervisor.validate_payload(payload))


if __name__ == "__main__":
    unittest.main(verbosity=2)
