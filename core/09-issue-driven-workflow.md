# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Despacho y Recepción de Tareas (Fase 1: Bajo Demanda):**
  - El agente opera bajo demanda ante directivas conversacionales del usuario en el chat:
    - **Instrucción directa (*"implementa la issue #<id>"*):**
      1. Consultar el contexto técnico completo mediante `gh issue view <id>` (con `BypassSandbox: true`).
      2. Transicionar el estado del ticket en el tablero central (Project 1) a `⚙️ In Progress`:
         `gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "⚙️ In Progress"`
    - **Instrucción de backlog (*"toma la siguiente tarea lista en Ready for Dev"*):**
      1. Consultar los ítems del tablero con `gh project item-list 1 --owner JerbilX --format json`.
      2. Identificar el primer ticket cuyo estado sea `🎯 Ready for Dev`.
      3. Transicionar dicho ítem a `⚙️ In Progress` y proceder con la ingesta técnica.

- **Convención Canónica de Ramas de Trabajo:**
  - Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código.
  - **Nomenclatura Obligatoria:**
    - Para nuevas funcionalidades o tareas generales: `feat/issue-<id>-<slug>`
    - Para corrección de errores o parches: `fix/issue-<id>-<slug>`
  - Creación de rama in-place (Fase 1): `git checkout -b <nombre-de-rama>`.

- **Ciclo de Vida E2E de la Tarea:**
  1. **Ingesta:** Lectura del ticket con `gh issue view <id>`.
  2. **Aislamiento e Higiene del Workspace:**
     - Posicionarse en la rama principal (`git checkout main`) y sincronizar cambios (`git pull`).
     - Ejecutar la poda de higiene local para remover ramas ya fusionadas cuyo upstream remoto fue eliminado:
       `git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d`
     - Crear y cambiar a la rama descriptiva (`git checkout -b <nombre-de-rama>`).
  3. **Planificación y Refinamiento:** Elaboración del plan en `implementation_plan.md` si el alcance lo amerita (obligatorio ante bug fixing o arquitectura, salvo aplicación de Fast-Path Ejecutivo por consenso previo explícito en chat según `core/07-anti-hallucination.md`). Si se toman decisiones arquitectónicas, registrar nuevo ADR con `status: proposed` mediante el skill `adr-manager`.
  4. **Desarrollo y Verificación:** Modificaciones atómicas mediante herramientas nativas de archivos (`write_to_file`, `replace_file_content`), ejecución de builds y suites de pruebas locales.
  5. **Commit Atómico:** Redacción del mensaje convencional en `.commit_msg` con la API nativa de archivos y ejecución de `git commit -F .commit_msg`.
  6. **Publicación Remota:** Subida de la rama con `git push -u origin <nombre-de-rama>` (ejecutado con `BypassSandbox: true`).
  7. **Apertura de Pull Request:** Creación del PR formal mediante `gh pr create` (ejecutado con `BypassSandbox: true`).

- **Flujo Mandatorio de Pull Requests:**
  - **Prohibición Total de Push/Merge a `main`:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
  - **Vinculación Canónica de Cierre:** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse.
  - **Sincronización Determinista con el Tablero Central:** Asegurar que el estado del ítem en Project 1 pase a `👀 In Review / PR` mediante el comando determinista directo:
    `gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "👀 In Review / PR"`
    *(Queda prohibido ejecutar consultas exploratorias de `field-list` o `item-list` para resolver IDs de campos cuando el comando directo por nombre es determinista).*
  - **Gate de Aprobación Humana:** La revisión del diff, aprobación y fusión del PR es responsabilidad exclusiva del PM / Tech Lead en GitHub.

- **Protocolo Operativo de Salida y Reporte:**
  - Al completar la publicación del PR, el agente **DEBE emitir un reporte final estandarizado** que incluya:
    1. Resumen técnico conciso de los cambios realizados.
    2. Verificaciones y pruebas ejecutadas exitosamente.
    3. Enlace web directo al Pull Request creado en GitHub.
    4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
    5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.
