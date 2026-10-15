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

cmd_skills() {
    echo "==> [skills] Provisionando entorno de skills de Antigravity..."
    local AGY_SKILLS_PATH="${AGY_SKILLS_PATH:-"${SCRIPT_DIR}/../AGY-Skills/skills"}"
    local GEMINI_SKILLS_DIR="${HOME}/.gemini/config/skills"
    local CONFIG_FILE="${RUNTIMES_DIR}/config.json"

    # Garantizar directorios base
    mkdir -p "${GEMINI_SKILLS_DIR}"
    mkdir -p "${HOME}/.local/bin"

    # 1. Purgar symlinks previos en el entorno de ejecución (Idempotencia)
    find "${GEMINI_SKILLS_DIR}" -maxdepth 1 -type l -delete

    # 2. Leer configuración estructurada (skills) y aprovisionar
    if [[ -f "${CONFIG_FILE}" ]]; then
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
                            # Sobreescribir nombre genérico por comando global de ecosistema
                            if [[ "${bin_name}" == "build_release" && "${skill_name}" == "eso-addon"* ]]; then
                                bin_name="eso-build"
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
    else
        echo "Error: Archivo de configuración no encontrado en ${CONFIG_FILE}" >&2
        exit 1
    fi
}

cmd_all() {
    cmd_build
    cmd_link
    cmd_skills
    cmd_status
}

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
