#!/usr/bin/env bash
# lib/check_runtime.sh - Auditoría de runtimes, esquemas, skills, MCP, hooks, presupuestos y symlinks

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
        local hooks_report
        if hooks_report="$(python3 -I -c '
import json, os, sys
root, path = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path, encoding="utf-8"))
except Exception as e:
    print(f"Error de sintaxis JSON: {e}")
    sys.exit(1)

errors, count = [], 0
if not isinstance(data, dict):
    errors.append("hooks.json debe ser un objeto JSON")
    data = {}

for section, content in data.items():
    if not isinstance(content, dict):
        continue
    for event, entries in content.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            matcher = entry.get("matcher", "")
            where = f"{section}/{event}/{matcher}"
            hooks = entry.get("hooks", [])
            if not isinstance(hooks, list):
                errors.append(f"{where}: falta lista de hooks")
                continue
            for h in hooks:
                if not isinstance(h, dict):
                    continue
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
' "${SCRIPT_DIR}" "${hooks_source}" 2>&1)"; then
            echo "  [✓] [${r}] Lifecycle Hooks: hooks.json con ${hooks_report} hook(s) resolubles por ruta canónica"
        else
            echo "  [✗] [${r}] Lifecycle Hooks inválidos en ${hooks_source}:" >&2
            echo "${hooks_report}" | sed 's/^/      /' >&2
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
