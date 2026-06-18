"""Launch-readiness guard tests."""
import os
import unittest
from unittest.mock import patch

from brain.pipeline import build_launch_readiness


class TestLaunchReadiness(unittest.TestCase):
    def test_live_exchange_gate_defaults_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            out = build_launch_readiness("mock", {"securities": 54, "events": 148}, "2026-06-18T00:00:00+00:00")
        self.assertFalse(out["summary"]["live_exchange_refresh_enabled"])
        gate = next(c for c in out["checks"] if c["id"] == "live_exchange_gate")
        self.assertEqual(gate["status"], "pass")
        self.assertIn("exits safely", gate["evidence"])

    def test_real_launch_blockers_are_explicit(self):
        out = build_launch_readiness("mock", {"securities": 54, "events": 148}, "2026-06-18T00:00:00+00:00")
        blocked = {c["id"] for c in out["checks"] if c["status"] == "blocked"}
        self.assertIn("data_rights", blocked)
        self.assertIn("sca_signoff", blocked)
        self.assertEqual(out["summary"]["real_launch_status"], "blocked")

    def test_gate_flag_is_visible(self):
        with patch.dict(os.environ, {"UAE_ALLOW_LIVE_EXCHANGE": "1"}, clear=True):
            out = build_launch_readiness("live", {"securities": 54, "events": 148}, "2026-06-18T00:00:00+00:00")
        self.assertTrue(out["summary"]["live_exchange_refresh_enabled"])
        gate = next(c for c in out["checks"] if c["id"] == "live_exchange_gate")
        self.assertEqual(gate["status"], "review")


if __name__ == "__main__":
    unittest.main()
