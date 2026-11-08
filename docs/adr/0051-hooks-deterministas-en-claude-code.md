---
status: accepted
date: 2026-11-08
decision-makers: [JerbilX, Claude Code]
supersedes: []
superseded-by: []
references:
  - docs/adr/0043-hard-circuit-breaker-y-lifecycle-hooks.md
  - docs/adr/0045-operacion-multi-runtime-e-issues-cruzadas.md
  - docs/adr/0046-limite-del-circuit-breaker-basado-en-datos.md
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
---

# 0051 - Hooks Deterministas en Claude Code: Circuit Breaker, Paginación y Lecturas por Bash

## Contexto y Planteamiento del Problema

`ENV_PAGED_READ_CIRCUIT_BREAKER` está registrada como P0 (ADR-0048), pero solo Antigravity la hace cumplir con un hook (`agent-circuit-breaker`, ADR-0043/0046). En Claude Code se cumple solo por texto. Al relevar #287 aparecieron cuatro hechos que la issue no contemplaba:

1. **No hay `settings.json` compilado para Claude.** `runtimes/claude/settings.json` no pasa por `dist/`: `lib/link.sh` lo combina en `~/.claude/settings.json` mediante `lib/merge_settings.py`, que solo combinaba `permissions`.
2. **Otro protocolo de hook.** Claude Code envía `tool_name`, `tool_input` y `transcript_path`, y espera `hookSpecificOutput.permissionDecision`. Un `allow` explícito saltea su sistema de permisos.
3. **Otro formato de transcript.** Cada `tool_use` es un registro con su `message.id`, los `tool_result` llegan como registros `user` y la llamada en curso puede no estar escrita todavía.
4. **Las lecturas pasan por Bash.** En Claude Code la inspección se hace mayormente con `cat`, `sed -n` o `grep` desde Bash, y el breaker trataba todo comando de terminal como acción activa. Un hook limitado a `Read|Grep|Glob` casi nunca se activaría. La regla basal ya establece que la inspección pasiva por terminal no reinicia el contador.

## Impulsores de la Decisión (Decision Drivers)

* Llevar a P0 en Claude Code la regla que el registro ya declara P0.
* Misma semántica de umbral y ping-pong en ambos runtimes (ADR-0046).
* Cero falsos bloqueos sobre comandos de build, tests o mutaciones.
* No pisar la configuración propia del usuario en `~/.claude/settings.json` (ADR-0045).

## Opciones Consideradas

**Ubicación de los hooks**

* **A1:** `runtimes/claude/hooks.json` compilado a `dist/` y enlazado.
* **A2:** clave `hooks` en `runtimes/claude/settings.json`, combinada por `merge_settings.py` durante `link`.

**Bash**

* **B1:** todo Bash es activo (semántica actual de Antigravity).
* **B2:** lista conservadora de comandos de inspección cuenta como lectura pasiva; el resto, activo.
* **B3:** posponer la clasificación a otra issue.

## Decisión Adoptada

**A2 + B2**, con un único binario `agent-circuit-breaker` que detecta el formato del payload.

1. **Ubicación (A2).** Claude Code lee los hooks desde `settings.json`, así que la combinación con el archivo del usuario es inevitable. `merge_settings.py` trata los comandos del fragmento como propiedad del repo: los retira del destino (aunque estén bajo otro matcher) y agrega las entradas del fragmento. El merge es idempotente, un cambio de matcher no deja duplicados y los hooks del usuario no se tocan. El comando usa `${DOTFILES_ROOT}` para no depender del `PATH`. `./build.sh check` valida la estructura y que el comando sea ejecutable. Los hooks se aplican en `link`, no en `build`.
2. **Matcher `Read|Grep|Glob|Bash`.** Solo una lectura pasiva pasa por la lógica del breaker. Un Bash activo se permite antes de evaluar el ping-pong, por paridad con Antigravity, cuyo matcher no intercepta `run_command`. Así un ciclo editar -> probar no se confunde con un bucle.
3. **Clasificación de Bash (B2).** Un comando es pasivo solo si todos sus segmentos (`|`, `;`, `&&`, `||`) son de una lista cerrada (`cat`, `head`, `grep`, `sed` sin `-i`, `find` sin `-exec`/`-delete`, `git log/show/diff/status`, `gh <recurso> view/list`, etc.) y no hay redirecciones a archivo, heredocs, sustitución de comandos ni asignaciones. Ante la duda, activo: un error de clasificación reinicia el contador, nunca bloquea.
4. **Transcript.** Se agrupa por `message.id` (un mensaje del modelo = un paso, igual que en Antigravity), se descartan los `tool_use` sin `tool_result` (la llamada en curso y sus paralelas, sin depender del orden de escritura) y se ignoran los registros `isMeta` e `isSidechain`. Solo un mensaje de usuario que no sea `tool_result` reinicia el contador.
5. **Paginación.** Se deniega un `Read` con `limit` > 200, o sin `limit` sobre un archivo de texto de más de 150 líneas.
6. **Salida.** Solo se emite salida al denegar. Ante cualquier error interno el hook falla en abierto.

### Consecuencias

* **Positivas:** la regla P0 se hace cumplir mecánicamente en ambos runtimes con una sola implementación. `CLAUDE_SKILLS_CIRCUIT_BREAKER` reduce su texto a la conducta ante el bloqueo, y #284 puede evacuar el resto.
* **Negativas / Trade-offs:** la lista de comandos pasivos requiere mantenimiento, y un comando pasivo no listado reinicia el contador. Los hooks quedan activos recién tras `./build.sh link`. Cada `Read` sin `limit` cuenta líneas del archivo (con corte temprano).
