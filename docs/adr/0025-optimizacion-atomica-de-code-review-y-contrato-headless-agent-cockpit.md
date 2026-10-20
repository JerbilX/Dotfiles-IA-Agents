---
status: accepted
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0025 - Optimización Atómica de Code Review y Contrato Headless para Agent-Cockpit

## Contexto y Planteamiento del Problema
En ADR-0022 se formalizó el sub-protocolo de Feedback Loop y Resolución Autónoma de Code Review dentro de `skills/issue-driven-workflow/SKILL.md` (Sección 7). Si bien este marco permitió atender revisiones humanas sobre la rama activa del PR sin crear ramas ni tickets huérfanos, la implementación presentaba áreas de fricción operativa:

1. **Latencia e Ingesta Fragmentada:** La ingesta requería pasos secuenciales exploratorios (`gh pr view --comments` seguido de consultas a `pulls/<pr_id>/comments` que incluían `diff_hunk`), lo que sobrecargaba la ventana de contexto con bloques de código redundantes y ralentizaba el análisis.
2. **Ambigüedad en Planning Mode:** Ante revisiones puntuales (corrección de sintaxis, formato o tipografía), algunos agentes activaban el *Planning Mode* generando artefactos `implementation_plan.md` con pausas bloqueantes innecesarias, cuando las observaciones del revisor ya constituían directivas de aplicación directa.
3. **Integración con Agent-Cockpit:** Con el desarrollo de Agent-Cockpit (panel web local para administración y encolado centralizado de tareas, issues y PRs), se requiere que la atención de reviews pueda operar como un trabajo atómico *headless* (desatendido), donde el orquestador despache la orden y el agente resuelva, valide y reporte en un único turno sin degradar el confinamiento de seguridad ni romper el *prefix matching* en Antigravity.

## Impulsores de la Decisión (Decision Drivers)
* **Economía de Contexto y Baja Latencia:** Reducir la sobrecarga de tokens eliminando fragmentos innecesarios (`diff_hunk`) en la consulta CLI de comentarios.
* **Resolución en Turno Único (Fast-Path):** Eliminar pausas bloqueantes redundantes para observaciones de review puntuales y explícitas.
* **Compatibilidad Headless:** Soportar tanto la invocación manual en chat como el despacho programático desde Agent-Cockpit sin intervención humana intermedia.
* **Preservación del Confinamiento y Prefix Matching:** Garantizar que todas las operaciones CLI se mantengan atómicas, sin scripts envoltorios ni tuberías complejas.
* **Minimal Blast Radius (ADR-0017):** Limitar los cambios a Nivel 0 (flags de CLI) y Nivel 2 (skills bajo demanda), sin alterar la capa basal (`core/`).

## Opciones Consideradas
* **Opción 1: Endpoint GraphQL Complejo en un Script Auxiliar.**
  * Escribir un script en Python/Node que consulte la API GraphQL de GitHub (`reviewThreads`) para parsear hilos resueltos y pendientes.
  * *Descarte:* Viola la política de no scripts auxiliares para operaciones de red/CLI, rompe el *prefix matching* de seguridad y añade mantenimiento innecesario.
* **Opción 2: Mantener Flujo Exploratorio con Doble Consulta.**
  * Conservar `gh pr view` y consultas sucesivas con `diff_hunk`.
  * *Descarte:* Mantiene una alta latencia de turnos y satura el contexto del modelo con duplicación del diff.
* **Opción 3: Consulta Atómica Compacta (`gh api --jq`) y Contrato Fast-Path en Nivel 2 (Elegida).**
  * Estandarizar la consulta de comentarios inline mediante:
    ```bash
    gh api repos/:owner/:repo/pulls/<pr_id>/comments --jq '.[] | {id: .id, path: .path, line: (.line // .original_line), body: .body}'
    ```
  * Establecer un contrato de ejecución *Fast-Path* que exima de planes bloqueantes a correcciones puntuales de review.
  * Formalizar una estructura de respuesta estandarizada para consumo de Agent-Cockpit.

## Decisión Adoptada
Se adopta la **Opción 3**:

1. **Ingesta Compacta Unificada (Nivel 0/1):**
   * Se elimina la extracción de `diff_hunk` y metadatos de enlaces en la llamada CLI. Se obtiene directamente `{id, path, line, body}` en una sola invocación de `gh api`.
2. **Contrato de Ejecución Fast-Path (Nivel 2):**
   * Al ser despachado para atender un PR (vía chat o Agent-Cockpit), el agente reconoce que las observaciones del revisor ya están aprobadas y delimitadas, ejecutando la secuencia atómica en turno único: sincronizar -> consultar comentarios -> aplicar parches nativos -> `./build.sh check` -> commit atómico -> push -> cierre de feedback.
   * Si la observación exige un rediseño arquitectónico sustantivo, el agente suspende el fast-path y aplica *Stop & Ask* o registra un nuevo ADR.
3. **Compatibilidad con Despacho Headless desde Agent-Cockpit:**
   * La interacción no asume preguntas interactivas innecesarias y emite una confirmación final estructurada (PR, commits, archivos tocados, resultado de linter/build).

### Consecuencias
* **Positivas:**
  * Reducción drástica del consumo de contexto y tiempo de respuesta en revisiones de PRs.
  * Flujo fluido de resolución en un único turno.
  * Total integración desatendida con Agent-Cockpit.
  * Conformidad plena con las políticas de sandbox y prefix matching de Antigravity.
* **Negativas / Trade-offs:**
  * Si un revisor deja observaciones puramente conversacionales sin vincular a líneas de código, se requiere el fallback a `gh pr view <pr_id> --comments`.

### Pros y Contras de las Opciones
#### Opción 1: Script GraphQL
* **Pro:** Soporta estado de resolución de hilos nativo.
* **Contra:** Viola confinamiento de Antigravity, genera scripts efímeros, rompe prefix matching.

#### Opción 2: Doble Consulta Exploratoria
* **Pro:** Sin cambios requeridos.
* **Contra:** Alta latencia, sobrecarga de contexto por `diff_hunk`, pausas innecesarias en planning mode.

#### Opción 3: Consulta Atómica Compacta y Contrato Fast-Path (Elegida)
* **Pro:** Turno único, determinista, respeta Minimal Blast Radius, compatible con Agent-Cockpit y chat.
* **Contra:** Requiere fallback explícito para comentarios fuera del diff.
