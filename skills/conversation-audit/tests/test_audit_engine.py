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


class TestUnpaginatedFileReadAntipattern(unittest.TestCase):
    """Pruebas para la detección del antipatrón UNPAGINATED_FILE_READ en AuditEngine."""

    def setUp(self):
        self.engine = AuditEngine()
        self.metadata = ConversationMetadata(
            session_id="test-session-178",
            runtime="antigravity",
            source_path="/tmp/transcript.jsonl",
        )

    def _make_step(self, step_index: int, tool_name: str, args: dict) -> NormalizedStep:
        return NormalizedStep(
            step_index=step_index,
            source="MODEL",
            step_type="PLANNER_RESPONSE",
            tool_calls=[
                NormalizedToolCall(
                    name=tool_name,
                    args=args,
                    status="DONE",
                )
            ],
            status="DONE",
        )

    def test_unpaginated_view_file_without_delimiters(self):
        """Detecta llamada a view_file sin delimitadores StartLine/EndLine."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py"}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 1)
        ap = unpaginated[0]
        self.assertEqual(ap.severity, "ALTA")
        self.assertEqual(ap.title, "Lectura No Paginada de Archivo")
        self.assertEqual(ap.step_index, 1)
        self.assertIn("sin especificar delimitadores de paginación", ap.description)
        self.assertIn("grep_search", ap.recommendation)
        self.assertIn("StartLine y EndLine", ap.recommendation)

    def test_partial_delimiters_start_only(self):
        """Detecta llamada a view_file con solo StartLine sin delimitar EndLine."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 50}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 1)
        ap = unpaginated[0]
        self.assertIn("sin especificar EndLine", ap.description)

    def test_partial_delimiters_end_only(self):
        """Detecta llamada a view_file con solo EndLine sin delimitar StartLine."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "EndLine": 300}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 1)
        ap = unpaginated[0]
        self.assertIn("sin especificar StartLine", ap.description)

    def test_excessive_line_range_detected(self):
        """Detecta rango de líneas que supera el umbral configurable (350 - 1 = 349 > 200)."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 350}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 1)
        ap = unpaginated[0]
        self.assertEqual(ap.severity, "ALTA")
        self.assertIn("rango de 349 líneas", ap.description)
        self.assertIn("superando el umbral configurable de 200 líneas", ap.description)

    def test_acceptable_line_range_not_flagged(self):
        """Lecturas dentro del umbral (<= 200 líneas) no disparan el antipatrón."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 200}),
            self._make_step(2, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 50, "EndLine": 120}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 0)

    def test_exact_threshold_boundary(self):
        """Diferencia de exactamente 200 no dispara; 201 sí dispara."""
        # StartLine=1, EndLine=201 -> diff = 200 <= 200 (OK)
        steps_ok = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 201}),
        ]
        report_ok = self.engine.analyze(self.metadata, steps_ok)
        self.assertEqual(len([ap for ap in report_ok.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]), 0)

        # StartLine=1, EndLine=202 -> diff = 201 > 200 (Antipatrón)
        steps_over = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 202}),
        ]
        report_over = self.engine.analyze(self.metadata, steps_over)
        self.assertEqual(len([ap for ap in report_over.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]), 1)

    def test_custom_configurable_threshold(self):
        """Verifica que el umbral de líneas sea configurable a través de file_lines_threshold."""
        custom_engine = AuditEngine(file_lines_threshold=50)
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 80}),
        ]
        report = custom_engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 1)
        self.assertIn("superando el umbral configurable de 50 líneas", unpaginated[0].description)

    def test_claude_adapter_view_range(self):
        """Verifica compatibilidad con el formato view_range de Claude Code."""
        steps_over = [
            self._make_step(1, "View", {"file_path": "/workspace/main.ts", "view_range": [1, 500]}),
        ]
        report_over = self.engine.analyze(self.metadata, steps_over)
        self.assertEqual(len([ap for ap in report_over.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]), 1)

        steps_ok = [
            self._make_step(1, "View", {"file_path": "/workspace/main.ts", "view_range": [1, 100]}),
        ]
        report_ok = self.engine.analyze(self.metadata, steps_ok)
        self.assertEqual(len([ap for ap in report_ok.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]), 0)

    def test_binary_files_ignored(self):
        """Archivos binarios o imágenes (ej. .png, .jpg, .pdf) no requieren paginación y se ignoran."""
        steps = [
            self._make_step(1, "view_file", {"AbsolutePath": "/workspace/assets/logo.png"}),
            self._make_step(2, "view_file", {"AbsolutePath": "/workspace/docs/manual.pdf"}),
            self._make_step(3, "View", {"file_path": "/workspace/assets/photo.jpg"}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 0)

    def test_non_read_tools_ignored(self):
        """Otras herramientas sin función de lectura de archivos no son evaluadas."""
        steps = [
            self._make_step(1, "run_command", {"CommandLine": "ls -la"}),
            self._make_step(2, "grep_search", {"Query": "pattern", "SearchPath": "/workspace"}),
        ]
        report = self.engine.analyze(self.metadata, steps)
        unpaginated = [ap for ap in report.antipatterns if ap.code == "UNPAGINATED_FILE_READ"]
        self.assertEqual(len(unpaginated), 0)


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

    def test_cli_detects_unpaginated_file_read_and_threshold_flag(self):
        """El CLI detecta UNPAGINATED_FILE_READ y respeta --threshold-file-lines."""
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
                    "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "/workspace/main.py", "StartLine": 1, "EndLine": 80}}],
                },
            ]
            with open(transcript_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line) + "\n")

            # Con umbral default (200), 80 líneas no dispara fallo
            test_argv_default = ["agent-audit", str(transcript_file), "--fail-on-antipattern"]
            with patch("sys.argv", test_argv_default):
                code = self.agent_audit.main()
                self.assertEqual(code, 0)

            # Con umbral --threshold-file-lines 50, 80 líneas dispara antipatrón ALTA -> código 2
            test_argv_custom = ["agent-audit", str(transcript_file), "--threshold-file-lines", "50", "--fail-on-antipattern"]
            with patch("sys.argv", test_argv_custom):
                code = self.agent_audit.main()
                self.assertEqual(code, 2)


class TestStepInspectionAndFailedSteps(unittest.TestCase):
    """Pruebas unitarias para las funcionalidades quirúrgicas --inspect-step y --failed-steps."""

    def setUp(self):
        self.step_with_error = NormalizedStep(
            step_index=5,
            source="MODEL",
            step_type="PLANNER_RESPONSE",
            created_at=datetime(2026, 10, 29, 12, 0, 0),
            duration_seconds=3.5,
            thinking="Analizando si el comando existe...",
            content="Voy a ejecutar el comando.",
            tool_calls=[
                NormalizedToolCall(
                    name="run_command",
                    args={"CommandLine": "git-prune-gone --sync"},
                    tool_action="Pruning branches",
                    tool_summary="Prune branches",
                    status="ERROR",
                    error="Command not found: git-prune-gone",
                )
            ],
            status="ERROR",
        )

        self.step_ok = NormalizedStep(
            step_index=1,
            source="MODEL",
            step_type="PLANNER_RESPONSE",
            created_at=datetime(2026, 10, 29, 11, 59, 0),
            duration_seconds=1.2,
            content="Lectura de estado completada.",
            tool_calls=[
                NormalizedToolCall(
                    name="run_command",
                    args={"CommandLine": "git status"},
                    tool_action="Checking git status",
                    status="DONE",
                    raw_output="On branch main\nnothing to commit",
                )
            ],
            status="DONE",
        )

    def test_format_step_text_markdown_json(self):
        from audit_engine import format_json_step, format_markdown_step, format_text_step
        import json

        # Texto
        text_out = format_text_step(self.step_with_error)
        self.assertIn("DETALLE DE PASO 5", text_out)
        self.assertIn("run_command", text_out)
        self.assertIn("Command not found: git-prune-gone", text_out)
        self.assertIn("PENSAMIENTO / THINKING:", text_out)

        # Markdown
        md_out = format_markdown_step(self.step_with_error)
        self.assertIn("# Detalle del Paso `5`", md_out)
        self.assertIn("`run_command`", md_out)
        self.assertIn("Command not found: git-prune-gone", md_out)
        self.assertIn("## Pensamiento (Thinking)", md_out)

        # JSON
        json_out = format_json_step(self.step_with_error)
        data = json.loads(json_out)
        self.assertEqual(data["step_index"], 5)
        self.assertEqual(data["status"], "ERROR")
        self.assertEqual(len(data["tool_calls"]), 1)
        self.assertEqual(data["tool_calls"][0]["error"], "Command not found: git-prune-gone")

    def test_format_step_truncates_large_fields(self):
        from audit_engine import format_markdown_step, format_text_step

        huge_step = NormalizedStep(
            step_index=10,
            source="MODEL",
            step_type="PLANNER_RESPONSE",
            content="A" * 3000,
            tool_calls=[
                NormalizedToolCall(
                    name="run_command",
                    args={"CommandLine": "cat huge_file.log"},
                    raw_output="B" * 5000,
                    status="DONE",
                )
            ],
            status="DONE",
        )
        text_out = format_text_step(huge_step, max_content_chars=500)
        self.assertIn("[Salida truncada: se muestran 500 de 5000 caracteres]", text_out)
        self.assertIn("[Salida truncada: se muestran 500 de 3000 caracteres]", text_out)

        md_out = format_markdown_step(huge_step, max_content_chars=500)
        self.assertIn("[Salida truncada: se muestran 500 de 5000 caracteres]", md_out)

    def test_get_failed_steps_filtering_and_deduplication(self):
        from audit_engine import get_failed_steps

        # Paso 1: OK
        # Paso 2: Tool call con ERROR
        # Paso 3: GENERIC output step con el mismo error duplicado (Antigravity)
        steps = [
            self.step_ok,
            self.step_with_error,
            NormalizedStep(
                step_index=6,
                source="SYSTEM",
                step_type="GENERIC",
                content="Command not found: git-prune-gone",
                status="ERROR",
            ),
        ]
        failed = get_failed_steps(steps)
        # Debe incluir solo el paso 5 (el tool call con error), deduplicando el paso 6
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].step_index, 5)

    def test_format_failed_steps_text_markdown_json(self):
        from audit_engine import (
            format_json_failed_steps,
            format_markdown_failed_steps,
            format_text_failed_steps,
        )
        import json

        failed_steps = [self.step_with_error]

        # Texto con fallos
        txt_out = format_text_failed_steps(failed_steps)
        self.assertIn("Total de pasos con errores: 1", txt_out)
        self.assertIn("Paso 5", txt_out)
        self.assertIn("Command not found: git-prune-gone", txt_out)

        # Markdown con fallos
        md_out = format_markdown_failed_steps(failed_steps)
        self.assertIn("Total de pasos con errores detectados: **1**", md_out)
        self.assertIn("`run_command`", md_out)

        # JSON con fallos
        json_out = format_json_failed_steps(failed_steps)
        data = json.loads(json_out)
        self.assertEqual(data["total_failed_steps"], 1)
        self.assertEqual(len(data["failed_steps"]), 1)
        self.assertEqual(data["failed_steps"][0]["failed_tools"][0]["name"], "run_command")

        # Texto sin fallos
        clean_txt = format_text_failed_steps([])
        self.assertIn("No se registraron pasos con errores de herramientas", clean_txt)

        # Markdown sin fallos
        clean_md = format_markdown_failed_steps([])
        self.assertIn("No se registraron pasos con errores de herramientas", clean_md)

    def test_cli_inspect_step_flag(self):
        import json
        import tempfile
        from unittest.mock import patch
        import importlib.machinery
        import importlib.util

        cli_path = SKILL_ROOT / "bin" / "agent-audit"
        loader = importlib.machinery.SourceFileLoader("agent_audit_cli_test", str(cli_path))
        spec = importlib.util.spec_from_loader("agent_audit_cli_test", loader)
        cli_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(cli_mod)

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_file = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"step_index": 0, "source": "USER", "type": "USER_INPUT", "content": "hola"},
                {
                    "step_index": 1,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": "ls"}}],
                },
            ]
            with open(transcript_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line) + "\n")

            # Paso existente (0 y 1)
            with patch("sys.argv", ["agent-audit", str(transcript_file), "--inspect-step", "1"]):
                code = cli_mod.main()
                self.assertEqual(code, 0)

            # Paso inexistente (999) -> código 1
            with patch("sys.argv", ["agent-audit", str(transcript_file), "--inspect-step", "999"]):
                code = cli_mod.main()
                self.assertEqual(code, 1)

    def test_cli_failed_steps_flag(self):
        import json
        import tempfile
        from unittest.mock import patch
        import importlib.machinery
        import importlib.util

        cli_path = SKILL_ROOT / "bin" / "agent-audit"
        loader = importlib.machinery.SourceFileLoader("agent_audit_cli_test_failed", str(cli_path))
        spec = importlib.util.spec_from_loader("agent_audit_cli_test_failed", loader)
        cli_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(cli_mod)

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_file = Path(tmpdir) / "transcript.jsonl"
            lines = [
                {"step_index": 0, "source": "USER", "type": "USER_INPUT", "content": "hola"},
                {
                    "step_index": 1,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "status": "ERROR",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": "false"}}],
                },
                {
                    "step_index": 2,
                    "source": "SYSTEM",
                    "type": "GENERIC",
                    "status": "ERROR",
                    "content": "The command exited with code 1",
                },
            ]
            with open(transcript_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line) + "\n")

            with patch("sys.argv", ["agent-audit", str(transcript_file), "--failed-steps", "--format", "json"]):
                code = cli_mod.main()
                self.assertEqual(code, 0)


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
        self.assertIn("UNPAGINATED_FILE_READ", content)
        self.assertIn("Diagnóstico Ejecutivo Consolidado", content)
        self.assertIn("Veredicto de Antipatrones", content)

    def test_subagent_prompt_contains_strict_shielding_rules(self):
        """Verifica que el prompt del subagente prohíba comandos ajenos y delimite presupuesto."""
        template_file = SKILL_ROOT / "templates" / "subagent_prompt.md"
        content = template_file.read_text(encoding="utf-8")
        # Prohibición explícita de herramientas no autorizadas
        self.assertIn("PROHIBIDO TAXATIVAMENTE", content)
        self.assertIn("python3", content)
        self.assertIn("bash", content)
        self.assertIn("grep", content)
        # Presupuesto acotado
        self.assertIn("Tool Budget", content)
        self.assertIn("2 a 3 invocaciones de herramientas", content)
        self.assertIn("--failed-steps", content)
        self.assertIn("--inspect-step", content)
        # Disyuntor autónomo
        self.assertIn("Stop & Synthesize", content)
        self.assertIn("Circuit Breaker", content)

    def test_skill_docs_cover_subagent_mode_and_shielding(self):
        skill_file = SKILL_ROOT / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("## 5. Modo de Auditoría Desacoplada en Background vía Subagente", content)
        self.assertIn("templates/subagent_prompt.md", content)
        self.assertIn('"TypeName": "self"', content)
        self.assertIn('"Model": "flash"', content)
        self.assertIn("--inspect-step <N>", content)
        self.assertIn("--failed-steps", content)
        self.assertIn("Stop & Synthesize", content)
        self.assertIn("máximo 3 tool calls", content)

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


