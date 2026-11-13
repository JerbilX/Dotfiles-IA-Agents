#!/usr/bin/env python3
"""Tests de lib/merge_mcp.py (ADR-0057, #375)."""

import glob
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(REPO_ROOT, "lib", "merge_mcp.py")

LEANTOKEN = {"command": "npx", "args": ["-y", "leantoken", "mcp"], "env": {}}


class TestMergeMcp(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name
        self.dist = os.path.join(self.home, "dist_mcp_config.json")
        self.target = os.path.join(self.home, ".claude.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, path, data, mode=None):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if mode is not None:
            os.chmod(path, mode)

    def _run(self, servers, managed=("leantoken",)):
        self._write(self.dist, {"mcpServers": servers})
        subprocess.run([sys.executable, "-I", SCRIPT, self.dist, self.target, *managed],
                       check=True, stdout=subprocess.DEVNULL)
        with open(self.target, encoding="utf-8") as f:
            return json.load(f)

    def _backups(self):
        return glob.glob(f"{self.target}.bak.*")

    def test_adds_server_to_missing_target(self):
        result = self._run({"leantoken": LEANTOKEN})
        self.assertEqual(result["mcpServers"], {"leantoken": LEANTOKEN})
        self.assertEqual(stat.S_IMODE(os.stat(self.target).st_mode), 0o600)
        self.assertEqual(self._backups(), [])

    def test_preserves_user_keys_and_servers_with_backup_and_mode(self):
        user = {"numStartups": 7, "projects": {"/x": {}}, "mcpServers": {"mine": {"command": "foo"}}}
        self._write(self.target, user, mode=0o600)
        result = self._run({"leantoken": LEANTOKEN})
        self.assertEqual(result["numStartups"], 7)
        self.assertEqual(result["projects"], {"/x": {}})
        self.assertEqual(result["mcpServers"], {"mine": {"command": "foo"}, "leantoken": LEANTOKEN})
        self.assertEqual(stat.S_IMODE(os.stat(self.target).st_mode), 0o600)
        backups = self._backups()
        self.assertEqual(len(backups), 1)
        with open(backups[0], encoding="utf-8") as f:
            self.assertEqual(json.load(f), user)

    def test_idempotent_without_new_backups(self):
        self._write(self.target, {"theme": "dark"})
        first = self._run({"leantoken": LEANTOKEN})
        second = self._run({"leantoken": LEANTOKEN})
        self.assertEqual(first, second)
        self.assertEqual(len(self._backups()), 1)

    def test_removes_disabled_managed_server_only(self):
        self._write(self.target, {"mcpServers": {"leantoken": LEANTOKEN, "mine": {"command": "foo"}}})
        result = self._run({}, managed=("leantoken",))
        self.assertEqual(result["mcpServers"], {"mine": {"command": "foo"}})

    def test_invalid_target_json_is_not_modified(self):
        with open(self.target, "w", encoding="utf-8") as f:
            f.write("{roto")
        self._write(self.dist, {"mcpServers": {"leantoken": LEANTOKEN}})
        proc = subprocess.run([sys.executable, "-I", SCRIPT, self.dist, self.target],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        with open(self.target, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{roto")

    def test_claude_runtime_declares_merge_file(self):
        with open(os.path.join(REPO_ROOT, "runtimes", "claude", "config.json"), encoding="utf-8") as f:
            target = json.load(f)["target"]
        self.assertEqual(target["mcp_merge_file"], "${HOME}/.claude.json")


if __name__ == "__main__":
    unittest.main()
