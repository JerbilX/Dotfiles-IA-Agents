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
MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-2000}"
TARGET_CONTEXT_WORDS="${TARGET_CONTEXT_WORDS:-1100}"
MAX_MODULE_WORDS="${MAX_MODULE_WORDS:-300}"
MAX_README_WORDS="${MAX_README_WORDS:-600}"

# ------------------------------------------------------------------------------
# Inclusión de Módulos de Soporte (lib/*.sh)
# ------------------------------------------------------------------------------

source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/validate.sh"
source "${SCRIPT_DIR}/lib/build_core.sh"
source "${SCRIPT_DIR}/lib/link.sh"
source "${SCRIPT_DIR}/lib/check.sh"

# ------------------------------------------------------------------------------
# Flujo Completo
# ------------------------------------------------------------------------------

cmd_all() {
    local target_arg="${1:-}"
    validate_runtime_arg "${target_arg}" || return 1
    cmd_build "${target_arg}"
    cmd_link "${target_arg}"
    cmd_status "${target_arg}"
    echo ""
    cmd_check "${target_arg}"
    echo ""
    cmd_test
}

# ------------------------------------------------------------------------------
# Punto de Entrada
# ------------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    COMMAND="${1:-all}"
    RUNTIME_ARG="${2:-}"

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
        test)
            cmd_test "${RUNTIME_ARG}"
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
            echo "Uso: $0 {build|link|skills|mcp|status|rollback|check|test|reconcile|workspace|all} [runtime|all]" >&2
            exit 1
            ;;
    esac
fi
