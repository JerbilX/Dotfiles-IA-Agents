# Especialización de Herramientas y Permisos (Runtime: Claude Code)

<!-- rule: id=CLAUDE_SKILLS_CIRCUIT_BREAKER level=P0/P2 origin=legacy -->
- **Skills y Circuit Breaker:** Las skills se cargan con la herramienta `Skill` desde cualquier workspace. El circuit breaker de lectura rige como regla (sin hook).
<!-- rule: id=CLAUDE_ATTRIBUTION level=P1 origin=legacy -->
- **Atribución:** Runtime `Claude Code`; modelo: el ID del modelo en curso (ej. `claude-opus-5-5`). En issues y PRs: `Creado por: Claude Code (<modelo>)`. En commits (trailer Git): `Generated-by: Claude Code (<modelo>)`; prohibido agregar o mantener `Co-Authored-By`.
<!-- rule: id=CLAUDE_NO_BYPASSSANDBOX level=Build origin=legacy -->
- **Sin `BypassSandbox`:** Ese parámetro no existe en este runtime. Los permisos de `git`, `gh` y CLIs autorizados (`agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`) se gestionan con la lista de permisos de Claude Code, no por llamada. Commits con `git commit -F .commit_msg` (archivo creado con `Write`).
<!-- rule: id=CLAUDE_SUBAGENTS level=P2 origin=legacy -->
- **Subagentes:** El subagente `research` con modelo `flash` es propio de Antigravity. En Claude Code, delegar exploración extensa solo si el usuario lo pide.
<!-- rule: id=CLAUDE_RUNTIME_CONTINUITY level=P2 origin=legacy -->
- **Continuidad entre Runtimes:** Issue, rama, commits y PR son la fuente de verdad del estado de una tarea. Al retomar trabajo iniciado en otro entorno, leer la issue y el historial de la rama antes de actuar.
