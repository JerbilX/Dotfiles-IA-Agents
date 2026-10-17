#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${SCRIPT_DIR}/core"
RUNTIMES_BASE_DIR="${SCRIPT_DIR}/runtimes"
SCHEMA_FILE="${RUNTIMES_BASE_DIR}/schema/runtime-config.schema.json"
MCP_SCHEMA_FILE="${RUNTIMES_BASE_DIR}/schema/mcp-server.schema.json"
SKILLS_DIR="${SCRIPT_DIR}/skills"
MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-4000}"

# ------------------------------------------------------------------------------
# Descubrimiento y Resolución Dinámica de Runtimes
# ------------------------------------------------------------------------------

get_available_runtimes() {
    local runtimes=()
    for d in "${RUNTIMES_BASE_DIR}"/*; do
        [ ! -d "$d" ] && continue
        local rname
        rname="$(basename "$d")"
        [ "$rname" = "schema" ] && continue
        if [ -f "$d/config.json" ]; then
            runtimes+=("$rname")
        fi
    done
    printf '%s\n' "${runtimes[@]}"
}

validate_runtime_arg() {
    local target_arg="${1:-all}"
    if [ -n "${target_arg}" ] && [ "${target_arg}" != "all" ]; then
        local config_path="${RUNTIMES_BASE_DIR}/${target_arg}/config.json"
        if [ ! -f "${config_path}" ]; then
            echo "Error: Runtime '${target_arg}' no encontrado en ${RUNTIMES_BASE_DIR}/ (falta config.json)" >&2
            return 1
        fi
    fi
    return 0
}

resolve_target_runtimes() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    if [ -z "${target_arg}" ] || [ "${target_arg}" = "all" ]; then
        get_available_runtimes
    else
        echo "${target_arg}"
    fi
}

get_runtime_dir() { echo "${RUNTIMES_BASE_DIR}/$1"; }
get_runtime_config_file() { echo "${RUNTIMES_BASE_DIR}/$1/config.json"; }
get_runtime_rules_dir() { echo "${RUNTIMES_BASE_DIR}/$1/rules"; }
get_runtime_mcp_dir() { echo "${RUNTIMES_BASE_DIR}/$1/mcp"; }
get_runtime_dist_dir() { echo "${SCRIPT_DIR}/dist/$1"; }
get_runtime_dist_prompt_file() { echo "${SCRIPT_DIR}/dist/$1/AGENTS.md"; }
get_runtime_dist_mcp_file() { echo "${SCRIPT_DIR}/dist/$1/mcp_config.json"; }

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
    local cfg
    cfg="$(get_runtime_config_file "$r")"
    local t_dir=""
    if [ -f "${cfg}" ]; then
        if command -v jq >/dev/null 2>&1; then
            t_dir="$(jq -r '.target.config_dir // empty' "${cfg}" 2>/dev/null || true)"
        elif command -v python3 >/dev/null 2>&1; then
            t_dir="$(python3 -c "import json; print(json.load(open('${cfg}')).get('target', {}).get('config_dir', ''))" 2>/dev/null || true)"
        fi
    fi
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
    local cfg
    cfg="$(get_runtime_config_file "$r")"
    local t_name=""
    if [ -f "${cfg}" ]; then
        if command -v jq >/dev/null 2>&1; then
            t_name="$(jq -r '.target.prompt_filename // empty' "${cfg}" 2>/dev/null || true)"
        elif command -v python3 >/dev/null 2>&1; then
            t_name="$(python3 -c "import json; print(json.load(open('${cfg}')).get('target', {}).get('prompt_filename', ''))" 2>/dev/null || true)"
        fi
    fi
    if [ -z "${t_name}" ]; then
        t_name="AGENTS.md"
    fi
    local t_dir
    t_dir="$(get_runtime_target_dir "$r")"
    echo "${t_dir}/${t_name}"
}

get_runtime_target_mcp_file() {
    local r="$1"
    local cfg
    cfg="$(get_runtime_config_file "$r")"
    local t_name=""
    if [ -f "${cfg}" ]; then
        if command -v jq >/dev/null 2>&1; then
            t_name="$(jq -r '.target.mcp_filename // empty' "${cfg}" 2>/dev/null || true)"
        elif command -v python3 >/dev/null 2>&1; then
            t_name="$(python3 -c "import json; print(json.load(open('${cfg}')).get('target', {}).get('mcp_filename', ''))" 2>/dev/null || true)"
        fi
    fi
    if [ -z "${t_name}" ]; then
        t_name="mcp_config.json"
    fi
    local t_dir
    t_dir="$(get_runtime_target_dir "$r")"
    echo "${t_dir}/${t_name}"
}

get_runtime_target_skills_dir() {
    local r="$1"
    local cfg
    cfg="$(get_runtime_config_file "$r")"
    local s_dir=""
    if [ -f "${cfg}" ]; then
        if command -v jq >/dev/null 2>&1; then
            s_dir="$(jq -r '.target.skills_dir // empty' "${cfg}" 2>/dev/null || true)"
        elif command -v python3 >/dev/null 2>&1; then
            s_dir="$(python3 -c "import json; print(json.load(open('${cfg}')).get('target', {}).get('skills_dir', ''))" 2>/dev/null || true)"
        fi
    fi
    if [ -z "${s_dir}" ]; then
        if [ "$r" = "antigravity" ]; then
            s_dir="${HOME}/.gemini/config/skills"
        fi
    else
        s_dir="$(expand_path "${s_dir}")"
    fi
    echo "${s_dir}"
}

# ------------------------------------------------------------------------------
# Validaciones de Esquema y Configuración
# ------------------------------------------------------------------------------

validate_config() {
    local config_file="$1"
    local schema_file="$2"
    local caller="${3:-validate}"

    if [[ ! -f "${config_file}" ]]; then
        echo "Error: Archivo de configuración no encontrado en ${config_file}" >&2
        return 1
    fi

    if [[ ! -f "${schema_file}" ]]; then
        echo "Error: Archivo de esquema no encontrado en ${schema_file}" >&2
        return 1
    fi

    echo "==> [${caller}] Validando ${config_file} contra ${schema_file}..."
    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c '
import json, sys

config_path, schema_path = sys.argv[1], sys.argv[2]
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
except Exception as e:
    print(f"Error de sintaxis JSON: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(config, dict):
    print("Error de validación: El archivo de configuración debe ser un objeto JSON.", file=sys.stderr)
    sys.exit(1)

for req in schema.get("required", []):
    if req not in config:
        print(f"Error de validación: Falta la propiedad requerida '\''{req}'\''.", file=sys.stderr)
        sys.exit(1)

allowed_props = set(schema.get("properties", {}).keys())
if not schema.get("additionalProperties", True):
    extra = set(config.keys()) - allowed_props
    if extra:
        print(f"Error de validación: Propiedades no permitidas encontradas: {extra}", file=sys.stderr)
        sys.exit(1)

if "skills" in config:
    if not isinstance(config["skills"], list):
        print("Error de validación: '\''skills'\'' debe ser un array.", file=sys.stderr)
        sys.exit(1)
    for skill in config["skills"]:
        if not isinstance(skill, str) or not skill.strip():
            print("Error de validación: Cada elemento de '\''skills'\'' debe ser una cadena no vacía.", file=sys.stderr)
            sys.exit(1)

if "binaries" in config:
    if not isinstance(config["binaries"], dict):
        print("Error de validación: '\''binaries'\'' debe ser un objeto.", file=sys.stderr)
        sys.exit(1)
    for k, v in config["binaries"].items():
        if not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip():
            print("Error de validación: Claves y valores de '\''binaries'\'' deben ser cadenas no vacías.", file=sys.stderr)
            sys.exit(1)

if "mcp_servers" in config:
    if not isinstance(config["mcp_servers"], list):
        print("Error de validación: '\''mcp_servers'\'' debe ser un array.", file=sys.stderr)
        sys.exit(1)
    for server in config["mcp_servers"]:
        if not isinstance(server, str) or not server.strip():
            print("Error de validación: Cada elemento de '\''mcp_servers'\'' debe ser una cadena no vacía.", file=sys.stderr)
            sys.exit(1)

if "disabled_core_rules" in config:
    if not isinstance(config["disabled_core_rules"], list):
        print("Error de validación: '\''disabled_core_rules'\'' debe ser un array.", file=sys.stderr)
        sys.exit(1)
    for rule in config["disabled_core_rules"]:
        if not isinstance(rule, str) or not rule.strip():
            print("Error de validación: Cada elemento de '\''disabled_core_rules'\'' debe ser una cadena no vacía.", file=sys.stderr)
            sys.exit(1)

if "overrides" in config:
    if not isinstance(config["overrides"], dict):
        print("Error de validación: '\''overrides'\'' debe ser un objeto.", file=sys.stderr)
        sys.exit(1)
    for k, v in config["overrides"].items():
        if not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip():
            print("Error de validación: Claves y valores de '\''overrides'\'' deben ser cadenas no vacías.", file=sys.stderr)
            sys.exit(1)

if "target" in config:
    if not isinstance(config["target"], dict):
        print("Error de validación: '\''target'\'' debe ser un objeto.", file=sys.stderr)
        sys.exit(1)
    for k, v in config["target"].items():
        if not isinstance(v, str) or not v.strip():
            print(f"Error de validación: La propiedad '\''{k}'\'' de '\''target'\'' debe ser una cadena no vacía.", file=sys.stderr)
            sys.exit(1)
' "${config_file}" "${schema_file}"; then
            return 1
        fi
    elif command -v jq >/dev/null 2>&1; then
        if ! jq empty "${config_file}" >/dev/null 2>&1; then
            echo "Error de sintaxis JSON en ${config_file}" >&2
            return 1
        fi
        local has_skills
        has_skills=$(jq 'has("skills") and (.skills | type == "array")' "${config_file}")
        if [[ "${has_skills}" != "true" ]]; then
            echo "Error de validación: 'skills' es requerido y debe ser un array." >&2
            return 1
        fi
        if jq -e 'has("disabled_core_rules") and (.disabled_core_rules | type != "array")' "${config_file}" >/dev/null 2>&1; then
            echo "Error de validación: 'disabled_core_rules' debe ser un array." >&2
            return 1
        fi
        if jq -e 'has("overrides") and (.overrides | type != "object")' "${config_file}" >/dev/null 2>&1; then
            echo "Error de validación: 'overrides' debe ser un objeto." >&2
            return 1
        fi
        if jq -e 'has("target") and (.target | type != "object")' "${config_file}" >/dev/null 2>&1; then
            echo "Error de validación: 'target' debe ser un objeto." >&2
            return 1
        fi
    else
        echo "Error: Se requiere 'python3' o 'jq' para validar ${config_file}" >&2
        return 1
    fi
}

get_enabled_skills() {
    local config_file="$1"
    if command -v jq >/dev/null 2>&1; then
        jq -r '.skills[]?' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; [print(s) for s in json.load(open('${config_file}')).get('skills', [])]" 2>/dev/null || true
    fi
}

resolve_skill_dir() {
    local skill_name="$1"
    echo "${SKILLS_DIR}/${skill_name}"
}

get_binary_alias() {
    local config_file="$1"
    local bin_name="$2"
    if command -v jq >/dev/null 2>&1; then
        jq -r --arg b "${bin_name}" '.binaries[$b] // empty' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; print(json.load(open('${config_file}')).get('binaries', {}).get('${bin_name}', ''))" 2>/dev/null || true
    fi
}

get_declared_binaries() {
    local config_file="$1"
    if command -v jq >/dev/null 2>&1; then
        jq -r '.binaries | to_entries[]? | "\(.key)=\(.value)"' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; [print(f'{k}={v}') for k, v in json.load(open('${config_file}')).get('binaries', {}).items()]" 2>/dev/null || true
    fi
}

get_enabled_mcp_servers() {
    local config_file="$1"
    if command -v jq >/dev/null 2>&1; then
        jq -r '.mcp_servers[]?' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; [print(s) for s in json.load(open('${config_file}')).get('mcp_servers', [])]" 2>/dev/null || true
    fi
}

get_disabled_core_rules() {
    local config_file="$1"
    if [ ! -f "${config_file}" ]; then
        return 0
    fi
    if command -v jq >/dev/null 2>&1; then
        jq -r '.disabled_core_rules[]?' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; [print(r) for r in json.load(open('${config_file}')).get('disabled_core_rules', [])]" 2>/dev/null || true
    fi
}

get_core_overrides() {
    local config_file="$1"
    if [ ! -f "${config_file}" ]; then
        return 0
    fi
    if command -v jq >/dev/null 2>&1; then
        jq -r '.overrides | to_entries[]? | "\(.key)=\(.value)"' "${config_file}" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import json; [print(f'{k}={v}') for k, v in json.load(open('${config_file}')).get('overrides', {}).items()]" 2>/dev/null || true
    fi
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

validate_mcp_server() {
    local mcp_file="$1"
    local schema_file="$2"
    local caller="${3:-validate}"

    if [[ ! -f "${mcp_file}" ]]; then
        echo "Error: Módulo MCP no encontrado en ${mcp_file}" >&2
        return 1
    fi

    if [[ ! -f "${schema_file}" ]]; then
        echo "Error: Esquema MCP no encontrado en ${schema_file}" >&2
        return 1
    fi

    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c '
import json, sys

mcp_path, schema_path = sys.argv[1], sys.argv[2]
try:
    with open(mcp_path, "r", encoding="utf-8") as f:
        mcp = json.load(f)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
except Exception as e:
    print(f"Error de sintaxis JSON en {mcp_path}: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(mcp, dict):
    print(f"Error de validación en {mcp_path}: Debe ser un objeto JSON.", file=sys.stderr)
    sys.exit(1)

allowed_props = set(schema.get("properties", {}).keys())
if not schema.get("additionalProperties", True):
    extra = set(mcp.keys()) - allowed_props
    if extra:
        print(f"Error de validación en {mcp_path}: Propiedades no permitidas encontradas: {extra}", file=sys.stderr)
        sys.exit(1)

has_command = "command" in mcp
has_url = "serverUrl" in mcp

if not has_command and not has_url:
    print(f"Error de validación en {mcp_path}: Debe definir '\''command'\'' (stdio) o '\''serverUrl'\'' (sse).", file=sys.stderr)
    sys.exit(1)

if has_command and has_url:
    print(f"Error de validación en {mcp_path}: No puede definir '\''command'\'' y '\''serverUrl'\'' simultáneamente.", file=sys.stderr)
    sys.exit(1)

if has_command:
    if not isinstance(mcp["command"], str) or not mcp["command"].strip():
        print(f"Error de validación en {mcp_path}: '\''command'\'' debe ser una cadena no vacía.", file=sys.stderr)
        sys.exit(1)

if has_url:
    if not isinstance(mcp["serverUrl"], str) or not mcp["serverUrl"].strip():
        print(f"Error de validación en {mcp_path}: '\''serverUrl'\'' debe ser una cadena no vacía.", file=sys.stderr)
        sys.exit(1)

if "args" in mcp:
    if not isinstance(mcp["args"], list):
        print(f"Error de validación en {mcp_path}: '\''args'\'' debe ser un array.", file=sys.stderr)
        sys.exit(1)
    for arg in mcp["args"]:
        if not isinstance(arg, str):
            print(f"Error de validación en {mcp_path}: Cada elemento de '\''args'\'' debe ser una cadena.", file=sys.stderr)
            sys.exit(1)

if "env" in mcp:
    if not isinstance(mcp["env"], dict):
        print(f"Error de validación en {mcp_path}: '\''env'\'' debe ser un objeto.", file=sys.stderr)
        sys.exit(1)
    for k, v in mcp["env"].items():
        if not isinstance(k, str) or not isinstance(v, str):
            print(f"Error de validación en {mcp_path}: Claves y valores de '\''env'\'' deben ser cadenas.", file=sys.stderr)
            sys.exit(1)
' "${mcp_file}" "${schema_file}"; then
            return 1
        fi
    elif command -v jq >/dev/null 2>&1; then
        if ! jq empty "${mcp_file}" >/dev/null 2>&1; then
            echo "Error de sintaxis JSON en ${mcp_file}" >&2
            return 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# Compilación de Directivas y MCP por Runtime
# ------------------------------------------------------------------------------

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

    local server_count
    server_count=$(get_enabled_mcp_servers "${config_file}" | grep -c . || true)
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
  Components: core/*.md, runtimes/${r}/rules/*.md
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

    local first=true
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        local fname
        fname="$(basename "$f")"
        if [ ${#suppressed_rules[@]} -gt 0 ] && is_rule_suppressed "${fname}" "${suppressed_rules[@]}"; then
            echo "  [-] [${r}] Directiva core omitida por configuración de runtime: ${fname}"
            continue
        fi
        if [ "$first" = false ]; then
            printf "\n\n" >> "${tmp_file}"
        fi
        cat "$f" >> "${tmp_file}"
        first=false
    done

    if [ -d "${rules_dir}" ]; then
        for f in $(find "${rules_dir}" -maxdepth 1 -name "*.md" | sort); do
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
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        compile_runtime_build "$r"
    done
}

# ------------------------------------------------------------------------------
# Enlace Simbólico hacia el Sistema Anfitrión
# ------------------------------------------------------------------------------

link_runtime_mcp() {
    local r="$1"
    local dist_mcp_file
    dist_mcp_file="$(get_runtime_dist_mcp_file "$r")"
    local target_mcp_file
    target_mcp_file="$(get_runtime_target_mcp_file "$r")"
    local target_dir
    target_dir="$(get_runtime_target_dir "$r")"

    echo "==> [link] Asegurando enlace simbólico para MCP [${r}] en ${target_dir}..."
    mkdir -p "${target_dir}"

    if [ ! -f "${dist_mcp_file}" ]; then
        echo "Error: ${dist_mcp_file} no existe. Ejecuta './build.sh build ${r}' primero." >&2
        return 1
    fi

    if [ -e "${target_mcp_file}" ] || [ -L "${target_mcp_file}" ]; then
        local current_target=""
        if [ -L "${target_mcp_file}" ]; then
            current_target="$(readlink "${target_mcp_file}" || true)"
        fi

        if [ "${current_target}" = "${dist_mcp_file}" ]; then
            echo "==> [link] [${r}] El symlink MCP ya apunta correctamente a ${dist_mcp_file}."
            return 0
        fi

        local timestamp
        timestamp="$(date +%Y%m%d_%H%M%S)"
        echo "==> [link] [${r}] Respaldando archivo/symlink MCP preexistente en ${target_mcp_file}.bak.${timestamp}..."
        mv "${target_mcp_file}" "${target_mcp_file}.bak.${timestamp}"
    fi

    echo "==> [link] [${r}] Creando symlink atómico: ${target_mcp_file} -> ${dist_mcp_file}..."
    ln -sfn "${dist_mcp_file}" "${target_mcp_file}"
    echo "==> [link] [${r}] Symlink MCP establecido exitosamente."
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
    mkdir -p "${target_dir}"

    if [ ! -f "${dist_file}" ]; then
        echo "Error: ${dist_file} no existe. Ejecuta './build.sh build ${r}' primero." >&2
        return 1
    fi

    if [ -e "${target_file}" ] || [ -L "${target_file}" ]; then
        local current_target=""
        if [ -L "${target_file}" ]; then
            current_target="$(readlink "${target_file}" || true)"
        fi

        if [ "${current_target}" = "${dist_file}" ]; then
            echo "==> [link] [${r}] El symlink ya apunta correctamente a ${dist_file}."
        else
            local timestamp
            timestamp="$(date +%Y%m%d_%H%M%S)"
            echo "==> [link] [${r}] Respaldando archivo/symlink preexistente en ${target_file}.bak.${timestamp}..."
            mv "${target_file}" "${target_file}.bak.${timestamp}"
            echo "==> [link] [${r}] Creando symlink atómico: ${target_file} -> ${dist_file}..."
            ln -sfn "${dist_file}" "${target_file}"
            echo "==> [link] [${r}] Symlink establecido exitosamente."
        fi
    else
        echo "==> [link] [${r}] Creando symlink atómico: ${target_file} -> ${dist_file}..."
        ln -sfn "${dist_file}" "${target_file}"
        echo "==> [link] [${r}] Symlink establecido exitosamente."
    fi

    link_runtime_mcp "${r}"
}

cmd_link() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        link_runtime "$r"
    done
}

# ------------------------------------------------------------------------------
# Inspección de Estado
# ------------------------------------------------------------------------------

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
            echo "    Estado: VÁLIDO"
        else
            echo "    Estado: ROTO (destino no existe)"
        fi
    elif [ -e "${target_file}" ]; then
        echo "    Tipo: Archivo regular (NO es symlink)"
        echo "    Estado: Requiere './build.sh link ${r}'"
    else
        echo "    Tipo: Inexistente"
        echo "    Estado: No configurado. Ejecuta './build.sh link ${r}'"
    fi

    echo "  Servidores MCP (${target_mcp_file}):"
    if [ -L "${target_mcp_file}" ]; then
        local target
        target="$(readlink "${target_mcp_file}")"
        echo "    Tipo: Enlace simbólico (symlink) -> ${target}"
        if [ -e "${target_mcp_file}" ]; then
            echo "    Estado: VÁLIDO"
        else
            echo "    Estado: ROTO"
        fi
    elif [ -e "${target_mcp_file}" ]; then
        echo "    Tipo: Archivo regular (NO es symlink)"
        echo "    Estado: Requiere './build.sh link ${r}'"
    else
        echo "    Tipo: Inexistente"
        echo "    Estado: No configurado"
    fi
}

cmd_status() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        status_runtime "$r"
        echo ""
    done
}

cmd_mcp() {
    local target_arg="${1:-all}"
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

# ------------------------------------------------------------------------------
# Aprovisionamiento de Skills
# ------------------------------------------------------------------------------

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
        if [[ -d "${target_dir}/scripts" ]]; then
            for script in "${target_dir}/scripts/"*.sh; do
                if [[ -f "${script}" && -x "${script}" ]]; then
                    local bin_name
                    bin_name=$(basename "${script}" .sh)
                    local bin_alias
                    bin_alias="$(get_binary_alias "${config_file}" "${bin_name}")"
                    if [[ -n "${bin_alias}" ]]; then
                        bin_name="${bin_alias}"
                    fi
                    ln -sfn "${script}" "${HOME}/.local/bin/${bin_name}"
                    echo "      -> [${r}] Binario expuesto en PATH: ~/.local/bin/${bin_name}"
                fi
            done
        fi
    done
    echo "==> [skills] Provisionamiento finalizado para '${r}'."
}

cmd_skills() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        skills_runtime "$r"
    done
}

# ------------------------------------------------------------------------------
# Auditoría Estática de Integridad (cmd_check)
# ------------------------------------------------------------------------------

CHECK_ERRORS=0
CHECK_WARNINGS=0

check_core_rules() {
    local seen_core_prefixes=()
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        local fname
        fname="$(basename "$f")"
        if [[ "${fname}" =~ ^([0-9]+)- ]]; then
            local pfx="${BASH_REMATCH[1]}"
            if printf '%s\n' "${seen_core_prefixes[@]}" | grep -qx "${pfx}"; then
                echo "  [✗] Colisión de prefijo '${pfx}-' detectada en core/: ${fname}" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            else
                seen_core_prefixes+=("${pfx}")
            fi
        else
            echo "  [!] Advertencia: Archivo ${fname} en core/ no sigue el patrón numérico 'NN-*.md'" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        fi
    done
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

        for skill_name in "${enabled_skills[@]}"; do
            [ -z "${skill_name}" ] && continue
            local skill_dir
            skill_dir="$(resolve_skill_dir "${skill_name}")"
            local script_path="${skill_dir}/scripts/${src_name}.sh"
            if [ -f "${script_path}" ]; then
                found=true
                break
            fi
        done

        if [ "${found}" = false ]; then
            echo "  [!] Advertencia [${r}]: Alias de binario '${src_name}' en config.json no coincide con ningún script en los skills habilitados" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        fi
    done

    if [ "${bin_scripts_ok}" = true ]; then
        echo "  [✓] [${r}] Binarios de skills: ${count_scripts} script(s) verificado(s)"
    fi

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
                if command -v jq >/dev/null 2>&1; then
                    cmd="$(jq -r '.command // empty' "${s_path}")"
                elif command -v python3 >/dev/null 2>&1; then
                    cmd="$(python3 -c "import json; print(json.load(open('${s_path}')).get('command', ''))")"
                fi

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
        for f in $(find "${rules_dir}" -maxdepth 1 -name "*.md" | sort); do
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
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        local fname
        fname="$(basename "$f")"
        if [ ${#suppressed_rules_check[@]} -gt 0 ] && is_rule_suppressed "${fname}" "${suppressed_rules_check[@]}"; then
            continue
        fi
        all_files+=("$f")
    done
    if [ -d "${rules_dir}" ]; then
        for f in $(find "${rules_dir}" -maxdepth 1 -name "*.md" | sort); do
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

    # 8. Presupuesto de contexto
    if [ -f "${dist_file}" ]; then
        local w
        w="$(wc -w < "${dist_file}" | tr -d ' ')"
        local max_w="${MAX_CONTEXT_WORDS:-4000}"
        local pct=$(( w * 100 / max_w ))
        if [ "${w}" -gt "${max_w}" ]; then
            echo "  [!] Advertencia [${r}]: Presupuesto de contexto superado: ${w} / ${max_w} palabras (${pct}%)" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        else
            echo "  [✓] [${r}] Presupuesto de contexto: ${w} / ${max_w} palabras (${pct}%)"
        fi
    else
        echo "  [!] Advertencia [${r}]: ${dist_file} no ha sido compilado aún (ejecuta './build.sh build ${r}')" >&2
        CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
    fi
}

check_local_bin_symlinks() {
    if [ -d "${HOME}/.local/bin" ]; then
        for item in "${HOME}/.local/bin"/*; do
            [ ! -e "${item}" ] && [ ! -L "${item}" ] && continue
            if [ -L "${item}" ]; then
                local link_target
                link_target="$(readlink "${item}" || true)"
                if [[ "${link_target}" == "${SCRIPT_DIR}"* ]]; then
                    if [ ! -e "${item}" ]; then
                        echo "  [✗] Symlink roto en ~/.local/bin: ${item} -> ${link_target}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    fi
                fi
            fi
        done
    fi
}

cmd_check() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    CHECK_ERRORS=0
    CHECK_WARNINGS=0

    echo "==> [check] Ejecutando verificaciones estáticas (read-only)..."

    # Verificaciones comunes de directivas core
    check_core_rules

    # Verificaciones por runtime
    for r in "${target_runtimes[@]}"; do
        [ -z "$r" ] && continue
        check_runtime "$r"
    done

    # Verificaciones comunes de ~/.local/bin
    check_local_bin_symlinks

    echo "==> [check] Verificación completada: ${CHECK_ERRORS} error(es), ${CHECK_WARNINGS} advertencia(s)."
    if [ "${CHECK_ERRORS}" -gt 0 ]; then
        return 1
    fi
    return 0
}

# ------------------------------------------------------------------------------
# Flujo Completo
# ------------------------------------------------------------------------------

cmd_all() {
    local target_arg="${1:-all}"
    validate_runtime_arg "${target_arg}" || return 1
    cmd_build "${target_arg}"
    cmd_link "${target_arg}"
    cmd_skills "${target_arg}"
    cmd_status "${target_arg}"
    echo ""
    cmd_check "${target_arg}"
}

# ------------------------------------------------------------------------------
# Punto de Entrada
# ------------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    COMMAND="${1:-all}"
    RUNTIME_ARG="${2:-all}"

    case "${COMMAND}" in
        build)
            cmd_build "${RUNTIME_ARG}"
            ;;
        link)
            cmd_link "${RUNTIME_ARG}"
            ;;
        skills)
            cmd_skills "${RUNTIME_ARG}"
            ;;
        mcp)
            cmd_mcp "${RUNTIME_ARG}"
            ;;
        status)
            cmd_status "${RUNTIME_ARG}"
            ;;
        check)
            cmd_check "${RUNTIME_ARG}"
            ;;
        all)
            cmd_all "${RUNTIME_ARG}"
            ;;
        *)
            echo "Uso: $0 {build|link|skills|mcp|status|check|all} [runtime]" >&2
            exit 1
            ;;
    esac
fi
