---
status: accepted
date: 2026-11-09
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
references:
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
  - docs/adr/0049-regimen-transitorio-de-admision-p0.md
  - docs/adr/0052-guards-p0-enforcement-mecanico-invariantes-basales.md
---

# 0054 - Evacuación de Guards Mecánicos P0 del Prompt Basal

## Contexto y Planteamiento del Problema

El ADR-0048 formalizó la separación en tres niveles de enforcement:
- **P0:** Enforcement mecánico determinista (hooks pre-tool, denegación física y git hooks).
- **P1:** Procedimientos especializados cargados bajo demanda en skills.
- **P2:** Prompt basal inyectado en cada sesión para criterios heurísticos no verificables por tooling.

Bajo el ADR-0049 se estableció un régimen transitorio donde las reglas P0 puras se redujeron a una línea residual de acción ante bloqueo (≤ 30 palabras). Posteriormente, el ADR-0052 implementó los hooks pre-tool `agent-guard` y `agent-circuit-breaker` en Antigravity y Claude Code, garantizando interdicción mecánica determinista para:
1. `ENV_NATIVE_FILE_API`: Bloqueo físico de I/O sobre archivos vía terminal (`cat`, `sed`, `awk`, `tee`).
2. `ENV_PROHIBITION_REPL`: Bloqueo físico de evaluadores en línea y subshells (`python -c`, `node -e`, etc.).
3. `ENV_PAGED_READ_CIRCUIT_BREAKER`: Bloqueo físico tras ráfagas consecutivas de inspección pasiva.

Dado que los hooks emiten mensajes de error autocontenidos y accionables que indican inmediatamente al modelo la alternativa correcta al momento de la interdicción, mantener estas directivas estáticas en `core/00-router.md` introduce redundancia y consumo innecesario del presupuesto de tokens en cada turno de conversación.

## Impulsores de la Decisión (Decision Drivers)

* **Economía de Contexto y Progressive Disclosure Radical:** Maximizar el espacio útil en la ventana de contexto de los agentes eliminando instrucciones que ya están 100% blindadas por software.
* **Cero Duplicación de Enforcement:** El comportamiento restrictivo se ejecuta en la capa más baja y determinista disponible (MBR Capa 1 Tooling / Capa 3 Runtime Hooks).
* **Certificación Estructural en Pruebas:** La garantía de preservación de estas invariantes críticas no debe basarse en la presencia de texto estático en el prompt basal, sino en la existencia activa y comprobada de los hooks ejecutables y su cobertura en pruebas unitarias.

## Opciones Consideradas

* **Opción 1: Evacuación total del prompt basal (Seleccionada).**
  Retirar completamente las directivas `ENV_NATIVE_FILE_API`, `ENV_PROHIBITION_REPL` y `ENV_PAGED_READ_CIRCUIT_BREAKER` de `core/00-router.md`. La instrucción correctiva se entrega dinámicamente en el mensaje de error del hook si el agente llega a intentar la acción no autorizada.
* **Opción 2: Fusión en una sola regla residual consolidada.**
  Condensar las tres reglas en una única viñeta genérica (≤ 30 palabras). Aunque ahorra tokens parcialmente, perpetúa la redundancia conceptual de describir en texto lo que el hook intercepta mecánicamente.
* **Opción 3: Evacuación a Skills (P1).**
  Mover las directivas a `issue-driven-workflow`. Inadecuado porque estas invariantes son universales y aplican a cualquier interacción del agente, no solo al flujo de desarrollo de issues.

## Decisión

1. **Evacuar de `core/00-router.md`:** Se eliminan definitivamente las directivas `ENV_NATIVE_FILE_API`, `ENV_PROHIBITION_REPL` y `ENV_PAGED_READ_CIRCUIT_BREAKER`, junto con sus comentarios de metadatos HTML.
2. **Delegación Mecánica:** El enforcement queda delegado 100% a `agent-guard` y `agent-circuit-breaker` vía `runtimes/antigravity/hooks.json` y la configuración de hooks de Claude Code.
3. **Certificación en Arnés de Tests:** Se actualiza `tests/test_progressive_disclosure.py` retirando los asertos textuales de `test_core_invariants_preserved` e incorporando `test_p0_invariants_mechanically_enforced`, el cual certifica que:
   - Los hooks pre-tool estén debidamente configurados en los manifiestos de runtime.
   - Los binarios ejecutables correspondientes existan y tengan permisos de ejecución.
   - La suite `test_agent_guard.py` preserve la cobertura unitaria de interdicción y ausencia de falsos positivos.

## Consecuencias

### Positivas
* **Reducción del Prompt Basal:** Reducción neta de tokens en `core/00-router.md` y en los archivos compilados `dist/*/AGENTS.md` para todos los runtimes.
* **Claridad Arquitectónica:** Consolidación estricta de la jerarquía de enforcement: lo determinista corre en hooks mecánicos; el prompt basal conserva únicamente ruteo, objetividad e invariantes de gobernanza heurística (P2).

### Negativas / Mitigaciones
* **Ausencia de Señal Preventiva Inicial:** Un modelo en una sesión limpia que no haya sido expuesto previamente a la restricción podría intentar un comando no permitido (como `cat` o un `python -c`).
  * *Mitigación:* Los mensajes emitidos por `agent-guard` y `agent-circuit-breaker` son inmediatamente accionables e instruyen al modelo sobre la herramienta nativa o prueba en `scratch/` a utilizar, recuperando el flujo sin desvío.
