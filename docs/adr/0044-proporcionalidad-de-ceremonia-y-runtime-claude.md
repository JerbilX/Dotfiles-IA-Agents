---
status: accepted
date: 2026-11-03
decision-makers: [Usuario, Claude]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0044 - Proporcionalidad de Ceremonia por Nivel y Equivalencias del Runtime Claude

## Contexto y Planteamiento del Problema
El `AGENTS.md` compilado es la base global de todos los agentes. Se observó sobreingeniería generalizada: toda tarea arrastraba issue con perfil, plan bloqueante, ADR, evaluación de blast radius, subagentes de exploración e higiene proactiva, y todo hallazgo secundario se convertía en issue. Además, el runtime `claude` carecía de reglas propias: las directivas nombran herramientas de Antigravity.

## Impulsores de la Decisión (Decision Drivers)
* Conservar la trazabilidad issue → rama → commit → PR (qué, por qué y cuándo).
* Reducir el costo de ceremonia por tarea sin relajar los invariantes de seguridad.
* Mantener el presupuesto de 800 palabras del `AGENTS.md` compilado.
* Operar los mismos repositorios desde Antigravity y Claude Code con las mismas reglas basales.

## Opciones Consideradas
* **Opción 1:** Eximir de issue a los cambios menores.
* **Opción 2:** Mantener el flujo y solo agregar una regla de "hacer lo mínimo".
* **Opción 3:** Escalar la ceremonia por niveles (N0/N1/N2) conservando la trazabilidad en todo cambio al workspace.

## Decisión Adoptada
Opción elegida: **"Opción 3"**. N0 (sin cambios al workspace) no requiere issue ni rama; N1 (cambio acotado) usa issue mínima sin plan, ADR ni perfil; N2 (feature, ambigüedad real, `core/`, `runtimes/` o ADR) conserva el ciclo E2E completo. Se agrega la regla de Proporcionalidad, los hallazgos secundarios requieren confirmación del usuario, la higiene se ejecuta al iniciar tarea o tras un merge, y el umbral de delegación a `research` sube a más de 8 archivos o pedido del usuario. El runtime `claude` incorpora `rules/01-claude-tools.md` con equivalencias de herramientas.

### Consecuencias
* **Positivas:** Menor fricción en tareas chicas, trazabilidad intacta, regla explícita contra el alcance excesivo, reglas utilizables desde Claude Code.
* **Negativas / Trade-offs:** La clasificación N0/N1/N2 depende del criterio del agente; `core/00-router.md` queda en el límite del presupuesto de palabras. Pendientes: hooks de circuit breaker y configuración MCP nativa para Claude Code.
