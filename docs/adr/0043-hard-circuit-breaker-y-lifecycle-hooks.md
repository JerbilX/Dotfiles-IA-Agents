---
status: accepted
date: 2026-11-02
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0043 - Hard Circuit Breaker y Soporte de Lifecycle Hooks

## Contexto y Planteamiento del Problema

Durante la auditoría de rendimiento y estabilidad de la sesión `42ab3442-7f15-48f1-8c7a-ed6d6d5fb972` (Issue #217), se constató un bucle operativo persistente donde el agente realizó 39 llamadas consecutivas a `view_file` en un lapso de 17 minutos, sin emitir respuesta ni ejecutar acciones intermedias observables.

El análisis forense evidenció dos limitaciones estructurales en el enfoque previo adoptado en el Issue #215:
1. **Brecha de Evasión por Ping-Pong Multi-Archivo:** La directiva basal en `core/00-router.md` restringía *"máximo 2 llamadas consecutivas a view_file sobre un mismo archivo"*. El modelo eludió esta restricción alternando llamadas entre `SettlementEvaluator.lua`, `SpikeA.lua` y `SpikeB.lua`, cayendo en un bucle cíclico continuo de inspección multi-archivo.
2. **Fragilidad de Restricciones Exclusivamente Basadas en Prompts (*Soft Constraints*):** Las reglas en Markdown dentro de `AGENTS.md` dependen de la observancia probabilística del LLM. En escenarios de saturación de contexto, pérdida de atención o modelos sin tokens de razonamiento (`Gemini 3.8 Flash (Low)`), el agente ignora las directivas de texto.
3. **Carencia de Mecanismo Determinista de Interrupción:** No existía una barrera mecánica a nivel de plataforma que impidiera físicamente la ejecución de herramientas pasivas cuando se sobrepasa el umbral de seguridad.

## Impulsores de la Decisión (Decision Drivers)

* **Determinismo Absoluto (Zero-Bypass de Seguridad):** Las restricciones críticas de detención de bucles no pueden depender de la buena voluntad del modelo; deben ejecutarse de forma mecánica e ineludible.
* **Integración Nativa de Ciclo de Vida:** Antigravity provee soporte para Lifecycle Hooks (`PreToolUse` en `hooks.json`), permitiendo evaluar parámetros y bloquear invocaciones (`decision: deny`) antes de que se ejecute la herramienta.
* **Cero Dependencias Externas (Standard Library First):** El mecanismo de interrupción y las comprobaciones deben operar al 100% con Python 3 estándar (`json`, `sys`, `os`, `pathlib`).
* **Presupuesto Estricto de Contexto:** Las directivas de `core/00-router.md` deben mantenerse compactas para respetar el límite de 800 palabras en `antigravity`.

## Opciones Consideradas

* **Opción 1:** Ajustar únicamente el texto de `core/00-router.md` para prohibir la alternancia de archivos. (Insuficiente: vulnerable a degradación de atención del modelo en contextos largos).
* **Opción 2:** Implementar un Lifecycle Hook determinista (`PreToolUse` en `hooks.json`) gestionado por `build.sh`, respaldado por el script `agent-circuit-breaker`, junto con el endurecimiento de la regla basal en `core/00-router.md` y la ampliación de antipatrones en `agent-audit`.
* **Opción 3:** Delegar toda lectura de archivos a subagentes efímeros aislados. (Inviable: introduce latencia extrema en tareas habituales de edición local).

## Decisión Adoptada

Se adopta la **Opción 2**:

1. **Hard Circuit Breaker Determinista (`agent-circuit-breaker`):**
   - Se crea el binario ejecutable `skills/conversation-audit/bin/agent-circuit-breaker` conforme al contrato `PreToolUse` de Antigravity.
   - Consume el payload JSON por `stdin`, inspecciona el log de transcripción (`transcriptPath`) y computa la cantidad de llamadas pasivas consecutivas (`view_file`, `grep_search`, `find_by_name`, `list_dir`).
   - Si se intentan más de 3 lecturas consecutivas sin una mutación intermedia (`write_to_file`, `replace_file_content`) o ejecución de comando (`run_command`), responde deterministamente `{"decision": "deny", "reason": "..."}`, forzando al modelo a detenerse y actuar.
2. **Soporte de Lifecycle Hooks en Dotfiles:**
   - Se extiende el esquema canónico `runtimes/schema/runtime-config.schema.json` para dar soporte a `hooks_filename`.
   - Se implementa `runtimes/antigravity/hooks.json` configurando el evento `PreToolUse` para herramientas pasivas.
   - Se integran helpers de compilación, symlinks y auditoría estática en `lib/build_core.sh`, `lib/link.sh` y `lib/check.sh`.
3. **Endurecimiento de Directiva Basal (`core/00-router.md`):**
   - Se modifica el Circuit Breaker para vetar un máximo de 3 lecturas pasivas globales consecutivas sin acción intermedia observable, independientemente de si alternan entre distintos archivos.
4. **Detección Ampliada en `agent-audit`:**
   - Se incorporan los antipatrones `READ_ONLY_LOOP` (inspección continua desmedida) y `PING_PONG_TOOL_LOOP` (bucle cíclico alternante) en `scripts/audit_engine.py`.

## Consecuencias

### Positivas
* Se elimina de raíz la posibilidad de bucles infinitos de lectura, tanto a nivel lógico (prompt) como a nivel mecánico (hook nativo `PreToolUse`).
* `agent-audit` adquiere capacidad forense para señalar parálisis por inspección y bucles de alternancia multi-archivo.
* El pipeline de aprovisionamiento de dotfiles queda formalmente habilitado para gestionar lifecycle hooks en runtimes compatibles.

### Negativas / Mitigaciones
* Requiere que el usuario enlace o actualice `hooks.json` en `~/.gemini/config/hooks.json` vía `./build.sh link`.
* Si un flujo legítimo requiere explorar más de 3 archivos, el agente debe formular hipótesis intermedias o apoyarse en subagentes especializados (`research`), promoviendo el ahorro de contexto.
