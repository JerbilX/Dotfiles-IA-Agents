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

    local enabled_mcps=()
    mapfile -t enabled_mcps < <(get_enabled_mcp_servers "${config_file}")

    if [ ${#enabled_mcps[@]} -eq 0 ]; then
        echo '{"mcpServers":{}}' > "${dist_mcp_file}"
        echo "==> [build] Configuración MCP compilada para '${r}' (0 servidores habilitados): ${dist_mcp_file}"
        return 0
    fi

    for s_name in "${enabled_mcps[@]}"; do
        [ -z "${s_name}" ] && continue
        local s_path="${mcp_dir}/${s_name}.json"
        if [ ! -f "${s_path}" ]; then
            echo "Error: Módulo de servidor MCP '${s_name}' declarado en ${config_file} no existe en ${s_path}" >&2
            return 1
        fi
        validate_mcp_server "${s_path}" "${MCP_SCHEMA_FILE}" "build-mcp" || return 1
    done

    if command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, os, sys

config_file, mcp_dir, dist_file = sys.argv[1], sys.argv[2], sys.argv[3]
with open(config_file, "r", encoding="utf-8") as f:
    config = json.load(f)

enabled_servers = config.get("mcp_servers", [])
mcp_servers_dict = {}

def expand_val(val):
    if isinstance(val, str):
        return os.path.expandvars(val)
    elif isinstance(val, list):
        return [expand_val(x) for x in val]
    elif isinstance(val, dict):
        return {k: expand_val(v) for k, v in val.items()}
    return val

for s_name in enabled_servers:
    s_path = os.path.join(mcp_dir, f"{s_name}.json")
    with open(s_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data.pop("$schema", None)
    data.pop("description", None)

    expanded_data = expand_val(data)
    mcp_servers_dict[s_name] = expanded_data

output = {
    "mcpServers": mcp_servers_dict
}

tmp_file = f"{dist_file}.tmp"
with open(tmp_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
    f.write("\n")

os.replace(tmp_file, dist_file)
' "${config_file}" "${mcp_dir}" "${dist_mcp_file}"
    else
        echo "Error: Se requiere python3 para compilar la configuración de MCP." >&2
        return 1
    fi

    local server_count="${#enabled_mcps[@]}"
    echo "==> [build] Configuración MCP compilada con éxito para '${r}': ${dist_mcp_file} (${server_count} servidor(es))"
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
        cat "$f" >> "${tmp_file}"
        first=false
    done

    if [ -d "${rules_dir}" ]; then
        for f in "${rules_dir}"/*.md; do
            [ -e "$f" ] || continue
            if [ "$first" = false ]; then
                printf "\n\n" >> "${tmp_file}"
            fi
            cat "$f" >> "${tmp_file}"
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
    if [ "${words}" -gt "${MAX_CONTEXT_WORDS}" ]; then
        echo "  [!] Advertencia [${r}]: El contexto compilado supera el límite recomendado (${words} > ${MAX_CONTEXT_WORDS} palabras)." >&2
        echo "      Considera modularizar directivas extensas hacia skills bajo demanda." >&2
    fi

    # Compilación modular de configuración MCP
    compile_runtime_mcp "${r}"
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
