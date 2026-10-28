# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Prohibición de Backlogs Locales:** Terminantemente prohibido crear o depender de archivos `TODO.md`, `backlog.md` o carpetas temporales huérfanas (`tasks/`, `prompts/`).
- **Registro Canónico y Control de Alcance (Scope Creep):** Toda tarea futura, deuda técnica o bug secundario detectado durante el desarrollo debe registrarse formalmente como una nueva GitHub Issue e indexarse en Projects v2. Prohibido inflar el alcance del ticket asignado.
- **Estructura Canónica del Tablero:** El ciclo de vida en Projects v2 se rige por 6 estados formales: `📥 Backlog` -> `🎯 Ready for Dev` -> `📐 In Planning` -> `⚙️ In Progress` -> `👀 In Review / PR` -> `Done`.
- **Gobernanza y Delegación Procedimental:** El despacho, la máquina de estados desacoplada (ciclo nativo Git/GitHub y automatizaciones de Projects v2) y la interacción CLI se rigen exclusivamente por el skill `issue-driven-workflow`.

