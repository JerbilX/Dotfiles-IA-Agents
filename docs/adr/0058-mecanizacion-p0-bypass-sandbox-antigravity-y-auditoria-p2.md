---
status: accepted
date: 2026-11-13
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
references:
  - docs/adr/0011-ratificacion-de-bypass-en-git-y-gh-por-restricciones-del-sandbox.md
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
  - docs/adr/0049-regimen-transitorio-de-admision-p0.md
  - docs/adr/0052-guards-p0-enforcement-mecanico-invariantes-basales.md
  - docs/adr/0054-evacuacion-de-guards-mecanicos-p0-del-prompt-basal.md
---

# 0058 - Mecanización P0 de Sandbox Bypass en Antigravity y Auditoría de Reglas P2

## Contexto y Planteamiento del Problema

En el runtime Antigravity, los agentes de IA se ejecutan dentro de un contenedor Linux restringido (sandbox vía namespaces y bwrap/Landlock). El system prompt base inyectado por Google DeepMind prescribe la directiva operativa *Try Sandboxed First* (`BypassSandbox: false`). Por otra parte, las directivas canónicas de Dotfiles-IA-Agents (ADR-0011) establecen que cualquier invocación de GitHub CLI (`gh`) y de subcomandos mutadores o remotos de Git (`git push`, `git fetch`, `git commit`, `git add`, etc.) requiere obligatoriamente `BypassSandbox: true` para acceder al keyring/configuración (`~/.config/gh/hosts.yml`) y superar el montaje de solo lectura (`EROFS`) de `.git/`.

Hasta el momento, esta excepción se gestionaba exclusivamente mediante texto en el prompt basal (`AGY_GIT_SANDBOX_BYPASS` en `runtimes/antigravity/rules/01-sandbox.md`, nivel P2). Esta arquitectura probabilística ocasionaba:
1. **Instruction Precedence Bias:** Los modelos favorecían recurrentemente la directiva de DeepMind ("Try Sandboxed First") por sobre la directiva de usuario en P2, ejecutando `gh` con `BypassSandbox: false` y fallando con `HTTP 401: Requires authentication`.
2. **Contaminación del Historial y Desperdicio de Tokens:** Cada fallo inyectaba trazas de error y forzaba un turno adicional de razonamiento y reintento (~400 a 600 tokens perdidos por incidente en la ventana de contexto).
3. **Sobrecarga del Prompt Basal:** Describir excepciones técnicas en texto inflaba permanentemente la ventana de tokens en cada turno de todas las sesiones.

Se requiere promover esta salvaguarda a enforcement mecánico determinista (P0) conforme a la jerarquía establecida en ADR-0048, y auditar el catálogo completo de reglas canónicas para identificar oportunidades adicionales de mecanización de P2 hacia P0.

## Impulsores de la Decisión (Decision Drivers)

* **Determinismo en Nivel P0:** Sustituir la adhesión probabilística del LLM por resolución mecánica a nivel de Lifecycle Hooks antes de que el comando alcance el contenedor.
* **Economía de Contexto y Reducción del Historial:** Eliminar turnos fallidos por errores 401 y podar el texto redundante del prompt basal en `01-sandbox.md`.
* **Zero-Intervention Developer Experience:** Garantizar que comandos legítimos de `gh` y Git mutador funcionen al primer intento sin intervención humana ni reintentos del agente.
* **Preservación de Invariantes de Seguridad:** Mantener el sandbox estricto para operaciones pasivas locales (`git status`, `git diff`, `git log`, `build.sh check`, tests unitarios) y asegurar que las denegaciones (`decision: deny`) de guards P0 prevalezcan sobre cualquier bypass.

## Decisión Adoptada

### 1. Mecanización P0 de Sandbox Bypass en Antigravity (`PreToolUse` Hook)

Se implementa en `skills/conversation-audit/bin/agent-guard` la función determinista `command_requires_sandbox_bypass(command: str) -> bool`:
- **GitHub CLI (`gh`):** Toda invocación a `gh` (ej. `gh issue view`, `gh pr create`, `gh api`, `gh project`, `gh run`, etc.) exige `BypassSandbox: true` por requerir credenciales en el host y acceso a red.
- **Git Mutador y de Red:** Subcomandos que escriben en `.git/` o acceden a remotos (`init`, `clone`, `fetch`, `pull`, `push`, `commit`, `merge`, `rebase`, `cherry-pick`, `revert`, `reset`, `restore`, `checkout`, `switch`, `add`, `rm`, `mv`, `tag`, `stash`, `clean` y operaciones mutadoras de `branch` como `-d`, `-D`, `-m`, `-M` o creación) exigen `BypassSandbox: true`.
- **Inspección Pasiva Confinada:** Operaciones de solo lectura (`git status`, `git diff`, `git log`, `git show`, `git rev-parse`, `git branch` de consulta) permanecen 100% confinadas en sandbox (`BypassSandbox: false`).
- **Tooling Autorizado:** Comandos que delegan en `gh` o Git mutador (`gh-pr-review`, `git-prune-gone`) exigen `BypassSandbox: true`.

### 2. Modificación Dinámica de Argumentos mediante `overwrite`

Cuando Antigravity emite una llamada a `run_command` (o `bash`/`execute_command`):
1. `agent-guard` evalúa las invariantes duras P0 (no push a `main`, no REPL, no I/O terminal sobre workspace, no archivos prohibidos). Si se detecta una violación, retorna `{"decision": "deny", "reason": "Guard P0 Activado: ..."}` con precedencia absoluta.
2. Si el comando es válido y `command_requires_sandbox_bypass` retorna `True`, y el agente proveyó `BypassSandbox: false` (o lo omitió), el hook retorna:
   ```json
   {
     "decision": "allow",
     "overwrite": {
       "BypassSandbox": true
     }
   }
   ```
3. El runtime de Antigravity aplica un merge superficial sobre los argumentos de la herramienta, inyectando `BypassSandbox: true` antes de la ejecución y ejecutando el comando sin fallos de autenticación ni aislamiento de filesystem.

### 3. Poda Sustractiva del Prompt Basal

En cumplimiento de ADR-0048 §2.2, se reduce la directiva `AGY_GIT_SANDBOX_BYPASS` en `runtimes/antigravity/rules/01-sandbox.md` de 33 a 18 palabras:
```markdown
<!-- rule: id=AGY_GIT_SANDBOX_BYPASS level=P0/P2 origin=#382 -->
- **Ejecución de Git y Bypass:** Bypass de sandbox automatizado en P0 para gh y git mutador; temporales (.commit_msg, .pr_body) en <appDataDir>/brain/<conversation-id>/scratch/.
```
Esta reducción permanente de palabras beneficia a todas las sesiones de Antigravity en cada turno conversacional.

---

## 4. Informe de Auditoría: Viabilidad de Promoción P2 -> P0 del Catálogo Canónico

Se auditaron las 33 reglas basales que componen el catálogo canónico (`core/` y `runtimes/*/rules/`), clasificando su viabilidad técnica de promoción de P2 a P0 bajo el estándar de ADR-0048:

### A. Reglas Mecanizadas en P0 (Implementadas o Activas)
1. `ENV_ANTI_RECON` (`P0/P2`): Bloqueo de `find /`, `find $HOME`, `ls /` en `agent-guard`. Huella residual mínima en P2.
2. `TRACK_IMMUTABILITY_TRACEABILITY` (`P0/P2`): Bloqueo de commit/push directo a `main` en `agent-guard` y git hooks (`.githooks/pre-push`, `pre-commit`).
3. `TRACK_NO_LOCAL_BACKLOGS` (`P0/P2`): Bloqueo físico de creación/edición de `TODO.md`, `backlog.md`, `tasks/`, `prompts/` en `agent-guard`.
4. `TRACK_DECISIONS_MADR` (`P0/P2`): Bloqueo físico de `GEMINI.md` e `HISTORIAL.md` en `agent-guard`.
5. `AGY_GIT_SANDBOX_BYPASS` (`P0/P2`): Mecanizado en P0 mediante `overwrite: {"BypassSandbox": true}` en `agent-guard` (Issue #382).
6. `CLAUDE_SKILLS_CIRCUIT_BREAKER` (`P0/P2`): Interdicción mecánica vía `agent-circuit-breaker` y `agent-guard`.

### B. Candidatas Prioritarias para Futura Promoción a P0 (Alta / Media Viabilidad)
1. **`UNPAGINATED_FILE_READ` (Lecturas no paginadas masivas):**
   - *Estado actual:* Auditado post-hoc por `agent-audit` y restringido en Claude Code por hook `Read`.
   - *Viabilidad P0 en Antigravity:* **Alta**. En `agent-circuit-breaker` o `agent-guard`, inspeccionar `view_file`. Si `StartLine`/`EndLine` faltan o la ventana supera 200 líneas, inyectar `overwrite` con ventana acotada o denegar con `decision: deny`.
2. **`TERMINAL_REPL_LOOP` (Wrappers y evaluadores iterativos):**
   - *Estado actual:* Evaluadores directos (`python -c`, `node -e`, `bash -c`, `eval`) ya son bloqueados por `agent-guard`.
   - *Viabilidad P0 para loops:* **Alta**. Monitorear secuencias de comandos de terminal consecutivos similares en `agent-circuit-breaker`, deteniendo bucles repetitivos de prueba-error antes de alcanzar la parálisis.
3. **`AGY_ARTIFACT_METADATA_SCOPE` (Alcance de ArtifactMetadata):**
   - *Estado actual:* Regla P2 en `01-sandbox.md`.
   - *Viabilidad P0:* **Alta**. En `agent-guard`, inspeccionar `write_to_file`. Si `TargetFile` no reside dentro de `<appDataDir>/brain/<conversation-id>/` y trae `ArtifactMetadata`, el hook puede eliminar mecánicamente el campo `ArtifactMetadata` vía `overwrite` o emitir denegación explicativa.
4. **`AGY_NATIVE_FILE_INSPECTION` (Inspección Pasiva de Archivos):**
   - *Estado actual:* P0 bloquea `cat`, `sed`, `awk`, `tee`.
   - *Viabilidad P0:* **Alta**. Extender `_check_terminal_file_io` en `agent-guard` para bloquear también `head` y `tail` dirigidos a archivos del workspace, canalizando hacia `view_file`.
5. **`ENV_WORKSPACE` (Confinamiento de Workspace):**
   - *Estado actual:* P0/P2 con criterio textual.
   - *Viabilidad P0:* **Media-Alta**. En `agent-guard`, bloquear rutas que contengan traversals (`../`) o rutas absolutas fuera del workspace activo (salvo directorios autorizados como `.gemini/` o `/tmp`).

### C. Reglas Inviables en P0 (P2 Puro o P1 por Juicio / Heurística No Mecanizable)
1. `ENV_NORMATIVE_IMMUNITY` (P2): Criterio epistemológico sobre validez de fuentes de verdad.
2. `ENG_PROPORTIONALITY_MBR` (P2): Juicio cualitativo de proporcionalidad y Minimal Blast Radius.
3. `ENG_PRODUCTION_CODE_PREVALENCE` (P2): Criterio de ingeniería sobre contratos reales vs mocks.
4. `LOGIC_INCONSISTENCY_STOP_ASK` (P2): Heurística de detección de contradicciones y freno.
5. `LOGIC_ISSUE_AS_PROPOSAL` (P2): Criterio crítico de contraste de issues contra ADRs vigentes.
6. `RIGIDITY_DIRECTIVE_BOUNDARY`, `RIGIDITY_ACTIONABLE_FALLBACK` (P2): Directivas metodológicas y heurísticas conversacionales.
7. `CRIT_ZERO_COMPLACENCY`, `CRIT_CHALLENGE_PROPOSE`, `CRIT_ZERO_FLATTERY_APOLOGIES` (P2): Normas de conducta e interacción conversacional.
8. `SKILL_ROUTING_*` (P2): Tabla de ruteo canónico indispensable en P2 para el descubrimiento y activación de skills P1.

---

## Consecuencias y Efectos

### Positivas
* **Eliminación determinista de fallos 401 en `gh`:** Antigravity ejecuta `gh` con `BypassSandbox: true` de forma mecánica y transparente.
* **Ahorro permanente de contexto:** Reducción de 15 palabras en el prompt basal compilado y eliminación de 400-600 tokens de reintentos por incidencia.
* **Compatibilidad Multi-Runtime:** Claude Code permanece protegido con su contrato existente sin alteraciones de comportamiento.
* **Cobertura Unitaria:** 47 pruebas unitarias en `test_agent_guard.py` certificando la detección y no-regresión.

### Negativas / Deuda Mitigada
* Modificaciones de herramientas vía `overwrite` generan un aviso informativo en el transcript de Antigravity indicando que un hook modificó `BypassSandbox`. Esto es esperado y beneficia la trazabilidad de la sesión.
