#!/usr/bin/env python3
"""
Unit tests for lib/compile_mcp.py (Issue #308).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
COMPILE_MCP_PY = os.path.join(LIB_DIR, "compile_mcp.py")
MCP_SCHEMA = os.path.join(REPO_ROOT, "runtimes", "schema", "mcp-server.schema.json")

import sys

if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from compile_mcp import compile_mcp


class TestCompileMcp(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.mcp_dir = os.path.join(self._tmp, "mcp")
        os.makedirs(self.mcp_dir, exist_ok=True)
        self.config_path = os.path.join(self._tmp, "config.json")
        self.dist_path = os.path.join(self._tmp, "dist", "mcp_config.json")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_compile_mcp_success_with_env_expansion_and_schema_removal(self):
        """Valid MCP compiles successfully, removing $schema and expanding env vars."""
        os.environ["TEST_COMPILE_MCP_PORT"] = "9090"
        server_content = {
            "$schema": "../../schema/mcp-server.schema.json",
            "description": "Servidor de prueba",
            "command": "node",
            "args": ["server.js", "--port", "${TEST_COMPILE_MCP_PORT}"],
            "env": {"DEBUG": "1"},
        }
        with open(os.path.join(self.mcp_dir, "test-server.json"), "w", encoding="utf-8") as f:
            json.dump(server_content, f)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["test-server"]}, f)

        count = compile_mcp(self.config_path, self.mcp_dir, self.dist_path, MCP_SCHEMA)
        self.assertEqual(count, 1)

        self.assertTrue(os.path.isfile(self.dist_path))
        with open(self.dist_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("mcpServers", data)
        self.assertIn("test-server", data["mcpServers"])
        srv = data["mcpServers"]["test-server"]
        self.assertNotIn("$schema", srv)
        self.assertNotIn("description", srv)
        self.assertEqual(srv["command"], "node")
        self.assertEqual(srv["args"], ["server.js", "--port", "9090"])
        self.assertEqual(srv["env"], {"DEBUG": "1"})

    def test_compile_mcp_zero_servers(self):
        """Compiling when mcp_servers is empty produces empty mcpServers object."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": []}, f)

        count = compile_mcp(self.config_path, self.mcp_dir, self.dist_path, MCP_SCHEMA)
        self.assertEqual(count, 0)

        with open(self.dist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"mcpServers": {}})

    def test_compile_mcp_missing_config_raises(self):
        """Missing config_file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            compile_mcp(os.path.join(self._tmp, "nonexistent.json"), self.mcp_dir, self.dist_path)

    def test_compile_mcp_invalid_config_json_raises(self):
        """Malformed config JSON raises ValueError."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json")

        with self.assertRaises(ValueError):
            compile_mcp(self.config_path, self.mcp_dir, self.dist_path)

    def test_compile_mcp_missing_server_file_raises(self):
        """Server declared in config but missing in mcp_dir raises FileNotFoundError."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["missing-server"]}, f)

        with self.assertRaises(FileNotFoundError) as ctx:
            compile_mcp(self.config_path, self.mcp_dir, self.dist_path)

        expected_msg = f"Error: Módulo de servidor MCP 'missing-server' declarado en {self.config_path} no existe en {os.path.join(self.mcp_dir, 'missing-server.json')}"
        self.assertIn(expected_msg, str(ctx.exception))

    def test_compile_mcp_invalid_server_json_raises(self):
        """Server file with invalid JSON raises ValueError."""
        with open(os.path.join(self.mcp_dir, "bad-json.json"), "w", encoding="utf-8") as f:
            f.write("{ not json")

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["bad-json"]}, f)

        with self.assertRaises(ValueError):
            compile_mcp(self.config_path, self.mcp_dir, self.dist_path)

    def test_compile_mcp_schema_validation_failure_raises(self):
        """Server file violating schema raises ValueError with validation details."""
        bad_server = {
            "description": "Falta command",
            "args": ["foo"],
        }
        with open(os.path.join(self.mcp_dir, "invalid-schema.json"), "w", encoding="utf-8") as f:
            json.dump(bad_server, f)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["invalid-schema"]}, f)

        with self.assertRaises(ValueError) as ctx:
            compile_mcp(self.config_path, self.mcp_dir, self.dist_path, MCP_SCHEMA)

        self.assertIn("Error de validación", str(ctx.exception))

    def test_compile_mcp_cli_execution(self):
        """CLI invocation of compile_mcp.py validates arguments and exit codes."""
        # 1. Argument count error
        res_usage = subprocess.run(
            ["python3", COMPILE_MCP_PY],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_usage.returncode, 2)
        self.assertIn("Uso: compile_mcp.py", res_usage.stderr)

        # 2. Success run
        server_content = {
            "command": "python3",
            "args": ["-m", "demo"],
        }
        with open(os.path.join(self.mcp_dir, "cli-server.json"), "w", encoding="utf-8") as f:
            json.dump(server_content, f)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["cli-server"]}, f)

        res_ok = subprocess.run(
            ["python3", COMPILE_MCP_PY, self.config_path, self.mcp_dir, self.dist_path, MCP_SCHEMA],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_ok.returncode, 0)
        self.assertTrue(os.path.isfile(self.dist_path))

        # 3. Missing server error
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"mcp_servers": ["nonexistent"]}, f)

        res_err = subprocess.run(
            ["python3", COMPILE_MCP_PY, self.config_path, self.mcp_dir, self.dist_path, MCP_SCHEMA],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_err.returncode, 1)
        self.assertIn("Error: Módulo de servidor MCP 'nonexistent'", res_err.stderr)


if __name__ == "__main__":
    unittest.main()
