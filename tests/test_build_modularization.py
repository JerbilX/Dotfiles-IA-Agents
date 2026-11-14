#!/usr/bin/env python3
"""
Unit tests for build.sh modularization, json_get helper, safe_symlink helper,
and lib/validate.py independent schema validation (Issue #194).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
VALIDATE_PY = os.path.join(LIB_DIR, "validate.py")
RUNTIMES_SCHEMA = os.path.join(REPO_ROOT, "runtimes", "schema", "runtime-config.schema.json")
MCP_SCHEMA = os.path.join(REPO_ROOT, "runtimes", "schema", "mcp-server.schema.json")
MODULE_SCHEMA = os.path.join(REPO_ROOT, "runtimes", "schema", "module-config.schema.json")
BUILD_SH = os.path.join(REPO_ROOT, "build.sh")


class TestBuildModularization(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_modular_files_exist_and_are_executable_or_readable(self):
        """All lib/*.sh and lib/validate.py files must exist."""
        expected_files = [
            "common.sh",
            "validate.sh",
            "build_core.sh",
            "link.sh",
            "check.sh",
            "check_rules.sh",
            "check_runtime.sh",
            "check_modules.sh",
            "check_environment.sh",
            "validate.py",
            "tool_vocabulary.py",
        ]
        for name in expected_files:
            p = os.path.join(LIB_DIR, name)
            self.assertTrue(os.path.isfile(p), f"Missing {p}")

    def test_validate_py_validates_canonical_configs(self):
        """lib/validate.py validates all existing runtime and module configs successfully."""
        configs_to_test = [
            (os.path.join(REPO_ROOT, "runtimes", "antigravity", "config.json"), RUNTIMES_SCHEMA),
            (os.path.join(REPO_ROOT, "runtimes", "claude", "config.json"), RUNTIMES_SCHEMA),
            (os.path.join(REPO_ROOT, "modules", "eso", "module.json"), MODULE_SCHEMA),
        ]
        for cfg, schema in configs_to_test:
            res = subprocess.run(
                ["python3", VALIDATE_PY, cfg, schema],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"Validation failed for {cfg}: {res.stderr}")

    def test_validate_py_detects_invalid_schema(self):
        """lib/validate.py returns non-zero when required field or type is wrong."""
        bad_cfg = os.path.join(self._tmp, "bad_config.json")
        with open(bad_cfg, "w", encoding="utf-8") as f:
            json.dump({"status": "invalid_status", "skills": "not_an_array"}, f)

        res = subprocess.run(
            ["python3", VALIDATE_PY, bad_cfg, RUNTIMES_SCHEMA],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Error de validación", res.stderr)

    def test_validate_py_mcp_server_oneof(self):
        """lib/validate.py validates MCP schema oneOf condition correctly."""
        # Valid stdio MCP
        valid_mcp = os.path.join(self._tmp, "stdio_mcp.json")
        with open(valid_mcp, "w", encoding="utf-8") as f:
            json.dump({"command": "npx", "args": ["-y", "test"]}, f)

        res = subprocess.run(
            ["python3", VALIDATE_PY, valid_mcp, MCP_SCHEMA],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Valid MCP failed: {res.stderr}")

        # Invalid: defining both command and serverUrl
        invalid_mcp = os.path.join(self._tmp, "conflict_mcp.json")
        with open(invalid_mcp, "w", encoding="utf-8") as f:
            json.dump({"command": "npx", "serverUrl": "https://example.com/sse"}, f)

        res_inv = subprocess.run(
            ["python3", VALIDATE_PY, invalid_mcp, MCP_SCHEMA],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_inv.returncode, 0)

    def test_safe_symlink_behavior(self):
        """safe_symlink creates symlink, leaves existing matching symlink, and creates backup on conflict."""
        src_a = os.path.join(self._tmp, "src_a.txt")
        src_b = os.path.join(self._tmp, "src_b.txt")
        dst = os.path.join(self._tmp, "target_link.txt")

        with open(src_a, "w") as f:
            f.write("A")
        with open(src_b, "w") as f:
            f.write("B")

        bash_cmd = f"""
source "{REPO_ROOT}/lib/common.sh"
safe_symlink "{src_a}" "{dst}" "test-link"
"""
        res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(os.path.islink(dst))
        self.assertEqual(os.path.realpath(dst), os.path.realpath(src_a))

        # Re-running with same src should be a no-op
        res2 = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res2.returncode, 0)
        self.assertIn("ya apunta correctamente", res2.stdout)

        # Re-running with different src should backup the previous target
        bash_cmd_b = f"""
source "{REPO_ROOT}/lib/common.sh"
safe_symlink "{src_b}" "{dst}" "test-link"
"""
        res3 = subprocess.run(["bash", "-c", bash_cmd_b], capture_output=True, text=True)
        self.assertEqual(res3.returncode, 0)
        self.assertEqual(os.path.realpath(dst), os.path.realpath(src_b))
        baks = [f for f in os.listdir(self._tmp) if "target_link.txt.bak." in f]
        self.assertEqual(len(baks), 1)

    def test_json_get_helper_parity(self):
        """json_get extracts properties identically with jq and without jq."""
        data_file = os.path.join(self._tmp, "data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump({"status": "active", "nested": {"val": "123"}}, f)

        # Con jq
        bash_with_jq = f"""
source "{REPO_ROOT}/lib/common.sh"
json_get "{data_file}" ".nested.val"
"""
        res_jq = subprocess.run(["bash", "-c", bash_with_jq], capture_output=True, text=True)
        self.assertEqual(res_jq.returncode, 0)
        self.assertEqual(res_jq.stdout.strip(), "123")

        # Sin jq (PATH restringido)
        bin_no_jq = os.path.join(self._tmp, "bin_no_jq")
        os.makedirs(bin_no_jq, exist_ok=True)
        for bin_name in ["bash", "python3", "env", "dirname"]:
            bin_path = shutil.which(bin_name)
            if bin_path:
                dst = os.path.join(bin_no_jq, bin_name)
                if not os.path.exists(dst):
                    os.symlink(bin_path, dst)

        env_no_jq = os.environ.copy()
        env_no_jq["PATH"] = bin_no_jq

        bash_without_jq = f"""
source "{REPO_ROOT}/lib/common.sh"
json_get "{data_file}" ".nested.val"
"""
        res_no_jq = subprocess.run(["bash", "-c", bash_without_jq], env=env_no_jq, capture_output=True, text=True)
        self.assertEqual(res_no_jq.returncode, 0)
        self.assertEqual(res_no_jq.stdout.strip(), "123")

        # Fallback de empty en clave ausente
        url_file = os.path.join(self._tmp, "server_url.json")
        with open(url_file, "w", encoding="utf-8") as f:
            json.dump({"serverUrl": "https://example.com/sse"}, f)

        bash_empty_jq = f"""
source "{REPO_ROOT}/lib/common.sh"
json_get "{url_file}" ".command // empty"
"""
        res_empty_jq = subprocess.run(["bash", "-c", bash_empty_jq], capture_output=True, text=True)
        self.assertEqual(res_empty_jq.returncode, 0)
        self.assertEqual(res_empty_jq.stdout.strip(), "")

        res_empty_no_jq = subprocess.run(["bash", "-c", bash_empty_jq], env=env_no_jq, capture_output=True, text=True)
        self.assertEqual(res_empty_no_jq.returncode, 0)
        self.assertEqual(res_empty_no_jq.stdout.strip(), "")

    def test_mcp_verification_safety_and_expansion(self):
        """MCP verification does not execute command via eval and expands env vars safely."""
        pwned_file = os.path.join(self._tmp, "pwned_marker")
        if os.path.exists(pwned_file):
            os.remove(pwned_file)

        mock_home = os.path.join(self._tmp, "fake_home")
        os.makedirs(mock_home, exist_ok=True)

        mcp_dir = os.path.join(self._tmp, "mcp")
        os.makedirs(mcp_dir, exist_ok=True)

        # 1. Manifiesto con inyección de comando arbitrario
        pwned_mcp = os.path.join(mcp_dir, "pwned.json")
        with open(pwned_mcp, "w", encoding="utf-8") as f:
            json.dump({"command": f"$(touch {pwned_file})", "args": []}, f)

        # 2. Manifiesto con variable ${HOME}
        home_mcp = os.path.join(mcp_dir, "home_var.json")
        with open(home_mcp, "w", encoding="utf-8") as f:
            json.dump({"command": "${HOME}/bin/custom-mcp", "args": []}, f)

        # 3. Manifiesto con serverUrl (sin command)
        url_mcp = os.path.join(mcp_dir, "sse.json")
        with open(url_mcp, "w", encoding="utf-8") as f:
            json.dump({"serverUrl": "https://example.com/sse"}, f)

        bash_script = f"""
export REPO_ROOT="{REPO_ROOT}"
export LIB_DIR="{LIB_DIR}"
source "{LIB_DIR}/common.sh"
source "{LIB_DIR}/validate.sh"

CHECK_ERRORS=0
CHECK_WARNINGS=0

enabled_mcps=("pwned" "home_var" "sse")
r="test_runtime"
mcp_dir="{mcp_dir}"

for s_name in "${{enabled_mcps[@]}}"; do
    s_path="${{mcp_dir}}/${{s_name}}.json"
    cmd="$(json_get "${{s_path}}" ".command // empty")"
    if [ -n "${{cmd}}" ]; then
        expanded_cmd="$(python3 -c 'import os, sys; print(os.path.expandvars(sys.argv[1]))' "${{cmd}}")"
        if [[ "${{expanded_cmd}}" == *"/"* ]]; then
            if [ ! -e "${{expanded_cmd}}" ]; then
                echo "Advertencia [${{r}}]: Ejecutable MCP '${{expanded_cmd}}' del servidor '${{s_name}}' no existe en disco" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            fi
        else
            if ! command -v "${{expanded_cmd}}" >/dev/null 2>&1; then
                echo "Advertencia [${{r}}]: Comando MCP '${{expanded_cmd}}' del servidor '${{s_name}}' no encontrado en \\$PATH" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            fi
        fi
    fi
done
"""
        env = os.environ.copy()
        env["HOME"] = mock_home
        res = subprocess.run(["bash", "-c", bash_script], env=env, capture_output=True, text=True)

        # Criterio: no se ejecutó touch ni se creó el archivo
        self.assertFalse(os.path.exists(pwned_file), "Vulnerabilidad eval: se creó el archivo pwned")
        self.assertIn("Ejecutable MCP '$(touch", res.stderr)

        # Criterio: ${HOME} se expande igual que en compilación
        expected_home_path = os.path.join(mock_home, "bin", "custom-mcp")
        self.assertIn(f"Ejecutable MCP '{expected_home_path}'", res.stderr)

        # Criterio: sse.json sin command no produce advertencia 'empty'
        self.assertNotIn("'empty'", res.stderr)

    def test_cmd_link_invokes_skills_runtime(self):
        """cmd_link must call skills_runtime for each target runtime (Issue #277)."""
        bash_cmd = f"""
export RUNTIMES_BASE_DIR="{REPO_ROOT}/runtimes"
source "{REPO_ROOT}/lib/common.sh"
source "{REPO_ROOT}/lib/link.sh"

invoked_skills=()
skills_runtime() {{
    invoked_skills+=("$1")
}}
link_runtime() {{
    :
}}
setup_gh_aliases() {{
    :
}}
setup_git_hooks() {{
    :
}}
setup_global_git_hooks() {{
    :
}}

cmd_link "antigravity"
echo "Skills invoked: ${{invoked_skills[*]}}"
"""
        res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Skills invoked: antigravity", res.stdout)

    def test_cmd_link_skills_failure_is_not_fatal(self):
        """A skills_runtime failure must not abort aliases/hooks setup under set -e."""
        bash_cmd = f"""
set -euo pipefail
export RUNTIMES_BASE_DIR="{REPO_ROOT}/runtimes"
source "{REPO_ROOT}/lib/common.sh"
source "{REPO_ROOT}/lib/link.sh"

skills_runtime() {{ return 1; }}
link_runtime() {{ :; }}
setup_gh_aliases() {{ echo "aliases-ok"; }}
setup_git_hooks() {{ echo "hooks-ok"; }}
setup_global_git_hooks() {{ echo "global-hooks-ok"; }}

cmd_link "antigravity"
"""
        res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("aliases-ok", res.stdout)
        self.assertIn("hooks-ok", res.stdout)
        self.assertIn("global-hooks-ok", res.stdout)
        self.assertIn("Falló el aprovisionamiento de skills", res.stderr)

    def test_check_sh_modular_domain_submodules(self):
        """lib/check.sh must source domain submodules and expose all check functions (#307)."""
        bash_cmd = f"""
set -euo pipefail
source "{REPO_ROOT}/lib/common.sh"
source "{REPO_ROOT}/lib/check.sh"

required_functions=(
    check_core_rules
    check_basal_rules_admission
    check_prompt_tool_crossings
    check_runtime
    check_local_bin_symlinks
    check_domain_modules
    check_global_mcp_purity
    check_global_skills_purity
    cmd_workspace
    check_documentation
    check_unit_tests
    check_gh_aliases
    check_skill_bypass_quotes
    check_p0_guards
    cmd_check
    cmd_test
)

for fn in "${{required_functions[@]}}"; do
    if ! declare -F "$fn" >/dev/null; then
        echo "Missing function: $fn" >&2
        exit 1
    fi
done
echo "all-check-functions-present"
"""
        res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("all-check-functions-present", res.stdout)

    def test_build_test_subcommand(self):
        """./build.sh test executes unittest discovery for test_build_path_safety.py successfully."""
        res = subprocess.run(
            [BUILD_SH, "test", "test_build_path_safety.py"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Ran 6 tests", res.stderr)



if __name__ == "__main__":
    unittest.main()
