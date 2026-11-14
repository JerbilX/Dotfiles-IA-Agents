import json
import os
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

# Cargar dinámicamente el script sin extensión skills/conversation-audit/bin/agent-guard
bin_path = Path(__file__).parent.parent / "skills" / "conversation-audit" / "bin" / "agent-guard"
guard_mod = types.ModuleType("agent_guard")
with open(bin_path, "r", encoding="utf-8") as f:
    exec(f.read(), guard_mod.__dict__)


class TestAgentGuardREPL(unittest.TestCase):
    """Verifica detección de evaluadores en línea y subshells (ENV_PROHIBITION_REPL)."""

    def test_python_eval_inline_denied(self):
        for cmd in (
            "python3 -c 'print(1)'",
            "python -c 'import sys'",
            "python3.12 --command 'exit()'",
            "VAR=1 python3 -c 'print(1)'",
            "sudo python3 -c 'print(1)'",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("evaluador en línea", err)

    def test_node_eval_inline_denied(self):
        for cmd in (
            "node -e 'console.log(1)'",
            "node --eval 'process.exit()'",
            "nodejs -p '2+2'",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("evaluador en línea", err)

    def test_subshell_c_denied(self):
        for cmd in (
            "bash -c 'ls -la'",
            "sh -c 'echo 1'",
            "zsh -c 'whoami'",
            "eval 'echo dangerous'",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")

    def test_combined_flags_and_wrappers_denied(self):
        for cmd in (
            "bash -lc 'ls'",
            "sh -ec 'echo 1'",
            "bash -o pipefail -c 'ls'",
            "python3 -Ic 'print(1)'",
            "python3 -X dev -c 'print(1)'",
            "node -pe '1+1'",
            "perl -ne 'print' x",
            "ruby -ne 'puts 1'",
            "timeout 5 python3 -c 'print(1)'",
            "env -u X python3 -c 'print(1)'",
            "find . -name '*.py' | xargs -I{} python3 -c 'print(1)'",
            "command bash -c 'ls'",
            "nice -n 10 bash -c 'ls'",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")

    def test_interpreter_options_after_script_allowed(self):
        for cmd in (
            "python3 -m pytest -c setup.cfg",
            "python3 scratch/tool.py -c config.json",
            "bash scripts/run.sh -c",
            "perl -MList::Util script.pl",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"Falso positivo en opción posterior al script: {cmd}")

    def test_formal_scripts_and_tests_allowed(self):
        for cmd in (
            "python3 script.py",
            "python3 -m unittest discover -s tests",
            "python3 -m unittest tests/test_agent_guard.py",
            "pytest tests/",
            "node build.js",
            "bash script.sh",
            "./build.sh check",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"No debería bloquearse comando legítimo: {cmd}")


class TestAgentGuardHostRecon(unittest.TestCase):
    """Verifica blindaje anti-reconocimiento del host (ENV_ANTI_RECON)."""

    def test_blind_find_denied(self):
        for cmd in (
            "find /",
            "find / -name '*.txt'",
            "find $HOME",
            "find ~",
            "find /home",
            "find /root",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("reconocimiento ciego del host", err)

    def test_blind_ls_denied(self):
        for cmd in (
            "ls /",
            "ls $HOME",
            "ls ~",
            "ls /home",
            "ls /root",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("listado no confinado del host", err)

    def test_scoped_recon_allowed(self):
        for cmd in (
            "find . -name '*.py'",
            "find src/ -type f",
            "find tests/ -name 'test_*.py'",
            "ls -la",
            "ls lib/",
            "ls -la skills/",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"No debería bloquearse búsqueda confinada: {cmd}")


class TestAgentGuardTerminalFileIO(unittest.TestCase):
    """Verifica uso exclusivo de APIs nativas y control de falsos positivos (ENV_NATIVE_FILE_API)."""

    def setUp(self):
        super().setUp()
        self._orig_get_branch = guard_mod.get_current_git_branch
        guard_mod.get_current_git_branch = lambda workspace_hint=None: (
            self._orig_get_branch(workspace_hint) if workspace_hint else "feat/test"
        )

    def tearDown(self):
        guard_mod.get_current_git_branch = self._orig_get_branch
        super().tearDown()

    def test_terminal_cat_file_denied(self):
        for cmd in (
            "cat README.md",
            "cat core/00-router.md",
            "cat src/main.py",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("cat", err)

    def test_terminal_tee_file_denied(self):
        for cmd in (
            "tee README.md",
            "echo 'x' | tee file.txt",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("tee", err)

    def test_terminal_sed_inplace_denied(self):
        for cmd in (
            "sed -i 's/foo/bar/' file.py",
            "sed --in-place 's/foo/bar/' file.py",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("sed -i", err)

    def test_terminal_redirection_to_workspace_denied(self):
        for cmd in (
            "echo 'hello' > README.md",
            "echo 'hello' >> file.txt",
            "cat << EOF > test.py",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("redirección", err)

    def test_filtering_pipelines_allowed(self):
        for cmd in (
            "git status | grep modified",
            "git diff | head -n 20",
            "ps aux | awk '{print $1}'",
            "git branch | awk '{print $2}'",
            "git log -n 5 | cat",
            "echo 'test' | sed 's/test/pass/'",
            "cat -n | grep foo",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"Falso positivo en pipeline de filtrado: {cmd}")

    def test_allowed_temporaries_and_scratch(self):
        for cmd in (
            "git commit -F .commit_msg",
            "cat .commit_msg",
            "echo 'chore: update' > .commit_msg",
            "echo 'pr body' > .pr_body",
            "echo 'data' > scratch/temp.txt",
            "ls > /dev/null 2>&1",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"No debería bloquearse temporal permitido: {cmd}")

    def test_build_and_test_commands_exempt(self):
        for cmd in (
            "./build.sh check",
            "./build.sh build",
            "python3 -m unittest discover -s tests",
            "pytest",
            "make test",
            "agent-audit summarize",
            "gh-pr-review comments 283",
            "git-prune-gone --sync",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"Comando de build/test bloqueado indebidamente: {cmd}")

    def test_exemption_does_not_cover_chained_segments(self):
        for cmd in (
            "./build.sh check && python3 -c 'print(1)'",
            "make test; cat README.md",
            "pytest || echo x > README.md",
            "npm run build | tee out.txt",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"La exención no debe propagarse a segmentos encadenados: {cmd}")

    def test_quoted_operators_not_treated_as_shell(self):
        for cmd in (
            "git commit -m 'estado proposed -> accepted'",
            'git commit -m "fix; cat README.md > x"',
            "gh pr list --jq '.[] | select(.n > 3)'",
            "jq '.items[] | {a: .b}' 2>/dev/null",
            "grep -E 'a>b|c' --include='*.md' -rn docs | head -n 20",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"Falso positivo por operador entre comillas: {cmd}")

    def test_heredoc_body_ignored_but_target_checked(self):
        allowed = "cat > .commit_msg <<'EOF'\nfeat: x -> y; cat README.md\nEOF"
        self.assertIsNone(guard_mod.evaluate_shell_command(allowed))
        denied = "cat > README.md <<EOF\nhola\nEOF"
        self.assertIsNotNone(guard_mod.evaluate_shell_command(denied))

    def test_tmp_segment_only_at_root_or_absolute(self):
        self.assertIsNone(guard_mod.evaluate_shell_command("echo x > /tmp/out.txt"))
        self.assertIsNotNone(guard_mod.evaluate_shell_command("echo x > src/tmp/out.txt"))


class TestAgentGuardMainProtection(unittest.TestCase):
    """Verifica protección contra commit y push directo a main (TRACK_IMMUTABILITY_TRACEABILITY)."""

    def test_push_explicit_main_denied(self):
        for cmd in (
            "git push origin main",
            "git push upstream main",
            "git push origin HEAD:main",
            "git push origin refs/heads/main",
            "git push -u origin master",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")
            self.assertIn("main", err)

    def test_push_non_main_allowed(self):
        for cmd in (
            "git push -u origin feat/guards-p0",
            "git push origin fix/issue-123",
            "git push origin HEAD:refs/heads/feat/test",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNone(err, f"Push a rama efímera no debería bloquearse: {cmd}")

    def test_commit_on_main_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            err = guard_mod.evaluate_shell_command("git commit -F .commit_msg", cwd=tmpdir)
            self.assertIsNotNone(err)
            self.assertIn("prohibido comitear directamente en 'main'", err)

    def test_commit_on_feature_branch_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/feat/guard\n", encoding="utf-8")
            err = guard_mod.evaluate_shell_command("git commit -F .commit_msg", cwd=tmpdir)
            self.assertIsNone(err)

    def test_commit_with_global_options_on_main_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            for cmd in ("git -C repo commit -m x", "git -c user.name=x -C repo commit -m x"):
                err = guard_mod.evaluate_shell_command(cmd, cwd=tmpdir)
                self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")

    def test_commit_on_master_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".git").mkdir()
            (Path(tmpdir) / ".git" / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
            self.assertIsNotNone(guard_mod.evaluate_shell_command("git commit -m x", cwd=tmpdir))

    def test_push_refspec_to_main_denied(self):
        for cmd in (
            "git push origin feat/x:main",
            "git push origin +feat/x:refs/heads/main",
            "git push --force origin HEAD:master",
            "git push origin :main",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")

    def test_push_without_refspec_on_main_denied_for_any_remote(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".git").mkdir()
            (Path(tmpdir) / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            for cmd in ("git push", "git push fork", "git push origin HEAD"):
                err = guard_mod.evaluate_shell_command(cmd, cwd=tmpdir)
                self.assertIsNotNone(err, f"Esperaba bloqueo para: {cmd}")

    def test_push_without_refspec_on_feature_branch_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".git").mkdir()
            (Path(tmpdir) / ".git" / "HEAD").write_text("ref: refs/heads/feat/test\n", encoding="utf-8")
            for cmd in ("git push", "git push fork", "git push origin HEAD"):
                err = guard_mod.evaluate_shell_command(cmd, cwd=tmpdir)
                self.assertIsNone(err, f"Push sin refspec en rama efímera no debería bloquearse: {cmd}")


class TestAgentGuardBannedFiles(unittest.TestCase):
    """Verifica prohibición de backlogs locales y archivos vetados (TRACK_NO_LOCAL_BACKLOGS, TRACK_DECISIONS_MADR)."""

    def test_target_files_denied(self):
        for fpath in (
            "TODO.md",
            "todo.md",
            "TODO",
            "backlog.md",
            "GEMINI.md",
            "gemini.md",
            "HISTORIAL.md",
            "historial.md",
            "tasks/todo.txt",
            "prompts/system.md",
            "subdir/TODO.md",
        ):
            err = guard_mod.evaluate_target_file(fpath)
            self.assertIsNotNone(err, f"Esperaba bloqueo para archivo: {fpath}")

    def test_nested_tasks_prompts_dirs_allowed(self):
        """tasks/ y prompts/ solo se vetan en la raíz del workspace (ej. roles de Ansible)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".git").mkdir()
            for fpath in ("roles/web/tasks/main.yml", "src/prompts/system.txt", "sub/tasks/task.json"):
                err = guard_mod.evaluate_target_file(fpath, cwd=tmpdir)
                self.assertIsNone(err, f"Directorio anidado bloqueado indebidamente: {fpath}")
                err = guard_mod.evaluate_target_file(str(Path(tmpdir) / fpath))
                self.assertIsNone(err, f"Ruta absoluta anidada bloqueada indebidamente: {fpath}")
            for fpath in ("tasks/x.md", "prompts/y.md"):
                self.assertIsNotNone(guard_mod.evaluate_target_file(fpath, cwd=tmpdir))
                self.assertIsNotNone(guard_mod.evaluate_target_file(str(Path(tmpdir) / fpath)))

    def test_legitimate_files_allowed(self):
        for fpath in (
            "README.md",
            "docs/adr/0052-guard.md",
            "core/00-router.md",
            "AGENTS.md",
            "tests/test_agent_guard.py",
            "skills/conversation-audit/bin/agent-guard",
        ):
            err = guard_mod.evaluate_target_file(fpath)
            self.assertIsNone(err, f"Archivo legítimo bloqueado: {fpath}")

    def test_shell_command_touching_banned_files_denied(self):
        for cmd in (
            "touch TODO.md",
            "mkdir tasks",
            "cp file.txt backlog.md",
            "mv old.md HISTORIAL.md",
            "echo 'task' > TODO.md",
        ):
            err = guard_mod.evaluate_shell_command(cmd)
            self.assertIsNotNone(err, f"Comando shell hacia archivo prohibido debió bloquearse: {cmd}")


class TestAgentGuardPayloadIntegrations(unittest.TestCase):
    """Verifica la compatibilidad de entrada/salida para Antigravity y Claude Code."""

    def test_antigravity_payload_allow(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"},
            }
        }
        res = guard_mod.evaluate_tool_request("run_command", payload["toolCall"]["args"])
        out = guard_mod.to_antigravity_response(res)
        self.assertEqual(out["decision"], "allow")

    def test_antigravity_payload_deny(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "python3 -c 'print(1)'"},
            }
        }
        res = guard_mod.evaluate_tool_request("run_command", payload["toolCall"]["args"])
        out = guard_mod.to_antigravity_response(res)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("Guard P0 Activado", out["reason"])

    def test_claude_payload_allow(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
        res = guard_mod.evaluate_tool_request(payload["tool_name"], payload["tool_input"])
        out = guard_mod.to_claude_response(res)
        self.assertIsNone(out)

    def test_claude_payload_deny(self):
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "TODO.md"},
        }
        res = guard_mod.evaluate_tool_request(payload["tool_name"], payload["tool_input"])
        out = guard_mod.to_claude_response(res)
        self.assertIsNotNone(out)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Guard P0 Activado", out["hookSpecificOutput"]["permissionDecisionReason"])


class TestGitHooksExecution(unittest.TestCase):
    """Verifica el comportamiento de los git hooks en .githooks/."""

    def setUp(self):
        self.repo_root = Path(__file__).parent.parent
        self.pre_push = self.repo_root / ".githooks" / "pre-push"
        self.pre_commit = self.repo_root / ".githooks" / "pre-commit"

    def test_pre_push_blocks_main(self):
        proc = subprocess.run(
            [str(self.pre_push), "origin", "git@github.com:repo.git"],
            input="refs/heads/main 1111111111111111111111111111111111111111 refs/heads/main 2222222222222222222222222222222222222222\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Push directo a 'main' bloqueado", proc.stderr)

    def test_pre_push_allows_feature_branch(self):
        proc = subprocess.run(
            [str(self.pre_push), "origin", "git@github.com:repo.git"],
            input="refs/heads/feat/test 1111111111111111111111111111111111111111 refs/heads/feat/test 2222222222222222222222222222222222222222\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)


class TestAgentGuardSandboxBypass(unittest.TestCase):
    """Verifica detección mecánica de bypass de sandbox y emisión de overwrite (ADR-0058, #382)."""

    def test_gh_commands_require_bypass(self):
        for cmd in (
            "gh issue view 382",
            "gh pr create --title 'feat: test'",
            "gh project item-list 1",
            "gh api graphql -f query='...'",
            "gh board",
            "gh board-ready",
            "gh run view 123 --log-failed",
        ):
            self.assertTrue(
                guard_mod.command_requires_sandbox_bypass(cmd),
                f"Comando gh debería exigir bypass: {cmd}",
            )

    def test_git_mutating_and_network_commands_require_bypass(self):
        for cmd in (
            "git add .",
            "git add core/00-router.md",
            "git commit -F .commit_msg",
            "git push -u origin feat/test",
            "git fetch --prune origin",
            "git pull --ff-only",
            "git switch --no-track -c feat/test origin/main",
            "git checkout -b feat/test",
            "git merge origin/main",
            "git branch -D feat/old",
            "git branch -d feat/old",
            "git branch -m old new",
            "git branch feat/new",
            "git stash",
            "git revert HEAD",
            "git reset --hard HEAD",
            "git restore file.txt",
            "git init",
            "git -C /path/to/repo add .",
        ):
            self.assertTrue(
                guard_mod.command_requires_sandbox_bypass(cmd),
                f"Comando mutador/red git debería exigir bypass: {cmd}",
            )

    def test_git_readonly_commands_stay_sandboxed(self):
        for cmd in (
            "git status",
            "git diff",
            "git diff --cached",
            "git log -n 5",
            "git show HEAD",
            "git rev-parse HEAD",
            "git rev-parse --show-toplevel",
            "git branch",
            "git branch -a",
            "git branch -r",
            "git branch --list",
            "git remote -v",
        ):
            self.assertFalse(
                guard_mod.command_requires_sandbox_bypass(cmd),
                f"Comando git de solo lectura no debería exigir bypass: {cmd}",
            )

    def test_authorized_clis_require_bypass(self):
        for cmd in (
            "gh-pr-review comments 382",
            "git-prune-gone --sync",
        ):
            self.assertTrue(
                guard_mod.command_requires_sandbox_bypass(cmd),
                f"CLI autorizado debería exigir bypass: {cmd}",
            )

    def test_local_build_and_tests_stay_sandboxed(self):
        for cmd in (
            "./build.sh check",
            "./build.sh test",
            "./build.sh build",
            "python3 -m unittest",
            "pytest tests/",
            "ls -la",
        ):
            self.assertFalse(
                guard_mod.command_requires_sandbox_bypass(cmd),
                f"Comando local de compilación/test no debería exigir bypass: {cmd}",
            )

    def test_antigravity_payload_enforces_overwrite_when_bypass_false(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "gh issue view 382",
                    "BypassSandbox": False,
                },
            }
        }
        res = guard_mod.evaluate_tool_request("run_command", payload["toolCall"]["args"])
        self.assertIsNone(res)
        self.assertTrue(guard_mod.command_requires_sandbox_bypass(payload["toolCall"]["args"]["CommandLine"]))
        out = guard_mod.to_antigravity_response(res, {"BypassSandbox": True})
        self.assertEqual(out["decision"], "allow")
        self.assertEqual(out.get("overwrite"), {"BypassSandbox": True})

    def test_antigravity_payload_no_overwrite_when_bypass_already_true(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "gh issue view 382",
                    "BypassSandbox": True,
                },
            }
        }
        res = guard_mod.evaluate_tool_request("run_command", payload["toolCall"]["args"])
        out = guard_mod.to_antigravity_response(res, None)
        self.assertEqual(out["decision"], "allow")
        self.assertNotIn("overwrite", out)

    def test_antigravity_denial_takes_precedence_over_bypass(self):
        orig_get_branch = guard_mod.get_current_git_branch
        guard_mod.get_current_git_branch = lambda ws=None: "main"
        try:
            payload = {
                "toolCall": {
                    "name": "run_command",
                    "args": {
                        "CommandLine": "git commit -m 'feat: bypass'",
                        "BypassSandbox": False,
                    },
                }
            }
            res = guard_mod.evaluate_tool_request("run_command", payload["toolCall"]["args"])
            self.assertIsNotNone(res)
            self.assertIn("prohibido comitear directamente en 'main'", res)
            out = guard_mod.to_antigravity_response(res, {"BypassSandbox": True})
            self.assertEqual(out["decision"], "deny")
            self.assertNotIn("overwrite", out)
            self.assertIn("Guard P0 Activado", out["reason"])
        finally:
            guard_mod.get_current_git_branch = orig_get_branch


if __name__ == "__main__":
    unittest.main()
