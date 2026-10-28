# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia de Producción:** Contratos de producción priman sobre tests; prohibido degradar código por mocks obsoletos.
- **Fallos en Tests:** Si el mock está desfasado, actualizarlo; si falla regla de negocio, corregir código de producción.
- **Minimal Blast Radius:** Resolver al nivel más bajo (N0 CLI -> N1 Tooling -> N2 Skills -> N3 Runtime -> N4 Core). Modificar `core/` exige justificación basal; al clasificar tareas, leer [`skills/issue-driven-workflow/references/issue-backlog.md`](skills/issue-driven-workflow/references/issue-backlog.md).
