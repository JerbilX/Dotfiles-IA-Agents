# Especialización de Herramientas y Permisos (Runtime: Claude Code)

<!-- rule: id=CLAUDE_TOOL_EQUIVALENCES level=Build origin=#282 -->
- **Equivalencias de Herramientas:** Donde las directivas nombran herramientas de Antigravity, usar las nativas de Claude Code: `view_file` → `Read` (con `offset`/`limit`, ventana ≤ 200 líneas), `grep_search` → `Grep`, `find_by_name` → `Glob`, `write_to_file` → `Write`, `replace_file_content` → `Edit`, `run_command` → `Bash`. Las reglas de lectura paginada, circuit breaker y granularidad atómica aplican igual.
<!-- rule: id=CLAUDE_SKILLS_CIRCUIT_BREAKER level=P0 origin=#282 -->
- **Skills y Circuit Breaker:** Las skills se cargan con la herramienta `Skill` desde cualquier workspace. El circuit breaker de lectura rige como regla (sin hook).
<!-- rule: id=CLAUDE_ATTRIBUTION level=P1 origin=#282 -->
- **Atribución:** Runtime `Claude Code`; modelo: el ID del modelo en curso (ej. `claude-opus-5-5`). En issues y PRs: `Creado por: Claude Code (<modelo>)`. En commits (trailer Git): `Generated-by: Claude Code (<modelo>)`; prohibido agregar o mantener `Co-Authored-By`.
<!-- rule: id=CLAUDE_NO_BYPASSSANDBOX level=Build origin=#282 -->
- **Sin `BypassSandbox`:** Ese parámetro no existe en este runtime. Los permisos de `git`, `gh` y CLIs autorizados (`agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`) se gestionan con la lista de permisos de Claude Code, no por llamada. Commits con `git commit -F .commit_msg` (archivo creado con `Write`).
<!-- rule: id=CLAUDE_SUBAGENTS level=P2 origin=#282 -->
- **Subagentes:** El subagente `research` con modelo `flash` es propio de Antigravity. En Claude Code, delegar exploración extensa solo si el usuario lo pide.
<!-- rule: id=CLAUDE_RUNTIME_CONTINUITY level=P2 origin=#282 -->
- **Continuidad entre Runtimes:** Issue, rama, commits y PR son la fuente de verdad del estado de una tarea. Al retomar trabajo iniciado en otro entorno, leer la issue y el historial de la rama antes de actuar.
