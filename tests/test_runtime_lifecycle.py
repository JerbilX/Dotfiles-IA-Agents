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


if __name__ == "__main__":
    unittest.main()
