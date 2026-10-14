# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Prohibición Estricta de Backlogs Locales:**
  - Queda terminantemente prohibido crear, sincronizar o depender de archivos `TODO.md`, `backlog.md` o similares en cualquier nivel del proyecto.
  - Queda terminantemente prohibido volcar prompts, especificaciones de tareas o planes de ejecución en archivos huérfanos dentro de carpetas temporales (ej. `tasks/`, `prompts/`).

- **Registro Canónico de Tareas Futuras:**
  - Cuando el usuario solicite registrar una tarea, mejora, refactor o deuda técnica para el futuro, el agente **DEBE registrarla formalmente como una GitHub Issue** mediante el CLI:
    `gh issue create --title "<tipo>(<alcance>): <descripción>" --body "<especificación técnica detallada>"`
  - El cuerpo de la issue debe contener el diagnóstico del problema, objetivos, requerimientos técnicos y criterios de aceptación, eliminando la necesidad de redactar prompts manuales posteriores.
  - Al completar la creación, el agente debe reportar al usuario el número de issue asignado y el enlace web directo.

- **Consumo y Ejecución de Tareas desde el Backlog:**
  - Cuando el usuario instruya trabajar sobre una tarea existente (ej. *"implementa la issue #4"*), el agente **DEBE consultar el contexto técnico directamente con `gh issue view <número>`**.
  - Si la tarea implica cambios de código, el agente debe trabajar preferentemente en una rama descriptiva asociada (`feat/issue-<número>-<nombre>` o `fix/issue-<número>-<nombre>`).
  - Al finalizar la tarea y generar los commits correspondientes, el agente debe incluir la referencia de cierre canónica (`Closes #<número>` o `Fixes #<número>`) para que GitHub cierre la issue y el tablero mueva la tarjeta a `Done` automáticamente.
