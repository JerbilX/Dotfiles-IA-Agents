# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Prohibición de Backlogs Locales:** Terminantemente prohibido crear o depender de archivos `TODO.md`, `backlog.md` o carpetas temporales huérfanas (`tasks/`, `prompts/`).
- **Registro Canónico y Control de Alcance (Scope Creep):** Toda tarea futura, deuda técnica o bug secundario detectado durante el desarrollo se lista al usuario; con su confirmación se registra como nueva GitHub Issue e indexa en Projects v2, o se resuelve en el momento si él lo decide. Prohibido inflar el alcance del ticket asignado.
- **Tipificación Obligatoria de Perfil de Ejecución:** Todo issue de backlog diferido (no ejecutado en el mismo turno) debe tipificarse obligatoriamente mediante labels estándar de perfil (`profile:flash-low`, `profile:flash-medium`, `profile:flash-high`, `profile:pro`) según su Minimal Blast Radius (MBR 0 a 4) para habilitar su orquestación determinista y desatendida (*headless*).
- **Estructura Canónica del Tablero:** El ciclo de vida en Projects v2 se rige por 6 estados formales: `📥 Backlog` -> `🎯 Ready for Dev` -> `📐 In Planning` -> `⚙️ In Progress` -> `👀 In Review / PR` -> `Done`.
- **Gobernanza y Delegación Procedimental:** El despacho, la máquina de estados desacoplada (ciclo nativo Git/GitHub y automatizaciones de Projects v2) y la interacción CLI se rigen exclusivamente por el skill `issue-driven-workflow`.

