#!/usr/bin/env python3
"""
Pruebas automatizadas unitarias para el CLI git-prune-gone.
Ref: docs/adr/0032-compatibilidad-de-poda-y-rollback-con-squash-merge.md
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "skills",
        "issue-driven-workflow",
        "bin",
        "git-prune-gone",
    )
)


class TestGitPruneGone(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_prune_gone_")
        self._git(["init", "-b", "main"])
        self._git(["config", "user.name", "Test Agent"])
        self._git(["config", "user.email", "agent@test.local"])
        self._git(["remote", "add", "origin", "https://example.com/test-repo.git"])

        # Commit inicial en main
        init_file = os.path.join(self.test_dir, "README.md")
        with open(init_file, "w", encoding="utf-8") as f:
            f.write("# Repo Test\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "chore: initial commit"])

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _git(self, args):
        res = subprocess.run(
            ["git"] + args,
            cwd=self.test_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git command failed: git {' '.join(args)}\n{res.stderr}")
        return res.stdout.strip()

    def _run_cli(self, cli_args):
        cmd = [sys.executable, SCRIPT_PATH] + cli_args
        res = subprocess.run(
            cmd,
            cwd=self.test_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return res

    def _create_gone_branch(self, branch_name):
        self._git(["config", f"branch.{branch_name}.remote", "origin"])
        self._git(["config", f"branch.{branch_name}.merge", f"refs/heads/{branch_name}"])

    def _branch_exists(self, branch_name):
        branches = self._git(["branch", "--format=%(refname:short)"]).splitlines()
        return branch_name in [b.strip() for b in branches]

    def test_clean_tree(self):
        """Verifica que un árbol sin ramas [gone] retorna estado clean y código 0."""
        res = self._run_cli(["--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "clean")
        self.assertEqual(len(data["pruned"]), 0)

    def test_squash_merged_branch_pruned(self):
        """Verifica que una rama integrada vía squash merge es clasificada como squash-merged y podada sin error."""
        branch = "feat/squash-test"
        self._git(["checkout", "-b", branch])
        fpath = os.path.join(self.test_dir, "feature.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("feature content\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "feat: first commit"])

        with open(fpath, "a", encoding="utf-8") as f:
            f.write("second line\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "feat: second commit"])

        # Integrar en main vía squash merge
        self._git(["checkout", "main"])
        self._git(["merge", "--squash", branch])
        self._git(["commit", "-m", "feat: squash merge feature (#1)"])

        # Configurar tracking remoto inexistente ([gone])
        self._create_gone_branch(branch)

        res = self._run_cli(["--json"])
        self.assertEqual(res.returncode, 0, f"CLI falló: {res.stderr}\n{res.stdout}")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["pruned"]), 1)
        self.assertEqual(data["pruned"][0]["branch"], branch)
        self.assertEqual(data["pruned"][0]["classification"], "squash-merged")
        self.assertFalse(self._branch_exists(branch))

    def test_traditionally_merged_branch_pruned(self):
        """Verifica que una rama integrada vía merge commit tradicional es clasificada como merged y podada sin error."""
        branch = "feat/merge-test"
        self._git(["checkout", "-b", branch])
        fpath = os.path.join(self.test_dir, "trad.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("trad merge\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "feat: trad commit"])

        # Integrar en main vía merge tradicional (--no-ff)
        self._git(["checkout", "main"])
        self._git(["merge", "--no-ff", branch, "-m", "Merge PR #2"])

        self._create_gone_branch(branch)

        res = self._run_cli(["--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["pruned"]), 1)
        self.assertEqual(data["pruned"][0]["branch"], branch)
        self.assertEqual(data["pruned"][0]["classification"], "merged")
        self.assertFalse(self._branch_exists(branch))

    def test_unmerged_branch_safeguard(self):
        """Verifica que una rama [gone] con cambios no integrados NO sea eliminada sin --force y retorne código 1."""
        branch = "feat/unmerged-work"
        self._git(["checkout", "-b", branch])
        fpath = os.path.join(self.test_dir, "secret.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("unmerged changes\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "work in progress"])

        self._git(["checkout", "main"])
        self._create_gone_branch(branch)

        res = self._run_cli(["--json"])
        self.assertEqual(res.returncode, 1, "Debe retornar código 1 al omitir rama no integrada")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(len(data["pruned"]), 0)
        self.assertEqual(len(data["unmerged"]), 1)
        self.assertEqual(data["unmerged"][0]["branch"], branch)
        self.assertEqual(data["unmerged"][0]["classification"], "unmerged")
        self.assertTrue(self._branch_exists(branch), "La rama no integrada no debe ser eliminada")

    def test_unmerged_branch_forced_deletion(self):
        """Verifica que una rama no integrada sea eliminada al especificar -f / --force."""
        branch = "feat/abandoned-work"
        self._git(["checkout", "-b", branch])
        fpath = os.path.join(self.test_dir, "abandoned.txt")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("abandoned\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "abandoned commit"])

        self._git(["checkout", "main"])
        self._create_gone_branch(branch)

        res = self._run_cli(["--force", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["pruned"]), 1)
        self.assertFalse(self._branch_exists(branch))

    def test_dry_run_and_json_classification(self):
        """Verifica que --dry-run y --json clasifiquen correctamente múltiples ramas sin eliminarlas."""
        # Rama 1: squash-merged
        b_squash = "feat/b-squash"
        self._git(["checkout", "-b", b_squash])
        with open(os.path.join(self.test_dir, "f1.txt"), "w") as f:
            f.write("f1\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "c1"])
        self._git(["checkout", "main"])
        self._git(["merge", "--squash", b_squash])
        self._git(["commit", "-m", "squash c1"])
        self._create_gone_branch(b_squash)

        # Rama 2: merged tradicional
        b_trad = "feat/b-trad"
        self._git(["checkout", "-b", b_trad])
        with open(os.path.join(self.test_dir, "f2.txt"), "w") as f:
            f.write("f2\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "c2"])
        self._git(["checkout", "main"])
        self._git(["merge", "--no-ff", b_trad, "-m", "merge c2"])
        self._create_gone_branch(b_trad)

        # Rama 3: unmerged
        b_unmerged = "feat/b-unmerged"
        self._git(["checkout", "-b", b_unmerged])
        with open(os.path.join(self.test_dir, "f3.txt"), "w") as f:
            f.write("f3\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "c3"])
        self._git(["checkout", "main"])
        self._create_gone_branch(b_unmerged)

        res = self._run_cli(["--dry-run", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "dry_run")

        cand_map = {c["branch"]: c["classification"] for c in data["candidates"]}
        self.assertEqual(cand_map.get(b_squash), "squash-merged")
        self.assertEqual(cand_map.get(b_trad), "merged")
        self.assertEqual(cand_map.get(b_unmerged), "unmerged")

        # Asegurar que ninguna rama fue borrada en dry-run
        self.assertTrue(self._branch_exists(b_squash))
        self.assertTrue(self._branch_exists(b_trad))
        self.assertTrue(self._branch_exists(b_unmerged))

    def test_custom_base_branch_and_config(self):
        """Verifica la resolución de base_branch mediante flag --base y archivo .repo-config.json."""
        self._git(["checkout", "-b", "dev"])

        branch = "feat/dev-feature"
        self._git(["checkout", "-b", branch])
        with open(os.path.join(self.test_dir, "dev_feat.txt"), "w") as f:
            f.write("dev feat\n")
        self._git(["add", "."])
        self._git(["commit", "-m", "dev feature commit"])

        # Integrar en dev vía squash
        self._git(["checkout", "dev"])
        self._git(["merge", "--squash", branch])
        self._git(["commit", "-m", "squash into dev"])
        self._create_gone_branch(branch)

        # Crear .repo-config.json declarativo
        with open(os.path.join(self.test_dir, ".repo-config.json"), "w", encoding="utf-8") as f:
            json.dump({"repository_type": "category_b", "base_branch": "dev"}, f)

        res = self._run_cli(["--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["base_branch"], "dev")
        self.assertEqual(len(data["pruned"]), 1)
        self.assertEqual(data["pruned"][0]["branch"], branch)
        self.assertEqual(data["pruned"][0]["classification"], "squash-merged")
        self.assertFalse(self._branch_exists(branch))


if __name__ == "__main__":
    unittest.main()
