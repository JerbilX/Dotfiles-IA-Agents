#!/usr/bin/env bash
# lib/check.sh - Orquestador modular de auditoría estática, verificación y tests

CHECK_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Carga de módulos por dominio (Issue #307)
source "${CHECK_LIB_DIR}/check_rules.sh"
source "${CHECK_LIB_DIR}/check_runtime.sh"
source "${CHECK_LIB_DIR}/check_modules.sh"
source "${CHECK_LIB_DIR}/check_environment.sh"

cmd_check() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    local target_runtimes=()
    mapfile -t target_runtimes < <(resolve_target_runtimes "${target_arg}")
    CHECK_ERRORS=0
    CHECK_WARNINGS=0

    echo "==> [check] Ejecutando verificaciones estáticas (read-only)..."

    # Verificaciones comunes de directivas core
    check_core_rules
    check_basal_rules_admission
    check_prompt_tool_crossings

    # Verificación de pureza de perfil global (MCP y Skills)
    check_global_mcp_purity
    check_global_skills_purity

    # Verificación de módulos de dominio y plantillas de workspace
    check_domain_modules

    # Verificación de documentación técnica (README y enlaces a docs/)
    check_documentation

    # Verificación de esquemas para runtimes registrados no incluidos en target_runtimes
    for r_avail in $(get_available_runtimes); do
        local is_in_target=false
        for tr in "${target_runtimes[@]}"; do
            if [ "$tr" = "$r_avail" ]; then
                is_in_target=true
                break
            fi
        done
        if [ "$is_in_target" = false ]; then
            local cfg_avail
            cfg_avail="$(get_runtime_config_file "${r_avail}")"
            if [ -f "${cfg_avail}" ]; then
                echo "--- Auditoría de Esquema (bajo demanda): '${r_avail}' ---"
                if ! validate_config "${cfg_avail}" "${SCHEMA_FILE}" "check"; then
                    echo "  [✗] [${r_avail}] Fallo en la validación de ${cfg_avail}" >&2
                    CHECK_ERRORS=$((CHECK_ERRORS + 1))
                else
                    echo "  [✓] [${r_avail}] Esquema y sintaxis válidos: ${cfg_avail}"
                fi
            fi
        fi
    done

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

    # Verificación de guards P0 y blindaje mecánico
    check_p0_guards

    echo "==> [check] Verificación completada: ${CHECK_ERRORS} error(es), ${CHECK_WARNINGS} advertencia(s)."
    if [ "${CHECK_ERRORS}" -gt 0 ]; then
        return 1
    fi
    return 0
}

cmd_test() {
    local pattern="${1:-test_*.py}"
    local repo_root="${SCRIPT_DIR:-$(cd "${CHECK_LIB_DIR}/.." && pwd)}"
    local tests_dir="${repo_root}/tests"
    if [ ! -d "${tests_dir}" ]; then
        echo "  [✗] Error: Directorio de pruebas no encontrado: ${tests_dir}" >&2
        return 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "  [✗] Error: python3 no está disponible en el entorno" >&2
        return 1
    fi
    echo "==> [test] Ejecutando suite de pruebas unitarias (${pattern})..."
    python3 -m unittest discover -s "${tests_dir}" -p "${pattern}"
}
