#!/usr/bin/env python3
"""
query_decisions.py - Consulta y extracción estructurada de precedentes arquitectónicos y decisiones pasadas (MADR / HISTORIAL).

Utilidad CLI determinista (Zero-Dependencies) para que agentes y desarrolladores consulten
decisiones previas, diagnostiquen fallos recurrentes y contrasten hipótesis contra
el historial documentado del repositorio.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DOMAIN_KEYWORDS = {
    "sandbox-permissions": [
        "sandbox", "bypass", "bypasssandbox", "permission", "read-only", "ro",
        "prefix matching", "kernel", "comillas", "pipe", "evaluador de permisos"
    ],
    "git-workflow": [
        "git", "branch", "prune", "ff-only", "fast-forward", "push", "checkout",
        "commit", "pull", "merge", "pull request", "pr", "gone", "upstream"
    ],
    "architecture-modularity": [
        "runtime", "multi-runtime", "desacopl", "madr", "adr", "blast radius",
        "minima intervencion", "jerarquia de resolucion", "modulariz"
    ],
    "testing-quality": [
        "test", "mock", "fixture", "produccion", "doble", "regresion", "arnes"
    ],
    "context-budget": [
        "token", "palabras", "contexto", "presupuesto", "poda", "check", "telemetria"
    ],
    "tooling-automation": [
        "zero-cli", "build.sh", "schema", "json schema", "link", "symlink",
        "draft 2020-12", "valida"
    ],
}


def find_repo_root(start_path: Path) -> Path:
    """Busca la raíz del repositorio ascendiendo desde start_path."""
    cur = start_path.resolve()
    for _ in range(10):
        if (cur / ".git").is_dir() or (cur / "docs" / "adr").is_dir():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return start_path.resolve()


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extrae el frontmatter YAML y el cuerpo markdown."""
    frontmatter = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        raw_yaml, body = match.group(1), match.group(2)
        for line in raw_yaml.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if val.startswith("[") and val.endswith("]"):
                    items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                    frontmatter[key] = items
                else:
                    frontmatter[key] = val

    return frontmatter, body


def extract_sections(body: str) -> dict[str, str]:
    """Divide el cuerpo en secciones estándar de MADR."""
    sections = {}
    current_header = "Intro"
    current_lines = []

    for line in body.splitlines():
        header_match = re.match(r"^#{1,3}\s+(.+)$", line)
        if header_match:
            if current_lines:
                sections[current_header] = "\n".join(current_lines).strip()
                current_lines = []
            current_header = header_match.group(1).strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_header] = "\n".join(current_lines).strip()

    return sections


def infer_domains(text: str) -> list[str]:
    """Infiere los dominios técnicos asociados al texto analizado."""
    matched = []
    text_lower = text.lower()
    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            matched.append(domain)
    return matched or ["general"]


def load_adrs(adr_dir: Path) -> list[dict]:
    """Carga y parsea todos los archivos de ADRs en adr_dir."""
    records = []
    if not adr_dir.is_dir():
        return records

    for path in sorted(adr_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Advertencia: No se pudo leer {path}: {e}", file=sys.stderr)
            continue

        fm, body = parse_frontmatter(content)
        sections = extract_sections(body)

        title = path.stem
        for h, c in sections.items():
            if h.startswith("0") or " - " in h:
                title = h
                break

        full_searchable = f"{title}\n{body}".lower()
        domains = infer_domains(full_searchable)

        record = {
            "id": path.stem.split("-")[0],
            "filename": path.name,
            "filepath": str(path),
            "title": title,
            "status": fm.get("status", "unknown").lower(),
            "date": fm.get("date", "unknown"),
            "decision_makers": fm.get("decision-makers", []),
            "supersedes": fm.get("supersedes", []),
            "superseded_by": fm.get("superseded-by", []),
            "domains": domains,
            "sections": sections,
            "raw_body": body,
        }
        records.append(record)

    return records


def load_legacy_historial(historial_path: Path) -> list[dict]:
    """Parsea entradas históricas de un archivo legacy HISTORIAL.md si existe."""
    records = []
    if not historial_path.is_file():
        return records

    try:
        content = historial_path.read_text(encoding="utf-8")
    except Exception:
        return records

    entries = re.split(r"\n##\s+", content)
    for idx, entry in enumerate(entries):
        if not entry.strip():
            continue
        lines = entry.strip().splitlines()
        title = lines[0].strip() if lines else f"Entrada {idx}"
        body = "\n".join(lines[1:])
        domains = infer_domains(entry)
        records.append({
            "id": f"LEGACY-{idx+1:03d}",
            "filename": historial_path.name,
            "filepath": str(historial_path),
            "title": f"[LEGACY] {title}",
            "status": "legacy",
            "date": "historical",
            "decision_makers": ["historical-agent"],
            "supersedes": [],
            "superseded_by": [],
            "domains": domains,
            "sections": {"General": body},
            "raw_body": body,
        })
    return records


def filter_records(
    records: list[dict],
    status: str | None,
    domain: str | None,
    query: str | None
) -> list[dict]:
    """Aplica filtros combinados sobre los registros cargados."""
    filtered = []

    for r in records:
        if status and status != "all":
            rec_status = r["status"]
            if status == "superseded" and "superseded" in rec_status:
                pass
            elif rec_status != status:
                continue

        if domain and domain != "all":
            if domain not in r["domains"]:
                continue

        if query:
            q = query.lower()
            searchable = (
                f"{r['title']} {r['status']} {' '.join(r['domains'])} {r['raw_body']}"
            ).lower()
            if q not in searchable:
                continue

        filtered.append(r)

    return filtered


def format_table(records: list[dict]) -> str:
    """Renderiza los registros en una tabla ASCII concisa."""
    if not records:
        return "No se encontraron precedentes que coincidan con los criterios."

    col_id = max(max(len(r["id"]) for r in records), 4)
    col_status = max(max(len(r["status"]) for r in records), 6)
    col_date = max(max(len(r["date"]) for r in records), 10)
    col_title = 60

    lines = []
    header = f"{'ID':<{col_id}}  {'ESTADO':<{col_status}}  {'FECHA':<{col_date}}  {'TÍTULO'}"
    sep = f"{'-'*col_id}  {'-'*col_status}  {'-'*col_date}  {'-'*col_title}"
    lines.append(header)
    lines.append(sep)

    for r in records:
        title_trunc = (r["title"][:57] + "...") if len(r["title"]) > 60 else r["title"]
        lines.append(f"{r['id']:<{col_id}}  {r['status']:<{col_status}}  {r['date']:<{col_date}}  {title_trunc}")

    return "\n".join(lines)


def format_detail(r: dict) -> str:
    """Renderiza la ficha estructurada completa de un precedente."""
    lines = [
        f"=== PRECEDENTE [{r['id']}] {r['title']} ===",
        f"Archivo: {r['filepath']}",
        f"Estado:  {r['status']} | Fecha: {r['date']}",
        f"Dominios: {', '.join(r['domains'])}",
    ]
    if r["supersedes"]:
        lines.append(f"Reemplaza a: {r['supersedes']}")
    if r["superseded_by"]:
        lines.append(f"Reemplazado por: {r['superseded_by']}")

    lines.append("\n--- Secciones Relevantes ---")
    for sec_name, sec_content in r["sections"].items():
        if any(k in sec_name.lower() for k in ["contexto", "problema", "decisión", "consecuencia"]):
            lines.append(f"\n[## {sec_name}]")
            lines.append(sec_content[:800] + ("\n... [truncado]" if len(sec_content) > 800 else ""))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta estructurada de precedentes arquitectónicos y decisiones pasadas (MADR / HISTORIAL)."
    )
    parser.add_argument("-q", "--query", help="Término o síntoma a buscar en el cuerpo y títulos de las decisiones.")
    parser.add_argument(
        "--status",
        choices=["accepted", "rejected", "superseded", "proposed", "all"],
        default="all",
        help="Filtrar por estado del ciclo de vida del ADR.",
    )
    parser.add_argument(
        "--domain",
        choices=list(DOMAIN_KEYWORDS.keys()) + ["all"],
        default="all",
        help="Filtrar por dominio técnico específico.",
    )
    parser.add_argument("--list", action="store_true", help="Listar todos los registros disponibles de forma concisa.")
    parser.add_argument("--detail", help="Mostrar la ficha completa del ADR especificado por su ID correlativo (ej. 0001).")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Formato de salida.")
    parser.add_argument("--dir", help="Directorio raíz opcional para buscar docs/adr/.")

    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = Path(args.dir).resolve() if args.dir else find_repo_root(script_path)
    adr_dir = repo_root / "docs" / "adr"
    legacy_historial = repo_root / "HISTORIAL.md"

    records = load_adrs(adr_dir)
    if legacy_historial.is_file():
        records.extend(load_legacy_historial(legacy_historial))

    if not records:
        print(f"Error: No se encontraron registros de decisiones en {adr_dir}", file=sys.stderr)
        return 1

    if args.detail:
        match = next((r for r in records if r["id"] == args.detail.zfill(4) or r["id"] == args.detail), None)
        if not match:
            print(f"Error: No se encontró el registro con ID '{args.detail}'.", file=sys.stderr)
            return 1
        if args.format == "json":
            print(json.dumps(match, indent=2, ensure_ascii=False))
        else:
            print(format_detail(match))
        return 0

    status_filter = None if args.status == "all" else args.status
    domain_filter = None if args.domain == "all" else args.domain
    results = filter_records(records, status=status_filter, domain=domain_filter, query=args.query)

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_table(results))
        if args.query:
            print(f"\nTotal coincidencias encontradas para '{args.query}': {len(results)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
