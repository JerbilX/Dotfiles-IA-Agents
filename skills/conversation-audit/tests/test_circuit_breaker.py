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


if __name__ == "__main__":
    unittest.main()
