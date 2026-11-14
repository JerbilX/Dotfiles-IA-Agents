#!/usr/bin/env bash
# lib/common.sh - Rutas base, helpers JSON y symlinks, resolución y caché de runtimes

# ------------------------------------------------------------------------------
# Helpers Canónicos JSON y Symlinks
# ------------------------------------------------------------------------------

json_get() {
    local json_file="$1"
    local expr="$2"

    if [[ ! -f "${json_file}" ]]; then
        return 1
    fi

    if command -v jq >/dev/null 2>&1; then
        jq -r "${expr}" "${json_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, sys

filepath = sys.argv[1]
expr = sys.argv[2].strip()

try:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

# Simplistic evaluation for jq-like paths (.a.b // default)
if expr.startswith("."):
    parts = expr.split("//")
    path_expr = parts[0].strip()
    strip_chars = chr(34) + chr(39)
    raw_default = parts[1].strip() if len(parts) > 1 else ""
    if raw_default == "empty":
        default_val = ""
    else:
        default_val = raw_default.strip(strip_chars)
    keys = [k for k in path_expr.lstrip(".").split(".") if k]
    cur = data
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            cur = None
            break
    if cur is not None and cur != "":
        print(cur)
    elif default_val:
        print(default_val)
' "${json_file}" "${expr}" 2>/dev/null || true
    fi
}

safe_symlink() {
    local src="$1"
    local dst="$2"
    local label="${3:-symlink}"

    local dst_dir
    dst_dir="$(dirname "${dst}")"
    mkdir -p "${dst_dir}"

    if [ -e "${dst}" ] || [ -L "${dst}" ]; then
        local current_target=""
        if [ -L "${dst}" ]; then
            current_target="$(readlink "${dst}" || true)"
        fi

        if [ "${current_target}" = "${src}" ]; then
            echo "==> [link] [${label}] El symlink ya apunta correctamente a ${src}."
            return 0
        fi

        local timestamp
        timestamp="$(date +%Y%m%d_%H%M%S)"
        echo "==> [link] [${label}] Respaldando archivo/symlink preexistente en ${dst}.bak.${timestamp}..."
        mv "${dst}" "${dst}.bak.${timestamp}"
    fi

    echo "==> [link] [${label}] Creando symlink atómico: ${dst} -> ${src}..."
    ln -sfn "${src}" "${dst}"
    echo "==> [link] [${label}] Symlink establecido exitosamente."
}

# ------------------------------------------------------------------------------
# Descubrimiento y Resolución Dinámica de Runtimes
# ------------------------------------------------------------------------------

declare -A RUNTIME_CONFIG_CACHE

load_runtime_config() {
    local r="$1"
    if [[ -n "${RUNTIME_CONFIG_CACHE["${r}:_loaded"]:-}" ]]; then
        return 0
    fi
    local cfg="${RUNTIMES_BASE_DIR}/${r}/config.json"
    if [[ ! -f "${cfg}" ]]; then
        return 0
    fi
    local raw=""
    if command -v jq >/dev/null 2>&1; then
        raw="$(jq -r '
          "status=" + (.status // "active"),
          "config_dir=" + (.target.config_dir // ""),
          "prompt_filename=" + (.target.prompt_filename // "AGENTS.md"),
          "mcp_filename=" + (.target.mcp_filename // "mcp_config.json"),
          "mcp_merge_file=" + (.target.mcp_merge_file // ""),
          "hooks_filename=" + (.target.hooks_filename // "hooks.json"),
          "skills_dir=" + (.target.skills_dir // ""),
          "skills=" + ((.skills // []) | join("\t")),
          "mcp_servers=" + ((.mcp_servers // []) | join("\t")),
          "disabled_core_rules=" + ((.disabled_core_rules // []) | join("\t")),
          "binaries=" + ((.binaries // {}) | to_entries | map("\(.key)=\(.value)") | join("\t")),
          "overrides=" + ((.overrides // {}) | to_entries | map("\(.key)=\(.value)") | join("\t"))
        ' "${cfg}" 2>/dev/null || true)"
    elif command -v python3 >/dev/null 2>&1; then
        raw="$(python3 -c '
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
print("status=" + (cfg.get("status") or "active"))
print("config_dir=" + (cfg.get("target", {}).get("config_dir") or ""))
print("prompt_filename=" + (cfg.get("target", {}).get("prompt_filename") or "AGENTS.md"))
print("mcp_filename=" + (cfg.get("target", {}).get("mcp_filename") or "mcp_config.json"))
print("mcp_merge_file=" + (cfg.get("target", {}).get("mcp_merge_file") or ""))
print("hooks_filename=" + (cfg.get("target", {}).get("hooks_filename") or "hooks.json"))
print("skills_dir=" + (cfg.get("target", {}).get("skills_dir") or ""))
print("skills=" + "\t".join(cfg.get("skills") or []))
print("mcp_servers=" + "\t".join(cfg.get("mcp_servers") or []))
print("disabled_core_rules=" + "\t".join(cfg.get("disabled_core_rules") or []))
print("binaries=" + "\t".join(f"{k}={v}" for k, v in (cfg.get("binaries") or {}).items()))
print("overrides=" + "\t".join(f"{k}={v}" for k, v in (cfg.get("overrides") or {}).items()))
' "${cfg}" 2>/dev/null || true)"
    fi
    while IFS="=" read -r k v; do
        [[ -n "${k}" ]] && RUNTIME_CONFIG_CACHE["${r}:${k}"]="${v}"
    done <<< "${raw}"
    RUNTIME_CONFIG_CACHE["${r}:_loaded"]="1"
}

cfg_to_runtime() {
    local cfg="$1"
    local dir
    dir="$(dirname "${cfg}")"
    basename "${dir}"
}

get_tab_delimited_items() {
    local val="$1"
    if [[ -z "${val}" ]]; then
        return 0
    fi
    local items=()
    IFS=$'\t' read -r -a items <<< "${val}"
    for it in "${items[@]}"; do
        [[ -n "${it}" ]] && echo "${it}"
    done
}

get_runtime_dir() { echo "${RUNTIMES_BASE_DIR}/$1"; }
get_runtime_config_file() { echo "${RUNTIMES_BASE_DIR}/$1/config.json"; }
get_runtime_rules_dir() { echo "${RUNTIMES_BASE_DIR}/$1/rules"; }
get_runtime_mcp_dir() { echo "${RUNTIMES_BASE_DIR}/$1/mcp"; }
get_runtime_dist_dir() { echo "${SCRIPT_DIR}/dist/$1"; }
get_runtime_dist_prompt_file() { echo "${SCRIPT_DIR}/dist/$1/AGENTS.md"; }
get_runtime_dist_mcp_file() { echo "${SCRIPT_DIR}/dist/$1/mcp_config.json"; }
get_runtime_dist_hooks_file() { echo "${SCRIPT_DIR}/dist/$1/hooks.json"; }
get_runtime_hooks_source_file() { echo "${RUNTIMES_BASE_DIR}/$1/hooks.json"; }

get_runtime_status() {
    local r="$1"
    load_runtime_config "$r"
    local status="${RUNTIME_CONFIG_CACHE["${r}:status"]:-}"
    if [ -z "${status}" ]; then
        status="active"
    fi
    echo "${status}"
}

get_available_runtimes() {
    local runtimes=()
    for d in "${RUNTIMES_BASE_DIR}"/*; do
        [ ! -d "$d" ] && continue
        local rname
        rname="$(basename "$d")"
        [ "$rname" = "schema" ] && continue
        if [ -f "$d/config.json" ]; then
            load_runtime_config "$rname"
            local st="${RUNTIME_CONFIG_CACHE["${rname}:status"]:-active}"
            if [ "$st" != "disabled" ]; then
                runtimes+=("$rname")
            fi
        fi
    done
    printf '%s\n' "${runtimes[@]}"
}

get_active_runtimes() {
    local runtimes=()
    for d in "${RUNTIMES_BASE_DIR}"/*; do
        [ ! -d "$d" ] && continue
        local rname
        rname="$(basename "$d")"
        [ "$rname" = "schema" ] && continue
        if [ -f "$d/config.json" ]; then
            load_runtime_config "$rname"
            local st="${RUNTIME_CONFIG_CACHE["${rname}:status"]:-active}"
            if [ "$st" = "active" ]; then
                runtimes+=("$rname")
            fi
        fi
    done
    printf '%s\n' "${runtimes[@]}"
}

LAST_VALIDATED_RUNTIME=""

validate_runtime_arg() {
    local target_arg="${1:-}"
    if [ -n "${LAST_VALIDATED_RUNTIME}" ] && [ "${LAST_VALIDATED_RUNTIME}" = "${target_arg}" ]; then
        return 0
    fi
    if [ -n "${target_arg}" ] && [ "${target_arg}" != "all" ] && [ "${target_arg}" != "default" ] && [ "${target_arg}" != "active" ]; then
        local config_path="${RUNTIMES_BASE_DIR}/${target_arg}/config.json"
        if [ ! -f "${config_path}" ]; then
            echo "Error: Runtime '${target_arg}' no encontrado en ${RUNTIMES_BASE_DIR}/ (falta config.json)" >&2
            return 1
        fi
        local st
        st="$(get_runtime_status "${target_arg}")"
        if [ "${st}" = "disabled" ]; then
            echo "Error: Runtime '${target_arg}' está deshabilitado ('status': 'disabled' en ${config_path})" >&2
            return 1
        fi
    fi
    LAST_VALIDATED_RUNTIME="${target_arg}"
    return 0
}

resolve_target_runtimes() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    if [ -z "${target_arg}" ] || [ "${target_arg}" = "default" ] || [ "${target_arg}" = "active" ]; then
        get_active_runtimes
    elif [ "${target_arg}" = "all" ]; then
        get_available_runtimes
    else
        echo "${target_arg}"
    fi
}

expand_path() {
    local p="$1"
    if [[ "$p" =~ ^~(/.*)?$ ]]; then
        p="${HOME}${p:1}"
    fi
    p="${p//\$HOME/${HOME}}"
    p="${p//\$\{HOME\}/${HOME}}"
    echo "$p"
}

get_runtime_target_dir() {
    local r="$1"
    load_runtime_config "$r"
    local t_dir="${RUNTIME_CONFIG_CACHE["${r}:config_dir"]:-}"
    if [ -z "${t_dir}" ]; then
        if [ "$r" = "antigravity" ]; then
            t_dir="${HOME}/.gemini/config"
        elif [ "$r" = "claude" ]; then
            t_dir="${HOME}/.claude"
        else
            t_dir="${HOME}/.${r}"
        fi
    else
        t_dir="$(expand_path "${t_dir}")"
    fi
    echo "${t_dir}"
}

get_runtime_target_prompt_file() {
    local r="$1"
    load_runtime_config "$r"
    local t_name="${RUNTIME_CONFIG_CACHE["${r}:prompt_filename"]:-}"
    if [ -z "${t_name}" ]; then
        t_name="AGENTS.md"
    fi
    local t_dir
    t_dir="$(get_runtime_target_dir "$r")"
    echo "${t_dir}/${t_name}"
}

# Archivo JSON del host donde se fusiona mcpServers en lugar de enlazar (ADR-0057); vacío si el runtime usa symlink
get_runtime_mcp_merge_file() {
    local r="$1"
    load_runtime_config "$r"
    local m_file="${RUNTIME_CONFIG_CACHE["${r}:mcp_merge_file"]:-}"
    [ -n "${m_file}" ] && expand_path "${m_file}"
    return 0
}

# Ruta de symlink MCP en config_dir (heredada en runtimes con mcp_merge_file)
get_runtime_target_mcp_link() {
    local r="$1"
    load_runtime_config "$r"
    local t_name="${RUNTIME_CONFIG_CACHE["${r}:mcp_filename"]:-}"
    if [ -z "${t_name}" ]; then
        t_name="mcp_config.json"
    fi
    local t_dir
    t_dir="$(get_runtime_target_dir "$r")"
    echo "${t_dir}/${t_name}"
}

# Lista (una por línea) los servidores registrados en mcpServers de un JSON del host
get_registered_mcp_servers() {
    [ -f "$1" ] || return 0
    python3 -I -c '
import json, sys
try:
    print("\n".join(json.load(open(sys.argv[1], encoding="utf-8")).get("mcpServers", {})))
except Exception:
    pass
' "$1"
}

get_runtime_target_mcp_file() {
    local r="$1"
    local m_file
    m_file="$(get_runtime_mcp_merge_file "$r")"
    if [ -n "${m_file}" ]; then
        echo "${m_file}"
        return 0
    fi
    get_runtime_target_mcp_link "$r"
}

get_runtime_target_hooks_file() {
    local r="$1"
    load_runtime_config "$r"
    local t_name="${RUNTIME_CONFIG_CACHE["${r}:hooks_filename"]:-}"
    if [ -z "${t_name}" ]; then
        t_name="hooks.json"
    fi
    local t_dir
    t_dir="$(get_runtime_target_dir "$r")"
    echo "${t_dir}/${t_name}"
}

get_runtime_target_skills_dir() {
    local r="$1"
    load_runtime_config "$r"
    local s_dir="${RUNTIME_CONFIG_CACHE["${r}:skills_dir"]:-}"
    if [ -z "${s_dir}" ]; then
        if [ "$r" = "antigravity" ]; then
            s_dir="${HOME}/.gemini/config/skills"
        fi
    else
        s_dir="$(expand_path "${s_dir}")"
    fi
    echo "${s_dir}"
}

get_enabled_skills() {
    local config_file="$1"
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    get_tab_delimited_items "${RUNTIME_CONFIG_CACHE["${r}:skills"]:-}"
}

resolve_skill_dir() {
    local skill_name="$1"
    echo "${SKILLS_DIR}/${skill_name}"
}

get_binary_alias() {
    local config_file="$1"
    local bin_name="$2"
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    local entries="${RUNTIME_CONFIG_CACHE["${r}:binaries"]:-}"
    if [[ -n "${entries}" ]]; then
        local items=()
        IFS=$'\t' read -r -a items <<< "${entries}"
        for entry in "${items[@]}"; do
            if [[ "${entry%%=*}" == "${bin_name}" ]]; then
                echo "${entry#*=}"
                return 0
            fi
        done
    fi
}

get_declared_binaries() {
    local config_file="$1"
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    get_tab_delimited_items "${RUNTIME_CONFIG_CACHE["${r}:binaries"]:-}"
}

get_enabled_mcp_servers() {
    local config_file="$1"
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    get_tab_delimited_items "${RUNTIME_CONFIG_CACHE["${r}:mcp_servers"]:-}"
}

get_disabled_core_rules() {
    local config_file="$1"
    if [ ! -f "${config_file}" ]; then
        return 0
    fi
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    get_tab_delimited_items "${RUNTIME_CONFIG_CACHE["${r}:disabled_core_rules"]:-}"
}

get_core_overrides() {
    local config_file="$1"
    if [ ! -f "${config_file}" ]; then
        return 0
    fi
    local r
    r="$(cfg_to_runtime "${config_file}")"
    load_runtime_config "${r}"
    get_tab_delimited_items "${RUNTIME_CONFIG_CACHE["${r}:overrides"]:-}"
}

is_rule_suppressed() {
    local fname="$1"
    local base_fname="${fname%.md}"
    shift
    local suppressed_list=("$@")

    for item in "${suppressed_list[@]}"; do
        [ -z "${item}" ] && continue
        local item_clean="${item%.md}"
        if [ "${fname}" = "${item}" ] || [ "${fname}" = "${item}.md" ] || [ "${base_fname}" = "${item_clean}" ]; then
            return 0
        fi
    done
    return 1
}
