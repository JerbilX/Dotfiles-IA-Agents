#!/usr/bin/env python3
"""
Unit tests for declarative runtime lifecycle status and on-demand build/check execution (Issue #180).
"""

import json
import os
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNTIMES_DIR = os.path.join(REPO_ROOT, "runtimes")
SCHEMA_FILE = os.path.join(RUNTIMES_DIR, "schema", "runtime-config.schema.json")
BUILD_SH = os.path.join(REPO_ROOT, "build.sh")


class TestRuntimeLifecycle(unittest.TestCase):

    def test_schema_declares_status_enum(self):
        """runtime-config.schema.json must declare status with active, on-demand, and disabled enum."""
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)
        status_prop = schema.get("properties", {}).get("status")
        self.assertIsNotNone(status_prop, "Schema must contain 'status' property")
        self.assertEqual(status_prop.get("type"), "string")
        self.assertEqual(
            status_prop.get("enum"),
            ["active", "on-demand", "disabled"],
            "status enum must be ['active', 'on-demand', 'disabled']"
        )
        self.assertEqual(status_prop.get("default"), "active")

    def test_antigravity_status_is_active(self):
        """runtimes/antigravity/config.json must have status set to 'active'."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("status"), "active")

    def test_claude_status_is_on_demand(self):
        """runtimes/claude/config.json must have status set to 'on-demand'."""
        cfg_path = os.path.join(RUNTIMES_DIR, "claude", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("status"), "on-demand")

    def test_default_build_only_targets_active_runtimes(self):
        """./build.sh build (no args) must only compile active runtimes (antigravity), skipping claude."""
        res = subprocess.run(
            [BUILD_SH, "build"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"build.sh build failed: {res.stderr}")
        self.assertIn("Telemetría de contexto [antigravity]", res.stdout)
        self.assertNotIn("Telemetría de contexto [claude]", res.stdout)

    def test_explicit_build_compiles_on_demand_runtime(self):
        """./build.sh build claude must compile claude on-demand."""
        res = subprocess.run(
            [BUILD_SH, "build", "claude"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"build.sh build claude failed: {res.stderr}")
        self.assertIn("Telemetría de contexto [claude]", res.stdout)
        self.assertNotIn("Telemetría de contexto [antigravity]", res.stdout)

    def test_build_all_compiles_all_registered_runtimes(self):
        """./build.sh build all must compile both antigravity and claude."""
        res = subprocess.run(
            [BUILD_SH, "build", "all"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"build.sh build all failed: {res.stderr}")
        self.assertIn("Telemetría de contexto [antigravity]", res.stdout)
        self.assertIn("Telemetría de contexto [claude]", res.stdout)

    def test_invalid_runtime_returns_error(self):
        """./build.sh build non_existent must exit with error."""
        res = subprocess.run(
            [BUILD_SH, "build", "non_existent_runtime_xyz"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Error: Runtime 'non_existent_runtime_xyz' no encontrado", res.stderr)

    def test_declared_binaries_physical_existence_and_executable_permissions(self):
        """All declared binaries in runtime configs must exist in origin and be executable (+x) (Issue #184)."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        declared_binaries = cfg.get("binaries", {})
        self.assertIn("agent-module", declared_binaries)
        self.assertIn("agent-audit", declared_binaries)
        self.assertIn("gh-pr-review", declared_binaries)
        self.assertIn("git-prune-gone", declared_binaries)

        skills_dir = os.path.join(REPO_ROOT, "skills")
        for src_name in declared_binaries.keys():
            found = False
            for s_name in cfg.get("skills", []):
                candidate_paths = [
                    os.path.join(skills_dir, s_name, "bin", src_name),
                    os.path.join(skills_dir, s_name, "scripts", f"{src_name}.sh"),
                ]
                for p in candidate_paths:
                    if os.path.isfile(p):
                        found = True
                        self.assertTrue(
                            os.access(p, os.X_OK),
                            f"Declared binary {src_name} at {p} must have executable permissions (+x)"
                        )
                        break
                if found:
                    break
            self.assertTrue(found, f"Declared binary {src_name} not found in enabled skills")

    def test_anti_reconnaissance_and_anti_exfiltration_invariants(self):
        """core/10-environment-standards.md must declare anti-reconnaissance and anti-exfiltration rules (Issue #184)."""
        env_standards = os.path.join(REPO_ROOT, "core", "10-environment-standards.md")
        with open(env_standards, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Blindaje Anti-Reconocimiento y Anti-Exfiltración", content)
        self.assertIn("find /", content)
        self.assertIn("find $HOME", content)
        self.assertIn("gh api", content)
        self.assertIn("Stop & Ask", content)

    def test_antigravity_rules_authorize_agent_module_bypass(self):
        """runtimes/antigravity/rules/01-sandbox.md must authorize agent-module for bypass (Issue #184)."""
        sandbox_rule = os.path.join(RUNTIMES_DIR, "antigravity", "rules", "01-sandbox.md")
        with open(sandbox_rule, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("agent-module", content)
        self.assertIn("BypassSandbox: true", content)

    def test_config_json_cached_single_parse(self):
        """build.sh must cache config.json and avoid redundant parsing per runtime execution (Issue #192)."""
        res = subprocess.run(
            ["bash", "-c", f"source {BUILD_SH} && load_runtime_config antigravity && echo ${{RUNTIME_CONFIG_CACHE['antigravity:_loaded']}}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Cache verification failed: {res.stderr}")
        self.assertEqual(res.stdout.strip(), "1")


if __name__ == "__main__":
    unittest.main()
