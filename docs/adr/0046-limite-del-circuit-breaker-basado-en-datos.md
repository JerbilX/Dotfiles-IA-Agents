---
status: accepted
date: 2026-11-05
decision-makers: [Usuario, Claude]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0046 - Límite del Circuit Breaker de Lectura Basado en Datos y Salida por Síntesis

## Contexto y Planteamiento del Problema
ADR-0043 fijó en 3 el máximo de lecturas pasivas consecutivas (hook `agent-circuit-breaker` y directivas). El valor no tenía respaldo empírico. En la sesión `77fd4067` (#239), el agente salió del bloqueo con una edición grande. El análisis del hook mostró que solo una herramienta activa o un mensaje del usuario reinician el contador, y que el mensaje de bloqueo priorizaba "procede a editar código".

## Impulsores de la Decisión (Decision Drivers)
* Cortar la parálisis por inspección sin cortar la exploración normal.
* No incentivar ediciones provisorias ni comandos irrelevantes para reiniciar el contador.
* Decidir con datos de sesiones reales.

## Datos
Rachas de lecturas pasivas consecutivas en ~200 sesiones de Antigravity, contadas con la lógica del hook:

| Racha | Sin hook (859 rachas, ≤ 2026-11-01) | Con hook en 3 (645 rachas) |
|---|---|---|
| 1 | 47% | 45% |
| 2 | 21% | 20% |
| 3 | 9% | 27% |
| 4–9 | 16% | 4% |
| 10+ | 7% (picos de 53 y 113) | 3% |

La exploración normal decae de 1 a 9; aparte hay una cola de parálisis de 10+. El límite 3 cortaba el 23% de las rachas naturales. Después de una activación registrada, el agente corrió un comando o editó en 6 de 9 casos y nunca sintetizó (muestra chica: el transcript rara vez guarda los rechazos del hook).

## Opciones Consideradas
* **Opción 1:** Mantener 3.
* **Opción 2:** Subir a 5 (corta el 13%).
* **Opción 3:** Subir a 6 (corta el 11%, incluida toda la cola de parálisis).
* **Opción 4:** Subir a 8 (corta el 8%, casi solo la cola, con más contexto acumulado por racha).

## Decisión Adoptada
Opción elegida: **"Opción 3"**. Límite de 6 lecturas pasivas consecutivas en el hook (`DEFAULT_MAX_PASSIVE_READS`) y en las directivas (`core/00`, `core/06`, `issue-driven-workflow`). El mensaje de bloqueo prescribe primero detenerse y sintetizar (hallazgos, hipótesis, plan; Stop & Ask si falta información), limita la edición o las pruebas a cuando hay evidencia suficiente para un cambio acotado, y prohíbe ediciones provisorias o comandos irrelevantes para reiniciar el contador. El detector de ping-pong no cambia.

### Consecuencias
* **Positivas:** La exploración normal deja de cortarse en 1 de cada 4 rachas; se mantiene el corte de la parálisis; la salida prescrita deja de empujar a editar.
* **Negativas / Trade-offs:** Hasta 6 lecturas acumulan más contexto por racha. Nada impide mecánicamente reiniciar el contador con un comando irrelevante: depende de la directiva. Conviene repetir la medición de rachas (método descrito en #239) después de unos días de uso.
