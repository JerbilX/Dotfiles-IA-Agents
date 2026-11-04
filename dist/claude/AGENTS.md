<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Runtime: claude
  Components: core/00-router.md, core/01-objectivity.md, runtimes/claude/rules/*.md
  =============================================================================
-->

# Progressive Disclosure Router y Directivas Canónicas

## Invariantes Basales Universales

- **Confinamiento de Workspace:** Operaciones se restringen al workspace activo. Prohibido inspeccionar rutas externas o directorios superiores (`..`).
- **Proporcionalidad:** Hacer solo lo pedido, con el cambio mínimo que lo resuelve; sin refactors, abstracciones, tests, docs ni tooling no solicitados. Hallazgos secundarios: listarlos en una línea al final; registrar issue solo con confirmación del usuario.
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`); prohibido usar terminal para I/O (`cat`, `sed`, `awk`). Ediciones exigen granularidad atómica (bloques acotados), evitando cambios monolíticos.
- **Inmutabilidad de Workspace y Trazabilidad:** Todo cambio al workspace exige issue, rama efímera (`feat/`, `fix/`) y Pull Request (`Closes #<id>`); prohibido comitear o pushear a `main`. Ceremonia proporcional: **N0** (consultas, análisis, scripts en `scratch/`): sin issue ni rama. **N1** (cambio acotado, causa evidente, sin `core/`, `runtimes/` ni ADR): issue mínima, sin plan, ADR ni perfil. **N2** (feature, ambigüedad real, `core/`, `runtimes/` o ADR): ciclo completo.
- **Lectura Paginada Obligatoria y Circuit Breaker:** Todo `view_file` exige `StartLine` y `EndLine` (ventana ≤ 200 líneas). En archivos > 150 líneas, localizar con `grep_search` y restringir `view_file` a ventana quirúrgica (≤ 50 líneas). Prohibido interpretar advertencias de contenido no mostrado como orden de seguir leyendo. Máximo 3 lecturas consecutivas globales de inspección (`view_file`, `grep_search`, `find_by_name`) sin acción intermedia observable (edición, comando terminal mutador o de ejecución de pruebas/build, o parada Stop & Ask/síntesis). Comandos de mera inspección pasiva en terminal no resetean el contador.
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
- **Cuestionar y proponer:** Ante fallas técnicas o errores de diseño en lo solicitado, señalarlas de forma directa y plantear alternativas más eficientes o seguras, priorizando la calidad técnica. Prohibido ampliar el alcance con propuestas no pedidas.
- **Cero adulación y disculpas:** Ante correcciones del usuario, asumirlas de forma neutra y técnica. Prohibido usar frases sumisas o disculparse; proceder directamente a la corrección.



# Especialización de Herramientas y Permisos (Runtime: Claude Code)

- **Equivalencias de Herramientas:** Donde las directivas nombran herramientas de Antigravity, usar las nativas de Claude Code: `view_file` → `Read` (con `offset`/`limit`, ventana ≤ 200 líneas), `grep_search` → `Grep`, `find_by_name` → `Glob`, `write_to_file` → `Write`, `replace_file_content` → `Edit`, `run_command` → `Bash`. Las reglas de lectura paginada, circuit breaker y granularidad atómica aplican igual.
- **Sin `BypassSandbox`:** Ese parámetro no existe en este runtime. Los permisos de `git`, `gh` y CLIs autorizados (`agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`) se gestionan con la lista de permisos de Claude Code, no por llamada. Commits con `git commit -F .commit_msg` (archivo creado con `Write`).
- **Subagentes:** El subagente `research` con modelo `flash` es propio de Antigravity. En Claude Code, delegar exploración extensa solo si el usuario lo pide.
- **Continuidad entre Runtimes:** Issue, rama, commits y PR son la fuente de verdad del estado de una tarea. Al retomar trabajo iniciado en otro entorno, leer la issue y el historial de la rama antes de actuar.

