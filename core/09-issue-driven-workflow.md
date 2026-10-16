# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Gobernanza Human-in-the-Loop y Prohibición de Push Directo a `main`:**
  - Queda **estrictamente prohibido** que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
  - Todo cambio funcional debe aislarse en una rama dedicada (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) y canalizarse exclusivamente mediante un Pull Request formal con vinculación canónica de cierre (`Closes #<id>` o `Fixes #<id>`).
  - La revisión del diff, aprobación y fusión del Pull Request es responsabilidad exclusiva del usuario en GitHub.

- **Trigger de Activación Obligatoria del Skill:**
  - Ante cualquier directiva conversacional de desarrollo (ej. *"implementa la issue #<id>"*, *"toma la siguiente tarea lista"*), ejecución de tareas de backlog o gestión de Pull Requests, el agente **DEBE activar y consultar obligatoriamente el skill `issue-driven-workflow`** antes de modificar cualquier archivo de código.
  - El skill gobierna el despacho desde GitHub Projects v2, la higiene de ramas locales (`git branch -d`), el ciclo de vida E2E de desarrollo, los comandos atómicos de commit/push/PR con bypass de sandbox, la sincronización determinista de estados (`👀 In Review / PR`) y el reporte estandarizado de salida.
