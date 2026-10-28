# Progressive Disclosure Router y Directivas Canónicas

## Invariantes Basales Universales

- **Confinamiento de Workspace:** Toda operación de lectura o escritura se restringe estrictamente al workspace activo. Prohibido acceder o inspeccionar rutas externas o directorios superiores (`..`).
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones de archivo deben usar estrictamente las APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`).
- **Inmutabilidad de main:** Prohibido comitear o pushear directamente a `main`. Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y entrega vía Pull Request (`Closes #<id>`).

## Progressive Disclosure Router (Directivas Modulares)

Para especificaciones operativas y procedimientos detallados, consultar obligatoriamente la directiva modular correspondiente antes de actuar:

- **Ciclo de Vida Git y Repositorios:** If initializing, configuring, or pushing to Git/GitHub repositories, read [core/02-git-lifecycle.md](core/02-git-lifecycle.md) first.
- **Convención de Reglas y Decisiones (MADR):** If defining agent rules, modifying architecture, or managing ADRs, read [core/03-agent-rules-convention.md](core/03-agent-rules-convention.md) and [skills/adr-manager/SKILL.md](skills/adr-manager/SKILL.md) first.
- **Disciplina de Búsqueda Web y Circuit Breakers:** If searching the web or consulting external documentation, read [core/04-web-search-discipline.md](core/04-web-search-discipline.md) first.
- **Flexibilidad y Degradación Elegante:** If encountering environment errors, tool failures, or rigid blocks, read [core/05-anti-rigidity.md](core/05-anti-rigidity.md) first.
- **Estándares de Ingeniería y Tests:** If writing code, updating tests, or evaluating blast radius, read [core/06-engineering-standards.md](core/06-engineering-standards.md) first.
- **Estabilidad Lógica y Planificación:** If formulating hypotheses, planning tasks, or resolving ambiguity, read [core/07-anti-hallucination.md](core/07-anti-hallucination.md) first.
- **Gestión de Backlog y Tareas:** If creating issues, indexing tasks, or updating GitHub Projects v2 boards, read [core/08-task-backlog-management.md](core/08-task-backlog-management.md) first.
- **Protocolo de Desarrollo Guiado por Issues y PRs:** If starting development, creating branches, opening PRs, or reviewing code, read [core/09-issue-driven-workflow.md](core/09-issue-driven-workflow.md) and [skills/issue-driven-workflow/SKILL.md](skills/issue-driven-workflow/SKILL.md) first.
- **Entorno y Confinamiento Detallado:** If running terminal commands, managing temporary files, or handling CLI tooling, read [core/10-environment-standards.md](core/10-environment-standards.md) first.
