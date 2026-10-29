#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${SCRIPT_DIR}/core"
RUNTIMES_BASE_DIR="${SCRIPT_DIR}/runtimes"
SCHEMA_FILE="${RUNTIMES_BASE_DIR}/schema/runtime-config.schema.json"
MCP_SCHEMA_FILE="${RUNTIMES_BASE_DIR}/schema/mcp-server.schema.json"
MODULE_SCHEMA_FILE="${RUNTIMES_BASE_DIR}/schema/module-config.schema.json"
MODULES_DIR="${SCRIPT_DIR}/modules"
SKILLS_DIR="${SCRIPT_DIR}/skills"
MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-800}"
MAX_MODULE_WORDS="${MAX_MODULE_WORDS:-300}"
MAX_README_WORDS="${MAX_README_WORDS:-600}"

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

    # Enlace de directivas modulares core hacia target_dir para soporte multi-workspace
    local target_core_dir="${target_dir}/core"
    if [ ! -e "${target_core_dir}" ] && [ ! -L "${target_core_dir}" ]; then
        echo "==> [link] [${r}] Creando symlink de directivas modulares: ${target_core_dir} -> ${CORE_DIR}..."
        ln -sfn "${CORE_DIR}" "${target_core_dir}"
    fi

    link_runtime_mcp "${r}"
}

setup_gh_aliases() {
    echo "==> [link] Asegurando configuración de aliases de GitHub CLI ('gh')..."
    if ! command -v gh >/dev/null 2>&1; then
        echo "  [-] gh no está instalado o no se encuentra en \$PATH; omitiendo aliases."
        return 0
    fi

    local err=false
    if gh alias set --shell board 'gh project item-list 1 --owner @me --limit 100 --query "repo:$1 -status:Done" --format json --jq ".items[] | {number: .content.number, title: .content.title, status: .status}"' --clobber >/dev/null 2>&1; then
        echo "  [+] [gh] Alias configurado: 'board' -> consulta de tareas activas (-status:Done) con limit 100"
    else
        echo "  [!] Advertencia: No se pudo configurar el alias 'board' de gh" >&2
        err=true
    fi

    if gh alias set --shell board-ready 'gh project item-list 1 --owner @me --limit 100 --query "repo:$1 status:\"🎯 Ready for Dev\"" --format json --jq ".items[] | {number: .content.number, title: .content.title, url: .content.url}"' --clobber >/dev/null 2>&1; then
        echo "  [+] [gh] Alias configurado: 'board-ready' -> consulta de tareas listas (Ready for Dev) con limit 100"
    else
        echo "  [!] Advertencia: No se pudo configurar el alias 'board-ready' de gh" >&2
        err=true
    fi

    if [ "${err}" = false ]; then
        echo "==> [link] Aliases de gh configurados con éxito."
    fi
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
    setup_gh_aliases
}

# ------------------------------------------------------------------------------
# Restauración de Respaldos (Rollback)
# ------------------------------------------------------------------------------

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
    local target_arg="${1:-all}"
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

# ------------------------------------------------------------------------------
# Reconciliación y Ratificación Post-Merge de ADRs (cmd_reconcile)
# ------------------------------------------------------------------------------

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
    local core_broken_links=0
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

        # Verificación de presupuesto modular (ADR-0013)
        local w
        w="$(wc -w < "$f" | tr -d ' ')"
        if [ "${w}" -gt "${MAX_MODULE_WORDS}" ]; then
            echo "  [!] Advertencia: core/${fname} supera el umbral modular (${w} > ${MAX_MODULE_WORDS} palabras). Evaluar extracción a skill (ADR-0013)" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
        fi

        # Verificación de integridad de enlaces relativos en Markdown (ADR-0038)
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
                    echo "  [✗] Enlace roto en core/${fname}: ${broken_target}" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    core_broken_links=$((core_broken_links + 1))
                done <<< "${broken_list}"
            fi
        fi
    done

    if [ "${core_broken_links}" -eq 0 ]; then
        echo "  [✓] Directivas Core: Enlaces relativos verificados"
    fi

    # Verificación de indexación de módulos en core/00-router.md (ADR-0038)
    local router_file="${CORE_DIR}/00-router.md"
    if [ -f "${router_file}" ]; then
        local unindexed_modules=0
        for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
            local fname
            fname="$(basename "$f")"
            [[ "${fname}" == "00-router.md" || "${fname}" == "01-objectivity.md" ]] && continue
            if ! grep -Fq "core/${fname}" "${router_file}"; then
                echo "  [✗] Módulo core/${fname} no está indexado en core/00-router.md" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
                unindexed_modules=$((unindexed_modules + 1))
            fi
        done
        if [ "${unindexed_modules}" -eq 0 ]; then
            echo "  [✓] Router de Progressive Disclosure: Todos los módulos core están indexados"
        fi
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

        for skill_name in "${enabled_skills[@]}"; do
            [ -z "${skill_name}" ] && continue
            local skill_dir
            skill_dir="$(resolve_skill_dir "${skill_name}")"
            local script_path="${skill_dir}/scripts/${src_name}.sh"
            local bin_path="${skill_dir}/bin/${src_name}"
            if [ -f "${script_path}" ] || [ -f "${bin_path}" ]; then
                found=true
                break
            fi
        done

        if [ "${found}" = false ]; then
            echo "  [!] Advertencia [${r}]: Alias de binario '${src_name}' en config.json no coincide con ningún script o binario en los skills habilitados" >&2
            CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
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
            if [ ! -e "${target_bin}" ] && [ ! -L "${target_bin}" ]; then
                echo "  [!] Advertencia [${r}]: Binario de skill '${bin_name}' no está enlazado en ~/.local/bin/${bin_name} (ejecuta './build.sh skills ${r}')" >&2
                CHECK_WARNINGS=$((CHECK_WARNINGS + 1))
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
        local max_w="${MAX_CONTEXT_WORDS:-800}"
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
        if command -v python3 >/dev/null 2>&1; then
            local mod_err
            if ! mod_err=$(python3 -c '
import json, sys
mpath, spath = sys.argv[1], sys.argv[2]
try:
    with open(mpath, "r", encoding="utf-8") as f:
        mod = json.load(f)
    with open(spath, "r", encoding="utf-8") as f:
        schema = json.load(f)
except Exception as e:
    print(f"Error JSON: {e}")
    sys.exit(1)
for req in schema.get("required", []):
    if req not in mod:
        print(f"Error: falta propiedad requerida '\''{req}'\''")
        sys.exit(1)
' "${mconfig}" "${MODULE_SCHEMA_FILE}" 2>&1); then
                echo "  [✗] Validación de esquema fallida en ${mconfig}: ${mod_err}" >&2
                CHECK_ERRORS=$((CHECK_ERRORS + 1))
            fi
        fi

        local template_dir="${mdir}/template"
        if [ -d "${template_dir}" ]; then
            for jf in $(find "${template_dir}" -name "*.json" 2>/dev/null); do
                if command -v python3 >/dev/null 2>&1; then
                    if ! python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "${jf}" >/dev/null 2>&1; then
                        echo "  [✗] Error de sintaxis JSON en plantilla: ${jf}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    fi
                fi
            done
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

cmd_workspace() {
    local module_name="${1:-}"
    local target_dir="${2:-}"
    local runtime_filter="${3:-all}"

    if [ -z "${module_name}" ] || [ -z "${target_dir}" ]; then
        echo "Uso: $0 workspace <nombre-modulo> <ruta-directorio-destino> [runtime]" >&2
        echo "Ejemplo: $0 workspace eso /ruta/a/mi-addon" >&2
        return 1
    fi

    local module_dir="${MODULES_DIR}/${module_name}"
    if [ ! -d "${module_dir}" ]; then
        echo "Error: Módulo de dominio '${module_name}' no existe en ${MODULES_DIR}" >&2
        return 1
    fi

    local template_dir="${module_dir}/template"
    if [ ! -d "${template_dir}" ]; then
        echo "Error: Módulo '${module_name}' no contiene directorio de plantillas en ${template_dir}" >&2
        return 1
    fi

    mkdir -p "${target_dir}"
    echo "==> [workspace] Aprovisionando módulo '${module_name}' en ${target_dir}..."

    if [ -d "${template_dir}/.agents" ] && [ "${runtime_filter}" != "claude" ]; then
        mkdir -p "${target_dir}/.agents"
        cp -rn "${template_dir}/.agents/"* "${target_dir}/.agents/" 2>/dev/null || cp -r "${template_dir}/.agents/"* "${target_dir}/.agents/"
        echo "  [+] [antigravity] Configuración de plugin copiada a ${target_dir}/.agents/plugins/"
    fi

    if [ -f "${template_dir}/.mcp.json" ] && [ "${runtime_filter}" != "antigravity" ]; then
        if [ ! -f "${target_dir}/.mcp.json" ]; then
            cp "${template_dir}/.mcp.json" "${target_dir}/.mcp.json"
            echo "  [+] [claude] Configuración MCP copiada a ${target_dir}/.mcp.json"
        else
            echo "  [-] [claude] .mcp.json ya existe en destino; se conserva archivo preexistente."
        fi
    fi

    echo "==> [workspace] Aprovisionamiento completado con éxito en ${target_dir}."
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

    # Verificación de pureza de perfil global
    check_global_mcp_purity

    # Verificación de módulos de dominio y plantillas de workspace
    check_domain_modules

    # Verificación de documentación técnica (README y enlaces a docs/)
    check_documentation

    # Verificación de suite de pruebas unitarias
    check_unit_tests

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
        rollback)
            cmd_rollback "${RUNTIME_ARG}"
            ;;
        check)
            cmd_check "${RUNTIME_ARG}"
            ;;
        reconcile)
            cmd_reconcile "${RUNTIME_ARG}"
            ;;
        workspace)
            cmd_workspace "${2:-}" "${3:-}" "${4:-all}"
            ;;
        all)
            cmd_all "${RUNTIME_ARG}"
            ;;
        *)
            echo "Uso: $0 {build|link|skills|mcp|status|rollback|check|reconcile|workspace|all} [args...]" >&2
            exit 1
            ;;
    esac
fi
