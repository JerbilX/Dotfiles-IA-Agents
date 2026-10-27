#!/usr/bin/env python3
"""
Motor de cálculo, agregación de métricas y detección de antipatrones para conversation-audit.
"""

import re
import shlex
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import ConversationMetadata, NormalizedStep, NormalizedToolCall


@dataclass
class DetectedAntipattern:
    """Representa un antipatrón o vicio de comportamiento detectado."""
    severity: str  # CRÍTICA, ALTA, MEDIA, BAJA
    code: str
    title: str
    step_index: int
    description: str
    recommendation: str


@dataclass
class ToolMetrics:
    """Métricas asociadas a una herramienta específica."""
    name: str
    invocations: int = 0
    errors: int = 0

    @property
    def error_rate(self) -> float:
        return (self.errors / self.invocations * 100.0) if self.invocations > 0 else 0.0


@dataclass
class AuditReport:
    """Reporte cuantitativo y cualitativo consolidado de una sesión."""
    metadata: ConversationMetadata
    total_steps: int = 0
    user_turns: int = 0
    model_turns: int = 0
    system_steps: int = 0
    wall_clock_seconds: float = 0.0
    avg_step_latency_seconds: float = 0.0
    max_step_latency_seconds: float = 0.0
    slowest_steps: List[Dict[str, Any]] = field(default_factory=list)
    total_tool_calls: int = 0
    total_tool_errors: int = 0
    tool_metrics: Dict[str, ToolMetrics] = field(default_factory=dict)
    thinking_steps_count: int = 0
    total_thinking_chars: int = 0
    avg_thinking_chars: float = 0.0
    antipatterns: List[DetectedAntipattern] = field(default_factory=list)
    steps_timeline: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def overall_tool_error_rate(self) -> float:
        return (self.total_tool_errors / self.total_tool_calls * 100.0) if self.total_tool_calls > 0 else 0.0


class AuditEngine:
    """Motor de análisis de sesiones de agentes."""

    COMPLACENCY_PATTERNS = [
        "gran idea",
        "tienes toda la razón",
        "tienes razón",
        "disculpa las molestias",
        "mil disculpas",
        "pido disculpas",
        "análisis impecable",
        "excelente observación",
    ]

    TERMINAL_TOOL_NAMES = {
        "run_command",
        "bash",
        "execute_command",
        "terminal",
        "sh",
        "run_shell_command",
    }

    INTERPRETER_REGEX = re.compile(
        r"^(python(?:\d+(?:\.\d+)?)?|node|nodejs|ruby|perl)(\.exe)?$",
        re.IGNORECASE,
    )

    WRAPPERS = {"sudo", "env", "nohup", "time", "winpty"}

    EVAL_FLAGS_BY_RUNTIME = {
        "python": {"-c"},
        "node": {"-e", "--eval"},
        "nodejs": {"-e", "--eval"},
        "ruby": {"-e"},
        "perl": {"-e"},
    }

    NON_EVAL_COMMANDS = {
        "echo", "cat", "grep", "git", "which", "curl", "wget", "sed", "awk",
        "find", "rg", "head", "tail", "less", "more", "touch", "rm", "cp", "mv",
        "ls", "pytest", "cargo", "npm", "yarn", "pnpm", "pip", "pip3", "docker",
    }

    FALLBACK_INLINE_EVAL_REGEX = re.compile(
        r"""
        (?:^|[\s;&|`$()])
        (?:(?:/[^\s/]+/)*(?:sudo\s+|env\s+(?:\w+=\S+\s+)*)*)?
        (?P<runtime>python(?:\d+(?:\.\d+)?)?|node|nodejs|ruby|perl)
        (?:\.exe)?
        \s+
        (?:-[a-zA-Z0-9_\-]+\s+)*
        (?P<flag>-c|-e|--eval)\b
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @classmethod
    def check_inline_eval(cls, cmd: str) -> Tuple[bool, str]:
        """Detecta si un comando invoca una evaluación en línea (REPL) en un intérprete soportado."""
        cmd_str = cmd.strip()
        if not cmd_str:
            return False, ""

        # Descarte rápido de comandos CLI no evaluadores
        first_word = cmd_str.split()[0].lower()
        first_word_clean = Path(first_word).name
        if first_word_clean in cls.NON_EVAL_COMMANDS:
            return False, ""

        # 1. Análisis estructurado de tokens vía shlex
        try:
            tokens = shlex.split(cmd_str)
        except Exception:
            tokens = None

        if tokens:
            idx = 0
            while idx < len(tokens):
                tok = tokens[idx]
                # Saltar asignaciones de variables de entorno (VAR=val)
                if "=" in tok and not tok.startswith("-"):
                    idx += 1
                    continue
                # Saltar ejecutables envoltorios comunes
                if tok.lower() in cls.WRAPPERS:
                    idx += 1
                    continue
                break

            if idx < len(tokens):
                candidate = Path(tokens[idx]).name.lower()
                if candidate.endswith(".exe"):
                    candidate = candidate[:-4]

                m = cls.INTERPRETER_REGEX.match(candidate)
                if m:
                    runtime_family = "python" if candidate.startswith("python") else candidate
                    valid_flags = cls.EVAL_FLAGS_BY_RUNTIME.get(runtime_family, {"-c", "-e", "--eval"})

                    # Verificar tokens subsiguientes
                    for arg in tokens[idx + 1:]:
                        if arg in valid_flags:
                            return True, candidate
                        if not arg.startswith("-"):
                            # Token no es flag: es el nombre de un archivo script (ej. python script.py -c ...)
                            return False, ""
                    return False, ""
            return False, ""

        # 2. Heurística fallback mediante regex
        m = cls.FALLBACK_INLINE_EVAL_REGEX.search(cmd_str)
        if m:
            rt = m.group("runtime").lower()
            flag = m.group("flag").lower()
            rt_family = "python" if rt.startswith("python") else rt
            valid_flags = cls.EVAL_FLAGS_BY_RUNTIME.get(rt_family, {"-c", "-e", "--eval"})
            if flag in valid_flags:
                return True, rt

        return False, ""

    def __init__(self, latency_threshold_seconds: float = 60.0):
        self.latency_threshold = latency_threshold_seconds

    def analyze(self, metadata: ConversationMetadata, steps: List[NormalizedStep]) -> AuditReport:
        """Calcula todas las métricas y detecta antipatrones a partir de los pasos."""
        report = AuditReport(metadata=metadata)
        report.total_steps = len(steps)

        if not steps:
            return report

        # 1. Contabilización de turnos
        for s in steps:
            if s.source == "USER" or s.step_type == "USER_INPUT":
                report.user_turns += 1
            elif s.source == "MODEL" or s.step_type == "PLANNER_RESPONSE":
                report.model_turns += 1
            else:
                report.system_steps += 1

        # 2. Métricas temporales (Wall-Clock y Latencias)
        valid_ts = [s.created_at for s in steps if s.created_at is not None]
        if valid_ts:
            valid_ts.sort()
            report.wall_clock_seconds = max(0.0, (valid_ts[-1] - valid_ts[0]).total_seconds())

        durations = [s.duration_seconds for s in steps if s.duration_seconds is not None]
        if durations:
            report.avg_step_latency_seconds = sum(durations) / len(durations)
            report.max_step_latency_seconds = max(durations)

        # Pasos más lentos (Top 5)
        steps_with_dur = [s for s in steps if s.duration_seconds is not None]
        steps_with_dur.sort(key=lambda s: s.duration_seconds or 0.0, reverse=True)
        report.slowest_steps = []
        for s in steps_with_dur[:5]:
            item = {
                "step_index": s.step_index,
                "duration_seconds": round(s.duration_seconds or 0.0, 2),
                "type": s.step_type,
                "source": s.source,
                "tools": [tc.name for tc in s.tool_calls],
            }
            if s.tool_calls:
                actions = [tc.tool_action or tc.args.get("CommandLine", "")[:60] for tc in s.tool_calls if tc.tool_action or tc.args.get("CommandLine")]
                if actions:
                    item["detail"] = " | ".join(actions)
            elif s.content:
                clean_c = s.content.strip().replace("\n", " ")
                item["detail"] = clean_c[:80] + "..." if len(clean_c) > 80 else clean_c
            report.slowest_steps.append(item)

        # Cronología de pasos
        for s in steps:
            tools_summary = []
            for tc in s.tool_calls:
                cmd = tc.args.get("CommandLine") or tc.args.get("command") or ""
                act = tc.tool_action or tc.tool_summary or ""
                target = tc.args.get("TargetFile") or tc.args.get("AbsolutePath") or ""
                tools_summary.append({
                    "name": tc.name,
                    "action": act,
                    "command": cmd,
                    "target": target,
                })

            report.steps_timeline.append({
                "step_index": s.step_index,
                "source": s.source,
                "type": s.step_type,
                "duration_seconds": round(s.duration_seconds or 0.0, 2),
                "tools": tools_summary,
                "content_snippet": (s.content[:100].replace("\n", " ") + "...") if s.content else "",
                "truncated": s.truncated_fields,
            })

        # 3. Métricas de Herramientas
        tool_counts: Dict[str, int] = defaultdict(int)
        tool_errors: Dict[str, int] = defaultdict(int)

        for s in steps:
            for tc in s.tool_calls:
                report.total_tool_calls += 1
                tool_counts[tc.name] += 1
                if tc.status == "ERROR":
                    report.total_tool_errors += 1
                    tool_errors[tc.name] += 1

        for name, count in tool_counts.items():
            report.tool_metrics[name] = ToolMetrics(
                name=name,
                invocations=count,
                errors=tool_errors[name],
            )

        # 4. Métricas de Thinking / Razonamiento
        for s in steps:
            if s.thinking:
                report.thinking_steps_count += 1
                report.total_thinking_chars += len(s.thinking)

        if report.thinking_steps_count > 0:
            report.avg_thinking_chars = report.total_thinking_chars / report.thinking_steps_count

        # 5. Detección de Antipatrones
        report.antipatterns = self._detect_antipatterns(steps)

        return report

    def _detect_antipatterns(self, steps: List[NormalizedStep]) -> List[DetectedAntipattern]:
        """Ejecuta heurísticas para identificar comportamientos defectuosos o ineficientes."""
        antipatterns: List[DetectedAntipattern] = []

        # A. Latencias anómalas
        for s in steps:
            if s.duration_seconds and s.duration_seconds > self.latency_threshold:
                antipatterns.append(
                    DetectedAntipattern(
                        severity="MEDIA",
                        code="HIGH_LATENCY_STEP",
                        title="Paso de Alta Latencia",
                        step_index=s.step_index,
                        description=f"El paso {s.step_index} tardó {s.duration_seconds:.1f}s (umbral: {self.latency_threshold}s). Herramientas invocadas: {[tc.name for tc in s.tool_calls]}.",
                        recommendation="Verificar si hubo descargas pesadas de red, subprocesos bloqueantes o si conviene acotar el alcance de la herramienta.",
                    )
                )

        # B. Truncamiento severo de contexto
        for s in steps:
            if s.truncated_fields:
                antipatterns.append(
                    DetectedAntipattern(
                        severity="ALTA",
                        code="CONTEXT_TRUNCATION",
                        title="Truncamiento de Contexto Detectado",
                        step_index=s.step_index,
                        description=f"El paso {s.step_index} sufrió truncamiento en campos: {', '.join(s.truncated_fields)}. Puede implicar pérdida de información crítica.",
                        recommendation="Evitar comandos o volcados masivos en stdout; utilizar paginación nativa, filtros JSON o herramientas nativas de archivos con límites acotados.",
                    )
                )

        # C. Bucles de reintento / Herramientas repetitivas
        for i in range(len(steps) - 1):
            curr_s = steps[i]
            next_s = steps[i + 1]
            if curr_s.tool_calls and next_s.tool_calls:
                curr_names = [tc.name for tc in curr_s.tool_calls]
                next_names = [tc.name for tc in next_s.tool_calls]
                if curr_names == next_names and len(curr_names) == 1:
                    # Comparar argumentos
                    tc1 = curr_s.tool_calls[0]
                    tc2 = next_s.tool_calls[0]
                    if tc1.args == tc2.args:
                        antipatterns.append(
                            DetectedAntipattern(
                                severity="ALTA",
                                code="REPETITIVE_TOOL_LOOP",
                                title="Bucle Repetitivo de Herramienta",
                                step_index=next_s.step_index,
                                description=f"Invocación consecutiva e idéntica de '{tc1.name}' entre los pasos {curr_s.step_index} y {next_s.step_index} con argumentos idénticos.",
                                recommendation="Verificar si el agente cayó en un bucle ciego sin procesar adecuadamente la respuesta anterior.",
                            )
                        )

        # D. Errores consecutivos de herramientas
        consecutive_errors = 0
        last_error_step = -1
        for s in steps:
            has_error = False
            for tc in s.tool_calls:
                if tc.status == "ERROR":
                    has_error = True
                    break
            if has_error:
                consecutive_errors += 1
                last_error_step = s.step_index
            else:
                if consecutive_errors >= 2:
                    antipatterns.append(
                        DetectedAntipattern(
                            severity="CRÍTICA",
                            code="CONSECUTIVE_TOOL_ERRORS",
                            title="Errores Consecutivos de Herramientas",
                            step_index=last_error_step,
                            description=f"Se registraron {consecutive_errors} pasos consecutivos con errores en ejecución de herramientas finalizando en el paso {last_error_step}.",
                            recommendation="Aplicar Stop & Ask tras 2-3 fallos consecutivos en lugar de iterar a ciegas.",
                        )
                    )
                consecutive_errors = 0

        if consecutive_errors >= 2:
            antipatterns.append(
                DetectedAntipattern(
                    severity="CRÍTICA",
                    code="CONSECUTIVE_TOOL_ERRORS",
                    title="Errores Consecutivos de Herramientas",
                    step_index=last_error_step,
                    description=f"Se registraron {consecutive_errors} pasos consecutivos con errores en ejecución de herramientas finalizando en el paso {last_error_step}.",
                    recommendation="Aplicar Stop & Ask tras 2-3 fallos consecutivos en lugar de iterar a ciegas.",
                )
            )

        # E. Pipelining / Encadenamiento en Terminal
        for s in steps:
            for tc in s.tool_calls:
                if tc.name in ("run_command", "bash", "execute_command"):
                    cmd = str(tc.args.get("CommandLine", tc.args.get("command", "")))
                    if any(pipe in cmd for pipe in (" | ", " && ", " || ", ";")):
                        antipatterns.append(
                            DetectedAntipattern(
                                severity="MEDIA",
                                code="TERMINAL_PIPELINING",
                                title="Encadenamiento de Comandos en Terminal",
                                step_index=s.step_index,
                                description=f"El paso {s.step_index} invocó comando con pipes o conectores ('{cmd[:60]}...'). Rompe el prefix matching de sandbox.",
                                recommendation="Dividir en llamadas atómicas independientes o utilizar herramientas nativas de archivos.",
                            )
                        )

        # F. Complacencia o adulación vacía
        for s in steps:
            if s.source == "MODEL" and s.content:
                low_c = s.content.lower()
                for pat in self.COMPLACENCY_PATTERNS:
                    if pat in low_c:
                        antipatterns.append(
                            DetectedAntipattern(
                                severity="BAJA",
                                code="COMPLACENCY_DETECTED",
                                title="Complacencia o Disculpa Innecesaria",
                                step_index=s.step_index,
                                description=f"El paso {s.step_index} contiene frase de complacencia ('{pat}'), contraria a core/01-critical-feedback.md.",
                                recommendation="Mantener tono neutro, técnico y asertivo; evitar disculpas o validaciones complacientes vacías.",
                            )
                        )
                        break

        # G. Bucle REPL Iterativo en Terminal (TERMINAL_REPL_LOOP)
        tool_events: List[Dict[str, Any]] = []
        for s in steps:
            for tc in s.tool_calls:
                is_terminal = tc.name.lower() in self.TERMINAL_TOOL_NAMES
                cmd = str(
                    tc.args.get("CommandLine")
                    or tc.args.get("command")
                    or tc.args.get("cmd")
                    or ""
                ) if isinstance(tc.args, dict) else ""

                is_eval = False
                rt = ""
                if is_terminal and cmd:
                    is_eval, rt = self.check_inline_eval(cmd)

                tool_events.append({
                    "step_index": s.step_index,
                    "tool_name": tc.name,
                    "command": cmd,
                    "is_eval": is_eval,
                    "runtime": rt,
                })

        window_size = 5
        min_density = 3
        flagged_indices = set()
        n_events = len(tool_events)

        for i in range(n_events):
            window = tool_events[i : i + window_size]
            eval_indices = [i + offset for offset, ev in enumerate(window) if ev["is_eval"]]
            if len(eval_indices) >= min_density:
                flagged_indices.update(eval_indices)

        if flagged_indices:
            sorted_flagged = sorted(flagged_indices)
            clusters: List[List[int]] = []
            curr_cluster: List[int] = []

            for idx in sorted_flagged:
                if not curr_cluster:
                    curr_cluster.append(idx)
                else:
                    if idx - curr_cluster[-1] <= window_size:
                        curr_cluster.append(idx)
                    else:
                        clusters.append(curr_cluster)
                        curr_cluster = [idx]
            if curr_cluster:
                clusters.append(curr_cluster)

            for cluster in clusters:
                cluster_events = [tool_events[idx] for idx in cluster]
                count = len(cluster_events)
                start_step = cluster_events[0]["step_index"]
                end_step = cluster_events[-1]["step_index"]
                runtimes = ", ".join(sorted(set(ev["runtime"] for ev in cluster_events if ev["runtime"]))) or "código en línea"

                if start_step == end_step:
                    step_desc = f"en el paso {start_step}"
                else:
                    step_desc = f"entre los pasos {start_step} y {end_step}"

                antipatterns.append(
                    DetectedAntipattern(
                        severity="ALTA",
                        code="TERMINAL_REPL_LOOP",
                        title="Bucle REPL Iterativo en Terminal",
                        step_index=end_step,
                        description=(
                            f"Se detectaron {count} ejecuciones de evaluación de código en línea ({runtimes}) "
                            f"en terminal {step_desc}. Indican un patrón de micro-evaluación iterativa / REPL "
                            f"costoso e ineficiente."
                        ),
                        recommendation=(
                            "Desalentar el uso de terminal como REPL e indicar la refactorización hacia un script "
                            "de prueba dedicado en scratch (<appDataDir>/brain/<conversation-id>/scratch/) "
                            "o tests unitarios locales."
                        ),
                    )
                )

        return antipatterns


def format_text_report(report: AuditReport, verbose: bool = False) -> str:
    """Genera una salida tabular compacta para terminal."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append(f" INFORME DE AUDITORÍA TÉCNICA - AGENT-AUDIT")
    lines.append("=" * 72)
    lines.append(f"  Sesión ID        : {report.metadata.session_id}")
    if report.metadata.title:
        lines.append(f"  Título / Objetivo: {report.metadata.title}")
    lines.append(f"  Runtime          : {report.metadata.runtime.upper()}")
    lines.append(f"  Origen           : {report.metadata.source_path}")
    lines.append(f"  Duración Total   : {report.wall_clock_seconds:.1f} s ({report.wall_clock_seconds / 60.0:.2f} min)")
    lines.append(f"  Pasos Totales    : {report.total_steps} (Usuario: {report.user_turns}, Modelo: {report.model_turns}, Sistema: {report.system_steps})")
    lines.append(f"  Latencia Pasos   : Promedio: {report.avg_step_latency_seconds:.2f} s | Máxima: {report.max_step_latency_seconds:.2f} s")
    lines.append(f"  Tool Calls       : {report.total_tool_calls} total | {report.total_tool_errors} errores ({report.overall_tool_error_rate:.1f}%)")
    lines.append(f"  Thinking / Razon : {report.thinking_steps_count} pasos | {report.total_thinking_chars} chars (prom: {report.avg_thinking_chars:.0f} chars/paso)")
    lines.append("-" * 72)

    # Desglose de herramientas
    lines.append(" DESGLOSE DE HERRAMIENTAS:")
    lines.append(f"  {'Herramienta':<28} {'Invocaciones':<14} {'Errores':<10} {'Tasa Fallo':<12}")
    lines.append("  " + "-" * 66)
    for name, m in sorted(report.tool_metrics.items(), key=lambda x: x[1].invocations, reverse=True):
        lines.append(f"  {name:<28} {m.invocations:<14} {m.errors:<10} {m.error_rate:.1f}%")
    lines.append("-" * 72)

    # Pasos más lentos
    if report.slowest_steps:
        lines.append(" PASOS DE MAYOR LATENCIA (TOP 5):")
        for s in report.slowest_steps:
            tools_str = ", ".join(s["tools"]) if s["tools"] else "N/A"
            detail_str = f" | {s['detail']}" if "detail" in s and s["detail"] else ""
            lines.append(f"  - Paso {s['step_index']:<3} : {s['duration_seconds']:>6.1f} s | {s['type']:<18} | Tools: {tools_str}{detail_str}")
        lines.append("-" * 72)

    # Cronología detallada si verbose
    if verbose and report.steps_timeline:
        lines.append(f" CRONOLOGÍA DE PASOS ({len(report.steps_timeline)} pasos):")
        for st in report.steps_timeline:
            tools_str = ", ".join(f"{t['name']}({t['action'] or t['command'][:40]})" if isinstance(t, dict) else str(t) for t in st["tools"]) if st["tools"] else ""
            snip = f" | {st['content_snippet']}" if st["source"] == "USER" else (f" | {tools_str}" if tools_str else "")
            dur = f"{st['duration_seconds']:>6.1f}s"
            lines.append(f"  [{st['step_index']:>3}] {dur} | {st['source']:<6} | {st['type']:<16}{snip}")
        lines.append("-" * 72)

    # Antipatrones
    lines.append(f" ANTIPATRONES DETECTADOS ({len(report.antipatterns)}):")
    if not report.antipatterns:
        lines.append("  [✓] No se detectaron anomalías ni antipatrones de comportamiento.")
    else:
        for ap in report.antipatterns:
            lines.append(f"  [{ap.severity}] Paso {ap.step_index}: {ap.title} ({ap.code})")
            lines.append(f"      Detalle: {ap.description}")
            lines.append(f"      Acción : {ap.recommendation}")
    lines.append("=" * 72)

    return "\n".join(lines)


def format_markdown_report(report: AuditReport, template_path: Optional[Path] = None) -> str:
    """Genera el informe en formato Markdown utilizando la plantilla o estructura estándar."""
    lines: List[str] = []
    lines.append(f"# Informe de Auditoría Técnica: Sesión `{report.metadata.session_id}`")
    lines.append("")
    lines.append("## 1. Resumen Ejecutivo")
    lines.append("")
    if report.metadata.title:
        lines.append(f"- **Título / Objetivo:** {report.metadata.title}")
    lines.append(f"- **Runtime:** `{report.metadata.runtime}`")
    lines.append(f"- **Origen:** `{report.metadata.source_path}`")
    lines.append(f"- **Duración Wall-Clock:** {report.wall_clock_seconds:.1f} s ({report.wall_clock_seconds / 60.0:.2f} min)")
    lines.append(f"- **Pasos Totales:** {report.total_steps} (Usuario: {report.user_turns}, Modelo: {report.model_turns}, Sistema: {report.system_steps})")
    lines.append(f"- **Latencia Promedio por Paso:** {report.avg_step_latency_seconds:.2f} s")
    lines.append(f"- **Latencia Máxima:** {report.max_step_latency_seconds:.2f} s")
    lines.append(f"- **Llamadas a Herramientas:** {report.total_tool_calls} (Errores: {report.total_tool_errors}, Tasa de falla: {report.overall_tool_error_rate:.1f}%)")
    lines.append(f"- **Pasos de Pensamiento/Thinking:** {report.thinking_steps_count} (Total caracteres: {report.total_thinking_chars})")
    lines.append("")
    lines.append("## 2. Desglose de Herramientas")
    lines.append("")
    lines.append("| Herramienta | Invocaciones | Errores | Tasa de Falla (%) |")
    lines.append("| :--- | :---: | :---: | :---: |")
    for name, m in sorted(report.tool_metrics.items(), key=lambda x: x[1].invocations, reverse=True):
        lines.append(f"| `{name}` | {m.invocations} | {m.errors} | {m.error_rate:.1f}% |")
    lines.append("")
    lines.append("## 3. Pasos de Mayor Latencia (Top 5)")
    lines.append("")
    lines.append("| Paso | Duración (s) | Tipo | Herramientas Invocadas |")
    lines.append("| :---: | :---: | :--- | :--- |")
    for s in report.slowest_steps:
        tools_str = ", ".join(f"`{t}`" for t in s["tools"]) if s["tools"] else "N/A"
        detail_str = f" ({s['detail']})" if "detail" in s and s["detail"] else ""
        lines.append(f"| {s['step_index']} | {s['duration_seconds']} | `{s['type']}` | {tools_str}{detail_str} |")
    lines.append("")
    lines.append("## 4. Antipatrones y Anomalías Detectadas")
    lines.append("")
    if not report.antipatterns:
        lines.append("> [!TIP]\n> No se detectaron anomalías ni vicios de comportamiento en esta sesión.")
    else:
        lines.append("| Severidad | Paso | Antipatrón | Descripción | Acción Correctiva |")
        lines.append("| :--- | :---: | :--- | :--- | :--- |")
        for ap in report.antipatterns:
            lines.append(f"| **{ap.severity}** | {ap.step_index} | `{ap.code}` | {ap.description} | {ap.recommendation} |")
    lines.append("")
    lines.append("---")
    lines.append("*Generado automáticamente por el CLI `agent-audit` de Dotfiles-IA-Agents.*")

    return "\n".join(lines)


def format_json_report(report: AuditReport) -> str:
    """Genera una salida serializable JSON."""
    import json

    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return asdict(obj)
        return str(obj)

    data = {
        "metadata": asdict(report.metadata),
        "metrics": {
            "total_steps": report.total_steps,
            "user_turns": report.user_turns,
            "model_turns": report.model_turns,
            "system_steps": report.system_steps,
            "wall_clock_seconds": round(report.wall_clock_seconds, 2),
            "avg_step_latency_seconds": round(report.avg_step_latency_seconds, 2),
            "max_step_latency_seconds": round(report.max_step_latency_seconds, 2),
            "total_tool_calls": report.total_tool_calls,
            "total_tool_errors": report.total_tool_errors,
            "overall_tool_error_rate": round(report.overall_tool_error_rate, 2),
            "thinking_steps_count": report.thinking_steps_count,
            "total_thinking_chars": report.total_thinking_chars,
            "avg_thinking_chars": round(report.avg_thinking_chars, 2),
        },
        "slowest_steps": report.slowest_steps,
        "tools": {name: asdict(m) for name, m in report.tool_metrics.items()},
        "antipatterns": [asdict(ap) for ap in report.antipatterns],
        "timeline": report.steps_timeline,
    }
    return json.dumps(data, indent=2, default=custom_serializer)


def format_text_metadata(metadata: ConversationMetadata) -> str:
    """Genera una salida compacta de metadatos de sesión para terminal."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append(" METADATOS DE SESIÓN - AGENT-AUDIT")
    lines.append("=" * 72)
    lines.append(f"  Sesión ID        : {metadata.session_id}")
    lines.append(f"  Título / Objetivo: {metadata.title or 'N/A'}")
    lines.append(f"  Runtime          : {metadata.runtime.upper()}")
    lines.append(f"  Origen           : {metadata.source_path}")
    if metadata.start_time:
        lines.append(f"  Inicio           : {metadata.start_time.isoformat()}")
    if metadata.end_time:
        lines.append(f"  Fin              : {metadata.end_time.isoformat()}")
    lines.append("=" * 72)
    return "\n".join(lines)


def format_markdown_metadata(metadata: ConversationMetadata) -> str:
    """Genera informe Markdown de metadatos de sesión."""
    lines: List[str] = []
    lines.append(f"# Metadatos de Sesión: `{metadata.session_id}`")
    lines.append("")
    lines.append(f"- **Título / Objetivo:** {metadata.title or 'N/A'}")
    lines.append(f"- **Runtime:** `{metadata.runtime}`")
    lines.append(f"- **Origen:** `{metadata.source_path}`")
    lines.append(f"- **Inicio:** {metadata.start_time.isoformat() if metadata.start_time else 'N/A'}")
    lines.append(f"- **Fin:** {metadata.end_time.isoformat() if metadata.end_time else 'N/A'}")
    lines.append("")
    lines.append("---")
    lines.append("*Generado por `agent-audit` (Dotfiles-IA-Agents).*")
    return "\n".join(lines)


def format_json_metadata(metadata: ConversationMetadata) -> str:
    """Genera JSON de metadatos de sesión."""
    import json

    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return asdict(obj)
        return str(obj)

    return json.dumps({"metadata": asdict(metadata)}, indent=2, default=custom_serializer)

