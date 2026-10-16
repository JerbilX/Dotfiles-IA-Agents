# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Prohibición Estricta de Backlogs Locales:**
  - Queda terminantemente prohibido crear, sincronizar o depender de archivos `TODO.md`, `backlog.md` o similares en cualquier nivel del proyecto.
  - Queda terminantemente prohibido volcar prompts, especificaciones de tareas o planes de ejecución en archivos huérfanos dentro de carpetas temporales (ej. `tasks/`, `prompts/`).

- **Registro Canónico de Tareas Futuras:**
  - Cuando el usuario solicite registrar una tarea, mejora, refactor o deuda técnica para el futuro, el agente **DEBE registrarla formalmente como una GitHub Issue** mediante el CLI:
    `gh issue create --title "<tipo>(<alcance>): <descripción>" --body "<especificación técnica detallada>"`
  - El cuerpo de la issue debe contener el diagnóstico del problema, objetivos, requerimientos técnicos y criterios de aceptación, eliminando la necesidad de redactar prompts manuales posteriores.
  - Para asegurar la indexación inmediata y agnóstica en el tablero central (sin depender de las restricciones de auto-add en cuentas GitHub Free), el agente debe añadirla proactivamente al tablero con:
    `gh project item-add 1 --owner JerbilX --url <issue-url>`
  - Al completar la creación, el agente debe reportar al usuario el número de issue asignado y el enlace web directo.

- **Control de Alcance y Desvíos (Scope Creep):**
  - El agente **no debe inflar** el objetivo del ticket original con refactors, mejoras o arreglos colaterales no contemplados en la especificación de la issue.
  - Si durante el desarrollo se detecta un bug, deuda técnica o necesidad secundaria, el agente **DEBE registrarla inmediatamente como una nueva GitHub Issue** (`gh issue create`), indexarla al tablero central (`gh project item-add 1 --owner JerbilX --url <issue-url>`) y continuar enfocado en el ticket asignado sin desviarse.

- **Consumo y Ejecución de Tareas:**
  - El ciclo de vida de ejecución técnica de tareas, despacho bajo demanda, convención de ramas y flujo mandatorio de Pull Requests se rigen exclusivamente por el skill `issue-driven-workflow` y la directiva de enlace en `core/09-issue-driven-workflow.md`.
