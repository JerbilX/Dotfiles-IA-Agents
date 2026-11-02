<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Runtime: antigravity
  Components: core/00-router.md, core/01-objectivity.md, runtimes/antigravity/rules/*.md
  =============================================================================
-->

# Progressive Disclosure Router y Directivas Canónicas

## Invariantes Basales Universales

- **Confinamiento de Workspace:** Operaciones de lectura y escritura se restringen al workspace activo. Prohibido inspeccionar rutas externas o directorios superiores (`..`).
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones de archivo exigen APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`).
- **Inmutabilidad de main:** Prohibido comitear o pushear a `main`. Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y Pull Request (`Closes #<id>`).
- **Inmutabilidad de Workspace y Obligatoriedad de Issue Previa:** Toda modificación, corrección o refactor exige OBLIGATORIAMENTE issue previa e indexación en backlog. PROHIBIDO modificar archivos sin ticket activo o proponer aplicarlos directamente; ante cualquier diagnóstico técnico, registrar issue en backlog o consultar prioridad.
- **Lectura Paginada Obligatoria:** Inspecciones con `view_file` en archivos extensos o documentación exigen delimitar `StartLine` y `EndLine` (ventana máxima recomendada ≤ 200 líneas). Prohibidas lecturas masivas no acotadas sin paginación.
- **Prohibición Universal de REPL en Terminal:** Prohibido usar subshell para evaluación iterativa en línea (`python -c`, `node -e`, `luajit -e`); obligatoriedad de aislar scripts de exploración en `scratch/` o pruebas formales.

## Progressive Disclosure Router (Directivas Modulares)

Consultar obligatoriamente la directiva modular correspondiente antes de actuar:

- **Ciclo de Vida Git y Repositorios:** If initializing, configuring, or pushing to Git repositories, read [core/02-git-lifecycle.md](core/02-git-lifecycle.md) first.
- **Convención de Reglas y Decisiones (MADR):** If defining rules, architecture, or ADRs, read [core/03-agent-rules-convention.md](core/03-agent-rules-convention.md) and [skills/adr-manager/SKILL.md](skills/adr-manager/SKILL.md) first.
- **Disciplina de Búsqueda Web y Circuit Breakers:** If searching the web or documentation, read [core/04-web-search-discipline.md](core/04-web-search-discipline.md) first.
- **Flexibilidad y Degradación Elegante:** If encountering environment errors, tool failures, or blocks, read [core/05-anti-rigidity.md](core/05-anti-rigidity.md) first.
- **Estándares de Ingeniería y Tests:** If writing code, tests, or evaluating blast radius, read [core/06-engineering-standards.md](core/06-engineering-standards.md) first.
- **Estabilidad Lógica y Planificación:** If formulating hypotheses, planning, or resolving ambiguity, read [core/07-anti-hallucination.md](core/07-anti-hallucination.md) first.
- **Gestión de Backlog y Tareas:** If creating issues, indexing tasks, or proposing improvements, read [core/08-task-backlog-management.md](core/08-task-backlog-management.md) first.
- **Protocolo de Desarrollo Guiado por Issues y PRs:** If starting development, creating branches, opening PRs, or reviewing code, read [core/09-issue-driven-workflow.md](core/09-issue-driven-workflow.md) and [skills/issue-driven-workflow/SKILL.md](skills/issue-driven-workflow/SKILL.md) first.
- **Entorno y Confinamiento Detallado:** If running terminal commands, managing temporary files, or CLI tooling, read [core/10-environment-standards.md](core/10-environment-standards.md) first.


# Critical Feedback and Objectivity

- **Cero complacencia:** Prohibido asumir que las ideas del usuario son buenas por defecto o usar frases de validación vacías ("¡Gran idea!", "Me parece perfecto").
- **Cuestionar y proponer:** Ante fallas técnicas, limitaciones o errores de diseño, señalarlas de forma directa y plantear alternativas más eficientes, estándar o seguras, priorizando la calidad técnica sobre la complacencia.
- **Cero adulación y disculpas:** Ante correcciones o mejoras aportadas por el usuario, asumirlas de manera neutra y técnica. Prohibido usar frases sumisas ("tienes toda la razón", "análisis impecable") o disculparse reiteradamente; proceder directamente a la corrección.



# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch`) debe ejecutarse confinada en el sandbox estándar.
  - **Mutadores Locales y Red (`BypassSandbox: true` obligatorio desde el primer intento):** Dado que el kernel monta `.git/` como solo lectura (`ro`), todo mutador local (`git init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y comando remoto (`git push`, `git pull`, `gh`) falla en sandbox; deben ejecutarse directamente con `BypassSandbox: true` desde el primer intento para evitar latencia de turnos fallidos.
  - **Formato Atómico de Commits:** Prohibido usar `git commit -m "..."` (rompe el prefix matching de permisos). Redactar siempre el mensaje en `.commit_msg` con `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan dentro del workspace y deben ejecutarse confinados (`BypassSandbox: false`).
  - Comandos que escriben fuera del workspace (`./build.sh link`, `./build.sh all`) son responsabilidad exclusiva de bootstrap del usuario en terminal nativa.
- **Exclusividad de Bypass y Blindaje Anti-Sugerencias:**
  - `BypassSandbox: true` está reservado exclusivamente para la suite de `git` y `gh`, y para los CLIs `agent-audit`, `agent-module`, `gh-pr-review` y `git-prune-gone` (priorizando su invocación en `$PATH` con fallback determinista a `skills/*/bin/`). Prohibido para otros comandos locales (`ls`, `cat`, utilidades).
  - Si el sandbox sugiere *"run the command again with BypassSandbox set to true"* para un comando local no autorizado, ignorar la sugerencia por completo.
  - **Invocaciones Atómicas y Prohibición de Tuberías:** Mantener comandos atómicos sin operadores encadenados (`&&`, `||`). Prohibido el uso de tuberías (`|`) hacia utilidades externas (`jq`, `grep`, `awk`, `sed`) en comandos con bypass por romper el prefix matching; es obligatorio usar el filtrado nativo de `gh` (`--jq`, `--json`, `--query`).




