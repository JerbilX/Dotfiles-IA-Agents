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
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "list_dir"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "grep_search"}]},
                {"source": "MODEL", "type": "PLANNER_RESPONSE", "tool_calls": [{"name": "find_by_name"}]},
            ]
            with open(tfile, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(json.dumps(l) + "\n")

            payload = {
                "toolCall": {"name": "view_file", "args": {}},
                "stepIdx": 7,
                "transcriptPath": str(tfile),
            }
            res = cb_mod.evaluate_pre_tool_use(payload)
            self.assertEqual(res["decision"], "deny")
            self.assertIn("Hard Circuit Breaker Activado", res["reason"])
            # ADR-0046: la salida prescrita es la síntesis, no una edición provisoria
            self.assertIn("Detente y sintetiza", res["reason"])
            self.assertIn("Prohibido usar ediciones provisorias", res["reason"])
            self.assertNotIn("procede a editar", res["reason"])

    def test_default_limit_is_six(self):
        self.assertEqual(cb_mod.DEFAULT_MAX_PASSIVE_READS, 6)

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


class TestClaudeCodeSupport(unittest.TestCase):
    """Payload, transcript y salida de Claude Code (#287, ADR-0051)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.transcript = self.dir / "session.jsonl"
        self.records = []
        self.n = 0
        self.user("arrancá")

    def tearDown(self):
        self.tmp.cleanup()

    # -- Constructores de transcript con el formato real de Claude Code --
    def user(self, text):
        self.records.append({"type": "user", "isSidechain": False, "message": {"role": "user", "content": text}})

    def call(self, name, tool_input, completed=True, message_id=None):
        self.n += 1
        tid = f"toolu_{self.n}"
        mid = message_id or f"msg_{self.n}"
        self.records.append({
            "type": "assistant", "isSidechain": False,
            "message": {"id": mid, "role": "assistant",
                        "content": [{"type": "tool_use", "id": tid, "name": name, "input": tool_input}]},
        })
        if completed:
            self.records.append({
                "type": "user", "isSidechain": False,
                "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok"}]},
            })

    def evaluate(self, name, tool_input):
        with open(self.transcript, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r) + "\n")
        payload = {"hook_event_name": "PreToolUse", "transcript_path": str(self.transcript),
                   "tool_name": name, "tool_input": tool_input}
        self.assertTrue(cb_mod.is_claude_payload(payload))
        return cb_mod.evaluate_claude_pre_tool_use(payload)

    def short_file(self, name="a.py", lines=10):
        p = self.dir / name
        p.write_text("x\n" * lines, encoding="utf-8")
        return str(p)

    # -- Circuit breaker --
    def test_seventh_passive_read_denied(self):
        for i in range(6):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        res = self.evaluate("Grep", {"pattern": "x", "path": str(self.dir)})
        self.assertEqual(res["decision"], "deny")
        self.assertIn("6 lecturas pasivas", res["reason"])

    def test_sixth_read_allowed(self):
        for i in range(5):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "allow")

    def test_passive_bash_counts_as_read(self):
        for i in range(6):
            self.call("Bash", {"command": f"grep -n foo file{i}.py | head -n 20"})
        res = self.evaluate("Bash", {"command": "cat other.py"})
        self.assertEqual(res["decision"], "deny")

    def test_active_bash_resets_counter(self):
        for i in range(5):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        self.call("Bash", {"command": "python3 -m unittest tests/test_x.py"})
        self.call("Read", {"file_path": self.short_file("g.py")})
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("h.py")})["decision"], "allow")

    def test_active_bash_candidate_always_allowed(self):
        for i in range(8):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        self.assertEqual(self.evaluate("Bash", {"command": "./build.sh check"})["decision"], "allow")

    def test_edit_test_cycle_not_treated_as_ping_pong(self):
        target = self.short_file("bar.py")
        for _ in range(2):
            self.call("Edit", {"file_path": target, "old_string": "a", "new_string": "b"})
            self.call("Bash", {"command": "python3 -m unittest tests/test_bar.py"})
        self.call("Edit", {"file_path": target, "old_string": "a", "new_string": "b"})
        self.assertEqual(self.evaluate("Bash", {"command": "python3 -m unittest tests/test_bar.py"})["decision"], "allow")

    def test_tool_results_do_not_reset_counter_and_user_does(self):
        for i in range(6):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        self.user("seguí")
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "allow")

    def test_meta_and_sidechain_records_ignored(self):
        for i in range(6):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        self.records.append({"type": "user", "isMeta": True, "message": {"role": "user", "content": "<system-reminder>"}})
        self.records.append({"type": "user", "isSidechain": True, "message": {"role": "user", "content": "subagente"}})
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "deny")

    def test_parallel_calls_of_one_message_count_as_one_step(self):
        for i in range(5):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        for j in range(3):  # tres lecturas paralelas en el mismo mensaje
            self.call("Read", {"file_path": self.short_file(f"p{j}.py")}, message_id="msg_parallel")
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "deny")
        self.records = self.records[:1]
        for i in range(4):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        for j in range(3):
            self.call("Read", {"file_path": self.short_file(f"p{j}.py")}, message_id="msg_parallel")
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "allow")

    def test_pending_tool_use_not_counted(self):
        for i in range(5):
            self.call("Read", {"file_path": self.short_file(f"f{i}.py")})
        # La llamada en curso ya escrita en el transcript, sin tool_result todavía.
        self.call("Read", {"file_path": self.short_file("g.py")}, completed=False)
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("g.py")})["decision"], "allow")

    # -- Paginación --
    def test_unpaged_read_of_long_file_denied(self):
        res = self.evaluate("Read", {"file_path": self.short_file("long.py", 151)})
        self.assertEqual(res["decision"], "deny")
        self.assertIn("long.py", res["reason"])

    def test_unpaged_read_of_short_file_allowed(self):
        self.assertEqual(self.evaluate("Read", {"file_path": self.short_file("ok.py", 150)})["decision"], "allow")

    def test_window_over_200_denied_and_within_allowed(self):
        long_file = self.short_file("long.py", 500)
        self.assertEqual(self.evaluate("Read", {"file_path": long_file, "offset": 1, "limit": 201})["decision"], "deny")
        self.assertEqual(self.evaluate("Read", {"file_path": long_file, "offset": 1, "limit": 50})["decision"], "allow")

    def test_non_text_and_missing_files_not_paged(self):
        img = self.dir / "big.png"
        img.write_bytes(b"\n" * 500)
        self.assertEqual(self.evaluate("Read", {"file_path": str(img)})["decision"], "allow")
        self.assertEqual(self.evaluate("Read", {"file_path": str(self.dir / "nope.py")})["decision"], "allow")

    # -- Clasificación de Bash --
    def test_shell_classification(self):
        passive = [
            "cat a.py",
            "grep -rn foo lib | head -n 20",
            "sed -n 1,40p lib/x.sh; wc -l lib/x.sh",
            "git log --oneline -5",
            "git -C repo diff --stat",
            "gh issue view 287 --json body --jq .body",
            "for i in 1 2; do gh pr view $i; done",
            "ls skills 2>/dev/null | head",
            "find . -name '*.py'",
        ]
        active = [
            "python3 -m unittest",
            "./build.sh check",
            "sed -i 's/a/b/' x",
            "cat a > b",
            "echo x | tee out.txt",
            "git commit -F .commit_msg",
            "git push -u origin feat/x",
            "gh pr create --body-file .pr_body",
            "find . -name '*.pyc' -delete",
            "f=$(ls -t | head -n 1)",
            "FOO=1 cat a",
            "cat <<EOF > x",
            "",
        ]
        for cmd in passive:
            self.assertTrue(cb_mod.is_passive_shell_command(cmd), cmd)
        for cmd in active:
            self.assertFalse(cb_mod.is_passive_shell_command(cmd), cmd)

    # -- Formato de salida --
    def test_output_only_on_deny(self):
        self.assertIsNone(cb_mod.to_claude_output({"decision": "allow"}))
        out = cb_mod.to_claude_output({"decision": "deny", "reason": "r"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecisionReason"], "r")

    def test_main_end_to_end_via_stdin(self):
        import subprocess
        import sys
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                   "tool_input": {"file_path": self.short_file("long.py", 300)}, "transcript_path": ""}
        proc = subprocess.run([sys.executable, "-I", str(bin_path)], input=json.dumps(payload),
                              capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        payload["tool_input"] = {"file_path": self.short_file("ok.py", 5)}
        proc = subprocess.run([sys.executable, "-I", str(bin_path)], input=json.dumps(payload),
                              capture_output=True, text=True, check=True)
        self.assertEqual(proc.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
