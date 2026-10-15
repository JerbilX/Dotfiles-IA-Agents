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
            echo "  [!] Advertencia: No se encontró el origen '${skill_name}' en ${AGY_SKILLS_PATH}"
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

    if [ ! -d "${AGY_SKILLS_PATH}" ]; then
        echo "  [✗] Directorio de origen de skills no encontrado: ${AGY_SKILLS_PATH}" >&2
        errors=$((errors + 1))
    else
        local skills_ok=true
        local count_skills=0
        for skill_name in "${enabled_skills[@]}"; do
            [ -z "${skill_name}" ] && continue
            count_skills=$((count_skills + 1))
            local skill_dir="${AGY_SKILLS_PATH}/${skill_name}"
            if [ ! -d "${skill_dir}" ]; then
                echo "  [✗] Skill habilitado '${skill_name}' no existe en ${AGY_SKILLS_PATH}" >&2
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
            echo "  [✓] Skills en disco: ${count_skills} habilitados y verificados en ${AGY_SKILLS_PATH}"
        fi
    fi

    # 3. Verificación de binarios de skills
    local count_scripts=0
    local bin_scripts_ok=true
    for skill_name in "${enabled_skills[@]}"; do
        [ -z "${skill_name}" ] && continue
        local skill_scripts_dir="${AGY_SKILLS_PATH}/${skill_name}/scripts"
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
            local script_path="${AGY_SKILLS_PATH}/${skill_name}/scripts/${src_name}.sh"
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

    # 4. Verificación de colisiones de directivas
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

    # 5. Integridad de enlaces simbólicos (solo lectura)
    local symlink_error=false

    # 5a. TARGET_FILE (~/.gemini/config/AGENTS.md)
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

    # 5b. Symlinks en GEMINI_SKILLS_DIR (~/.gemini/config/skills)
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

    # 5c. Symlinks en ~/.local/bin gobernados por este repositorio
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

    if [ "${symlink_error}" = false ]; then
        echo "  [✓] Integridad de symlinks: Sin enlaces rotos detectados"
    fi

    # 6. Presupuesto de contexto
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
            echo "Uso: $0 {build|link|skills|status|check|all}" >&2
            exit 1
            ;;
    esac
fi
