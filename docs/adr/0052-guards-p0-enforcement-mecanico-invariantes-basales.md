---
status: accepted
date: 2026-11-08
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
references:
  - docs/adr/0043-hard-circuit-breaker-y-lifecycle-hooks.md
  - docs/adr/0046-limite-del-circuit-breaker-basado-en-datos.md
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
  - docs/adr/0049-regimen-transitorio-de-admision-p0.md
  - docs/adr/0051-hooks-deterministas-en-claude-code.md
---

# 0052 - Guards P0: Enforcement Mecánico de Invariantes Basales

## Contexto y Planteamiento del Problema

El ADR-0048 definió una arquitectura de 3 niveles de enforcement:
- **P0:** Enforcement mecánico determinista (hooks `PreToolUse`, `permissions.deny`, git hooks) para patrones detectables.
- **P1:** Procedimientos cargados bajo demanda en skills.
- **P2:** Prompt basal (`AGENTS.md`) reservado exclusivamente para criterios no verificables mecánicamente.

Hasta ahora, varias invariantes basales críticas solo existían como directivas de texto en `core/00-router.md`:
1. **Prohibición de REPL / evaluadores en línea (`ENV_PROHIBITION_REPL`):** `python3 -c`, `node -e`, `bash -c`, `eval`.
2. **Reconocimiento ciego del host (`ENV_ANTI_RECON`):** `find /`, `find $HOME`, `find ~`, `ls /`, etc.
3. **Uso exclusivo de APIs nativas de archivos (`ENV_NATIVE_FILE_API`):** I/O por terminal (`cat`, `sed`, `awk`, `tee`) sobre archivos del workspace.
4. **Inmutabilidad y no push a `main` (`TRACK_IMMUTABILITY_TRACEABILITY`):** Commits directos o `git push` apuntando a `main`.
5. **Prohibición de backlogs locales y archivos vetados (`TRACK_NO_LOCAL_BACKLOGS`, `TRACK_DECISIONS_MADR`):** `TODO.md`, `backlog.md`, `tasks/`, `prompts/`, `GEMINI.md`, `HISTORIAL.md`.

Al ser restricciones puramente textuales, los modelos las eludían ante saturación de contexto o razonamiento reducido. Es indispensable llevarlas a enforcement mecánico (P0) con compatibilidad dual para Antigravity y Claude Code.

## Impulsores de la Decisión (Decision Drivers)

* **Determinismo Absoluto:** Si un patrón de comando o mutación es mecánicamente identificable, debe bloquearse antes de ejecutarse (`decision: deny`).
* **Paridad Multi-Runtime:** Comportamiento idéntico y predecible en Antigravity y Claude Code.
* **Cero Falsos Positivos en Flujos Legítimos:**
  - Tuberías de filtrado (`| head`, `| grep`, `| jq`, `| awk '{print $1}'` desde stdin) no deben bloquearse.
  - Comandos de build, suite de pruebas (`./build.sh`, `pytest`, `python3 -m unittest`) y herramientas del workspace no deben bloquearse.
  - Escrituras autorizadas en temporales (`.commit_msg`, `.pr_body`, `.issue_*`) y `scratch/` deben permitirse.
* **Independencia de Runtime para Push a Main:** La protección de `main` debe operar incluso si el comando git se ejecuta fuera del entorno del agente o en terminal interactiva humana.
* **Separación de Responsabilidades:** `agent-circuit-breaker` se mantiene enfocado en el análisis histórico de transcript (lecturas pasivas y bucles ping-pong), mientras un nuevo binario `agent-guard` audita los argumentos de la herramienta en evaluación inmediata.

## Opciones Consideradas

### Protección contra push a `main`:
* **Opción A (Branch Protection en GitHub API):** Inviable. La API devuelve `HTTP 403: Upgrade to GitHub Pro or make this repository public to enable this feature`. En repositorios privados gratuitos no está habilitada.
* **Opción B (Git Hooks en `.githooks/`):** Viable y determinista. El repositorio ya cuenta con `core.hooksPath = .githooks`. Un hook `pre-push` y un hook `pre-commit` detienen físicamente la mutación en Git, independientemente del runtime o cliente usado.
* **Opción C (Interceptación en PreToolUse):** Complementaria. `agent-guard` deniega `git push ... main` o `git commit` sobre `main` antes de invocar el binario.

### Arquitectura del Guard:
* **Opción 1:** Sobrecargar `agent-circuit-breaker` con toda la lógica de filtrado de comandos y análisis sintáctico de shell. (Descartada: acopla dos responsabilidades distintas y dificulta las pruebas unitarias y el rendimiento).
* **Opción 2:** Crear `skills/conversation-audit/bin/agent-guard` como script de `PreToolUse` especializado en auditar llamadas activas entrantes (`run_command`, `Bash`, `write_to_file`, `Write`, `replace_file_content`, `Edit`), complementado con `.githooks/` y `permissions.deny` en Claude Code.

## Decisión Adoptada

Se adopta la **Opción B + C** y la **Opción 2**:

1. **Nuevo binario `agent-guard`:**
   - Reside en `skills/conversation-audit/bin/agent-guard`.
   - Soporta formato dual de entrada:
     - Antigravity: `toolCall: {name, args}` sobre `run_command`, `write_to_file`, `replace_file_content`.
     - Claude Code: `tool_name` y `tool_input` sobre `Bash`, `Write`, `Edit`.
   - Normaliza y tokeniza comandos shell para detectar de forma robusta:
     - Evaluadores REPL (`python3 -c`, `node -e`, `bash -c`, `eval`).
     - Reconocimiento ciego (`find /`, `find $HOME`, `find ~`, `find /home`, `ls /`, etc.).
     - I/O de terminal sobre archivos del workspace (`cat`, `sed`, `awk`, `tee`, redirecciones `>`).
     - Commits o pushes directos a `main`.
     - Creación/edición de archivos vetados (`TODO.md`, `backlog.md`, `tasks/`, `prompts/`, `GEMINI.md`, `HISTORIAL.md`).
   - Retorna `{"decision": "deny", "reason": "..."}` en Antigravity y `hookSpecificOutput` en Claude Code con la justificación y alternativa canónica.

2. **Filtro de falsos positivos:**
   - Exime comandos que empiezan con `./build.sh`, `python3 -m unittest`, `pytest`, `make`, o tooling autorizado (`agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`).
   - Diferencia filtros puros en pipeline (ej. `| head`, `| grep`, `| awk '{print ...}'` sin rutas de archivos, `cat` leyendo de pipe) de operaciones I/O dirigidas a archivos del disco.

3. **Git Hooks Locales en `.githooks/`:**
   - `.githooks/pre-push`: bloquea cualquier push que intente actualizar `refs/heads/main`.
   - `.githooks/pre-commit`: bloquea cualquier commit si la rama activa es `main`.

4. **Claude Code `permissions.deny` y Lifecycle Hook:**
   - `permissions.deny` en `runtimes/claude/settings.json` para fast-path estático sobre `Write(...)`, `Edit(...)` y `Bash(find /:*)`.
   - Hook `PreToolUse` sobre `Bash|Write|Edit` ejecutando `${DOTFILES_ROOT}/skills/conversation-audit/bin/agent-guard`.

5. **Antigravity Lifecycle Hook:**
   - Entrada `guards` en `runtimes/antigravity/hooks.json` sobre `run_command|write_to_file|replace_file_content`.

6. **Registro de Reglas Basales:**
   - Se actualiza `TRACK_DECISIONS_MADR` a `level=P0/P1` en `core/00-router.md` para reflejar el guard P0 sobre `GEMINI.md` e `HISTORIAL.md`.

## Consecuencias

### Positivas
* Las 5 invariantes basales críticas quedan protegidas mecánicamente con tolerancia cero a degradación de atención de LLMs.
* Push y commit a `main` quedan doblemente protegidos: a nivel de hook de agente (PreToolUse) y a nivel de Git local (`.githooks/`), mitigando la falta de branch protection remota.
* `lib/check.sh` valida la integridad de los guards, git hooks y la ausencia total de archivos prohibidos en el repo.

### Negativas / Mitigaciones
* `agent-guard` analiza comandos shell mediante tokenización; comandos altamente ofuscados o alias no estándar podrían requerir mantenimiento de reglas en el futuro. El diseño minimiza esto operando sobre binarios canónicos.
