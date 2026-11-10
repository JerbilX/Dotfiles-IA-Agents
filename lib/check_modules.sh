#!/usr/bin/env bash
# lib/check_modules.sh - Verificación de módulos de dominio, pureza global y workspace

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
        if ! validate_module_config "${mconfig}" "${MODULE_SCHEMA_FILE}"; then
            echo "  [✗] Validación de esquema fallida en ${mconfig}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        fi

        local template_dir="${mdir}/template"
        if [ -d "${template_dir}" ]; then
            local jf
            while IFS= read -r -d '' jf; do
                if command -v python3 >/dev/null 2>&1; then
                    if ! python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "${jf}" >/dev/null 2>&1; then
                        echo "  [✗] Error de sintaxis JSON en plantilla: ${jf}" >&2
                        CHECK_ERRORS=$((CHECK_ERRORS + 1))
                    fi
                fi
            done < <(find "${template_dir}" -name "*.json" -print0 2>/dev/null | sort -z)
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

check_global_skills_purity() {
    if [ ! -d "${MODULES_DIR}" ]; then
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        local leak
        leak="$(python3 -c '
import glob, json, os, sys
modules_dir, runtimes_dir = sys.argv[1], sys.argv[2]
domain_skills = set()
domain_bins = set()
for mf in glob.glob(os.path.join(modules_dir, "*", "module.json")):
    try:
        data = json.load(open(mf, "r", encoding="utf-8"))
        domain_skills.update(data.get("skills", []))
        domain_bins.update(data.get("binaries", {}).values())
    except Exception:
        pass

leaks = []
for cf in glob.glob(os.path.join(runtimes_dir, "*", "config.json")):
    rname = os.path.basename(os.path.dirname(cf))
    if rname == "schema":
        continue
    try:
        cfg = json.load(open(cf, "r", encoding="utf-8"))
        r_skills = set(cfg.get("skills", []))
        r_bins = set(cfg.get("binaries", {}).values())
        sk_leak = r_skills.intersection(domain_skills)
        bin_leak = r_bins.intersection(domain_bins)
        if sk_leak:
            leaks.append(f"[{rname}] skills de dominio: {list(sk_leak)}")
        if bin_leak:
            leaks.append(f"[{rname}] binarios de dominio: {list(bin_leak)}")
    except Exception:
        pass
if leaks:
    print("; ".join(leaks))
' "${MODULES_DIR}" "${RUNTIMES_BASE_DIR}")"
        if [ -n "${leak}" ]; then
            echo "  [✗] Skill(s) o binario(s) de dominio detectados en perfil global: ${leak}" >&2
            CHECK_ERRORS=$((CHECK_ERRORS + 1))
        else
            echo "  [✓] Pureza de perfil global: runtimes no contienen skills ni binarios de dominio"
        fi
    fi
}

cmd_workspace() {
    local module_name="${1:-}"
    local target_dir="${2:-.}"
    local runtime_filter="${3:-all}"

    if [ -z "${module_name}" ]; then
        echo "Uso: $0 workspace <nombre-modulo> [ruta-directorio-destino] [runtime]" >&2
        echo "Ejemplo: $0 workspace eso . all" >&2
        echo "Nota: Si se omite la ruta destino, se asume el directorio actual (.)." >&2
        return 1
    fi

    local agent_module_cli="${SCRIPT_DIR}/skills/issue-driven-workflow/bin/agent-module"
    if [ -x "${agent_module_cli}" ]; then
        python3 "${agent_module_cli}" enable "${module_name}" "${target_dir}" --runtime "${runtime_filter}"
        return $?
    else
        echo "Error: CLI de aprovisionamiento no encontrado en ${agent_module_cli}" >&2
        return 1
    fi
}
