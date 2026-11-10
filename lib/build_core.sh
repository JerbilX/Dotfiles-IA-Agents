#!/usr/bin/env bash
# lib/build_core.sh - Compilación de directivas y configuración MCP por runtime

compile_runtime_mcp() {
    local r="$1"
    local dist_dir
    dist_dir="$(get_runtime_dist_dir "$r")"
    local dist_mcp_file
    dist_mcp_file="$(get_runtime_dist_mcp_file "$r")"
    local config_file
    config_file="$(get_runtime_config_file "$r")"
    local mcp_dir
    mcp_dir="$(get_runtime_mcp_dir "$r")"

    echo "==> [build] Compilando configuración MCP para runtime '${r}' en ${dist_mcp_file}..."
    mkdir -p "${dist_dir}"

    if ! command -v python3 >/dev/null 2>&1; then
        echo "Error: Se requiere python3 para compilar la configuración de MCP." >&2
        return 1
    fi

    local compile_script="${SCRIPT_DIR}/lib/compile_mcp.py"
    if [ ! -f "${compile_script}" ]; then
        echo "Error: Script de compilación MCP no encontrado en ${compile_script}" >&2
        return 1
    fi

    python3 "${compile_script}" "${config_file}" "${mcp_dir}" "${dist_mcp_file}" "${MCP_SCHEMA_FILE}" || return 1

    local enabled_mcps=()
    mapfile -t enabled_mcps < <(get_enabled_mcp_servers "${config_file}")
    local server_count=0
    for s in "${enabled_mcps[@]}"; do
        [ -n "${s}" ] && server_count=$((server_count + 1))
    done

    if [ "${server_count}" -eq 0 ]; then
        echo "==> [build] Configuración MCP compilada para '${r}' (0 servidores habilitados): ${dist_mcp_file}"
    else
        echo "==> [build] Configuración MCP compilada con éxito para '${r}': ${dist_mcp_file} (${server_count} servidor(es))"
    fi
}

compile_runtime_build() {
    local r="$1"
    local dist_dir
    dist_dir="$(get_runtime_dist_dir "$r")"
    local dist_file
    dist_file="$(get_runtime_dist_prompt_file "$r")"
    local config_file
    config_file="$(get_runtime_config_file "$r")"
    local rules_dir
    rules_dir="$(get_runtime_rules_dir "$r")"

    echo "==> [build] Compilando directivas para runtime '${r}' en ${dist_file}..."
    mkdir -p "${dist_dir}"

    local tmp_file
    tmp_file="$(mktemp "${dist_dir}/.agents.tmp.XXXXXX")"

    cat << EOF > "${tmp_file}"
<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Runtime: ${r}
  Components: core/00-router.md, core/01-objectivity.md, runtimes/${r}/rules/*.md
  =============================================================================
-->

EOF

    local suppressed_rules=()
    if [ -f "${config_file}" ]; then
        mapfile -t suppressed_rules < <(get_disabled_core_rules "${config_file}")
        local core_overrides=()
        mapfile -t core_overrides < <(get_core_overrides "${config_file}")
        for ovr in "${core_overrides[@]}"; do
            [ -z "${ovr}" ] && continue
            suppressed_rules+=("${ovr%%=*}")
        done
    fi

    local basal_core_rules=("00-router.md" "01-objectivity.md")
    local first=true
    for fname in "${basal_core_rules[@]}"; do
        local f="${CORE_DIR}/${fname}"
        [ ! -f "$f" ] && continue
        if [ ${#suppressed_rules[@]} -gt 0 ] && is_rule_suppressed "${fname}" "${suppressed_rules[@]}"; then
            echo "  [-] [${r}] Directiva core basal omitida por configuración de runtime: ${fname}"
            continue
        fi
        if [ "$first" = false ]; then
            printf "\n\n" >> "${tmp_file}"
        fi
        sed -E '/<!--[[:space:]]*rule:.*-->/d' "$f" >> "${tmp_file}"
        first=false
    done

    if [ -d "${rules_dir}" ]; then
        for f in "${rules_dir}"/*.md; do
            [ -e "$f" ] || continue
            if [ "$first" = false ]; then
                printf "\n\n" >> "${tmp_file}"
            fi
            sed -E '/<!--[[:space:]]*rule:.*-->/d' "$f" >> "${tmp_file}"
            first=false
        done
    fi

    printf "\n" >> "${tmp_file}"
    mv -f "${tmp_file}" "${dist_file}"
    echo "==> [build] Compilación finalizada para '${r}': ${dist_file}"

    # Telemetría de presupuesto de contexto
    local lines words bytes approx_tokens size_kb
    lines="$(wc -l < "${dist_file}" | tr -d ' ')"
    words="$(wc -w < "${dist_file}" | tr -d ' ')"
    bytes="$(wc -c < "${dist_file}" | tr -d ' ')"
    approx_tokens=$(( (words * 4 + 2) / 3 ))
    size_kb="$(awk "BEGIN {printf \"%.1f\", ${bytes}/1024}")"

    echo "==> [build] Telemetría de contexto [${r}]: ${lines} líneas | ${words} palabras | ~${approx_tokens} tokens estimados (${size_kb} KB)"
    local target_words="${TARGET_CONTEXT_WORDS}"
    local max_words="${MAX_CONTEXT_WORDS}"
    if [ "${words}" -gt "${max_words}" ]; then
        echo "  [!] Advertencia [${r}]: El contexto compilado supera el techo máximo (${words} > ${max_words} palabras)." >&2
        echo "      ADVERTENCIA: './build.sh check' fallará con error hasta reducir el prompt." >&2
    elif [ "${words}" -gt "${target_words}" ]; then
        echo "  [!] Advertencia [${r}]: El contexto compilado supera la banda objetivo (${words} > ${target_words} palabras, techo: ${max_words})." >&2
        echo "      Considera modularizar directivas extensas hacia skills bajo demanda o aplicar enforcement P0." >&2
    fi

    # Compilación modular de configuración MCP
    compile_runtime_mcp "${r}"

    # Compilación modular de Lifecycle Hooks
    compile_runtime_hooks "${r}"
}

compile_runtime_hooks() {
    local r="$1"
    local dist_dir
    dist_dir="$(get_runtime_dist_dir "$r")"
    local dist_hooks_file
    dist_hooks_file="$(get_runtime_dist_hooks_file "$r")"
    local hooks_source
    hooks_source="$(get_runtime_hooks_source_file "$r")"

    if [ -f "${hooks_source}" ]; then
        echo "==> [build] Compilando configuración de Lifecycle Hooks para runtime '${r}' en ${dist_hooks_file}..."
        mkdir -p "${dist_dir}"
        cp "${hooks_source}" "${dist_hooks_file}"
        echo "==> [build] Lifecycle Hooks compilados con éxito para '${r}': ${dist_hooks_file}"
    fi
}

cmd_build() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        compile_runtime_build "$r"
    done
}
