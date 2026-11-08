---
status: accepted
date: 2026-11-08
decision-makers: [JerbilX, Claude Code]
supersedes: []
superseded-by: []
references:
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
---

# 0049 - Régimen Transitorio del Control de Admisión P0

## Contexto y Planteamiento del Problema

ADR-0048 §2.2 limita la huella de una regla P0 en el basal a una sola línea residual, y #286 exige que `./build.sh check` falle si una regla `P0` conserva más de una línea. Pero las reglas mixtas (`P0/P2`, `P0/P1`) de la línea base (§6) todavía no tienen su componente P0 implementado como hook (#283, #284, #287): su texto basal sigue cumpliendo la función del control mecánico ausente. `AGY_GIT_SANDBOX_BYPASS` y `AGY_BYPASS_EXCLUSIVITY` ocupan varias líneas y hasta 98 palabras. Aplicar hoy el control estricto a esas reglas dejaría `check` en estado bloqueante, o forzaría a recortar texto que todavía no tiene reemplazo mecánico.

## Impulsores de la Decisión (Decision Drivers)

* Cumplir el criterio de #286 sin bloquear el repositorio antes de la evacuación de #283/#284.
* Evitar que el control se cumpla solo con quitar saltos de línea.
* Impedir que las reglas P0 crezcan mientras dura la transición.

## Opciones Consideradas

* **Opción 1:** Error de una línea para toda regla con componente P0.
* **Opción 2:** Solo advertencias, sin error de línea.
* **Opción 3:** Error de una línea para reglas `P0` puras; advertencia para reglas mixtas pendientes de evacuación, con un techo transitorio de palabras como error.

## Decisión Adoptada

Opción elegida: **"Opción 3"**, porque cumple el criterio de #286 donde ya es aplicable y deja la deuda de las reglas mixtas visible en cada `check`, sin estado bloqueante.

1. **Reglas `P0` puras:** error si conservan más de una línea física en el basal.
2. **Reglas mixtas con componente P0:** mientras su hook no exista, se rigen por su parte P2. Si conservan más de una línea, `check` emite una advertencia de evacuación pendiente.
3. **Techo transitorio de 100 palabras (error):** aplica a toda regla con componente P0. Se fijó por encima de la regla más extensa de la línea base (98 palabras) para no bloquear, y su función es impedir el crecimiento hasta la evacuación.
4. **Banda residual de 30 palabras (advertencia):** se mantiene como meta del §2.2 de ADR-0048.

**Salida del régimen:** al cerrar la evacuación de #283/#284, revisar este ADR para convertir la advertencia de reglas mixtas multilínea en error y bajar el techo hacia la banda residual de 30 palabras.

### Consecuencias

* **Positivas:** `check` hace cumplir el §2.2 en las reglas `P0` puras y frena el crecimiento de las mixtas; la deuda de evacuación queda listada en cada ejecución.
* **Negativas / Trade-offs:** mientras dure la transición, una regla mixta puede ocupar varias líneas y hasta 100 palabras sin fallar `check`. El techo de 100 palabras es un valor operativo, no derivado del §2.2.
