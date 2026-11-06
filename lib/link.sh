#!/usr/bin/env bash
# lib/link.sh - Symlinks hacia host, aprovisionamiento de skills, aliases gh y rollback

link_runtime_mcp() {
    local r="$1"
    local dist_mcp_file
    dist_mcp_file="$(get_runtime_dist_mcp_file "$r")"
    local target_mcp_file
    target_mcp_file="$(get_runtime_target_mcp_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"

    echo "==> [link] Asegurando enlace simbólico para MCP [${r}] en ${target_dir}..."
    if [ ! -f "${dist_mcp_file}" ]; then
        echo "Error: ${dist_mcp_file} no existe. Ejecuta './build.sh build ${r}' primero." >&2
        return 1
    fi

    safe_symlink "${dist_mcp_file}" "${target_mcp_file}" "${r} MCP"
}

link_runtime() {
    local r="$1"
    local dist_file
    dist_file="$(get_runtime_dist_prompt_file "$r")"
    local target_file
    target_file="$(get_runtime_target_prompt_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"

    echo "==> [link] Asegurando directorio destino para '${r}': ${target_dir}..."
    if [ ! -f "${dist_file}" ]; then
        echo "Error: ${dist_file} no existe. Ejecuta './build.sh build ${r}' primero." >&2
        return 1
    fi

    safe_symlink "${dist_file}" "${target_file}" "${r}"

    # Retira el symlink heredado de directivas modulares core (ADR-0047: el prompt compilado es autosuficiente)
    local target_core_dir="${target_dir}/core"
    if [ -L "${target_core_dir}" ] && [ "$(readlink "${target_core_dir}")" = "${CORE_DIR}" ]; then
        echo "==> [link] [${r}] Retirando symlink heredado de directivas modulares: ${target_core_dir}..."
        rm -f "${target_core_dir}"
    fi

    link_runtime_mcp "${r}"
    link_runtime_hooks "${r}"
    merge_runtime_settings "${r}"
}

# Combina permisos del runtime en el settings del host sin pisar claves del usuario (ADR-0045)
merge_runtime_settings() {
    local r="$1"
    local src="${RUNTIMES_BASE_DIR}/${r}/settings.json"
    [ -f "${src}" ] || return 0
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"
    echo "==> [link] Combinando permisos de '${r}' en ${target_dir}/settings.json..."
    python3 -I "${SCRIPT_DIR}/lib/merge_settings.py" "${src}" "${target_dir}/settings.json"
}

# Activa hooks de git versionados que regeneran dist/ tras merge o checkout (ADR-0045)
setup_git_hooks() {
    if git -C "${SCRIPT_DIR}" rev-parse --git-dir >/dev/null 2>&1; then
        git -C "${SCRIPT_DIR}" config core.hooksPath .githooks
        echo "  [✓] Hooks de git activos (core.hooksPath=.githooks)."
    fi
}

link_runtime_hooks() {
    local r="$1"
    local dist_hooks_file
    dist_hooks_file="$(get_runtime_dist_hooks_file "$r")"
    local target_hooks_file
    target_hooks_file="$(get_runtime_target_hooks_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"

    if [ -f "${dist_hooks_file}" ]; then
        echo "==> [link] Asegurando enlace simbólico para Lifecycle Hooks [${r}] en ${target_dir}..."
        safe_symlink "${dist_hooks_file}" "${target_hooks_file}" "${r} Hooks"
    fi
}

setup_gh_aliases() {
    echo "==> [link] Asegurando configuración de aliases de GitHub CLI ('gh')..."
    if ! command -v gh >/dev/null 2>&1; then
        echo "  [-] gh no está instalado o no se encuentra en \$PATH; omitiendo aliases."
        return 0
    fi

    # Alias 'board': Lista ítems activos excluyendo 'Done'
    if gh alias set --shell board 'gh project item-list 1 --owner @me --limit 100 --query "repo:$1 -status:Done" --format json --jq ".items[] | {number: .content.number, title: .content.title, status: .status}"' --clobber >/dev/null 2>&1; then
        echo "  [✓] Alias 'gh board' configurado exitosamente."
    else
        echo "  [!] Advertencia: No se pudo configurar el alias 'gh board'." >&2
    fi

    # Alias 'board-ready': Lista ítems en '🎯 Ready for Dev'
    if gh alias set --shell board-ready 'gh project item-list 1 --owner @me --limit 100 --query "repo:$1 status:\"🎯 Ready for Dev\"" --format json --jq ".items[] | {number: .content.number, title: .content.title, url: .content.url}"' --clobber >/dev/null 2>&1; then
        echo "  [✓] Alias 'gh board-ready' configurado exitosamente."
    else
        echo "  [!] Advertencia: No se pudo configurar el alias 'gh board-ready'." >&2
    fi
}

cmd_link() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        link_runtime "$r"
        skills_runtime "$r"
    done
    setup_gh_aliases
    setup_git_hooks
}

rollback_runtime() {
    local r="$1"
    local target_file
    target_file="$(get_runtime_target_prompt_file "$r")"
    local target_mcp_file
    target_mcp_file="$(get_runtime_target_mcp_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"

    echo "==> [rollback] Inspeccionando respaldos para runtime '${r}' en ${target_dir}..."

    if [ ! -d "${target_dir}" ]; then
        echo "Error: [${r}] Directorio destino no existe: ${target_dir}" >&2
        return 1
    fi

    local p_base m_base
    p_base="$(basename "${target_file}")"
    m_base="$(basename "${target_mcp_file}")"

    local latest_prompt_bak=""
    local latest_mcp_bak=""

    local prompt_baks=()
    mapfile -t prompt_baks < <(find "${target_dir}" -maxdepth 1 -name "${p_base}.bak.*" 2>/dev/null | sort -r || true)
    for b in "${prompt_baks[@]}"; do
        if [ -n "$b" ] && [ -e "$b" ]; then
            latest_prompt_bak="$b"
            break
        fi
    done

    local mcp_baks=()
    mapfile -t mcp_baks < <(find "${target_dir}" -maxdepth 1 -name "${m_base}.bak.*" 2>/dev/null | sort -r || true)
    for b in "${mcp_baks[@]}"; do
        if [ -n "$b" ] && [ -e "$b" ]; then
            latest_mcp_bak="$b"
            break
        fi
    done

    if [ -z "${latest_prompt_bak}" ] && [ -z "${latest_mcp_bak}" ]; then
        echo "Error: [${r}] No se encontraron archivos de respaldo (.bak.*) en ${target_dir}" >&2
        return 1
    fi

    local restored_count=0

    if [ -n "${latest_prompt_bak}" ]; then
        echo "==> [rollback] [${r}] Restaurando directivas: ${target_file} <- ${latest_prompt_bak}..."
        mv -f "${latest_prompt_bak}" "${target_file}"
        restored_count=$((restored_count + 1))
    fi

    if [ -n "${latest_mcp_bak}" ]; then
        echo "==> [rollback] [${r}] Restaurando servidores MCP: ${target_mcp_file} <- ${latest_mcp_bak}..."
        mv -f "${latest_mcp_bak}" "${target_mcp_file}"
        restored_count=$((restored_count + 1))
    fi

    echo "==> [rollback] [${r}] Rollback completado exitosamente (${restored_count} elemento(s) restaurado(s))."
    return 0
}

cmd_rollback() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    local total_success=0
    local total_attempts=0
    local has_error=false

    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        total_attempts=$((total_attempts + 1))
        if rollback_runtime "$r"; then
            total_success=$((total_success + 1))
        else
            has_error=true
        fi
    done

    if [ "${total_attempts}" -eq 0 ] || [ "${total_success}" -eq 0 ]; then
        echo "Error: No se pudo realizar rollback en ningún runtime (sin archivos de respaldo previos)." >&2
        return 1
    fi

    if [ "${target_arg}" != "all" ] && [ "${has_error}" = true ]; then
        return 1
    fi
    return 0
}

status_runtime() {
    local r="$1"
    local target_file
    target_file="$(get_runtime_target_prompt_file "$r")"
    local target_mcp_file
    target_mcp_file="$(get_runtime_target_mcp_file "$r")"

    echo "==> [status] Runtime: '${r}'"
    echo "  Directivas (${target_file}):"
    if [ -L "${target_file}" ]; then
        local target
        target="$(readlink "${target_file}")"
        echo "    Tipo: Enlace simbólico (symlink) -> ${target}"
        if [ -e "${target_file}" ]; then
            echo "    Estado: Válido (activo)"
        else
            echo "    Estado: Roto (el archivo de origen no existe)"
        fi
    elif [ -f "${target_file}" ]; then
        echo "    Tipo: Archivo regular (no gestionado por symlink)"
        echo "    Estado: Advertencia (ejecuta './build.sh link' para estandarizar)"
    else
        echo "    Tipo: Inexistente"
        echo "    Estado: No provisionado"
    fi

    echo "  Configuración MCP (${target_mcp_file}):"
    if [ -L "${target_mcp_file}" ]; then
        local target
        target="$(readlink "${target_mcp_file}")"
        echo "    Tipo: Enlace simbólico (symlink) -> ${target}"
        if [ -e "${target_mcp_file}" ]; then
            echo "    Estado: Válido (activo)"
        else
            echo "    Estado: Roto (el archivo de origen no existe)"
        fi
    elif [ -f "${target_mcp_file}" ]; then
        echo "    Tipo: Archivo regular (no gestionado por symlink)"
        echo "    Estado: Advertencia (ejecuta './build.sh link' para estandarizar)"
    else
        echo "    Tipo: Inexistente"
        echo "    Estado: No provisionado"
    fi
}

cmd_status() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        status_runtime "$r"
        echo ""
    done
}

cmd_reconcile() {
    local target_adr="${1:-all}"
    local adr_dir="${SCRIPT_DIR}/docs/adr"
    echo "==> [reconcile] Iniciando reconciliación y ratificación de ADRs post-merge..."

    if [ ! -d "${adr_dir}" ]; then
        echo "  [!] Directorio de ADRs no encontrado: ${adr_dir}"
        return 0
    fi

    local count=0
    for f in "${adr_dir}"/*.md; do
        [ ! -f "$f" ] && continue
        local fname
        fname="$(basename "$f")"

        if [ "${target_adr}" != "all" ] && [[ "${fname}" != *"${target_adr}"* ]]; then
            continue
        fi

        if grep -qE '^status:[[:space:]]*proposed' "$f"; then
            if command -v python3 >/dev/null 2>&1; then
                python3 -c "
import sys, re
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as fh:
    content = fh.read()
parts = content.split('---', 2)
if len(parts) >= 3:
    frontmatter = parts[1]
    new_fm = re.sub(r'(?m)^status:\s*proposed\b', 'status: accepted', frontmatter)
    if new_fm != frontmatter:
        new_content = '---' + new_fm + '---' + parts[2]
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
        sys.exit(0)
sys.exit(1)
" "$f" && {
                    echo "  [✓] Ratificado a 'status: accepted': ${fname}"
                    count=$((count + 1))
                }
            else
                sed -i '0,/^status:[[:space:]]*proposed/s//status: accepted/' "$f"
                echo "  [✓] Ratificado a 'status: accepted': ${fname}"
                count=$((count + 1))
            fi
        fi
    done

    echo "==> [reconcile] Reconciliación completada: ${count} ADR(s) ratificados formalmente."
}

cmd_mcp() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        echo "==> [mcp] Aprovisionando servidores MCP de ${r}..."
        compile_runtime_mcp "$r"
        link_runtime_mcp "$r"
    done
}

skills_runtime() {
    local r="$1"
    local config_file
    config_file="$(get_runtime_config_file "$r")"
    local skills_dir
    skills_dir="$(get_runtime_target_skills_dir "$r")"

    echo "==> [skills] Provisionando skills para runtime '${r}'..."
    mkdir -p "${HOME}/.local/bin" 2>/dev/null || true

    validate_config "${config_file}" "${SCHEMA_FILE}" "skills" || return 1

    if [ -n "${skills_dir}" ]; then
        mkdir -p "${skills_dir}"
        # Purgar symlinks previos en el directorio de skills del runtime
        find "${skills_dir}" -maxdepth 1 -type l -delete

        local enabled_skills=()
        mapfile -t enabled_skills < <(get_enabled_skills "${config_file}")

        for skill_name in "${enabled_skills[@]}"; do
            [[ -z "${skill_name}" ]] && continue
            local target_dir
            target_dir="$(resolve_skill_dir "${skill_name}")"
            target_dir="$(realpath -m "${target_dir}")"

            if [[ -d "${target_dir}" ]]; then
                ln -sfn "${target_dir}" "${skills_dir}/${skill_name}"
                echo "  [+] [${r}] Skill habilitado: ${skill_name} -> ${skills_dir}/${skill_name}"
            else
                echo "  [!] Advertencia [${r}]: No se encontró el origen '${skill_name}' en ${SKILLS_DIR}"
            fi
        done
    else
        echo "  [-] [${r}] No define skills_dir en target; se omite aprovisionamiento de carpeta de skills."
    fi

    # Exposición de binarios en ~/.local/bin
    local enabled_skills=()
    mapfile -t enabled_skills < <(get_enabled_skills "${config_file}")
    for skill_name in "${enabled_skills[@]}"; do
        [[ -z "${skill_name}" ]] && continue
        local target_dir
        target_dir="$(resolve_skill_dir "${skill_name}")"
        target_dir="$(realpath -m "${target_dir}")"
        local candidate_bins=()
        if [[ -d "${target_dir}/bin" ]]; then
            for b in "${target_dir}/bin/"*; do
                if [[ -f "${b}" && -x "${b}" ]]; then
                    candidate_bins+=("${b}")
                fi
            done
        fi
        if [[ -d "${target_dir}/scripts" ]]; then
            for script in "${target_dir}/scripts/"*.sh; do
                if [[ -f "${script}" && -x "${script}" ]]; then
                    candidate_bins+=("${script}")
                fi
            done
        fi

        for script in "${candidate_bins[@]}"; do
            [[ -z "${script}" ]] && continue
            local bin_name
            bin_name=$(basename "${script}")
            [[ "${bin_name}" == *.sh ]] && bin_name="${bin_name%.sh}"
            local bin_alias
            bin_alias="$(get_binary_alias "${config_file}" "${bin_name}")"
            if [[ -n "${bin_alias}" ]]; then
                bin_name="${bin_alias}"
            fi
            ln -sfn "${script}" "${HOME}/.local/bin/${bin_name}"
            echo "      -> [${r}] Binario expuesto en PATH: ~/.local/bin/${bin_name}"
        done
    done
}

cmd_skills() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        skills_runtime "$r"
    done
}
