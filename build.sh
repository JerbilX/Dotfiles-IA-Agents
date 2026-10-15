#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${SCRIPT_DIR}/core"
RUNTIMES_DIR="${SCRIPT_DIR}/runtimes/antigravity"
RULES_DIR="${RUNTIMES_DIR}/rules"
DIST_DIR="${SCRIPT_DIR}/dist/antigravity"
DIST_FILE="${DIST_DIR}/AGENTS.md"
TARGET_DIR="${HOME}/.gemini/config"
TARGET_FILE="${TARGET_DIR}/AGENTS.md"
SCHEMA_FILE="${SCRIPT_DIR}/runtimes/schema/runtime-config.schema.json"

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
            return 0
        fi

        local timestamp
        timestamp="$(date +%Y%m%d_%H%M%S)"
        echo "==> [link] Respaldando archivo/symlink preexistente en ${TARGET_FILE}.bak.${timestamp}..."
        mv "${TARGET_FILE}" "${TARGET_FILE}.bak.${timestamp}"
    fi

    echo "==> [link] Creando symlink atómico: ${TARGET_FILE} -> ${DIST_FILE}..."
    ln -sfn "${DIST_FILE}" "${TARGET_FILE}"
    echo "==> [link] Symlink establecido exitosamente."
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
}

validate_config() {
    local config_file="$1"
    local schema_file="$2"

    if [[ ! -f "${config_file}" ]]; then
        echo "Error: Archivo de configuración no encontrado en ${config_file}" >&2
        exit 1
    fi

    if [[ ! -f "${schema_file}" ]]; then
        echo "Error: Archivo de esquema no encontrado en ${schema_file}" >&2
        exit 1
    fi

    echo "==> [skills] Validando ${config_file} contra ${schema_file}..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -c '
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
' "${config_file}" "${schema_file}"
    elif command -v jq >/dev/null 2>&1; then
        if ! jq empty "${config_file}" >/dev/null 2>&1; then
            echo "Error de sintaxis JSON en ${config_file}" >&2
            exit 1
        fi
        local has_skills
        has_skills=$(jq 'has("skills") and (.skills | type == "array")' "${config_file}")
        if [[ "${has_skills}" != "true" ]]; then
            echo "Error de validación: 'skills' es requerido y debe ser un array." >&2
            exit 1
        fi
    else
        echo "Error: Se requiere 'python3' o 'jq' para validar ${config_file}" >&2
        exit 1
    fi
}

cmd_skills() {
    echo "==> [skills] Provisionando entorno de skills de Antigravity..."
    local AGY_SKILLS_PATH="${AGY_SKILLS_PATH:-"${SCRIPT_DIR}/../AGY-Skills/skills"}"
    local GEMINI_SKILLS_DIR="${HOME}/.gemini/config/skills"
    local CONFIG_FILE="${RUNTIMES_DIR}/config.json"

    # Garantizar directorios base
    mkdir -p "${GEMINI_SKILLS_DIR}"
    mkdir -p "${HOME}/.local/bin" 2>/dev/null || true

    # 1. Validar configuración contra esquema
    validate_config "${CONFIG_FILE}" "${SCHEMA_FILE}"

    # 2. Purgar symlinks previos en el entorno de ejecución (Idempotencia)
    find "${GEMINI_SKILLS_DIR}" -maxdepth 1 -type l -delete

    # 3. Leer configuración estructurada (skills) y aprovisionar
    local enabled_skills=()
    if command -v jq >/dev/null 2>&1; then
        mapfile -t enabled_skills < <(jq -r '.skills[]?' "${CONFIG_FILE}")
    elif command -v python3 >/dev/null 2>&1; then
        mapfile -t enabled_skills < <(python3 -c "import json; [print(s) for s in json.load(open('${CONFIG_FILE}'))['skills']]")
    else
        echo "Error: Se requiere 'jq' o 'python3' para parsear ${CONFIG_FILE}" >&2
        exit 1
    fi

    for skill_name in "${enabled_skills[@]}"; do
        [[ -z "${skill_name}" ]] && continue
        local target_dir
        target_dir="$(realpath -m "${AGY_SKILLS_PATH}/${skill_name}")"
        
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
                        local bin_alias=""
                        if command -v jq >/dev/null 2>&1; then
                            bin_alias=$(jq -r --arg b "${bin_name}" '.binaries[$b] // empty' "${CONFIG_FILE}")
                        elif command -v python3 >/dev/null 2>&1; then
                            bin_alias=$(python3 -c "import json; print(json.load(open('${CONFIG_FILE}')).get('binaries', {}).get('${bin_name}', ''))")
                        fi

                        if [[ -n "${bin_alias}" ]]; then
                            bin_name="${bin_alias}"
                        fi
                        
                        ln -sfn "${script}" "${HOME}/.local/bin/${bin_name}"
                        echo "      -> Binario expuesto en PATH: ~/.local/bin/${bin_name}"
                    fi
                done
            fi
        else
            echo "  [!] Advertencia: No se encontró el origen '${skill_name}' en ${AGY_SKILLS_PATH}"
        fi
    done
    echo "==> [skills] Provisionamiento finalizado."
}

cmd_all() {
    cmd_build
    cmd_link
    cmd_skills
    cmd_status
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
        status)
            cmd_status
            ;;
        all)
            cmd_all
            ;;
        *)
            echo "Uso: $0 {build|link|skills|status|all}" >&2
            exit 1
            ;;
    esac
fi
