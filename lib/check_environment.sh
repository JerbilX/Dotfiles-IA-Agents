#!/usr/bin/env bash
# lib/check_environment.sh - Verificación de documentación, tests unitarios, aliases gh, bypass quotes y guards P0

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

check_p0_guards() {
    echo "==> [check] Verificando guards P0 y blindaje mecánico..."
    local p0_errors=0

    # 1. Binario agent-guard
    local guard_bin="${SKILLS_DIR}/conversation-audit/bin/agent-guard"
    if [ ! -f "${guard_bin}" ]; then
        echo "  [✗] Binario agent-guard no encontrado en ${guard_bin}" >&2
        p0_errors=$((p0_errors + 1))
    elif [ ! -x "${guard_bin}" ]; then
        echo "  [✗] Binario agent-guard no tiene permisos de ejecución (${guard_bin})" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Binario agent-guard ejecutable y disponible"
    fi

    # 2. Git hooks locales (.githooks/)
    local pre_push="${SCRIPT_DIR}/.githooks/pre-push"
    local pre_commit="${SCRIPT_DIR}/.githooks/pre-commit"
    if [ ! -f "${pre_push}" ] || [ ! -x "${pre_push}" ]; then
        echo "  [✗] Git hook pre-push no encontrado o no ejecutable en ${pre_push}" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Git hook pre-push verificado"
    fi

    if [ ! -f "${pre_commit}" ] || [ ! -x "${pre_commit}" ]; then
        echo "  [✗] Git hook pre-commit no encontrado o no ejecutable en ${pre_commit}" >&2
        p0_errors=$((p0_errors + 1))
    else
        echo "  [✓] Guards P0: Git hook pre-commit verificado"
    fi

    # 3. Ausencia total de backlogs locales o archivos prohibidos
    local banned_found=0
    for bf in TODO.md todo.md TODO todo backlog.md backlog GEMINI.md historial.md HISTORIAL.md; do
        if [ -e "${SCRIPT_DIR}/${bf}" ]; then
            echo "  [✗] Archivo prohibido detectado en la raíz del repo: ${bf}" >&2
            p0_errors=$((p0_errors + 1))
            banned_found=$((banned_found + 1))
        fi
    done
    for bd in tasks prompts; do
        if [ -d "${SCRIPT_DIR}/${bd}" ]; then
            echo "  [✗] Directorio prohibido detectado en la raíz del repo: ${bd}/" >&2
            p0_errors=$((p0_errors + 1))
            banned_found=$((banned_found + 1))
        fi
    done
    if [ "${banned_found}" -eq 0 ]; then
        echo "  [✓] Guards P0: Ausencia de backlogs locales y archivos prohibidos verificada"
    fi

    if [ "${p0_errors}" -gt 0 ]; then
        CHECK_ERRORS=$((CHECK_ERRORS + p0_errors))
        return 1
    fi
    return 0
}
