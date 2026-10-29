#!/usr/bin/env python3
"""
Pruebas unitarias para el motor de auditoría de conversaciones y detección
del antipatrón TERMINAL_REPL_LOOP en agent-audit.
Ref: Issue #157.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

# Asegurar importación de audit_engine y adaptadores
CURRENT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = CURRENT_DIR.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from adapters.base import ConversationMetadata, NormalizedStep, NormalizedToolCall
from audit_engine import AuditEngine, DetectedAntipattern


class TestInlineEvalDetection(unittest.TestCase):
    """Pruebas para AuditEngine.check_inline_eval."""

    def test_positive_eval_commands(self):
        """Verifica que diversos comandos de evaluación en línea sean identificados con su runtime."""
        cases = [
            ('python3 -c "import re; print(1)"', "python3"),
            ("python -c 'print(1)'", "python"),
            ('python3.11 -c "x = 1"', "python3.11"),
            ('python3.12 -c "x = 1"', "python3.12"),
            ('/usr/bin/python3 -c "print(1)"', "python3"),
            ('/usr/local/bin/python -c "print(1)"', "python"),
            ('sudo python3 -c "print(1)"', "python3"),
            ('env FOO=1 python3 -c "print(1)"', "python3"),
            ('python3 -u -c "print(1)"', "python3"),
            ('python3 -O -c "print(1)"', "python3"),
            ('node -e "console.log(1)"', "node"),
            ('node --eval "console.log(1)"', "node"),
            ('/usr/bin/node -e "process.exit(0)"', "node"),
            ("nodejs -e 'console.log(process.version)'", "nodejs"),
            ("ruby -e 'puts 1'", "ruby"),
            ("/usr/bin/ruby -e 'puts 1'", "ruby"),
            ("perl -e 'print 1'", "perl"),
            ("/usr/bin/perl -e 'print 1'", "perl"),
        ]
        for cmd, expected_rt in cases:
            with self.subTest(cmd=cmd):
                is_eval, rt = AuditEngine.check_inline_eval(cmd)
                self.assertTrue(is_eval, f"Fallo al detectar evaluación inline en: {cmd}")
                self.assertEqual(rt, expected_rt)

    def test_negative_standard_cli_commands(self):
        """Verifica que comandos CLI atómicos estándar NO disparen falsos positivos."""
        cases = [
            "python3 script.py",
            "python3 -m unittest discover -s tests",
            "python3 -m pytest tests/",
            "python3 script.py -c config.json",
            "python script.py --eval mode",
            "node server.js",
            "node dist/main.js -e production",
            "ruby app.rb",
            "perl script.pl",
            "git status",
            "git commit -m 'feat: python3 -c implementation'",
            "git diff",
            "echo 'python3 -c \"print(1)\"'",
            "cat test.py",
            "grep -rn 'python3 -c' .",
            "which python3",
            "find . -name '*.py'",
            "pytest tests/",
            "npm test",
            "cargo test",
            "docker run -it alpine sh",
        ]
        for cmd in cases:
            with self.subTest(cmd=cmd):
                is_eval, rt = AuditEngine.check_inline_eval(cmd)
                self.assertFalse(is_eval, f"Falso positivo detectado para comando estándar: {cmd}")
                self.assertEqual(rt, "")


class TestTerminalReplLoopAntipattern(unittest.TestCase):
    """Pruebas para la detección del antipatrón TERMINAL_REPL_LOOP en AuditEngine."""

    def setUp(self):
        self.engine = AuditEngine()
        self.metadata = ConversationMetadata(
            session_id="test-session-157",
            runtime="antigravity",
            source_path="/tmp/transcript.jsonl",
        )

    def _make_step(self, step_index: int, tool_name: str, command: str) -> NormalizedStep:
        return NormalizedStep(
            step_index=step_index,
            source="MODEL",
            step_type="PLANNER_RESPONSE",
            tool_calls=[
                NormalizedToolCall(
                    name=tool_name,
                    args={"CommandLine": command},
                    status="DONE",
                )
            ],
            status="DONE",
        )

    def test_consecutive_inline_eval_loop(self):
        """Detecta bucle de 3 o más evaluaciones consecutivas con argumentos variantes."""
        steps = [
            self._make_step(1, "run_command", 'python3 -c "import re; print(1)"'),
            self._make_step(2, "run_command", 'python3 -c "import re; print(2)"'),
            self._make_step(3, "run_command", 'python3 -c "import re; print(3)"'),
        ]
        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 1)
        ap = repl_loops[0]
        self.assertEqual(ap.severity, "ALTA")
        self.assertEqual(ap.title, "Bucle REPL Iterativo en Terminal")
        self.assertEqual(ap.step_index, 3)
        self.assertIn("3 ejecuciones", ap.description)
        self.assertIn("scratch", ap.recommendation)
        self.assertIn("tests unitarios", ap.recommendation)

    def test_high_density_window_loop(self):
        """Detecta alta densidad en ventana corta (ej. 3 evaluaciones en ventana de 5 llamadas)."""
        steps = [
            self._make_step(1, "run_command", 'python3 -c "print(1)"'),
            NormalizedStep(
                step_index=2,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": "/tmp/a.py"}, status="DONE")],
            ),
            self._make_step(3, "run_command", 'python3 -c "print(2)"'),
            self._make_step(4, "run_command", 'python3 -c "print(3)"'),
            NormalizedStep(
                step_index=5,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": "/tmp/b.py"}, status="DONE")],
            ),
        ]
        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 1)
        self.assertEqual(repl_loops[0].step_index, 4)
        self.assertIn("3 ejecuciones", repl_loops[0].description)

    def test_no_false_positive_infrequent_eval(self):
        """Comandos aislados o en cantidad menor al umbral (ej. 2) no disparan el antipatrón."""
        steps = [
            self._make_step(1, "run_command", 'python3 -c "print(1)"'),
            NormalizedStep(
                step_index=2,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": "/tmp/a.py"}, status="DONE")],
            ),
            self._make_step(3, "run_command", 'python3 -c "print(2)"'),
        ]
        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 0)

    def test_no_false_positive_distant_eval_calls(self):
        """Evaluaciones espaciadas por muchos pasos no forman un bucle REPL."""
        steps = [
            self._make_step(1, "run_command", 'python3 -c "print(1)"'),
        ]
        # 10 pasos normales intercalados
        for i in range(2, 12):
            steps.append(
                NormalizedStep(
                    step_index=i,
                    source="MODEL",
                    step_type="PLANNER_RESPONSE",
                    tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": f"/tmp/{i}.py"}, status="DONE")],
                )
            )
        steps.append(self._make_step(12, "run_command", 'python3 -c "print(2)"'))
        for i in range(13, 23):
            steps.append(
                NormalizedStep(
                    step_index=i,
                    source="MODEL",
                    step_type="PLANNER_RESPONSE",
                    tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": f"/tmp/{i}.py"}, status="DONE")],
                )
            )
        steps.append(self._make_step(23, "run_command", 'python3 -c "print(3)"'))

        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 0)

    def test_multiple_bursts_detected_separately(self):
        """Múltiples ráfagas separadas generan eventos de antipatrón diferenciados."""
        steps = [
            # Ráfaga 1: 3 llamadas python3
            self._make_step(1, "run_command", 'python3 -c "print(1)"'),
            self._make_step(2, "run_command", 'python3 -c "print(2)"'),
            self._make_step(3, "run_command", 'python3 -c "print(3)"'),
        ]
        # Separador de 10 pasos normales
        for i in range(4, 14):
            steps.append(
                NormalizedStep(
                    step_index=i,
                    source="MODEL",
                    step_type="PLANNER_RESPONSE",
                    tool_calls=[NormalizedToolCall(name="view_file", args={"AbsolutePath": f"/tmp/{i}.py"}, status="DONE")],
                )
            )
        # Ráfaga 2: 3 llamadas node -e
        steps.extend([
            self._make_step(14, "run_command", 'node -e "console.log(1)"'),
            self._make_step(15, "run_command", 'node -e "console.log(2)"'),
            self._make_step(16, "run_command", 'node -e "console.log(3)"'),
        ])

        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 2)
        self.assertIn("python3", repl_loops[0].description)
        self.assertIn("node", repl_loops[1].description)

    def test_claude_adapter_bash_compatibility(self):
        """Verifica compatibilidad con el tool 'Bash' y argumento 'command' (Claude Code)."""
        steps = [
            NormalizedStep(
                step_index=1,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[
                    NormalizedToolCall(
                        name="Bash",
                        args={"command": 'python3 -c "import os; print(os.name)"'},
                        status="DONE",
                    )
                ],
            ),
            NormalizedStep(
                step_index=2,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[
                    NormalizedToolCall(
                        name="Bash",
                        args={"command": 'python3 -c "import sys; print(sys.version)"'},
                        status="DONE",
                    )
                ],
            ),
            NormalizedStep(
                step_index=3,
                source="MODEL",
                step_type="PLANNER_RESPONSE",
                tool_calls=[
                    NormalizedToolCall(
                        name="Bash",
                        args={"command": 'python3 -c "import platform; print(platform.system())"'},
                        status="DONE",
                    )
                ],
            ),
        ]
        report = self.engine.analyze(self.metadata, steps)
        repl_loops = [ap for ap in report.antipatterns if ap.code == "TERMINAL_REPL_LOOP"]
        self.assertEqual(len(repl_loops), 1)
        self.assertEqual(repl_loops[0].step_index, 3)


class TestAgentAuditCli(unittest.TestCase):
    """Pruebas de integración E2E para el CLI agent-audit con TERMINAL_REPL_LOOP."""

    @classmethod
    def setUpClass(cls):
        import importlib.machinery
        import importlib.util
        cli_path = SKILL_ROOT / "bin" / "agent-audit"
        loader = importlib.machinery.SourceFileLoader("agent_audit_cli", str(cli_path))
        spec = importlib.util.spec_from_loader("agent_audit_cli", loader)
        cls.agent_audit = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.agent_audit)

    def test_cli_detects_repl_loop_and_fails_on_antipattern(self):
        import json
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_file = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"step_index": 0, "source": "USER", "type": "USER_INPUT", "content": "test"},
                {
                    "step_index": 1,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": 'python3 -c "print(1)"'}}],
                },
                {
                    "step_index": 2,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": 'python3 -c "print(2)"'}}],
                },
                {
                    "step_index": 3,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": 'python3 -c "print(3)"'}}],
                },
            ]
            with open(transcript_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line) + "\n")

            test_argv = ["agent-audit", str(transcript_file), "--fail-on-antipattern"]
            with patch("sys.argv", test_argv):
                code = self.agent_audit.main()
                self.assertEqual(code, 2)


class TestSubagentPromptConsistency(unittest.TestCase):
    """Pruebas de consistencia para el modo de auditoría en background vía subagente."""

    def test_subagent_prompt_template_exists_and_valid(self):
        template_file = SKILL_ROOT / "templates" / "subagent_prompt.md"
        self.assertTrue(template_file.is_file(), f"No se encontró {template_file}")
        content = template_file.read_text(encoding="utf-8")
        self.assertIn("agent-audit {{TARGET_SESSION}} --format markdown", content)
        self.assertIn("CONSECUTIVE_TOOL_ERRORS", content)
        self.assertIn("REPETITIVE_TOOL_LOOP", content)
        self.assertIn("TERMINAL_REPL_LOOP", content)
        self.assertIn("CONTEXT_TRUNCATION", content)
        self.assertIn("Diagnóstico Ejecutivo Consolidado", content)
        self.assertIn("Veredicto de Antipatrones", content)

    def test_skill_docs_cover_subagent_mode(self):
        skill_file = SKILL_ROOT / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("## 5. Modo de Auditoría Desacoplada en Background vía Subagente", content)
        self.assertIn("templates/subagent_prompt.md", content)
        self.assertIn('"TypeName": "self"', content)
        self.assertIn('"Model": "flash"', content)

    def test_markdown_report_matches_subagent_expectations(self):
        from audit_engine import AuditReport, format_markdown_report

        metadata = ConversationMetadata(
            session_id="test-session-123",
            title="Test Session",
            runtime="antigravity",
            source_path="/tmp/test",
            start_time=datetime(2026, 10, 29, 10, 0, 0),
            end_time=datetime(2026, 10, 29, 10, 5, 0),
        )
        report = AuditReport(
            metadata=metadata,
            total_steps=10,
            user_turns=2,
            model_turns=5,
            system_steps=3,
            wall_clock_seconds=300.0,
            avg_step_latency_seconds=30.0,
            max_step_latency_seconds=45.0,
        )
        md = format_markdown_report(report)
        self.assertIn("## 1. Resumen Ejecutivo", md)
        self.assertIn("## 2. Desglose de Herramientas", md)
        self.assertIn("## 3. Pasos de Mayor Latencia", md)
        self.assertIn("## 4. Antipatrones y Anomalías Detectadas", md)


if __name__ == "__main__":
    unittest.main()

