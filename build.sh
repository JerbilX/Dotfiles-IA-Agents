#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${SCRIPT_DIR}/core"
RUNTIMES_DIR="${SCRIPT_DIR}/runtimes/antigravity"
RULES_DIR="${RUNTIMES_DIR}/rules"
MCP_DIR="${RUNTIMES_DIR}/mcp"
DIST_DIR="${SCRIPT_DIR}/dist/antigravity"
DIST_FILE="${DIST_DIR}/AGENTS.md"
DIST_MCP_FILE="${DIST_DIR}/mcp_config.json"
TARGET_DIR="${HOME}/.gemini/config"
TARGET_FILE="${TARGET_DIR}/AGENTS.md"
TARGET_MCP_FILE="${TARGET_DIR}/mcp_config.json"
SCHEMA_FILE="${SCRIPT_DIR}/runtimes/schema/runtime-config.schema.json"
MCP_SCHEMA_FILE="${SCRIPT_DIR}/runtimes/schema/mcp-server.schema.json"
GEMINI_SKILLS_DIR="${HOME}/.gemini/config/skills"
CONFIG_FILE="${RUNTIMES_DIR}/config.json"
AGY_SKILLS_PATH="${AGY_SKILLS_PATH:-"${SCRIPT_DIR}/../AGY-Skills/skills"}"
MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-4000}"

cmd_build() {
    echo "==> [build] Compilando directivas en ${DIST_FILE}..."
    mkdir -p "${DIST_DIR}"

    local tmp_file
    tmp_file="$(mktemp "${DIST_DIR}/.agents.tmp.XXXXXX")"

    cat << 'EOF' > "${tmp_file}"
<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Components: core/*.md, runtimes/antigravity/rules/*.md
  =============================================================================
-->

EOF

    local first=true
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        if [ "$first" = false ]; then
            printf "\n\n" >> "${tmp_file}"
        fi
        cat "$f" >> "${tmp_file}"
        first=false
    done

    if [ -d "${RULES_DIR}" ]; then
        for f in $(find "${RULES_DIR}" -maxdepth 1 -name "*.md" | sort); do
            if [ "$first" = false ]; then
                printf "\n\n" >> "${tmp_file}"
            fi
            cat "$f" >> "${tmp_file}"
            first=false
        done
    fi

    printf "\n" >> "${tmp_file}"
    mv -f "${tmp_file}" "${DIST_FILE}"
    echo "==> [build] Compilación finalizada con éxito: ${DIST_FILE}"

    # Telemetría de presupuesto de contexto
    local lines words bytes approx_tokens size_kb
    lines="$(wc -l < "${DIST_FILE}" | tr -d ' ')"
    words="$(wc -w < "${DIST_FILE}" | tr -d ' ')"
    bytes="$(wc -c < "${DIST_FILE}" | tr -d ' ')"
    approx_tokens=$(( (words * 4 + 2) / 3 ))
    size_kb="$(awk "BEGIN {printf \"%.1f\", ${bytes}/1024}")"

    echo "==> [build] Telemetría de contexto: ${lines} líneas | ${words} palabras | ~${approx_tokens} tokens estimados (${size_kb} KB)"
    if [ "${words}" -gt "${MAX_CONTEXT_WORDS}" ]; then
        echo "  [!] Advertencia: El contexto compilado supera el límite recomendado (${words} > ${MAX_CONTEXT_WORDS} palabras)." >&2
        echo "      Considera modularizar directivas extensas hacia skills bajo demanda." >&2
    fi

    # Compilación modular de configuración MCP
    compile_mcp_config
}

cmd_link() {
    echo "==> [link] Asegurando directorio destino: ${TARGET_DIR}..."
    mkdir -p "${TARGET_DIR}"

    if [ ! -f "${DIST_FILE}" ]; then
        echo "Error: ${DIST_FILE} no existe. Ejecuta './build.sh build' primero." >&2
        exit 1
    fi

    if [ -e "${TARGET_FILE}" ] || [ -L "${TARGET_FILE}" ]; then
        local current_target=""
        if [ -L "${TARGET_FILE}" ]; then
            current_target="$(readlink "${TARGET_FILE}" || true)"
        fi

        if [ "${current_target}" = "${DIST_FILE}" ]; then
            echo "==> [link] El symlink ya apunta correctamente a ${DIST_FILE}."
        else
            local timestamp
            timestamp="$(date +%Y%m%d_%H%M%S)"
            echo "==> [link] Respaldando archivo/symlink preexistente en ${TARGET_FILE}.bak.${timestamp}..."
            mv "${TARGET_FILE}" "${TARGET_FILE}.bak.${timestamp}"
            echo "==> [link] Creando symlink atómico: ${TARGET_FILE} -> ${DIST_FILE}..."
            ln -sfn "${DIST_FILE}" "${TARGET_FILE}"
            echo "==> [link] Symlink establecido exitosamente."
        fi
    else
        echo "==> [link] Creando symlink atómico: ${TARGET_FILE} -> ${DIST_FILE}..."
        ln -sfn "${DIST_FILE}" "${TARGET_FILE}"
        echo "==> [link] Symlink establecido exitosamente."
    fi

    # Enlace de configuración de servidores MCP
    link_mcp
}

cmd_status() {
    echo "==> [status] Inspeccionando ${TARGET_FILE}:"
    if [ -L "${TARGET_FILE}" ]; then
        local target
        target="$(readlink "${TARGET_FILE}")"
        echo "Tipo: Enlace simbólico (symlink)"
        echo "Apunta a: ${target}"
        if [ -e "${TARGET_FILE}" ]; then
            echo "Estado: VÁLIDO (el destino existe)"
        else
            echo "Estado: ROTO (el archivo destino no existe)"
        fi
    elif [ -e "${TARGET_FILE}" ]; then
        echo "Tipo: Archivo regular / directorio preexistente (NO es symlink)"
        echo "Estado: Requiere ejecución de './build.sh link' para migrar al symlink"
    else
        echo "Tipo: Inexistente"
        echo "Estado: No configurado. Ejecuta './build.sh link'"
    fi

    echo ""
    status_mcp
}

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
    local local_dir="${SCRIPT_DIR}/skills/${skill_name}"
    local remote_dir="${AGY_SKILLS_PATH}/${skill_name}"

    if [[ -d "${local_dir}" ]]; then
        echo "${local_dir}"
    elif [[ -d "${remote_dir}" ]]; then
        echo "${remote_dir}"
    else
        echo "${local_dir}"
    fi
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

compile_mcp_config() {
    echo "==> [build] Compilando configuración MCP en ${DIST_MCP_FILE}..."
    mkdir -p "${DIST_DIR}"

    local enabled_mcps=()
    mapfile -t enabled_mcps < <(get_enabled_mcp_servers "${CONFIG_FILE}")

    if [ ${#enabled_mcps[@]} -eq 0 ]; then
        echo '{"mcpServers":{}}' > "${DIST_MCP_FILE}"
        echo "==> [build] Configuración MCP compilada (0 servidores habilitados): ${DIST_MCP_FILE}"
        return 0
    fi

    # Validar que cada módulo habilitado exista en MCP_DIR y cumpla el esquema
    for s_name in "${enabled_mcps[@]}"; do
        [ -z "${s_name}" ] && continue
        local s_path="${MCP_DIR}/${s_name}.json"
        if [ ! -f "${s_path}" ]; then
            echo "Error: Módulo de servidor MCP '${s_name}' declarado en config.json no existe en ${s_path}" >&2
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
' "${CONFIG_FILE}" "${MCP_DIR}" "${DIST_MCP_FILE}"
    else
        echo "Error: Se requiere python3 para compilar la configuración de MCP." >&2
        return 1
    fi

    local server_count
    server_count=$(get_enabled_mcp_servers "${CONFIG_FILE}" | grep -c . || true)
    echo "==> [build] Configuración MCP compilada con éxito: ${DIST_MCP_FILE} (${server_count} servidor(es))"
}

link_mcp() {
    echo "==> [link] Asegurando enlace simbólico para MCP en ${TARGET_DIR}..."
    mkdir -p "${TARGET_DIR}"

    if [ ! -f "${DIST_MCP_FILE}" ]; then
        echo "Error: ${DIST_MCP_FILE} no existe. Ejecuta './build.sh build' primero." >&2
        return 1
    fi

    if [ -e "${TARGET_MCP_FILE}" ] || [ -L "${TARGET_MCP_FILE}" ]; then
        local current_target=""
        if [ -L "${TARGET_MCP_FILE}" ]; then
            current_target="$(readlink "${TARGET_MCP_FILE}" || true)"
        fi

        if [ "${current_target}" = "${DIST_MCP_FILE}" ]; then
            echo "==> [link] El symlink MCP ya apunta correctamente a ${DIST_MCP_FILE}."
            return 0
        fi

        local timestamp
        timestamp="$(date +%Y%m%d_%H%M%S)"
        echo "==> [link] Respaldando archivo/symlink MCP preexistente en ${TARGET_MCP_FILE}.bak.${timestamp}..."
        mv "${TARGET_MCP_FILE}" "${TARGET_MCP_FILE}.bak.${timestamp}"
    fi

    echo "==> [link] Creando symlink atómico: ${TARGET_MCP_FILE} -> ${DIST_MCP_FILE}..."
    ln -sfn "${DIST_MCP_FILE}" "${TARGET_MCP_FILE}"
    echo "==> [link] Symlink MCP establecido exitosamente."
}

status_mcp() {
    echo "==> [status] Inspeccionando ${TARGET_MCP_FILE}:"
    if [ -L "${TARGET_MCP_FILE}" ]; then
        local target
        target="$(readlink "${TARGET_MCP_FILE}")"
        echo "Tipo: Enlace simbólico (symlink)"
        echo "Apunta a: ${target}"
        if [ -e "${TARGET_MCP_FILE}" ]; then
            echo "Estado: VÁLIDO (el destino existe)"
        else
            echo "Estado: ROTO (el archivo destino no existe)"
        fi
    elif [ -e "${TARGET_MCP_FILE}" ]; then
        echo "Tipo: Archivo regular / directorio preexistente (NO es symlink)"
        echo "Estado: Requiere ejecución de './build.sh link' para migrar al symlink"
    else
        echo "Tipo: Inexistente"
        echo "Estado: No configurado. Ejecuta './build.sh link' o './build.sh mcp'"
    fi
}

cmd_mcp() {
    echo "==> [mcp] Aprovisionando servidores MCP de Antigravity..."
    compile_mcp_config
    link_mcp
    status_mcp
}

cmd_skills() {
    echo "==> [skills] Provisionando entorno de skills de Antigravity..."

    # Garantizar directorios base
    mkdir -p "${GEMINI_SKILLS_DIR}"
    mkdir -p "${HOME}/.local/bin" 2>/dev/null || true

    # 1. Validar configuración contra esquema
    validate_config "${CONFIG_FILE}" "${SCHEMA_FILE}" "skills" || exit 1

    # 2. Purgar symlinks previos en el entorno de ejecución (Idempotencia)
    find "${GEMINI_SKILLS_DIR}" -maxdepth 1 -type l -delete

    # 3. Leer configuración estructurada (skills) y aprovisionar
    local enabled_skills=()
    mapfile -t enabled_skills < <(get_enabled_skills "${CONFIG_FILE}")

    for skill_name in "${enabled_skills[@]}"; do
        [[ -z "${skill_name}" ]] && continue
        local target_dir
        target_dir="$(resolve_skill_dir "${skill_name}")"
        target_dir="$(realpath -m "${target_dir}")"
        
        if [[ -d "${target_dir}" ]]; then
            # Habilitar el skill
            ln -sfn "${target_dir}" "${GEMINI_SKILLS_DIR}/${skill_name}"
            echo "  [+] Skill habilitado: ${skill_name}"
            
            # (Opcional) Aprovisionamiento dinámico de binarios del skill
            if [[ -d "${target_dir}/scripts" ]]; then
                for script in "${target_dir}/scripts/"*.sh; do
                    if [[ -f "${script}" && -x "${script}" ]]; then
                        local bin_name
                        bin_name=$(basename "${script}" .sh)
                        
                        # Consultar mapeo declarativo opcional de binarios
                        local bin_alias
                        bin_alias="$(get_binary_alias "${CONFIG_FILE}" "${bin_name}")"

                        if [[ -n "${bin_alias}" ]]; then
                            bin_name="${bin_alias}"
                        fi
                        
                        ln -sfn "${script}" "${HOME}/.local/bin/${bin_name}"
                        echo "      -> Binario expuesto en PATH: ~/.local/bin/${bin_name}"
                    fi
                done
            fi
        else
            echo "  [!] Advertencia: No se encontró el origen '${skill_name}' en ${SCRIPT_DIR}/skills ni en ${AGY_SKILLS_PATH}"
        fi
    done
    echo "==> [skills] Provisionamiento finalizado."
}

cmd_check() {
    echo "==> [check] Ejecutando verificaciones estáticas (read-only)..."
    local errors=0
    local warnings=0

    # 1. Validación de esquema y sintaxis de configuración
    if ! validate_config "${CONFIG_FILE}" "${SCHEMA_FILE}" "check"; then
        echo "  [✗] Fallo en la validación de ${CONFIG_FILE}" >&2
        errors=$((errors + 1))
    else
        echo "  [✓] Esquema y sintaxis válidos: ${CONFIG_FILE}"
    fi

    # 2. Verificación de existencia de skills en disco
    local enabled_skills=()
    mapfile -t enabled_skills < <(get_enabled_skills "${CONFIG_FILE}")

    local skills_ok=true
    local count_skills=0
    for skill_name in "${enabled_skills[@]}"; do
        [ -z "${skill_name}" ] && continue
        count_skills=$((count_skills + 1))
        local skill_dir
        skill_dir="$(resolve_skill_dir "${skill_name}")"
        if [ ! -d "${skill_dir}" ]; then
            echo "  [✗] Skill habilitado '${skill_name}' no existe en ${SCRIPT_DIR}/skills ni en ${AGY_SKILLS_PATH}" >&2
            skills_ok=false
            errors=$((errors + 1))
        else
            if [ ! -f "${skill_dir}/SKILL.md" ]; then
                echo "  [!] Advertencia: Skill '${skill_name}' no contiene SKILL.md" >&2
                warnings=$((warnings + 1))
            fi
        fi
    done
    if [ "${skills_ok}" = true ]; then
        echo "  [✓] Skills en disco: ${count_skills} habilitados y verificados"
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
                    echo "  [✗] Script de skill '${script}' no tiene permisos de ejecución (+x)" >&2
                    bin_scripts_ok=false
                    errors=$((errors + 1))
                fi
            done
        fi
    done

    local declared_binaries=()
    mapfile -t declared_binaries < <(get_declared_binaries "${CONFIG_FILE}")
    local count_bin=0
    for bin_entry in "${declared_binaries[@]}"; do
        [ -z "${bin_entry}" ] && continue
        count_bin=$((count_bin + 1))
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
            echo "  [!] Advertencia: Alias de binario '${src_name}' en config.json no coincide con ningún script en los skills habilitados" >&2
            warnings=$((warnings + 1))
        fi
    done

    if [ "${bin_scripts_ok}" = true ]; then
        if [ "${count_scripts}" -gt 0 ]; then
            echo "  [✓] Binarios de skills: ${count_scripts} script(s) verificado(s) con permisos de ejecución"
        else
            echo "  [✓] Binarios de skills: 0 scripts encontrados en skills habilitados"
        fi
    fi

    # 4. Verificación de servidores MCP
    local enabled_mcps=()
    mapfile -t enabled_mcps < <(get_enabled_mcp_servers "${CONFIG_FILE}")
    local count_mcps=0
    local mcps_ok=true

    for s_name in "${enabled_mcps[@]}"; do
        [ -z "${s_name}" ] && continue
        count_mcps=$((count_mcps + 1))
        local s_path="${MCP_DIR}/${s_name}.json"
        if [ ! -f "${s_path}" ]; then
            echo "  [✗] Servidor MCP habilitado '${s_name}' no existe en ${MCP_DIR}" >&2
            mcps_ok=false
            errors=$((errors + 1))
        else
            if ! validate_mcp_server "${s_path}" "${MCP_SCHEMA_FILE}" "check"; then
                echo "  [✗] Esquema o sintaxis inválida en módulo MCP '${s_name}'" >&2
                mcps_ok=false
                errors=$((errors + 1))
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
                            echo "  [!] Advertencia: Ejecutable MCP '${expanded_cmd}' del servidor '${s_name}' no existe en disco" >&2
                            warnings=$((warnings + 1))
                        elif [ ! -x "${expanded_cmd}" ]; then
                            echo "  [✗] Ejecutable MCP '${expanded_cmd}' del servidor '${s_name}' no tiene permisos de ejecución (+x)" >&2
                            mcps_ok=false
                            errors=$((errors + 1))
                        fi
                    else
                        if ! command -v "${cmd}" >/dev/null 2>&1; then
                            echo "  [!] Advertencia: Comando MCP '${cmd}' del servidor '${s_name}' no encontrado en \$PATH" >&2
                            warnings=$((warnings + 1))
                        fi
                    fi
                fi
            fi
        fi
    done

    if [ "${mcps_ok}" = true ]; then
        if [ "${count_mcps}" -gt 0 ]; then
            echo "  [✓] Servidores MCP: ${count_mcps} módulo(s) verificado(s) contra esquema"
        else
            echo "  [✓] Servidores MCP: 0 servidores habilitados"
        fi
    fi

    # 5. Verificación de colisiones de directivas
    local collision_error=false

    # 4a. Prefijos numéricos intra-directorio en CORE_DIR
    local seen_core_prefixes=()
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        local fname
        fname="$(basename "$f")"
        if [[ "${fname}" =~ ^([0-9]+)- ]]; then
            local pfx="${BASH_REMATCH[1]}"
            if printf '%s\n' "${seen_core_prefixes[@]}" | grep -qx "${pfx}"; then
                echo "  [✗] Colisión de prefijo '${pfx}-' detectada en core/: ${fname}" >&2
                collision_error=true
                errors=$((errors + 1))
            else
                seen_core_prefixes+=("${pfx}")
            fi
        else
            echo "  [!] Advertencia: Archivo ${fname} en core/ no sigue el patrón numérico 'NN-*.md'" >&2
            warnings=$((warnings + 1))
        fi
    done

    # 4b. Prefijos numéricos intra-directorio en RULES_DIR
    if [ -d "${RULES_DIR}" ]; then
        local seen_rules_prefixes=()
        for f in $(find "${RULES_DIR}" -maxdepth 1 -name "*.md" | sort); do
            local fname
            fname="$(basename "$f")"
            if [[ "${fname}" =~ ^([0-9]+)- ]]; then
                local pfx="${BASH_REMATCH[1]}"
                if printf '%s\n' "${seen_rules_prefixes[@]}" | grep -qx "${pfx}"; then
                    echo "  [✗] Colisión de prefijo '${pfx}-' detectada en rules/: ${fname}" >&2
                    collision_error=true
                    errors=$((errors + 1))
                else
                    seen_rules_prefixes+=("${pfx}")
                fi
            else
                echo "  [!] Advertencia: Archivo ${fname} en rules/ no sigue el patrón numérico 'NN-*.md'" >&2
                warnings=$((warnings + 1))
            fi
        done
    fi

    # 4c. Títulos Markdown H1 únicos a través de todo el set compilado
    local seen_h1=()
    local all_files=()
    for f in $(find "${CORE_DIR}" -maxdepth 1 -name "*.md" | sort); do
        all_files+=("$f")
    done
    if [ -d "${RULES_DIR}" ]; then
        for f in $(find "${RULES_DIR}" -maxdepth 1 -name "*.md" | sort); do
            all_files+=("$f")
        done
    fi

    for f in "${all_files[@]}"; do
        while IFS= read -r line; do
            local title="${line#\# }"
            if printf '%s\n' "${seen_h1[@]}" | grep -Fxq "${title}"; then
                echo "  [✗] Título H1 duplicado detectado: '# ${title}' en $(basename "$f")" >&2
                collision_error=true
                errors=$((errors + 1))
            else
                seen_h1+=("${title}")
            fi
        done < <(grep "^# " "$f" || true)
    done

    if [ "${collision_error}" = false ]; then
        echo "  [✓] Ausencia de colisiones: Prefijos numéricos intra-directorio y títulos H1 únicos"
    fi

    # 6. Integridad de enlaces simbólicos (solo lectura)
    local symlink_error=false

    # 6a. TARGET_FILE (~/.gemini/config/AGENTS.md)
    if [ -L "${TARGET_FILE}" ]; then
        if [ ! -e "${TARGET_FILE}" ]; then
            echo "  [✗] Symlink roto: ${TARGET_FILE} -> $(readlink "${TARGET_FILE}" || true)" >&2
            symlink_error=true
            errors=$((errors + 1))
        fi
    elif [ ! -e "${TARGET_FILE}" ]; then
        echo "  [!] Advertencia: ${TARGET_FILE} no existe aún (ejecuta './build.sh link')" >&2
        warnings=$((warnings + 1))
    fi

    # 6b. Symlinks en GEMINI_SKILLS_DIR (~/.gemini/config/skills)
    if [ -d "${GEMINI_SKILLS_DIR}" ]; then
        for item in "${GEMINI_SKILLS_DIR}"/*; do
            [ ! -e "${item}" ] && [ ! -L "${item}" ] && continue
            if [ -L "${item}" ]; then
                if [ ! -e "${item}" ]; then
                    echo "  [✗] Symlink roto en skills: ${item} -> $(readlink "${item}" || true)" >&2
                    symlink_error=true
                    errors=$((errors + 1))
                fi
            fi
        done
    fi

    # 6c. Symlinks en ~/.local/bin gobernados por este repositorio
    if [ -d "${HOME}/.local/bin" ]; then
        for item in "${HOME}/.local/bin"/*; do
            [ ! -e "${item}" ] && [ ! -L "${item}" ] && continue
            if [ -L "${item}" ]; then
                local link_target
                link_target="$(readlink "${item}" || true)"
                # Solo verificar si apunta a SCRIPT_DIR o AGY_SKILLS_PATH
                if [[ "${link_target}" == "${SCRIPT_DIR}"* ]] || [[ "${link_target}" == "${AGY_SKILLS_PATH}"* ]]; then
                    if [ ! -e "${item}" ]; then
                        echo "  [✗] Symlink roto en ~/.local/bin: ${item} -> ${link_target}" >&2
                        symlink_error=true
                        errors=$((errors + 1))
                    fi
                fi
            fi
        done
    fi

    # 6d. TARGET_MCP_FILE (~/.gemini/config/mcp_config.json)
    if [ -L "${TARGET_MCP_FILE}" ]; then
        if [ ! -e "${TARGET_MCP_FILE}" ]; then
            echo "  [✗] Symlink roto en MCP: ${TARGET_MCP_FILE} -> $(readlink "${TARGET_MCP_FILE}" || true)" >&2
            symlink_error=true
            errors=$((errors + 1))
        fi
    elif [ ! -e "${TARGET_MCP_FILE}" ]; then
        if [ "${count_mcps}" -gt 0 ]; then
            echo "  [!] Advertencia: ${TARGET_MCP_FILE} no existe aún (ejecuta './build.sh link' o './build.sh mcp')" >&2
            warnings=$((warnings + 1))
        fi
    fi

    if [ "${symlink_error}" = false ]; then
        echo "  [✓] Integridad de symlinks: Sin enlaces rotos detectados"
    fi

    # 7. Presupuesto de contexto
    if [ -f "${DIST_FILE}" ]; then
        local w
        w="$(wc -w < "${DIST_FILE}" | tr -d ' ')"
        local max_w="${MAX_CONTEXT_WORDS:-4000}"
        local pct=$(( w * 100 / max_w ))
        if [ "${w}" -gt "${max_w}" ]; then
            echo "  [!] Advertencia: Presupuesto de contexto superado: ${w} / ${max_w} palabras (${pct}%)" >&2
            warnings=$((warnings + 1))
        else
            echo "  [✓] Presupuesto de contexto: ${w} / ${max_w} palabras (${pct}%)"
        fi
    else
        echo "  [!] Advertencia: ${DIST_FILE} no ha sido compilado aún (ejecuta './build.sh build')" >&2
        warnings=$((warnings + 1))
    fi

    echo "==> [check] Verificación completada: ${errors} error(es), ${warnings} advertencia(s)."
    if [ "${errors}" -gt 0 ]; then
        return 1
    fi
    return 0
}

cmd_all() {
    cmd_build
    cmd_link
    cmd_skills
    cmd_status
    echo ""
    cmd_check
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    COMMAND="${1:-all}"

    case "${COMMAND}" in
        build)
            cmd_build
            ;;
        link)
            cmd_link
            ;;
        skills)
            cmd_skills
            ;;
        mcp)
            cmd_mcp
            ;;
        status)
            cmd_status
            ;;
        check)
            cmd_check
            ;;
        all)
            cmd_all
            ;;
        *)
            echo "Uso: $0 {build|link|skills|mcp|status|check|all}" >&2
            exit 1
            ;;
    esac
fi
