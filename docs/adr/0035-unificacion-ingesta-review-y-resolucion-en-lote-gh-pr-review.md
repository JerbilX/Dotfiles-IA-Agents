---
status: accepted
date: 2026-10-24
decision-makers: [Usuario, Agente]
supersedes: ["0022-protocolo-de-resolucion-autonoma-de-code-review.md"]
superseded-by: []
---

# 0035 - Unificación de Ingesta de Review y Resolución en Lote de Hilos en gh-pr-review

## Contexto y Planteamiento del Problema

El sub-protocolo de feedback loop de Code Review formalizado en ADR-0022 y modularizado con tooling de Nivel 1 en ADR-0025 introdujo la herramienta determinista `skills/issue-driven-workflow/bin/gh-pr-review`. Dicho tooling redujo drásticamente el desborde de buffer y el consumo de contexto frente a tuberías complejas de shell.

Sin embargo, tras la experiencia acumulada y el análisis forense de sesiones (Issue #138), se identificaron dos ineficiencias críticas de red y procesos en el ciclo de revisión:

1. **Ingesta Duplicada (C5):** La Fase 2 de `references/code-review.md` exigía ejecutar dos comandos remotos independientes:
   - `gh pr view <pr_id> --comments`: Obtiene comentarios generales y veredicto en texto no estructurado.
   - `gh-pr-review comments <pr_id>`: Obtiene los hilos inline del diff en JSON estructurado.
   Esto consume dos llamadas con bypass de sandbox y round-trips de red para reconstruir un único contexto de revisión.
2. **Resolución N+1 de Hilos (C6):** El subcomando `gh-pr-review resolve` (incluyendo `--all <pr_id>` o múltiples IDs) iteraba secuencialmente sobre cada hilo invocando una mutación GraphQL `resolveReviewThread` por subprocess independiente. Para $N$ hilos pendientes, se ejecutaban $N$ procesos `gh` secuenciales, multiplicando la latencia y la fricción operativa.

Se requiere unificar la ingesta en una única consulta GraphQL estructurada y resolver múltiples hilos de forma agregada en una sola mutación por lotes, preservando el contrato de salida, el manejo de errores por hilo y la validación estricta de `isResolved` (Issue #127).

## Impulsores de la Decisión (Decision Drivers)

* **Eficiencia de Red y Disminución de Turnos/Procesos:** Minimizar los round-trips contra la API de GitHub pasando de $1 + N$ llamadas a una sola llamada de lectura y $\lceil N / \text{lote} \rceil$ mutaciones de resolución.
* **Principio de Mínima Intervención (Minimal Blast Radius - ADR-0017):** Resolver el problema estrictamente en Nivel 1 (Tooling local `gh-pr-review` y suite de pruebas unitarias), sin elevar requerimientos ni modificar directivas basales (`core/`).
* **Preservación del Contrato de Salida y Robustez de Errores:** Mantener el formato JSON esperado (`success`, `resolvedCount`, `resolvedThreads`, `errors`), garantizando que la falla de un hilo individual no invalide la resolución de los demás dentro del mismo lote (fallo parcial tolerante).
* **Validación Estricta de Integridad (`isResolved`):** Impedir falsos positivos mediante la verificación rigurosa de que cada hilo devuelva efectivamente `isResolved: true` en el payload de la mutación.
* **Flexibilidad Operativa:** Incorporar la capacidad de omitir el payload general de revisiones (`--threads-only`) si el cliente únicamente requiere procesar comentarios de diff.

## Opciones Consideradas

* **Opción 1: Conservar `gh pr view --comments` y paralelizar con subprocesos locales (ThreadPoolExecutor).**
  * Lanzar múltiples llamadas concurrentes de `gh api graphql` en paralelo desde Python.
  * *Descarte:* Aunque reduce el tiempo total wall-clock respecto a la ejecución secuencial, sigue consumiendo $N$ procesos de sistema y $N$ conexiones HTTP simultáneas contra el endpoint de GitHub, corriendo riesgo de rate limiting y desbordamiento de descriptores de archivo en sandbox.
* **Opción 2: Unificación de Ingesta GraphQL y Resolución por Lotes con Aliases GraphQL (Nivel 1).**
  * Extender la query de `cmd_comments` para incluir en el mismo payload de `pullRequest`: `reviewDecision`, `reviews(first: 50)` y `comments(first: 50)`.
  * Diseñar la mutación agregada en `resolve_threads_batch` utilizando alias de campos GraphQL (`t0: resolveReviewThread(...)`, `t1: ...`), particionada en lotes de tamaño configurable ($\le 50$ hilos por lote).
  * Parsear respuestas combinadas de `data` y `errors` de GraphQL para atribuir errores puntuales a cada `threadId` mediante su alias o ruta (`path: ["tX"]`), manteniendo `resolvedThreads` para aquellos confirmados con `isResolved: true`.
  * Proveer el flag `--threads-only` en `comments` para suprimir `reviewDecision`, `reviews` y `prComments` cuando solo se precisen hilos.

## Decisión Adoptada

Se adopta la **Opción 2**, estructurada en las siguientes directivas:

1. **Ingesta Unificada de Revisión (`comments`):**
   * La consulta GraphQL de `cmd_comments` solicita atómicamente:
     - `reviewDecision`: Veredicto del PR (`APPROVED`, `CHANGES_REQUESTED`, etc.).
     - `reviews(first: 50)`: Lista estructurada con `author`, `state`, `body` y `submittedAt`.
     - `comments(first: 50)`: Lista estructurada de comentarios de nivel PR con `author`, `body` y `createdAt`.
     - `reviewThreads(first: 100)`: Hilos inline paginados como en el contrato previo.
   * Por defecto, el JSON emitido expone `reviewDecision`, `reviews` y `prComments` en la raíz del objeto resumen.
   * Con el flag `--threads-only`, se omiten estas tres claves, preservando retrocompatibilidad compacta.
   * Se elimina `gh pr view <pr_id> --comments` del flujo estándar en `references/code-review.md` y `SKILL.md` §5.
2. **Resolución Agregada por Lotes (`resolve`):**
   * Se introduce `resolve_threads_batch(thread_ids, batch_size=50)` que genera dinámicamente:
     ```graphql
     mutation($t0: ID!, $t1: ID!) {
       t0: resolveReviewThread(input: {threadId: $t0}) {
         thread { id isResolved }
       }
       t1: resolveReviewThread(input: {threadId: $t1}) {
         thread { id isResolved }
       }
     }
     ```
   * Atribución precisa de errores: Si la mutación arroja errores parciales, se asocian al `threadId` correspondiente mapeando el alias `tX` en `path`. Si el payload devuelto no confirma `isResolved: true`, se marca como error no resuelto.
   * Los lotes se dividen en tamaños de $\le 50$ elementos, ejecutando exactamente $\lceil N / 50 \rceil$ mutaciones GraphQL.
3. **Manejo Resiliente en `run_gh_graphql`:**
   * Cuando `proc.returncode != 0`, si `stdout` contiene un JSON válido con campos `data` o `errors`, se preserva el payload para permitir a `resolve_threads_batch` procesar resoluciones exitosas y mapear fallos parciales con precisión.

### Consecuencias

* **Positivas:**
  * Reducción drástica del número de procesos e interacciones de red durante el ciclo de code review ($1$ lectura en vez de $2$, $\lceil N/50 \rceil$ mutaciones en vez de $N$).
  * Ingesta estructurada en JSON de veredicto, reviews y comentarios de PR sin depender de salidas en texto plano de `gh pr view`.
  * Tratamiento robusto de fallos parciales: si un hilo falla dentro de un lote (ej. ID inexistente o ya eliminado), los hilos válidos del mismo lote se resuelven exitosamente.
  * Cero alteraciones en directivas basales (`core/`), respetando el Minimal Blast Radius.
* **Negativas / Trade-offs:**
  * Ligeramente mayor complejidad en la construcción dinámica de strings de mutación GraphQL y el parseo de errores por alias. Mitigado con cobertura de pruebas unitarias exhaustivas con `gh` mockeado.

### Pros y Contras de las Opciones

#### Opción 1: Conservar gh pr view y subprocesos paralelos
* **Pro:** No requiere construir queries GraphQL con alias dinámicos.
* **Contra:** Consume $N$ subprocesos de sistema, riesgo de saturación de descriptores de archivo, no resuelve la salida no estructurada de `gh pr view`.

#### Opción 2: Ingesta unificada y mutación por lotes con alias (Elegida)
* **Pro:** 1 llamada de lectura, $\lceil N/50 \rceil$ escrituras, JSON uniforme, granularidad por hilo ante fallos parciales, cero dependencias adicionales.
* **Contra:** Requiere lógica de generación y correlación de alias en el CLI.
