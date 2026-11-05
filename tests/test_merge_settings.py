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


if __name__ == "__main__":
    unittest.main()
