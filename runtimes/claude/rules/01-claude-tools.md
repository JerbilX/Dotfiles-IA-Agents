# Especialización de Herramientas y Permisos (Runtime: Claude Code)

<!-- rule: id=CLAUDE_SKILLS_CIRCUIT_BREAKER level=P0/P2 origin=legacy -->
- **Skills y Circuit Breaker:** Las skills se cargan con `Skill` desde cualquier workspace. Circuit breaker y paginación van por hook: ante bloqueo, sintetizar o Stop & Ask, sin reintentar.
<!-- rule: id=CLAUDE_SUBAGENTS level=P2 origin=legacy -->
- **Subagentes:** El subagente `research` con modelo `flash` es propio de Antigravity. En Claude Code, delegar exploración extensa solo si el usuario lo pide.
<!-- rule: id=CLAUDE_RUNTIME_CONTINUITY level=P2 origin=legacy -->
- **Continuidad entre Runtimes:** Issue, rama, commits y PR son la fuente de verdad del estado de una tarea. Al retomar trabajo iniciado en otro entorno, leer la issue y el historial de la rama antes de actuar.

