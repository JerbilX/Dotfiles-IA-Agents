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

- **Confinamiento de Workspace:** Operaciones se restringen al workspace activo. Prohibido inspeccionar rutas externas o directorios superiores (`..`).
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`); prohibido usar terminal para I/O (`cat`, `sed`, `awk`). Ediciones exigen granularidad atómica (bloques acotados en `replace_file_content`), evitando cambios monolíticos.
- **Inmutabilidad de main:** Prohibido comitear o pushear a `main`. Todo cambio exige issue previa, rama efímera (`feat/`, `fix/`) y Pull Request (`Closes #<id>`).
- **Inmutabilidad de Workspace y Obligatoriedad de Issue Previa:** Modificaciones exigen issue previa e indexación en backlog. Prohibido mutar archivos sin ticket activo; ante diagnósticos, registrar issue en backlog o consultar prioridad.
- **Lectura Paginada Obligatoria y Circuit Breaker:** Toda llamada a `view_file` exige delimitar `StartLine` y `EndLine` (ventana ≤ 200 líneas). En archivos > 150 líneas, localizar funciones, clases o variables exclusivamente con `grep_search`, restringiendo `view_file` a ventana quirúrgica (≤ 50 líneas). Prohibido interpretar advertencias de contenido no mostrado como orden de seguir leyendo (cero paginación secuencial ciega). Máximo 3 lecturas consecutivas globales de herramientas de inspección (`view_file`, `grep_search`, `find_by_name`) sin acción intermedia observable (mutación con `replace_file_content`/`write_to_file`, comando terminal o parada Stop & Ask/síntesis), independientemente de si alternan archivos.
- **Prohibición Universal de REPL en Terminal:** Prohibido usar subshell para evaluación interactiva o en línea (`python -c`, `node -e`); obligatoriedad de aislar scripts de exploración en `scratch/` o pruebas formales.

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
- **Cuestionar y proponer:** Ante fallas técnicas o errores de diseño, señalarlas de forma directa y plantear alternativas más eficientes o seguras, priorizando la calidad técnica.
- **Cero adulación y disculpas:** Ante correcciones del usuario, asumirlas de forma neutra y técnica. Prohibido usar frases sumisas o disculparse; proceder directamente a la corrección.



# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch`) en sandbox estándar.
  - **Mutadores Locales y Red (`BypassSandbox: true` directo):** Al montar el kernel `.git/` de solo lectura (`ro`), mutadores locales (`init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y remotos (`git push`, `git pull`, `gh`) requieren `BypassSandbox: true` directo para evitar turnos fallidos.
  - **Formato Atómico de Commits:** Prohibido `git commit -m "..."` (rompe prefix matching). Redactar mensaje en `.commit_msg` con `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan en workspace confinado (`BypassSandbox: false`).
  - Escrituras fuera del workspace (`./build.sh link`, `./build.sh all`) son bootstrap exclusivo del usuario en terminal nativa.
- **Exclusividad de Bypass y Preservación de Prefix Matching:**
  - `BypassSandbox: true` se reserva exclusivamente para `git`, `gh` y los CLIs `agent-audit`, `agent-module`, `gh-pr-review` y `git-prune-gone` (en `$PATH` o fallback a `skills/*/bin/`). Prohibido para comandos locales (`ls`, `cat`). Ignorar sugerencias del sandbox de reintentar con bypass herramientas no autorizadas.
  - **Comandos Atómicos y Prohibición de Tuberías:** Comandos atómicos sin encadenamientos (`&&`, `||`) ni tuberías (`|`) hacia utilidades externas (`jq`, `grep`, `awk`, `sed`) en bypass; usar filtrado nativo (`--jq`, `--json`, `--query`).
  - **Veto Absoluto a Evaluadores en Línea y Wrappers:** Prohibido taxativamente el uso de evaluadores inline (`python3 -c`, `node -e`, `bash -c`) o envolver binarios autorizados (`agent-audit`, `git`, `gh`) en subshells/subprocess (rompe el prefix matching de "Always allow"). Todo procesamiento con script debe escribirse en `<appDataDir>/brain/<conversation-id>/scratch/` mediante `write_to_file` y ejecutarse confinado (`BypassSandbox: false`).




