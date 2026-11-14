#!/usr/bin/env python3
"""
Pruebas unitarias para el CLI determinista issue-create (#384).
Verifica:
1. Validación estricta y obligatoria de perfil (--profile <low|medium|high|pro> o --label "profile:*").
2. Resolución determinista de .repo-config.json con fallback por defecto (1 y @me).
3. Invocación estructurada a gh issue create e indexación atómica en gh project item-add.
4. Soporte para --dry-run, --no-project, repositorios cruzados (-R) y alias agent-issue.
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import types

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "skills" / "issue-driven-workflow" / "bin" / "issue-create"
ALIAS_PATH = Path(__file__).resolve().parent.parent / "skills" / "issue-driven-workflow" / "bin" / "agent-issue"

issue_create = types.ModuleType("issue_create")
with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    exec(f.read(), issue_create.__dict__)



class TestIssueCreateProfileValidation(unittest.TestCase):
    """Verifica validación estricta y obligatoria de perfiles MBR."""

    def test_missing_profile_aborts_with_exit_code_1(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = issue_create.run_issue_create(["--title", "feat: test", "--body", "test"])
        self.assertEqual(code, 1)
        self.assertIn("perfil de ejecución obligatorio", stderr.getvalue())

    def test_invalid_profile_flag_aborts(self):
        for invalid in ("foo", "critical", "urgent", "1", "default"):
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                code = issue_create.run_issue_create(["--title", "feat: test", "--profile", invalid])
            self.assertEqual(code, 1, f"Esperaba fallo para perfil: {invalid}")
            self.assertIn("inválido", stderr.getvalue())

    def test_invalid_profile_label_aborts(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = issue_create.run_issue_create(["--title", "feat: test", "-l", "profile:superpro"])
        self.assertEqual(code, 1)
        self.assertIn("inválido", stderr.getvalue())

    def test_conflicting_profiles_aborts(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = issue_create.run_issue_create(
                ["--title", "feat: test", "--profile", "low", "-l", "profile:high"]
            )
        self.assertEqual(code, 1)
        self.assertIn("Conflicto de perfiles", stderr.getvalue())

    def test_valid_profiles_accepted(self):
        for p in ("low", "medium", "high", "pro", "LOW", "Medium"):
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = issue_create.run_issue_create(
                    ["--title", "feat: test", "--profile", p, "--dry-run"]
                )
            self.assertEqual(code, 0, f"Perfil válido rechazado: {p}")
            self.assertIn(f"--label profile:{p.lower()}", stdout.getvalue())

    def test_valid_profile_from_label_accepted(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = issue_create.run_issue_create(
                ["--title", "feat: test", "-l", "profile:high", "-l", "documentation", "--dry-run"]
            )
        self.assertEqual(code, 0)
        out = stdout.getvalue()
        self.assertIn("--label profile:high", out)
        self.assertIn("--label documentation", out)


class TestIssueCreateRepoConfigResolution(unittest.TestCase):
    """Verifica resolución dinámica de .repo-config.json y fallbacks deterministas."""

    def test_default_fallback_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            num, owner = issue_create.resolve_repo_config(Path(tmpdir))
            self.assertEqual(num, 1)
            self.assertEqual(owner, "@me")

    def test_custom_repo_config_resolved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / ".repo-config.json"
            cfg_path.write_text(json.dumps({"project_number": 42, "project_owner": "MyOrg"}), encoding="utf-8")
            num, owner = issue_create.resolve_repo_config(Path(tmpdir))
            self.assertEqual(num, 42)
            self.assertEqual(owner, "MyOrg")

    def test_partial_repo_config_uses_individual_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / ".repo-config.json"
            cfg_path.write_text(json.dumps({"project_number": 99}), encoding="utf-8")
            num, owner = issue_create.resolve_repo_config(Path(tmpdir))
            self.assertEqual(num, 99)
            self.assertEqual(owner, "@me")


class TestIssueCreateExecution(unittest.TestCase):
    """Verifica la invocación atómica a gh issue create e indexación en Projects v2."""

    @patch("subprocess.run")
    def test_atomic_issue_create_and_project_indexing(self, mock_run):
        # Primer llamado: gh issue create
        proc_issue = MagicMock()
        proc_issue.returncode = 0
        proc_issue.stdout = "https://github.com/JerbilX/Dotfiles-IA-Agents/issues/399\n"
        proc_issue.stderr = ""

        # Segundo llamado: gh project item-add
        proc_project = MagicMock()
        proc_project.returncode = 0
        proc_project.stdout = "{\"id\": \"PVTI_123\"}\n"
        proc_project.stderr = ""

        mock_run.side_effect = [proc_issue, proc_project]

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / ".repo-config.json"
            cfg.write_text(json.dumps({"project_number": 1, "project_owner": "@me"}), encoding="utf-8")

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = issue_create.run_issue_create(
                    ["--title", "feat(test): atomic", "--profile", "medium", "-F", ".issue_body"],
                    cwd=Path(tmpdir),
                )

            self.assertEqual(code, 0)
            self.assertEqual(mock_run.call_count, 2)

            # Validar argumentos de gh issue create
            cmd1 = mock_run.call_args_list[0][0][0]
            self.assertEqual(cmd1[:3], ["gh", "issue", "create"])
            self.assertIn("--title", cmd1)
            self.assertIn("feat(test): atomic", cmd1)
            self.assertIn("--label", cmd1)
            self.assertIn("profile:medium", cmd1)
            self.assertIn("--body-file", cmd1)
            self.assertIn(".issue_body", cmd1)

            # Validar argumentos de gh project item-add
            cmd2 = mock_run.call_args_list[1][0][0]
            self.assertEqual(cmd2, [
                "gh", "project", "item-add", "1",
                "--owner", "@me",
                "--url", "https://github.com/JerbilX/Dotfiles-IA-Agents/issues/399"
            ])

    @patch("subprocess.run")
    def test_no_project_flag_skips_item_add(self, mock_run):
        proc_issue = MagicMock()
        proc_issue.returncode = 0
        proc_issue.stdout = "https://github.com/JerbilX/Dotfiles-IA-Agents/issues/400\n"
        proc_issue.stderr = ""
        mock_run.return_value = proc_issue

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = issue_create.run_issue_create(
                ["--title", "feat: test", "--profile", "low", "--no-project"]
            )

        self.assertEqual(code, 0)
        self.assertEqual(mock_run.call_count, 1)

    @patch("subprocess.run")
    def test_issue_create_failure_propagates_error(self, mock_run):
        proc_issue = MagicMock()
        proc_issue.returncode = 1
        proc_issue.stdout = ""
        proc_issue.stderr = "graphql error: repo not found\n"
        mock_run.return_value = proc_issue

        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = issue_create.run_issue_create(
                ["--title", "feat: test", "--profile", "low"]
            )

        self.assertEqual(code, 1)
        self.assertIn("graphql error", stderr.getvalue())
        self.assertEqual(mock_run.call_count, 1)

    @patch("subprocess.run")
    def test_cross_repo_issue_creation(self, mock_run):
        proc_issue = MagicMock()
        proc_issue.returncode = 0
        proc_issue.stdout = "https://github.com/Other/Repo/issues/10\n"
        proc_issue.stderr = ""

        proc_project = MagicMock()
        proc_project.returncode = 0
        proc_project.stdout = ""
        proc_project.stderr = ""

        mock_run.side_effect = [proc_issue, proc_project]

        with tempfile.TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = issue_create.run_issue_create(
                    ["-R", "Other/Repo", "--title", "fix: cross-repo", "--profile", "pro"],
                    cwd=Path(tmpdir),
                )

            self.assertEqual(code, 0)
            self.assertEqual(mock_run.call_count, 2)
            cmd1 = mock_run.call_args_list[0][0][0]
            self.assertIn("-R", cmd1)
            self.assertIn("Other/Repo", cmd1)

    def test_agent_issue_alias_delegates_to_issue_create(self):
        agent_issue = types.ModuleType("agent_issue")
        agent_issue.__file__ = str(ALIAS_PATH)
        with open(ALIAS_PATH, "r", encoding="utf-8") as f:
            exec(f.read(), agent_issue.__dict__)

        with patch("sys.argv", ["agent-issue", "--title", "chore: alias test", "--profile", "low", "--dry-run"]):
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = agent_issue.main()
            self.assertEqual(code, 0)
            self.assertIn("chore: alias test", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
