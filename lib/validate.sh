#!/usr/bin/env bash
# lib/validate.sh - Validaciones de esquema y configuración delegando a lib/validate.py

VALIDATE_PY="${SCRIPT_DIR}/lib/validate.py"

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
    if command -v python3 >/dev/null 2>&1 && [ -f "${VALIDATE_PY}" ]; then
        if ! python3 "${VALIDATE_PY}" "${config_file}" "${schema_file}"; then
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
        if jq -e 'has("status") and (.status != "active" and .status != "on-demand" and .status != "disabled")' "${config_file}" >/dev/null 2>&1; then
            echo "Error de validación: 'status' debe ser 'active', 'on-demand' o 'disabled'." >&2
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

    if command -v python3 >/dev/null 2>&1 && [ -f "${VALIDATE_PY}" ]; then
        if ! python3 "${VALIDATE_PY}" "${mcp_file}" "${schema_file}"; then
            return 1
        fi
    elif command -v jq >/dev/null 2>&1; then
        if ! jq empty "${mcp_file}" >/dev/null 2>&1; then
            echo "Error de sintaxis JSON en ${mcp_file}" >&2
            return 1
        fi
    fi
}

validate_module_config() {
    local module_file="$1"
    local schema_file="$2"

    if [[ ! -f "${module_file}" ]]; then
        echo "Error: Archivo de módulo no encontrado en ${module_file}" >&2
        return 1
    fi

    if [[ ! -f "${schema_file}" ]]; then
        echo "Error: Esquema no encontrado en ${schema_file}" >&2
        return 1
    fi

    if command -v python3 >/dev/null 2>&1 && [ -f "${VALIDATE_PY}" ]; then
        python3 "${VALIDATE_PY}" "${module_file}" "${schema_file}"
        return $?
    elif command -v jq >/dev/null 2>&1; then
        jq empty "${module_file}" >/dev/null 2>&1
        return $?
    fi
    return 0
}
