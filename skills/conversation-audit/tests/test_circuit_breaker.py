import json
import tempfile
import unittest
from pathlib import Path
import types

# Cargar dinámicamente el script sin extensión de bin/
bin_path = Path(__file__).parent.parent / "bin" / "agent-circuit-breaker"
cb_mod = types.ModuleType("agent_circuit_breaker")
with open(bin_path, "r", encoding="utf-8") as f:
    exec(f.read(), cb_mod.__dict__)


class TestAgentCircuitBreaker(unittest.TestCase):
    def test_active_tool_always_allowed(self):
        payload = {
            "toolCall": {"name": "replace_file_content", "args": {}},
            "stepIdx": 5,
        }
        res = cb_mod.evaluate_pre_tool_use(payload)
        self.assertEqual(res["decision"], "allow")

    def test_passive_tool_without_transcript_allowed(self):
        payload = {
            "toolCall": {"name": "view_file", "args": {}},
            "stepIdx": 5,
        }
        res = cb_mod.evaluate_pre_tool_use(payload)
        self.assertEqual(res["decision"], "allow")

    def test_passive_tool_under_threshold_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "hola"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "view_file", "args": {}},
                "stepIdx": 3,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "allow")

    def test_passive_tool_exceeding_threshold_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "hola"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "grep_search"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "find_by_name"}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "view_file", "args": {}},
                "stepIdx": 4,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "deny")
            self.assertIn("Hard Circuit Breaker Activado", res["reason"])

    def test_active_tool_resets_counter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "hola"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file"}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "view_file", "args": {}},
                "stepIdx": 5,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "allow")

    def test_ping_pong_view_file_and_run_command_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "fix bug"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/foo.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command", "args": {"CommandLine": "pytest"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/foo.py"}}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
                "stepIdx": 4,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "deny")
            self.assertIn("Hard Circuit Breaker Activado", res["reason"])
            self.assertIn("ping-pong", res["reason"])
            self.assertIn("view_file:foo.py <-> run_command", res["reason"])

    def test_ping_pong_view_file_and_replace_content_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "fix bug"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/bar.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "replace_file_content", "args": {"TargetFile": "/repo/bar.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/bar.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "replace_file_content", "args": {"TargetFile": "/repo/bar.py"}}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "view_file", "args": {"AbsolutePath": "/repo/bar.py"}},
                "stepIdx": 5,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "deny")
            self.assertIn("Hard Circuit Breaker Activado", res["reason"])
            self.assertIn("ping-pong", res["reason"])

    def test_ping_pong_depth_6_three_phase_cycle_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "refactor"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/a.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "replace_file_content", "args": {"TargetFile": "/repo/a.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command", "args": {"CommandLine": "make test"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/a.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "replace_file_content", "args": {"TargetFile": "/repo/a.py"}}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "run_command", "args": {"CommandLine": "make test"}},
                "stepIdx": 6,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "deny")
            self.assertIn("Hard Circuit Breaker Activado", res["reason"])
            self.assertIn("view_file:a.py -> replace_file_content:a.py -> run_command", res["reason"])

    def test_user_intervention_resets_ping_pong(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "fix bug"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/foo.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command", "args": {"CommandLine": "pytest"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/foo.py"}}]},
                {"source": "USER", "type": "USER_INPUT", "content": "por favor revisa baz.py"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/foo.py"}}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest"}},
                "stepIdx": 6,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "allow")

    def test_linear_flow_not_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tfile = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"source": "USER", "type": "USER_INPUT", "content": "start"},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/a.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "replace_file_content", "args": {"TargetFile": "/repo/a.py"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command", "args": {"CommandLine": "pytest"}}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/repo/b.py"}}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "replace_file_content", "args": {"TargetFile": "/repo/b.py"}},
                "stepIdx": 5,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
