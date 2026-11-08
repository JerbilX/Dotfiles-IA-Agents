#!/usr/bin/env bash
# lib/check.sh - Auditoría estática, verificación de pureza, reglas core, README y tests

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
import os, re, sys

repo_root = sys.argv[1]
core_dir = os.path.join(repo_root, "core")
dist_dir = os.path.join(repo_root, "dist")

errors = []

# 1. Verificar neutralidad en core/00-router.md
core_router = os.path.join(core_dir, "00-router.md")
if os.path.isfile(core_router):
    with open(core_router, "r", encoding="utf-8") as f:
        core_text = f.read()
    forbidden_core_tools = [
        "view_file", "replace_file_content", "write_to_file",
        "grep_search", "find_by_name", "read_url_content"
    ]
    for tool in forbidden_core_tools:
        if re.search(r"\b" + re.escape(tool) + r"\b", core_text):
            errors.append(f"Herramienta de runtime \"{tool}\" encontrada en core/00-router.md (el core debe usar vocabulario neutral, ADR-0050)")

# 2. Verificar prompts compilados en dist/
placeholder_pattern = re.compile(r"\{\{([a-zA-Z0-9_.-]+)\}\}")
# Mantener sincronizado con tests/test_tool_vocabulary_neutrality.py
foreign_tools_by_runtime = {
    "claude": [
        "view_file", "replace_file_content", "grep_search", "find_by_name",
        "write_to_file", "run_command", "read_url_content", "ask_question"
    ],
    "antigravity": [
        "`Read`", "`Grep`", "`Glob`", "`Write`", "`Edit`", "`Bash`"
    ]
}

for r_name in sorted(foreign_tools_by_runtime):
    prompt_file = os.path.join(dist_dir, r_name, "AGENTS.md")
    if not os.path.isfile(prompt_file):
        print(f"WARN:Prompt compilado ausente: dist/{r_name}/AGENTS.md (ejecutar ./build.sh build); verificación de herramientas omitida")
        continue
    with open(prompt_file, "r", encoding="utf-8") as f:
        content = f.read()

    for p in placeholder_pattern.findall(content):
        errors.append(f"Placeholder sin resolver \"{{{{{p}}}}}\" detectado en dist/{r_name}/AGENTS.md")

    for tool in foreign_tools_by_runtime[r_name]:
        if tool.startswith("`"):
            found = tool in content
        else:
            found = re.search(r"\b" + re.escape(tool) + r"\b", content) is not None
        if found:
            errors.append(f"Herramienta cruzada {tool} detectada en dist/{r_name}/AGENTS.md (propia de otro runtime)")

# 3. Verificar prosa normativa en skills/ (ADR-0050, Issue #292)
skills_dir = os.path.join(repo_root, "skills")
forbidden_skills_tools = [
    "view_file", "replace_file_content", "grep_search", "find_by_name",
    "write_to_file", "read_url_content", "ask_question", "list_dir", "run_command"
]
claude_specific_tokens = ["`Read`", "`Grep`", "`Glob`", "`Write`", "`Edit`", "`Bash`"]
forbidden_params = ["StartLine", "EndLine"]
# Mecanismos de subagentes de Antigravity: admitidos solo condicionados en la misma línea
# (fuera de bloques de código, que ilustran la invocación bajo un encabezado condicionado).
conditioned_subagent_tokens = ["invoke_subagent", "manage_subagents", "TypeName"]
# Archivos cuyos nombres de herramientas son datos (trazas reales), no instrucciones.
excluded_skills_files = set()

if os.path.isdir(skills_dir):
    for root, dirs, files in os.walk(skills_dir):
        dirs[:] = [d for d in dirs if d not in ("bin", "scripts", "tests", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, repo_root)
            if rel_path in excluded_skills_files:
                continue
            with open(file_path, "r", encoding="utf-8") as fp:
                content = fp.read()
            for tool in forbidden_skills_tools:
                if re.search(r"\b" + re.escape(tool) + r"\b", content):
                    errors.append(f"Herramienta de runtime \"{tool}\" encontrada en prosa normativa de {rel_path} (debe usar vocabulario neutral, ADR-0050)")
            for token in claude_specific_tokens:
                if token in content:
                    errors.append(f"Token de herramienta de Claude \"{token}\" encontrado en prosa normativa de {rel_path} (debe usar vocabulario neutral, ADR-0050)")
            for param in forbidden_params:
                if re.search(r"\b" + re.escape(param) + r"\b", content):
                    errors.append(f"Parámetro de runtime \"{param}\" encontrado en prosa normativa de {rel_path} (debe usar vocabulario neutral, ADR-0050)")
            in_fence = False
            for idx, line in enumerate(content.splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                conditioned = "Antigravity" in line or "antigravity" in line
                if re.search(r"\bBypassSandbox\b", line) and not conditioned:
                    errors.append(f"Mención incondicional de \"BypassSandbox\" en {rel_path}:{idx} (debe condicionarse al runtime puntual, Issue #292)")
                if in_fence or conditioned:
                    continue
                for token in conditioned_subagent_tokens:
                    if re.search(r"\b" + re.escape(token) + r"\b", line):
                        errors.append(f"Mención incondicional de \"{token}\" en {rel_path}:{idx} (debe condicionarse al runtime puntual, Issue #292)")

for err in errors:
    print(f"ERROR:{err}")
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

check_runtime() {
    local r="$1"
    local config_file
    config_file="$(get_runtime_config_file "$r")"
    local rules_dir
    rules_dir="$(get_runtime_rules_dir "$r")"
    local mcp_dir
    mcp_dir="$(get_runtime_mcp_dir "$r")"
    local dist_file
    dist_file="$(get_runtime_dist_prompt_file "$r")"
    local target_file
    target_file="$(get_runtime_target_prompt_file "$r")"
    local target_mcp_file
    target_mcp_file="$(get_runtime_target_mcp_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"
    local skills_dir
    skills_dir="$(get_runtime_target_skills_dir "$r")"

    echo "--- Auditoría de Runtime: '${r}' ---"

    # 1. Validación de esquema y sintaxis de configuración
    if ! validate_config "${config_file}" "${SCHEMA_FILE}" "check"; then
        echo "  [✗] [${r}] Fallo en la validación de ${config_file}" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
    else
        echo "  [✓] [${r}] Esquema y sintaxis válidos: ${config_file}"
    fi

    # 2. Verificación de existencia de skills en disco
    local enabled_skills=()
    mapfile -t enabled_skills < <(get_enabled_skills "${config_file}")

    local skills_ok=true
    local count_skills=0
    for skill_name in "${enabled_skills[@]}"; do
        [ -z "${skill_name}" ] && continue
        count_skills=$((count_skills + 1))
        local skill_dir
        skill_dir="$(resolve_skill_dir "${skill_name}")"
        if [ ! -d "${skill_dir}" ]; then
            echo "  [✗] [${r}] Skill habilitado '${skill_name}' no existe en ${SKILLS_DIR}" >&2
            skills_ok=false
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            if [ ! -f "${skill_dir}/SKILL.md" ]; then
                echo "  [!] Advertencia [${r}]: Skill '${skill_name}' no contiene SKILL.md" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            fi
        fi
    done
    if [ "${skills_ok}" = true ]; then
        echo "  [✓] [${r}] Skills en disco: ${count_skills} habilitados y verificados"
    fi

    # 3. Verificación de binarios de skills
    local count_scripts=0
    local bin_scripts_ok=true
    for skill_name in "${enabled_skills[@]}"; do
        [ -z "${skill_name}" ] && continue
        local skill_dir
        skill_dir="$(resolve_skill_dir "${skill_name}")"
        local skill_bin_dir="${skill_dir}/bin"
        if [ -d "${skill_bin_dir}" ]; then
            for b in "${skill_bin_dir}"/*; do
                [ ! -e "${b}" ] && continue
                count_scripts=$((count_scripts + 1))
                if [ ! -x "${b}" ]; then
                    echo "  [✗] [${r}] Binario de skill '${b}' no tiene permisos de ejecución (+x)" >&2
                    bin_scripts_ok=false
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                fi
            done
        fi
        local skill_scripts_dir="${skill_dir}/scripts"
        if [ -d "${skill_scripts_dir}" ]; then
            for script in "${skill_scripts_dir}"/*.sh; do
                [ ! -e "${script}" ] && continue
                count_scripts=$((count_scripts + 1))
                if [ ! -x "${script}" ]; then
                    echo "  [✗] [${r}] Script de skill '${script}' no tiene permisos de ejecución (+x)" >&2
                    bin_scripts_ok=false
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                fi
            done
        fi
    done

    local declared_binaries=()
    mapfile -t declared_binaries < <(get_declared_binaries "${config_file}")
    for bin_entry in "${declared_binaries[@]}"; do
        [ -z "${bin_entry}" ] && continue
        local src_name="${bin_entry%%=*}"
        local found=false
        local target_script=""

        for skill_name in "${enabled_skills[@]}"; do
            [ -z "${skill_name}" ] && continue
            local skill_dir
            skill_dir="$(resolve_skill_dir "${skill_name}")"
            local script_path="${skill_dir}/scripts/${src_name}.sh"
            local bin_path="${skill_dir}/bin/${src_name}"
            if [ -f "${script_path}" ]; then
                found=true
                target_script="${script_path}"
                break
            elif [ -f "${bin_path}" ]; then
                found=true
                target_script="${bin_path}"
                break
            fi
        done

        if [ "${found}" = false ]; then
            echo "  [✗] [${r}] Binario declarado '${src_name}' en config.json no existe físicamente en las rutas de origen de skills habilitados" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        elif [ ! -x "${target_script}" ]; then
            echo "  [✗] [${r}] Binario declarado '${src_name}' en '${target_script}' no tiene permisos de ejecución (+x)" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    done

    if [ "${bin_scripts_ok}" = true ]; then
        echo "  [✓] [${r}] Binarios de skills: ${count_scripts} script(s)/binario(s) verificado(s)"
    fi

    # Verificación de presencia de binarios en ~/.local/bin
    for skill_name in "${enabled_skills[@]}"; do
        [ -z "${skill_name}" ] && continue
        local skill_dir
        skill_dir="$(resolve_skill_dir "${skill_name}")"
        local candidate_bins=()
        if [ -d "${skill_dir}/bin" ]; then
            for b in "${skill_dir}/bin/"*; do
                [ -f "${b}" ] && [ -x "${b}" ] && candidate_bins+=("${b}")
            done
        fi
        if [ -d "${skill_dir}/scripts" ]; then
            for script in "${skill_dir}/scripts/"*.sh; do
                [ -f "${script}" ] && [ -x "${script}" ] && candidate_bins+=("${script}")
            done
        fi

        for script in "${candidate_bins[@]}"; do
            [ -z "${script}" ] && continue
            local bin_name
            bin_name=$(basename "${script}")
            [[ "${bin_name}" == *.sh ]] && bin_name="${bin_name%.sh}"
            local bin_alias
            bin_alias="$(get_binary_alias "${config_file}" "${bin_name}")"
            if [ -n "${bin_alias}" ]; then
                bin_name="${bin_alias}"
            fi

            local target_bin="${HOME}/.local/bin/${bin_name}"
            if [ -L "${target_bin}" ]; then
                if [ ! -e "${target_bin}" ]; then
                    echo "  [✗] [${r}] Symlink roto en ~/.local/bin/${bin_name} -> $(readlink "${target_bin}" || true)" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                elif [ ! -x "${target_bin}" ]; then
                    echo "  [✗] [${r}] Binario en ~/.local/bin/${bin_name} no tiene permisos de ejecución (+x)" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                fi
            elif [ ! -e "${target_bin}" ]; then
                echo "  [!] Advertencia [${r}]: Binario de skill '${bin_name}' no está enlazado en ~/.local/bin/${bin_name} (ejecuta './build.sh skills ${r}')" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            elif [ ! -x "${target_bin}" ]; then
                echo "  [✗] [${r}] Binario en ~/.local/bin/${bin_name} no tiene permisos de ejecución (+x)" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            fi
        done
    done

    # 4. Verificación de servidores MCP
    local enabled_mcps=()
    mapfile -t enabled_mcps < <(get_enabled_mcp_servers "${config_file}")
    local count_mcps=0
    local mcps_ok=true

    for s_name in "${enabled_mcps[@]}"; do
        [ -z "${s_name}" ] && continue
        count_mcps=$((count_mcps + 1))
        local s_path="${mcp_dir}/${s_name}.json"
        if [ ! -f "${s_path}" ]; then
            echo "  [✗] [${r}] Servidor MCP habilitado '${s_name}' no existe en ${mcp_dir}" >&2
            mcps_ok=false
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            if ! validate_mcp_server "${s_path}" "${MCP_SCHEMA_FILE}" "check"; then
                echo "  [✗] [${r}] Esquema o sintaxis inválida en módulo MCP '${s_name}'" >&2
                mcps_ok=false
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            else
                local cmd=""
                cmd="$(json_get "${s_path}" ".command // empty")"

                if [ -n "${cmd}" ]; then
                    local expanded_cmd
                    expanded_cmd="$(eval echo "${cmd}")"
                    if [[ "${expanded_cmd}" == *"/"* ]]; then
                        if [ ! -e "${expanded_cmd}" ]; then
                            echo "  [!] Advertencia [${r}]: Ejecutable MCP '${expanded_cmd}' del servidor '${s_name}' no existe en disco" >&2
                            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
                        elif [ ! -x "${expanded_cmd}" ]; then
                            echo "  [✗] [${r}] Ejecutable MCP '${expanded_cmd}' del servidor '${s_name}' no tiene permisos de ejecución (+x)" >&2
                            mcps_ok=false
                            CHECK_ERRORS=$((CHECK_ERRORS + 1))
                        fi
                    else
                        if ! command -v "${cmd}" >/dev/null 2>&1; then
                            echo "  [!] Advertencia [${r}]: Comando MCP '${cmd}' del servidor '${s_name}' no encontrado en \$PATH" >&2
                            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
                        fi
                    fi
                fi
            fi
        fi
    done

    if [ "${mcps_ok}" = true ]; then
        echo "  [✓] [${r}] Servidores MCP: ${count_mcps} módulo(s) verificado(s)"
    fi

    # 4b. Verificación de Lifecycle Hooks
    local hooks_source
    hooks_source="$(get_runtime_hooks_source_file "$r")"
    if [ -f "${hooks_source}" ]; then
        if python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "${hooks_source}" >/dev/null 2>&1; then
            echo "  [✓] [${r}] Lifecycle Hooks: hooks.json sintácticamente válido"
        else
            echo "  [✗] [${r}] Error de sintaxis JSON en ${hooks_source}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    fi

    # 4c. Hooks declarados en settings.json (combinados por merge_settings.py en link, ADR-0051)
    local settings_source="${RUNTIMES_BASE_DIR}/${r}/settings.json"
    if [ -f "${settings_source}" ]; then
        local settings_hooks_report
        if settings_hooks_report="$(python3 -I -c '
import json, os, sys
root, path = sys.argv[1], sys.argv[2]
hooks = json.load(open(path, encoding="utf-8")).get("hooks", {})
errors, count = [], 0
if not isinstance(hooks, dict):
    errors.append("la clave hooks debe ser un objeto")
    hooks = {}
for event, entries in hooks.items():
    for entry in entries if isinstance(entries, list) else [None]:
        if not isinstance(entry, dict) or not entry.get("matcher") or not isinstance(entry.get("hooks"), list):
            errors.append(f"{event}: entrada sin matcher o sin lista hooks")
            continue
        where = event + "/" + entry["matcher"]
        for h in entry["hooks"]:
            cmd = str(h.get("command", "")).replace("${DOTFILES_ROOT}", root)
            exe = cmd.split()[0] if cmd.split() else ""
            if h.get("type") != "command" or not exe:
                errors.append(f"{where}: hook sin type=command o sin command")
            elif os.sep in exe and not os.access(exe, os.X_OK):
                errors.append(f"{where}: comando no ejecutable {exe}")
            else:
                count += 1
print("\n".join(errors) if errors else count)
sys.exit(1 if errors else 0)
' "${SCRIPT_DIR}" "${settings_source}" 2>&1)"; then
            if [ "${settings_hooks_report}" != "0" ]; then
                echo "  [✓] [${r}] Hooks en settings.json: ${settings_hooks_report} hook(s) con comando resoluble"
            fi
        else
            echo "  [✗] [${r}] Hooks inválidos en ${settings_source}:" >&2
            echo "${settings_hooks_report}" | sed 's/^/      /' >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    fi

    # 5. Verificación de directivas excluidas y sobreescritas (disabled_core_rules y overrides)
    local disabled_rules=()
    mapfile -t disabled_rules < <(get_disabled_core_rules "${config_file}")
    for d_rule in "${disabled_rules[@]}"; do
        [ -z "${d_rule}" ] && continue
        local target_f="${CORE_DIR}/${d_rule}"
        [[ "${target_f}" != *".md" ]] && target_f="${target_f}.md"
        if [ ! -f "${target_f}" ]; then
            echo "  [✗] [${r}] Regla en disabled_core_rules '${d_rule}' no existe en ${CORE_DIR}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    done

    local declared_overrides=()
    mapfile -t declared_overrides < <(get_core_overrides "${config_file}")
    for ovr in "${declared_overrides[@]}"; do
        [ -z "${ovr}" ] && continue
        local src="${ovr%%=*}"
        local dst="${ovr#*=}"
        local src_f="${CORE_DIR}/${src}"
        [[ "${src_f}" != *".md" ]] && src_f="${src_f}.md"
        local dst_f="${rules_dir}/${dst}"
        [[ "${dst_f}" != *".md" ]] && dst_f="${dst_f}.md"

        if [ ! -f "${src_f}" ]; then
            echo "  [✗] [${r}] Origen de override '${src}' en config.json no existe en ${CORE_DIR}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
        if [ ! -f "${dst_f}" ]; then
            echo "  [✗] [${r}] Destino de override '${dst}' en config.json no existe en ${rules_dir}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    done

    # 6. Colisiones de reglas y títulos H1
    local collision_error=false
    if [ -d "${rules_dir}" ]; then
        local seen_rules_prefixes=()
        for f in "${rules_dir}"/*.md; do
            [ -e "$f" ] || continue
            local fname
            fname="$(basename "$f")"
            if [[ "${fname}" =~ ^([0-9]+)- ]]; then
                local pfx="${BASH_REMATCH[1]}"
                if printf '%s\n' "${seen_rules_prefixes[@]}" | grep -qx "${pfx}"; then
                    echo "  [✗] [${r}] Colisión de prefijo '${pfx}-' detectada en rules/: ${fname}" >&2
                    collision_error=true
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                else
                    seen_rules_prefixes+=("${pfx}")
                fi
            else
                echo "  [!] Advertencia [${r}]: Archivo ${fname} en rules/ no sigue el patrón numérico 'NN-*.md'" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            fi

            # Verificación de presupuesto modular (ADR-0013)
            local w
            w="$(wc -w < "$f" | tr -d ' ')"
            if [ "${w}" -gt "${MAX_MODULE_WORDS}" ]; then
                echo "  [!] Advertencia [${r}]: rules/${fname} supera el umbral modular (${w} > ${MAX_MODULE_WORDS} palabras). Evaluar extracción a skill (ADR-0013)" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
            fi

            # Verificación de integridad de enlaces relativos en Markdown (ADR-0038)
            if command -v python3 >/dev/null 2>&1; then
                local broken_rules_list
                broken_rules_list="$(python3 -c '
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
                if [ -n "${broken_rules_list}" ]; then
                    while IFS= read -r broken_target; do
                        [ -z "${broken_target}" ] && continue
                        echo "  [✗] [${r}] Enlace roto en rules/${fname}: ${broken_target}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    done <<< "${broken_rules_list}"
                fi
            fi
        done
    fi

    local suppressed_rules_check=()
    for d in "${disabled_rules[@]}"; do
        [ -n "$d" ] && suppressed_rules_check+=("$d")
    done
    for ovr in "${declared_overrides[@]}"; do
        [ -n "$ovr" ] && suppressed_rules_check+=("${ovr%%=*}")
    done

    local seen_h1=()
    local all_files=()
    for f in "${CORE_DIR}"/*.md; do
        [ -e "$f" ] || continue
        local fname
        fname="$(basename "$f")"
        if [ ${#suppressed_rules_check[@]} -gt 0 ] && is_rule_suppressed "${fname}" "${suppressed_rules_check[@]}"; then
            continue
        fi
        all_files+=("$f")
    done
    if [ -d "${rules_dir}" ]; then
        for f in "${rules_dir}"/*.md; do
            [ -e "$f" ] || continue
            all_files+=("$f")
        done
    fi

    for f in "${all_files[@]}"; do
        while IFS= read -r line; do
            local title="${line#\# }"
            if printf '%s\n' "${seen_h1[@]}" | grep -Fxq "${title}"; then
                echo "  [✗] [${r}] Título H1 duplicado detectado: '# ${title}' en $(basename "$f")" >&2
                collision_error=true
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            else
                seen_h1+=("${title}")
            fi
        done < <(grep "^# " "$f" || true)
    done

    if [ "${collision_error}" = false ]; then
        echo "  [✓] [${r}] Ausencia de colisiones de prefijos y títulos H1 únicos"
    fi

    # 7. Integridad de enlaces simbólicos en host
    if [ -L "${target_file}" ]; then
        if [ ! -e "${target_file}" ]; then
            echo "  [✗] [${r}] Symlink roto en directivas: ${target_file} -> $(readlink "${target_file}" || true)" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    elif [ ! -e "${target_file}" ]; then
        echo "  [!] Advertencia [${r}]: ${target_file} no existe aún (ejecuta './build.sh link ${r}')" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi

    if [ -n "${skills_dir}" ] && [ -d "${skills_dir}" ]; then
        for item in "${skills_dir}"/*; do
            [ ! -e "${item}" ] && [ ! -L "${item}" ] && continue
            if [ -L "${item}" ]; then
                if [ ! -e "${item}" ]; then
                    echo "  [✗] [${r}] Symlink roto en skills: ${item} -> $(readlink "${item}" || true)" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                fi
            fi
        done
    fi

    if [ -L "${target_mcp_file}" ]; then
        if [ ! -e "${target_mcp_file}" ]; then
            echo "  [✗] [${r}] Symlink roto en MCP: ${target_mcp_file} -> $(readlink "${target_mcp_file}" || true)" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi
    elif [ ! -e "${target_mcp_file}" ]; then
        if [ "${count_mcps}" -gt 0 ]; then
            echo "  [!] Advertencia [${r}]: ${target_mcp_file} no existe aún (ejecuta './build.sh link ${r}')" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        fi
    fi

    local dist_hooks_file
    dist_hooks_file="$(get_runtime_dist_hooks_file "$r")"
    local target_hooks_file
    target_hooks_file="$(get_runtime_target_hooks_file "$r")"
    if [ -f "${dist_hooks_file}" ]; then
        if [ -L "${target_hooks_file}" ]; then
            if [ ! -e "${target_hooks_file}" ]; then
                echo "  [✗] [${r}] Symlink roto en Hooks: ${target_hooks_file} -> $(readlink "${target_hooks_file}" || true)" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            fi
        elif [ ! -e "${target_hooks_file}" ]; then
            echo "  [!] Advertencia [${r}]: ${target_hooks_file} no existe aún (ejecuta './build.sh link ${r}')" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        fi
    fi

    # 8. Presupuesto de contexto
    if [ -f "${dist_file}" ]; then
        local w
        w="$(wc -w < "${dist_file}" | tr -d ' ')"
        local max_w="${MAX_CONTEXT_WORDS}"
        local target_w="${TARGET_CONTEXT_WORDS}"
        local pct=$(( w * 100 / max_w ))
        if [ "${w}" -gt "${max_w}" ]; then
            echo "  [✗] Error [${r}]: Presupuesto de contexto (techo) superado: ${w} / ${max_w} palabras (${pct}%)" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        elif [ "${w}" -gt "${target_w}" ]; then
            echo "  [!] Advertencia [${r}]: Presupuesto de contexto supera banda objetivo: ${w} / ${max_w} palabras (${pct}%, objetivo: <= ${target_w})" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        else
            echo "  [✓] [${r}] Presupuesto de contexto: ${w} / ${max_w} palabras (${pct}%)"
        fi
    else
        echo "  [!] Advertencia [${r}]: ${dist_file} no ha sido compilado aún (ejecuta './build.sh build ${r}')" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi

    # 9. Verificación de archivos de respaldo (rollback)
    local prompt_baks=()
    local mcp_baks=()
    if [ -d "${target_dir}" ]; then
        local p_base m_base
        p_base="$(basename "${target_file}")"
        m_base="$(basename "${target_mcp_file}")"
        mapfile -t prompt_baks < <(find "${target_dir}" -maxdepth 1 -name "${p_base}.bak.*" 2>/dev/null | sort -r || true)
        mapfile -t mcp_baks < <(find "${target_dir}" -maxdepth 1 -name "${m_base}.bak.*" 2>/dev/null | sort -r || true)
    fi
    local count_prompt_baks=0
    for b in "${prompt_baks[@]}"; do [ -n "$b" ] && [ -e "$b" ] && count_prompt_baks=$((count_prompt_baks + 1)); done
    local count_mcp_baks=0
    for b in "${mcp_baks[@]}"; do [ -n "$b" ] && [ -e "$b" ] && count_mcp_baks=$((count_mcp_baks + 1)); done
    local total_baks=$(( count_prompt_baks + count_mcp_baks ))

    if [ "${total_baks}" -gt 0 ]; then
        echo "  [✓] [${r}] Respaldos para rollback: ${total_baks} archivo(s) .bak detectado(s) (${count_prompt_baks} directivas, ${count_mcp_baks} MCP)"
    else
        echo "  [!] Advertencia [${r}]: No existen archivos de respaldo en ${target_dir} (rollback no disponible hasta el próximo link)" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi
}

check_local_bin_symlinks() {
    local local_bin="${HOME}/.local/bin"
    if [[ ":${PATH}:" != *":${local_bin}:"* ]]; then
        echo "  [!] Advertencia: '${local_bin}' no está presente en \$PATH (agrega 'export PATH=\"\${HOME}/.local/bin:\${PATH}\"' a tu shell)" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi

    if [ -d "${local_bin}" ]; then
        for item in "${local_bin}"/*; do
            [ ! -e "${item}" ] && [ ! -L "${item}" ] && continue
            if [ -L "${item}" ]; then
                local link_target
                link_target="$(readlink "${item}" || true)"
                if [[ "${link_target}" == "${SCRIPT_DIR}"* ]]; then
                    if [ ! -e "${item}" ]; then
                        echo "  [✗] Symlink roto en ~/.local/bin: ${item} -> ${link_target}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    elif [ ! -x "${item}" ]; then
                        echo "  [✗] Symlink en ~/.local/bin no tiene permisos de ejecución (+x): ${item} -> ${link_target}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    fi
                fi
            fi
        done
    fi
}

check_documentation() {
    local readme_file="${SCRIPT_DIR}/README.md"

    # 1. Presencia de README.md
    if [ ! -f "${readme_file}" ]; then
        echo "  [✗] Error: README.md no existe en la raíz del repositorio" >&2
        CHECK_ERRORS=$((CHECK_ERRORS + 1))
        return 0
    fi

    # 2. Presupuesto de palabras en README.md
    local words=0
    words="$(wc -w < "${readme_file}" | tr -d ' ')"
    if [ "${words}" -gt "${MAX_README_WORDS}" ]; then
        echo "  [!] Advertencia: README.md supera el umbral recomendado (${words} > ${MAX_README_WORDS} palabras). Modularizar hacia docs/" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    else
        echo "  [✓] Documentación: README.md cumple presupuesto de palabras (${words}/${MAX_README_WORDS} palabras)"
    fi

    # 3. Integridad de enlaces locales relativos en Markdown hacia docs/
    local broken_links=0
    if command -v python3 >/dev/null 2>&1; then
        local broken_list
        broken_list="$(python3 -c '
import re, os, sys

readme = sys.argv[1]
repo_root = sys.argv[2]

with open(readme, "r", encoding="utf-8") as f:
    content = f.read()

# Pattern for Markdown links: [text](docs/...)
links = re.findall(r"\[.*?\]\((docs/[^\s\)\#\?]+)(?:[#\?][^\s\)]*)?\)", content)
broken = []
for link in links:
    target_path = os.path.join(repo_root, link)
    if not os.path.exists(target_path):
        broken.append(link)

for b in broken:
    print(b)
' "${readme_file}" "${SCRIPT_DIR}")"

        if [ -n "${broken_list}" ]; then
            while IFS= read -r broken_target; do
                [ -z "${broken_target}" ] && continue
                echo "  [✗] Enlace roto detectado en README.md: ${broken_target}" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
                broken_links=$((broken_links + 1))
            done <<< "${broken_list}"
        fi
    elif command -v grep >/dev/null 2>&1; then
        local raw_links=()
        mapfile -t raw_links < <(grep -oE '\[[^]]*\]\(docs/[^)#?]+' "${readme_file}" | sed -E 's/.*\(//' || true)
        for link in "${raw_links[@]}"; do
            [ -z "${link}" ] && continue
            if [ ! -e "${SCRIPT_DIR}/${link}" ]; then
                echo "  [✗] Enlace roto detectado en README.md: ${link}" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
                broken_links=$((broken_links + 1))
            fi
        done
    fi

    if [ "${broken_links}" -eq 0 ]; then
        echo "  [✓] Documentación: Enlaces relativos a docs/ en README.md verificados"
    fi
}

check_unit_tests() {
    local tests_dir="${SCRIPT_DIR}/tests"
    if [ ! -d "${tests_dir}" ]; then
        return 0
    fi

    echo "==> [check] Ejecutando suite de pruebas unitarias (tests/)..."
    if command -v python3 >/dev/null 2>&1; then
        local test_output
        if ! test_output=$(python3 -m unittest discover -s "${tests_dir}" -p "test_*.py" 2>&1); then
            echo "  [✗] Fallo en la suite de pruebas unitarias:" >&2
            echo "${test_output}" | sed 's/^/      /' >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            local count
            count=$(echo "${test_output}" | grep -oE "Ran [0-9]+ tests" | awk '{print $2}' || echo "N/A")
            echo "  [✓] Pruebas unitarias: ${count} prueba(s) ejecutada(s) con éxito"
        fi
    else
        echo "  [!] Advertencia: python3 no está instalado; omitiendo pruebas unitarias" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi
}

check_gh_aliases() {
    if ! command -v gh >/dev/null 2>&1; then
        echo "  [-] gh no está instalado; omitiendo verificación de aliases"
        return 0
    fi

    local aliases_list
    aliases_list="$(gh alias list 2>/dev/null || true)"
    local missing=()

    if ! echo "${aliases_list}" | grep -qE '^board:'; then
        missing+=("board")
    fi
    if ! echo "${aliases_list}" | grep -qE '^board-ready:'; then
        missing+=("board-ready")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo "  [!] Advertencia: Alias(es) de gh no configurados: ${missing[*]} (ejecuta './build.sh link' o 'gh alias set')" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    else
        echo "  [✓] GitHub CLI: Aliases de tablero ('board' y 'board-ready') configurados"
    fi
}

check_skill_bypass_quotes() {
    if [ ! -d "${SKILLS_DIR}" ]; then
        return 0
    fi

    echo "==> [check] Verificando ausencia de argumentos entrecomillados en comandos con bypass (skills/)..."
    if command -v python3 >/dev/null 2>&1; then
        local lint_output
        if ! lint_output=$(python3 -c '
import glob, os, re, sys

skills_dir = sys.argv[1]
patterns = [
    (re.compile(r"git\s+commit\s+-m\s+[\"\x27]"), "git commit -m con comillas"),
    (re.compile(r"git\s+stash\s+.*-m\s+[\"\x27]"), "git stash con mensaje entrecomillado"),
    (re.compile(r"gh\s+project\s+.*--owner\s+[\"\x27]"), "--owner entrecomillado"),
    (re.compile(r"gh\s+project\s+item-list\s+.*--query\s+[\"\x27]"), "gh project item-list --query entrecomillado"),
    (re.compile(r"gh\s+issue\s+close\s+.*--comment\s+[\"\x27]"), "gh issue close --comment entrecomillado"),
    (re.compile(r"gh-pr-review\s+reply\s+.*--body\s+[\"\x27]"), "gh-pr-review reply --body entrecomillado"),
]

errors = []
for fpath in sorted(glob.glob(os.path.join(skills_dir, "**/*.md"), recursive=True)):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    in_bash = False
    bash_lines = []
    bash_start = 0

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```bash"):
            in_bash = True
            bash_lines = []
            bash_start = idx
            continue
        elif stripped.startswith("```") and in_bash:
            in_bash = False
            has_bypass = False
            for lookahead in range(idx, min(len(lines), idx + 3)):
                if "BypassSandbox: true" in lines[lookahead]:
                    has_bypass = True
                    break
            if has_bypass:
                for b_idx, b_line in enumerate(bash_lines, bash_start + 1):
                    b_strip = b_line.strip()
                    if b_strip.startswith("#") or "fallback" in b_strip.lower():
                        continue
                    for pat, desc in patterns:
                        if pat.search(b_line):
                            rel_path = os.path.relpath(fpath)
                            errors.append(f"  [✗] {desc} en {rel_path}:{b_idx} -> {b_strip}")
            continue

        if in_bash:
            bash_lines.append(line)

if errors:
    print("\n".join(errors))
    sys.exit(1)
sys.exit(0)
' "${SKILLS_DIR}" 2>&1); then
            echo "${lint_output}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            echo "  [✓] Skills: Ausencia de argumentos entrecomillados en comandos con bypass"
        fi
    fi
}

check_domain_modules() {
    if [ ! -d "${MODULES_DIR}" ]; then
        return 0
    fi

    echo "==> [check] Verificando módulos de dominio y plantillas (modules/)..."
    local count_modules=0
    for mdir in "${MODULES_DIR}"/*; do
        [ ! -d "${mdir}" ] && continue
        local mname
        mname="$(basename "${mdir}")"
        local mconfig="${mdir}/module.json"
        if [ ! -f "${mconfig}" ]; then
            echo "  [✗] Módulo '${mname}' no contiene module.json" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
            continue
        fi

        count_modules=$((count_modules + 1))
        if ! validate_module_config "${mconfig}" "${MODULE_SCHEMA_FILE}"; then
            echo "  [✗] Validación de esquema fallida en ${mconfig}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi

        local template_dir="${mdir}/template"
        if [ -d "${template_dir}" ]; then
            local jf
            while IFS= read -r -d '' jf; do
                if command -v python3 >/dev/null 2>&1; then
                    if ! python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "${jf}" >/dev/null 2>&1; then
                        echo "  [✗] Error de sintaxis JSON en plantilla: ${jf}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    fi
                fi
            done < <(find "${template_dir}" -name "*.json" -print0 2>/dev/null | sort -z)
        fi
    done

    echo "  [✓] Módulos de dominio: ${count_modules} módulo(s) verificado(s)"
}

check_global_mcp_purity() {
    local antigravity_cfg="${RUNTIMES_BASE_DIR}/antigravity/config.json"
    if [ -f "${antigravity_cfg}" ]; then
        if command -v python3 >/dev/null 2>&1; then
            local domain_mcps
            domain_mcps="$(python3 -c '
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    cfg = json.load(f)
servers = cfg.get("mcp_servers", [])
leak = [s for s in servers if s in ["eso-mcp-server"]]
if leak:
    print(", ".join(leak))
' "${antigravity_cfg}")"
            if [ -n "${domain_mcps}" ]; then
                echo "  [✗] Servidor(es) MCP de dominio detectados en perfil global de antigravity: ${domain_mcps}" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            else
                echo "  [✓] Pureza de perfil global: antigravity no contiene servidores MCP de dominio"
            fi
        fi
    fi
}

check_global_skills_purity() {
    if [ ! -d "${MODULES_DIR}" ]; then
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        local leak
        leak="$(python3 -c '
import glob, json, os, sys
modules_dir, runtimes_dir = sys.argv[1], sys.argv[2]
domain_skills = set()
domain_bins = set()
for mf in glob.glob(os.path.join(modules_dir, "*", "module.json")):
    try:
        data = json.load(open(mf, "r", encoding="utf-8"))
        domain_skills.update(data.get("skills", []))
        domain_bins.update(data.get("binaries", {}).values())
    except Exception:
        pass

leaks = []
for cf in glob.glob(os.path.join(runtimes_dir, "*", "config.json")):
    rname = os.path.basename(os.path.dirname(cf))
    if rname == "schema":
        continue
    try:
        cfg = json.load(open(cf, "r", encoding="utf-8"))
        r_skills = set(cfg.get("skills", []))
        r_bins = set(cfg.get("binaries", {}).values())
        sk_leak = r_skills.intersection(domain_skills)
        bin_leak = r_bins.intersection(domain_bins)
        if sk_leak:
            leaks.append(f"[{rname}] skills de dominio: {list(sk_leak)}")
        if bin_leak:
            leaks.append(f"[{rname}] binarios de dominio: {list(bin_leak)}")
    except Exception:
        pass
if leaks:
    print("; ".join(leaks))
' "${MODULES_DIR}" "${RUNTIMES_BASE_DIR}")"
        if [ -n "${leak}" ]; then
            echo "  [✗] Skill(s) o binario(s) de dominio detectados en perfil global: ${leak}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            echo "  [✓] Pureza de perfil global: runtimes no contienen skills ni binarios de dominio"
        fi
    fi
}

cmd_workspace() {
    local module_name="${1:-}"
    local target_dir="${2:-.}"
    local runtime_filter="${3:-all}"

    if [ -z "${module_name}" ]; then
        echo "Uso: $0 workspace <nombre-modulo> [ruta-directorio-destino] [runtime]" >&2
        echo "Ejemplo: $0 workspace eso . all" >&2
        echo "Nota: Si se omite la ruta destino, se asume el directorio actual (.)." >&2
        return 1
    fi

    local agent_module_cli="${SCRIPT_DIR}/skills/issue-driven-workflow/bin/agent-module"
    if [ -x "${agent_module_cli}" ]; then
        python3 "${agent_module_cli}" enable "${module_name}" "${target_dir}" --runtime "${runtime_filter}"
        return $?
    else
        echo "Error: CLI de aprovisionamiento no encontrado en ${agent_module_cli}" >&2
        return 1
    fi
}

check_p0_guards() {
    echo "==> [check] Verificando guards P0 y blindaje mecánico..."
    local p0_errors=0

    # 1. Binario agent-guard
    local guard_bin="${SKILLS_DIR}/conversation-audit/bin/agent-guard"
    if [ ! -f "${guard_bin}" ]; then
        echo "  [✗] Binario agent-guard no encontrado en ${guard_bin}" >&2
        p0_errors=$((p0_errors + 1))
    elif [ ! -x "${guard_bin}" ]; then
        echo "  [✗] Binario agent-guard no tiene permisos de ejecución (${guard_bin})" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Binario agent-guard ejecutable y disponible"
    fi

    # 2. Git hooks locales (.githooks/)
    local pre_push="${SCRIPT_DIR}/.githooks/pre-push"
    local pre_commit="${SCRIPT_DIR}/.githooks/pre-commit"
    if [ ! -f "${pre_push}" ] || [ ! -x "${pre_push}" ]; then
        echo "  [✗] Git hook pre-push no encontrado o no ejecutable en ${pre_push}" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Git hook pre-push verificado"
    fi

    if [ ! -f "${pre_commit}" ] || [ ! -x "${pre_commit}" ]; then
        echo "  [✗] Git hook pre-commit no encontrado o no ejecutable en ${pre_commit}" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Git hook pre-commit verificado"
    fi

    # 3. Ausencia total de backlogs locales o archivos prohibidos
    local banned_found=0
    for bf in TODO.md todo.md TODO todo backlog.md backlog GEMINI.md historial.md HISTORIAL.md; do
        if [ -e "${SCRIPT_DIR}/${bf}" ]; then
            echo "  [✗] Archivo prohibido detectado en la raíz del repo: ${bf}" >&2
            p0_errors=$((p0_errors + 1))
            banned_found=$((banned_found + 1))
        fi
    done
    for bd in tasks prompts; do
        if [ -d "${SCRIPT_DIR}/${bd}" ]; then
            echo "  [✗] Directorio prohibido detectado en la raíz del repo: ${bd}/" >&2
            p0_errors=$((p0_errors + 1))
            banned_found=$((banned_found + 1))
        fi
    done
    if [ "${banned_found}" -eq 0 ]; then
        echo "  [✓] Guards P0: Ausencia de backlogs locales y archivos prohibidos verificada"
    fi

    if [ "${p0_errors}" -gt 0 ]; then
        CHECK_ERRORS=$((CHECK_ERRORS + p0_errors))
        return 1
    fi
    return 0
}

cmd_check() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    CHECK_ERRORS=0
    CHECK_WARNINGS=0

    echo "==> [check] Ejecutando verificaciones estáticas (read-only)..."

    # Verificaciones comunes de directivas core
    check_core_rules
    check_basal_rules_admission
    check_prompt_tool_crossings

    # Verificación de pureza de perfil global (MCP y Skills)
    check_global_mcp_purity
    check_global_skills_purity

    # Verificación de módulos de dominio y plantillas de workspace
    check_domain_modules

    # Verificación de documentación técnica (README y enlaces a docs/)
    check_documentation

    # Verificación de suite de pruebas unitarias
    check_unit_tests

    # Verificación de esquemas para runtimes registrados no incluidos en target_runtimes
    for r_avail in $(get_available_runtimes); do
        local is_in_target=false
        for tr in "${target_runtimes[@]}"; do
            if [ "$tr" = "$r_avail" ]; then
                is_in_target=true
                break
            fi
        done
        if [ "$is_in_target" = false ]; then
            local cfg_avail
            cfg_avail="$(get_runtime_config_file "${r_avail}")"
            if [ -f "${cfg_avail}" ]; then
                echo "--- Auditoría de Esquema (bajo demanda): '${r_avail}' ---"
                if ! validate_config "${cfg_avail}" "${SCHEMA_FILE}" "check"; then
                    echo "  [✗] [${r_avail}] Fallo en la validación de ${cfg_avail}" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                else
                    echo "  [✓] [${r_avail}] Esquema y sintaxis válidos: ${cfg_avail}"
                fi
            fi
        fi
    done

    # Verificaciones por runtime
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        check_runtime "$r"
    done

    # Verificaciones comunes de ~/.local/bin
    check_local_bin_symlinks

    # Verificación de aliases de GitHub CLI
    check_gh_aliases

    # Verificación de comandos con bypass en skills/
    check_skill_bypass_quotes

    # Verificación de guards P0 y blindaje mecánico
    check_p0_guards

    echo "==> [check] Verificación completada: ${CHECK_ERRORS} error(es), ${CHECK_WARNINGS} advertencia(s)."
    if [ "${CHECK_ERRORS}" -gt 0 ]; then
        return 1
    fi
    return 0
}
