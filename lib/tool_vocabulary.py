#!/usr/bin/env python3
"""
Single Source of Truth for tool vocabulary neutrality, foreign tool detection,
and cross-runtime purity rules (ADR-0050, Issue #288, Issue #292, Issue #294).
"""

import os
import re
import sys

# 1. Herramientas de runtime prohibidas en core (ADR-0050)
FORBIDDEN_CORE_TOOLS = [
    "view_file",
    "replace_file_content",
    "write_to_file",
    "grep_search",
    "find_by_name",
    "read_url_content",
]

# 2. Placeholders sin resolver en dist/
PLACEHOLDER_PATTERN = re.compile(r"\{\{([a-zA-Z0-9_.-]+)\}\}")

# 3. Herramientas cruzadas por runtime en dist/ (ADR-0050)
FOREIGN_TOOLS_BY_RUNTIME = {
    "claude": [
        "view_file",
        "replace_file_content",
        "grep_search",
        "find_by_name",
        "write_to_file",
        "run_command",
        "read_url_content",
        "ask_question",
    ],
    "antigravity": [
        "`Read`",
        "`Grep`",
        "`Glob`",
        "`Write`",
        "`Edit`",
        "`Bash`",
    ],
}

# 4. Prosa normativa en skills/ (ADR-0050, Issue #292)
FORBIDDEN_SKILLS_TOOLS = [
    "view_file",
    "replace_file_content",
    "grep_search",
    "find_by_name",
    "write_to_file",
    "read_url_content",
    "ask_question",
    "list_dir",
    "run_command",
]

CLAUDE_SPECIFIC_TOKENS = [
    "`Read`",
    "`Grep`",
    "`Glob`",
    "`Write`",
    "`Edit`",
    "`Bash`",
]

FORBIDDEN_PARAMS = [
    "StartLine",
    "EndLine",
]

# Mecanismos de subagentes de Antigravity: admitidos solo condicionados en la misma línea
# (fuera de bloques de código, que ilustran la invocación bajo un encabezado condicionado).
CONDITIONED_SUBAGENT_TOKENS = [
    "invoke_subagent",
    "manage_subagents",
    "TypeName",
]

# Archivos cuyos nombres de herramientas son datos (trazas reales), no instrucciones.
EXCLUDED_SKILLS_FILES: set[str] = set()


def validate_core_router(core_dir: str) -> list[str]:
    """Verifica neutralidad de vocabulario en core/00-router.md."""
    errors: list[str] = []
    core_router = os.path.join(core_dir, "00-router.md")
    if os.path.isfile(core_router):
        with open(core_router, "r", encoding="utf-8") as f:
            core_text = f.read()
        for tool in FORBIDDEN_CORE_TOOLS:
            if re.search(r"\b" + re.escape(tool) + r"\b", core_text):
                errors.append(
                    f"Herramienta de runtime \"{tool}\" encontrada en core/00-router.md "
                    "(el core debe usar vocabulario neutral, ADR-0050)"
                )
    return errors


def validate_compiled_prompts(dist_dir: str) -> tuple[list[str], list[str]]:
    """Verifica ausencia de placeholders y herramientas cruzadas en dist/<runtime>/AGENTS.md."""
    errors: list[str] = []
    warnings: list[str] = []

    for r_name in sorted(FOREIGN_TOOLS_BY_RUNTIME):
        prompt_file = os.path.join(dist_dir, r_name, "AGENTS.md")
        if not os.path.isfile(prompt_file):
            warnings.append(
                f"Prompt compilado ausente: dist/{r_name}/AGENTS.md "
                "(ejecutar ./build.sh build); verificación de herramientas omitida"
            )
            continue
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        for p in PLACEHOLDER_PATTERN.findall(content):
            errors.append(f"Placeholder sin resolver \"{{{{{p}}}}}\" detectado en dist/{r_name}/AGENTS.md")

        for tool in FOREIGN_TOOLS_BY_RUNTIME[r_name]:
            if tool.startswith("`"):
                found = tool in content
            else:
                found = re.search(r"\b" + re.escape(tool) + r"\b", content) is not None
            if found:
                errors.append(
                    f"Herramienta cruzada {tool} detectada en dist/{r_name}/AGENTS.md "
                    "(propia de otro runtime)"
                )

    return errors, warnings


def validate_skills_file_content(content: str, rel_path: str = "skill.md") -> list[str]:
    """Verifica neutralidad de vocabulario y reglas de condicionamiento en el contenido de un archivo de skill."""
    errors: list[str] = []

    for tool in FORBIDDEN_SKILLS_TOOLS:
        if re.search(r"\b" + re.escape(tool) + r"\b", content):
            errors.append(
                f"Herramienta de runtime \"{tool}\" encontrada en prosa normativa de {rel_path} "
                "(debe usar vocabulario neutral, ADR-0050)"
            )

    for token in CLAUDE_SPECIFIC_TOKENS:
        if token in content:
            errors.append(
                f"Token de herramienta de Claude \"{token}\" encontrado en prosa normativa de {rel_path} "
                "(debe usar vocabulario neutral, ADR-0050)"
            )

    for param in FORBIDDEN_PARAMS:
        if re.search(r"\b" + re.escape(param) + r"\b", content):
            errors.append(
                f"Parámetro de runtime \"{param}\" encontrado en prosa normativa de {rel_path} "
                "(debe usar vocabulario neutral, ADR-0050)"
            )

    in_fence = False
    for idx, line in enumerate(content.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        conditioned = "Antigravity" in line or "antigravity" in line
        if re.search(r"\bBypassSandbox\b", line) and not conditioned:
            errors.append(
                f"Mención incondicional de \"BypassSandbox\" en {rel_path}:{idx} "
                "(debe condicionarse al runtime puntual, Issue #292)"
            )
        if in_fence or conditioned:
            continue
        for token in CONDITIONED_SUBAGENT_TOKENS:
            if re.search(r"\b" + re.escape(token) + r"\b", line):
                errors.append(
                    f"Mención incondicional de \"{token}\" en {rel_path}:{idx} "
                    "(debe condicionarse al runtime puntual, Issue #292)"
                )

    return errors


def validate_skills_prose(skills_dir: str, repo_root: str | None = None) -> list[str]:
    """Recorre skills/ y verifica neutralidad normativa en todos los archivos Markdown."""
    errors: list[str] = []
    if not os.path.isdir(skills_dir):
        return errors

    root_dir = repo_root if repo_root else os.path.abspath(os.path.join(skills_dir, ".."))

    for root, dirs, files in os.walk(skills_dir):
        dirs[:] = [d for d in dirs if d not in ("bin", "scripts", "tests", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, root_dir)
            if rel_path in EXCLUDED_SKILLS_FILES:
                continue
            with open(file_path, "r", encoding="utf-8") as fp:
                content = fp.read()
            errors.extend(validate_skills_file_content(content, rel_path))

    return errors


def check_tool_vocabulary(repo_root: str) -> tuple[list[str], list[str]]:
    """Ejecuta la suite integral de verificación de vocabulario de herramientas."""
    core_dir = os.path.join(repo_root, "core")
    dist_dir = os.path.join(repo_root, "dist")
    skills_dir = os.path.join(repo_root, "skills")

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(validate_core_router(core_dir))
    dist_errors, dist_warnings = validate_compiled_prompts(dist_dir)
    errors.extend(dist_errors)
    warnings.extend(dist_warnings)
    if os.path.isdir(skills_dir):
        errors.extend(validate_skills_prose(skills_dir, repo_root))

    return errors, warnings


if __name__ == "__main__":
    target_root = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    all_errors, all_warnings = check_tool_vocabulary(target_root)
    for err_msg in all_errors:
        print(f"ERROR:{err_msg}")
    for warn_msg in all_warnings:
        print(f"WARN:{warn_msg}")
