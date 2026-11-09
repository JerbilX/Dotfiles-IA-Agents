#!/usr/bin/env bash
# lib/check_rules.sh - Verificación de directivas core, admisión basal y vocabulario de herramientas

check_core_rules() {
    echo "==> [check] Verificando enlaces relativos en directivas Core..."
    local broken_links=0
    for f in "${CORE_DIR}"/*.md; do
        [ ! -f "$f" ] && continue
        local fname
        fname="$(basename "$f")"

        if command -v python3 >/dev/null 2>&1; then
            local broken_list
            broken_list="$(python3 -c '
import re, os, sys
file_path, repo_root = sys.argv[1], sys.argv[2]
with open(file_path, "r", encoding="utf-8") as fp:
    content = fp.read()
links = re.findall(r"\[.*?\]\(([^)\s#?]+)(?:[#?][^\s)]*)?\)", content)
for l in links:
    if not l.startswith(("http://", "https://", "mailto:", "#")):
        target = os.path.join(repo_root, l)
        if not os.path.exists(target):
            print(l)
' "$f" "${SCRIPT_DIR}")"
            if [ -n "${broken_list}" ]; then
                while IFS= read -r broken_target; do
                    [ -z "${broken_target}" ] && continue
                    echo "  [✗] Enlace roto detectado en core/${fname}: ${broken_target}" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    broken_links=$((broken_links + 1))
                done <<< "${broken_list}"
            fi
        fi
    done

    if [ "${broken_links}" -eq 0 ]; then
        echo "  [✓] Directivas Core: Enlaces relativos verificados"
    fi

    # Verificación de autosuficiencia y ausencia de enlaces huérfanos a core/ (ADR-0047)
    # Cualquier mención a un módulo core/02+ eliminado (enlace, backticks o texto plano) en artefactos que viajan al runtime
    local orphan_core_refs=0
    local orphan_file
    while IFS= read -r orphan_file; do
        [ -z "${orphan_file}" ] && continue
        echo "  [✗] Referencia a módulo de core/ inexistente en runtime detectada en ${orphan_file#"${SCRIPT_DIR}"/}" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        orphan_core_refs=$((orphan_core_refs + 1))
    done < <(grep -rlE "core/(0[2-9]|[1-9][0-9])-""${CORE_DIR}" "${SCRIPT_DIR}/skills" "${SCRIPT_DIR}/runtimes" "${SCRIPT_DIR}/dist" --include='*.md' 2>/dev/null)
    if [ "${orphan_core_refs}" -eq 0 ]; then
        echo "  [✓] Autosuficiencia de Directivas Basales: Sin referencias huérfanas a core/"
    fi
}

check_basal_rules_admission() {
    echo "==> [check] Verificando control de admisión y metadatos de reglas basales..."
    local rules_errors=0
    local rules_audited=0
    local count_found=0

    if ! command -v python3 >/dev/null 2>&1; then
        echo "  [✗] python3 no está disponible para validar metadatos de reglas basales" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        return
    fi

    local audit_output
    local py_status=0
    audit_output="$(python3 -c '
import glob, os, re, sys

repo_root = sys.argv[1]
core_dir = os.path.join(repo_root, "core")
runtimes_dir = os.path.join(repo_root, "runtimes")

target_files = sorted(glob.glob(os.path.join(core_dir, "*.md")))
for rd in sorted(glob.glob(os.path.join(runtimes_dir, "*", "rules"))):
    target_files.extend(sorted(glob.glob(os.path.join(rd, "*.md"))))

seen_ids = set()
errors = []
warnings = []
total_rules = 0

rule_comment_pattern = re.compile(
    r"^<!--\s*rule:\s*id=([A-Za-z0-9_]+)\s+level=([A-Za-z0-9_/]+)\s+origin=(#[0-9]+|legacy)\s*-->$"
)
valid_levels = {"P0", "P1", "P2", "Build", "P0/P2", "P0/P1", "P1/P2"}
root_bullet_pattern = re.compile(r"^([-*]|\d+\.)\s+")

for file_path in target_files:
    rel_path = os.path.relpath(file_path, repo_root)
    with open(file_path, "r", encoding="utf-8") as fp:
        lines = fp.readlines()

    pending_meta = None
    i = 0
    n = len(lines)
    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        line_no = i + 1

        if not line:
            i += 1
            continue

        m_comment = rule_comment_pattern.match(line)
        if m_comment:
            if pending_meta is not None:
                p_id = pending_meta["id"]
                p_lno = pending_meta["line_no"]
                errors.append(f"Metadato huérfano <!-- rule: id={p_id} ... --> en {rel_path}:{p_lno} sin regla asociada")
            rule_id, rule_level, rule_origin = m_comment.groups()
            pending_meta = {
                "id": rule_id,
                "level": rule_level,
                "origin": rule_origin,
                "line_no": line_no
            }
            i += 1
            continue

        is_root_bullet = bool(root_bullet_pattern.match(line)) and not raw_line.startswith("  ") and not raw_line.startswith("\t")

        if is_root_bullet:
            total_rules += 1
            rule_name = line
            if pending_meta is None:
                errors.append(f"Regla en {rel_path}:{line_no} sin metadatos de admisión (falta comentario <!-- rule: id=... level=... origin=... -->): {rule_name[:60]}")
            else:
                rid = pending_meta["id"]
                rlevel = pending_meta["level"]
                rlno = pending_meta["line_no"]
                if rid in seen_ids:
                    errors.append(f"ID de regla duplicado \"{rid}\" en {rel_path}:{rlno}")
                seen_ids.add(rid)

                if rlevel not in valid_levels:
                    errors.append(f"Nivel inválido \"{rlevel}\" para regla \"{rid}\" en {rel_path}:{rlno} (debe ser P0, P1, P2, Build o combinaciones mixtas)")

                rule_lines = [line]
                j = i + 1
                saw_blank = False
                while j < n:
                    next_raw = lines[j]
                    next_line = next_raw.strip()
                    if not next_line:
                        saw_blank = True
                        j += 1
                        continue
                    if rule_comment_pattern.match(next_line):
                        break
                    if next_line.startswith("#"):
                        break
                    is_next_root = bool(root_bullet_pattern.match(next_line)) and not next_raw.startswith("  ") and not next_raw.startswith("\t")
                    if is_next_root:
                        break
                    if saw_blank and not next_raw.startswith(" ") and not next_raw.startswith("\t"):
                        break
                    rule_lines.append(next_line)
                    saw_blank = False
                    j += 1

                rule_lines_count = len(rule_lines)
                rule_words_count = len(" ".join(rule_lines).split())

                # Ref: docs/adr/0049-regimen-transitorio-de-admision-p0.md
                levels = set(rlevel.split("/"))
                if "P0" in levels:
                    if rule_lines_count > 1:
                        if levels == {"P0"}:
                            errors.append(f"Regla P0 \"{rid}\" en {rel_path}:{line_no} conserva más de una línea en el basal ({rule_lines_count} líneas)")
                        else:
                            warnings.append(f"Regla mixta \"{rid}\" ({rlevel}) en {rel_path}:{line_no} conserva {rule_lines_count} líneas en el basal: pendiente de evacuación de su componente P0 (ADR-0049)")
                    if rule_words_count > 100:
                        errors.append(f"Regla P0 \"{rid}\" en {rel_path}:{line_no} supera el techo transitorio de 100 palabras ({rule_words_count}/100 palabras, ADR-0049)")
                    elif rule_words_count > 30:
                        warnings.append(f"Regla P0 \"{rid}\" en {rel_path}:{line_no} supera límite recomendado de palabras residuales ({rule_words_count}/30 palabras, ADR-0048 §2.2)")

                pending_meta = None
            i += 1
            continue

        if pending_meta is not None:
            p_id = pending_meta["id"]
            p_lno = pending_meta["line_no"]
            if line.startswith("#"):
                errors.append(f"Metadato huérfano <!-- rule: id={p_id} ... --> en {rel_path}:{p_lno} antes de encabezado de sección")
            else:
                errors.append(f"Metadato huérfano <!-- rule: id={p_id} ... --> en {rel_path}:{p_lno} seguido de texto no-bullet")
            pending_meta = None

        i += 1

    if pending_meta is not None:
        p_id = pending_meta["id"]
        p_lno = pending_meta["line_no"]
        errors.append(f"Metadato huérfano <!-- rule: id={p_id} ... --> al final de {rel_path}:{p_lno}")

print(f"COUNT:{total_rules}")
for warn in warnings:
    print(f"WARNING:{warn}")
for err in errors:
    print(f"ERROR:{err}")
' "${SCRIPT_DIR}" 2>&1)" || py_status=$?

    if [ "${py_status}" -ne 0 ]; then
        echo "  [✗] Error ejecutando auditoría de reglas basales (exit code ${py_status}):" >&2
        echo "${audit_output}" | sed 's/^/      /' >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        return
    fi

    while IFS= read -r line; do
        if [[ "${line}" =~ ^COUNT:([0-9]+)$ ]]; then
            rules_audited="${BASH_REMATCH[1]}"
            count_found=1
        elif [[ "${line}" =~ ^WARNING:(.*)$ ]]; then
            echo "  [!] Advertencia: ${BASH_REMATCH[1]}"
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        elif [[ "${line}" =~ ^ERROR:(.*)$ ]]; then
            echo "  [✗] ${BASH_REMATCH[1]}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
            rules_errors=$((rules_errors + 1))
        fi
    done <<< "${audit_output}"

    if [ "${count_found}" -eq 0 ]; then
        echo "  [✗] La verificación de reglas basales no retornó conteo de reglas (COUNT:)" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        rules_errors=$((rules_errors + 1))
    fi

    if [ "${rules_errors}" -eq 0 ]; then
        echo "  [✓] Control de admisión basal: ${rules_audited} regla(s) verificada(s) con ID y nivel válidos"
    fi
}

check_prompt_tool_crossings() {
    echo "==> [check] Verificando ausencia de placeholders y nombres cruzados de herramientas..."
    local crossing_errors=0

    if ! command -v python3 >/dev/null 2>&1; then
        echo "  [✗] python3 no está disponible para verificar herramientas en prompts" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        return
    fi

    local check_output
    local py_status=0
    check_output="$(python3 -c '
import os, sys
repo_root = sys.argv[1]
lib_dir = os.path.join(repo_root, "lib")
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)
from tool_vocabulary import check_tool_vocabulary

errors, warnings = check_tool_vocabulary(repo_root)
for err in errors:
    print(f"ERROR:{err}")
for warn in warnings:
    print(f"WARN:{warn}")
' "${SCRIPT_DIR}" 2>&1)" || py_status=$?

    if [ "${py_status}" -ne 0 ]; then
        echo "  [✗] Error ejecutando verificación de vocabulario de herramientas (exit code ${py_status}):" >&2
        echo "${check_output}" | sed 's/^/      /' >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        return
    fi

    while IFS= read -r line; do
        if [[ "${line}" =~ ^ERROR:(.*)$ ]]; then
            echo "  [✗] ${BASH_REMATCH[1]}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
            crossing_errors=$((crossing_errors + 1))
        elif [[ "${line}" =~ ^WARN:(.*)$ ]]; then
            echo "  [!] Advertencia: ${BASH_REMATCH[1]}"
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            crossing_errors=$((crossing_errors + 1))
        fi
    done <<< "${check_output}"

    if [ "${crossing_errors}" -eq 0 ]; then
        echo "  [✓] Vocabulario de herramientas: Ausencia de placeholders y nombres cruzados verificada"
    fi
}
