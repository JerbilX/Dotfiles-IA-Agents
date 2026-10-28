# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Inmutabilidad de Workspace y Clasificación de Tooling:** Toda creación o edición de archivos en el workspace (código, scripts/tooling, lanzadores, configuración o docs) constituye desarrollo del proyecto y exige GitHub Issue previa, rama efímera (`feat/` o `fix/`) y entrega vía PR. Prohibido mutar `main` bajo pretexto de scripts auxiliares, demos o conveniencia operativa.
- **Frontera ante Peticiones Informales:** Ante solicitudes de scripts o comandos sin ticket activo (*"dame un script..."*, *"cómo corro esto..."*):
  - *Vía Informativa:* Snippet exclusivamente como texto en el chat o en el scratchpad del runtime (`<appDataDir>/brain/<conversation-id>/scratch/`), jamás en el workspace.
  - *Vía Persistencia:* Si debe integrarse al proyecto, registrar previamente el ticket (`feat(tooling): ...`), indexarlo en Projects v2 y despachar la rama antes de tocar disco.
- **Flujo de Pull Requests y Rieles de Fusión:** Prohibido comitear o pushear a `main`. Todo cambio se entrega vía PR vinculando el cierre (`Closes #<id>` o `Fixes #<id>`).
  - *Riel 1 (Fast-Track 1-Gate - Default):* Gate humano único; `gh pr merge` requiere orden explícita en chat (*"aprobado, mergeá"*).
  - *Riel 2 (Auto-Merge Condicional - Opt-in):* Con label `automerge` u orden directa, merge autónomo (`gh pr merge <id> --squash --delete-branch`) con checks en verde.
  - *Circuit Breakers:* Si altera `core/`, `runtimes/`, ADRs (`docs/adr/`) (Nivel 3/4) o fallan checks, degrada a Riel 1.
- **Trigger de Activación y Despacho:** Ante órdenes de desarrollo o PRs, activar `issue-driven-workflow` antes de tocar archivos. Consultas exploratorias no autorizan mutar código; la higiene (sincronizar base y podar ramas de PRs cerrados/mergeados) es obligatoria y proactiva.
- **Ciclo E2E y Cierre:** Recorrer 8 fases: Ingesta, Higiene, Plan/ADR (`In Planning`), Desarrollo (`In Progress`), Commit, Push, PR (`In Review / PR`) y Cierre/Higiene (`Done`). Tras merge, validar cierre de issue, sincronizar base y podar ramas zombi.
