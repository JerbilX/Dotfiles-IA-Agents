"""Soporte de tests: regenera dist/ (no versionado, ADR-0045) a partir de las fuentes actuales."""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_built = False


def ensure_dist():
    """Compila dist/ una vez por proceso de tests con ./build.sh build all."""
    global _built
    if _built:
        return
    subprocess.run(
        [os.path.join(REPO_ROOT, "build.sh"), "build", "all"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _built = True
