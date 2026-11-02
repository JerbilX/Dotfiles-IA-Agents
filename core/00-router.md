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
