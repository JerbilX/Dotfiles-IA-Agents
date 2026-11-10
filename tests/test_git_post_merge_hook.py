import os
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_SCRIPT = os.path.join(REPO_ROOT, "git", "hooks", "post-merge")


class TestGitPostMergeHook(unittest.TestCase):
    def test_hook_permissions_and_syntax(self):
        """Verifica que git/hooks/post-merge sea ejecutable y tenga sintaxis bash válida."""
        self.assertTrue(os.path.isfile(HOOK_SCRIPT), f"{HOOK_SCRIPT} no existe")
        file_stat = os.stat(HOOK_SCRIPT)
        self.assertTrue(bool(file_stat.st_mode & stat.S_IXUSR), "git/hooks/post-merge debe ser ejecutable")

        res = subprocess.run(["bash", "-n", HOOK_SCRIPT], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error de sintaxis bash: {res.stderr}")

    def test_hook_outside_git_repo(self):
        """Si se ejecuta fuera de un repo git, debe terminar limpiamente con código 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout, "")

    def test_hook_ignores_feature_branches(self):
        """En ramas efímeras (feat/*), el hook debe salir silenciosamente sin ejecutar despliegue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", "-b", "feat/test"], cwd=tmpdir, check=True, capture_output=True)
            repo_cfg = os.path.join(tmpdir, ".repo-config.json")
            marker = os.path.join(tmpdir, "deployed.marker")
            with open(repo_cfg, "w", encoding="utf-8") as f:
                f.write(f'{{"deployCommand": "touch {marker}"}}')

            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertFalse(os.path.exists(marker), "No debe desplegar en ramas de feature")
            self.assertNotIn("Auto-despliegue", res.stdout)

    def test_hook_executes_on_main_with_deploy_command(self):
        """En rama main con deployCommand configurado, ejecuta el despliegue con éxito."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", "-b", "main"], cwd=tmpdir, check=True, capture_output=True)
            repo_cfg = os.path.join(tmpdir, ".repo-config.json")
            marker = os.path.join(tmpdir, "deployed.marker")
            with open(repo_cfg, "w", encoding="utf-8") as f:
                f.write(f'{{"deployCommand": "touch {marker}"}}')

            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertTrue(os.path.exists(marker), "Debe haber creado el archivo marker")
            self.assertIn("Auto-despliegue detectado en .repo-config.json", res.stdout)
            self.assertIn("Despliegue completado con éxito.", res.stdout)

    def test_hook_silent_when_no_deploy_command(self):
        """En rama main sin deployCommand o sin .repo-config.json, termina silenciosamente con código 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", "-b", "main"], cwd=tmpdir, check=True, capture_output=True)

            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout, "")

            # Con .repo-config.json pero sin deployCommand
            repo_cfg = os.path.join(tmpdir, ".repo-config.json")
            with open(repo_cfg, "w", encoding="utf-8") as f:
                f.write('{"projectId": 1}')

            res2 = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res2.returncode, 0)
            self.assertEqual(res2.stdout, "")

    def test_hook_failure_is_non_blocking_warning(self):
        """Si deployCommand falla, emite una advertencia a stderr pero no bloquea (exit 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", "-b", "main"], cwd=tmpdir, check=True, capture_output=True)
            repo_cfg = os.path.join(tmpdir, ".repo-config.json")
            with open(repo_cfg, "w", encoding="utf-8") as f:
                f.write('{"deployCommand": "false"}')

            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, "El fallo en deploy no debe romper la salida de git pull")
            self.assertIn("Advertencia: El comando de despliegue finalizó con error.", res.stderr)

    def test_hook_delegates_to_local_hook(self):
        """Si existe .git/hooks/post-merge.local, se ejecuta en cadena."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init", "-b", "main"], cwd=tmpdir, check=True, capture_output=True)
            hooks_dir = os.path.join(tmpdir, ".git", "hooks")
            os.makedirs(hooks_dir, exist_ok=True)
            local_hook = os.path.join(hooks_dir, "post-merge.local")
            local_marker = os.path.join(tmpdir, "local_hook.marker")
            with open(local_hook, "w", encoding="utf-8") as f:
                f.write(f"#!/usr/bin/env bash\ntouch {local_marker}\n")
            os.chmod(local_hook, 0o755)

            res = subprocess.run([HOOK_SCRIPT], cwd=tmpdir, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertTrue(os.path.exists(local_marker), "El hook local debe haberse ejecutado")


if __name__ == "__main__":
    unittest.main()
