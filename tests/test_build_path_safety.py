#!/usr/bin/env python3
"""
Regression tests for path safety in build.sh (Issue #193).

- Rule files with spaces in their name must be compiled intact.
- A repository path containing a single quote must not break the Python fallbacks.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_SH = os.path.join(REPO_ROOT, "build.sh")
IGNORE = shutil.ignore_patterns(".git", "dist", "__pycache__", ".commit_msg", ".pr_body")


class TestBuildPathSafety(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        # Path with spaces and a single quote to exercise argv-based Python fallbacks.
        self.repo = os.path.join(self._tmp, "repo with 'quote'")
        shutil.copytree(REPO_ROOT, self.repo, ignore=IGNORE)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_rule_with_spaces_in_filename_is_compiled(self):
        marker = "MARKER_ISSUE_193_SPACED_RULE"
        rule = os.path.join(self.repo, "runtimes", "antigravity", "rules", "99 spaced rule.md")
        with open(rule, "w", encoding="utf-8") as f:
            f.write(f"# Spaced Rule\n\n{marker}\n")

        res = subprocess.run(
            [os.path.join(self.repo, "build.sh"), "build", "antigravity"],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"build failed:\n{res.stdout}\n{res.stderr}")

        found = False
        for root, _dirs, files in os.walk(os.path.join(self.repo, "dist")):
            for name in files:
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8") as fh:
                        if marker in fh.read():
                            found = True
                except (UnicodeDecodeError, IsADirectoryError):
                    continue
        self.assertTrue(found, "Rule with spaces in filename was not compiled into dist/")

    def test_no_shell_interpolation_inside_python_c(self):
        with open(BUILD_SH, "r", encoding="utf-8") as f:
            content = f.read()
        offenders = re.findall(r'python3 -c "[^"]*\$\{[^"]*"', content)
        self.assertEqual(offenders, [], f"Shell interpolation inside python3 -c: {offenders}")


if __name__ == "__main__":
    unittest.main()
