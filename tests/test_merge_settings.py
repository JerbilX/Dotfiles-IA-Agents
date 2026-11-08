#!/usr/bin/env python3
"""Tests de lib/merge_settings.py (ADR-0045, #249)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(REPO_ROOT, "lib", "merge_settings.py")


class TestMergeSettings(unittest.TestCase):

    def _run(self, fragment, target):
        with tempfile.TemporaryDirectory() as d:
            f_path = os.path.join(d, "fragment.json")
            t_path = os.path.join(d, "settings.json")
            with open(f_path, "w", encoding="utf-8") as f:
                json.dump(fragment, f)
            if target is not None:
                with open(t_path, "w", encoding="utf-8") as f:
                    json.dump(target, f)
            for _ in range(2):  # segunda corrida: idempotencia
                subprocess.run([sys.executable, "-I", SCRIPT, f_path, t_path], check=True,
                               stdout=subprocess.DEVNULL)
            with open(t_path, encoding="utf-8") as f:
                return json.load(f)

    def test_preserves_user_keys_and_merges_without_duplicates(self):
        result = self._run(
            {"permissions": {"allow": ["Bash(git status:*)", "Bash(ls:*)"]}},
            {"theme": "auto", "permissions": {"allow": ["Bash(ls:*)"]}},
        )
        self.assertEqual(result["theme"], "auto")
        self.assertEqual(result["permissions"]["allow"], ["Bash(ls:*)", "Bash(git status:*)"])

    def test_expands_dotfiles_root_to_absolute_rule(self):
        result = self._run({"permissions": {"allow": ["Read(/${DOTFILES_ROOT}/core/**)"]}}, None)
        self.assertEqual(result["permissions"]["allow"], [f"Read(/{REPO_ROOT}/core/**)"])
        self.assertTrue(result["permissions"]["allow"][0].startswith("Read(//"))

    def test_runtime_claude_settings_reference_real_paths(self):
        with open(os.path.join(REPO_ROOT, "runtimes", "claude", "settings.json"), encoding="utf-8") as f:
            allow = json.load(f)["permissions"]["allow"]
        self.assertIn("Read(/${DOTFILES_ROOT}/skills/**)", allow)
        # ADR-0047: el prompt compilado es autosuficiente; no se habilitan lecturas sobre core/
        self.assertFalse(any("/core/" in rule for rule in allow))

    # --- Hooks (ADR-0051, #287) ---

    CB = "${DOTFILES_ROOT}/skills/conversation-audit/bin/agent-circuit-breaker"

    def _hook_entry(self, matcher, command):
        return {"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": 5}]}

    def test_merges_hooks_preserving_user_hooks_idempotently(self):
        user_entry = self._hook_entry("Write", "user-guard")
        result = self._run(
            {"hooks": {"PreToolUse": [self._hook_entry("Read|Bash", self.CB)]}},
            {"hooks": {"PreToolUse": [user_entry], "Stop": [self._hook_entry("", "notify")]}},
        )
        pre = result["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 2)  # _run ejecuta dos veces: sin duplicados
        self.assertEqual(pre[0], user_entry)
        self.assertEqual(pre[1]["hooks"][0]["command"],
                         f"{REPO_ROOT}/skills/conversation-audit/bin/agent-circuit-breaker")
        self.assertIn("Stop", result["hooks"])

    def test_matcher_change_replaces_owned_hook(self):
        expanded = self.CB.replace("${DOTFILES_ROOT}", REPO_ROOT)
        result = self._run(
            {"hooks": {"PreToolUse": [self._hook_entry("Read|Grep|Glob|Bash", self.CB)]}},
            {"hooks": {"PreToolUse": [self._hook_entry("Read", expanded)]}},
        )
        pre = result["hooks"]["PreToolUse"]
        self.assertEqual([e["matcher"] for e in pre], ["Read|Grep|Glob|Bash"])

    def test_runtime_claude_settings_declare_circuit_breaker_hook(self):
        with open(os.path.join(REPO_ROOT, "runtimes", "claude", "settings.json"), encoding="utf-8") as f:
            pre = json.load(f)["hooks"]["PreToolUse"]
        commands = {h["command"]: e["matcher"] for e in pre for h in e["hooks"]}
        self.assertIn(self.CB, commands)
        self.assertEqual(set(commands[self.CB].split("|")), {"Read", "Grep", "Glob", "Bash"})
        self.assertTrue(os.access(self.CB.replace("${DOTFILES_ROOT}", REPO_ROOT), os.X_OK))


if __name__ == "__main__":
    unittest.main()
