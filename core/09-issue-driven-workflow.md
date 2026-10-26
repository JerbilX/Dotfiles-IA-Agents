# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Prohibición de Push Directo a `main` y Flujo de PRs:** Prohibido comitear o pushear a `main`. Todo cambio debe aislarse en rama dedicada (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) y entregarse vía Pull Request con vinculación de cierre (`Closes #<id>` o `Fixes #<id>`).
  - *Riel 1 (Fast-Track 1-Gate - Default):* El PR es el único gate humano; `gh pr merge` se ejecuta tras orden explícita en chat (*"aprobado, mergeá"*).
  - *Riel 2 (Auto-Merge Condicional - Opt-in):* Con label `automerge` u orden directa, el agente ejecuta el merge autónomo con `gh pr merge <id> --squash --delete-branch` tras verificar tests y checks locales en verde.
  - *Circuit Breakers:* Si un issue en Riel 2 altera `core/`, `runtimes/`, genera/modifica un ADR (`docs/adr/`) (Nivel 3/4) o falla verificaciones, el auto-merge se cancela, degradando a Riel 1.
- **Trigger de Activación y Despacho:** Ante órdenes de desarrollo o apertura de PRs, activar y consultar obligatoriamente `issue-driven-workflow` antes de modificar archivos. Consultas exploratorias no autorizan mutar código, pero la higiene (sincronizar base y podar ramas de PRs cerrados/mergeados) es obligatoria y proactiva ante cualquier interacción.
- **Ciclo E2E y Cierre:** Toda tarea recorre 8 fases: Ingesta, Higiene, Plan/ADR (`In Planning`), Desarrollo (`In Progress`), Commit, Push, PR (`In Review / PR`) y Cierre/Higiene (`Done`). Tras el merge, validar cierre de la issue, sincronizar base y podar ramas locales zombi.

