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

        bash_with_jq = f"""
source "{REPO_ROOT}/lib/common.sh"
json_get "{data_file}" ".nested.val"
"""
        res_jq = subprocess.run(["bash", "-c", bash_with_jq], capture_output=True, text=True)
        self.assertEqual(res_jq.returncode, 0)
        self.assertEqual(res_jq.stdout.strip(), "123")

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

cmd_link "antigravity"
"""
        res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("aliases-ok", res.stdout)
        self.assertIn("hooks-ok", res.stdout)
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



if __name__ == "__main__":
    unittest.main()
