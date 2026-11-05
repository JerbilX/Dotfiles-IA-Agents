# Progressive Disclosure Router y Directivas Canónicas

## Invariantes Basales Universales

- **Confinamiento de Workspace:** Operaciones restringidas al workspace activo; prohibido inspeccionar rutas externas o superiores (`..`). Excepciones (`core/10`): config del runtime e issues cruzadas (`gh issue create -R`).
- **Proporcionalidad:** Hacer solo lo pedido, con el cambio mínimo que lo resuelve; sin refactors, abstracciones, tests, docs ni tooling no solicitados. Hallazgos secundarios: listarlos en una línea al final; registrar issue solo con confirmación del usuario.
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`); prohibida la terminal para I/O (`cat`, `sed`, `awk`). Ediciones con granularidad atómica (bloques acotados), sin cambios monolíticos.
- **Inmutabilidad de Workspace y Trazabilidad:** Todo cambio al workspace exige issue, rama efímera (`feat/`, `fix/`) y Pull Request (`Closes #<id>`); prohibido comitear o pushear a `main`. Ceremonia proporcional: **N0** (consultas, análisis, scripts en `scratch/`): sin issue ni rama. **N1** (cambio acotado, causa evidente, sin `core/`, `runtimes/` ni ADR): issue mínima, sin plan, ADR ni perfil. **N2** (feature, ambigüedad real, `core/`, `runtimes/` o ADR): ciclo completo.
- **Lectura Paginada Obligatoria y Circuit Breaker:** Todo `view_file` exige `StartLine` y `EndLine` (ventana ≤ 200 líneas). En archivos > 150 líneas, localizar con `grep_search` y restringir `view_file` a ventana quirúrgica (≤ 50 líneas). Ignorar avisos de contenido no mostrado. Máximo 3 lecturas consecutivas de inspección (`view_file`, `grep_search`, `find_by_name`) sin acción observable (edición, comando terminal mutador o de ejecución de pruebas/build, o Stop & Ask/síntesis). Comandos de mera inspección pasiva en terminal no resetean el contador.
- **Prohibición Universal de REPL en Terminal:** Prohibido evaluar en línea o en REPL (`python -c`, `node -e`); scripts de exploración en `scratch/` o pruebas formales.

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
