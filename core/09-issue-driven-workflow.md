# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Inmutabilidad de Workspace:** Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y PR (`Closes #<id>`). Prohibido push a `main`.
- **Peticiones Informales:** Snippets sin ticket van a chat o scratchpad; persistencia en workspace exige issue previa.
- **Rieles de PR:** Riel 1 (Default: orden en chat); Riel 2 (Auto-merge condicional; cambios en `core/`, `runtimes/` o ADRs degradan a Riel 1).
- **Ejecución E2E:** Al despachar tareas, ramas, PRs o reviews, leer [`skills/issue-driven-workflow/SKILL.md`](skills/issue-driven-workflow/SKILL.md) y [`skills/issue-driven-workflow/references/branch-lifecycle.md`](skills/issue-driven-workflow/references/branch-lifecycle.md).
