# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Prohibición de Push Directo a `main` y Flujo de PRs:** Prohibido comitear, pushear directamente a `main` o ejecutar `git merge` hacia `main`. Todo cambio debe aislarse en rama dedicada (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) y canalizarse mediante Pull Request formal con vinculación de cierre (`Closes #<id>` o `Fixes #<id>`). Aprobación y merge son potestad exclusiva del usuario.
- **Trigger de Activación Obligatoria:** Ante directivas de desarrollo ("implementa la issue #X", "toma la siguiente tarea lista") o apertura de PRs, activar y consultar obligatoriamente el skill `issue-driven-workflow` antes de modificar archivos.

