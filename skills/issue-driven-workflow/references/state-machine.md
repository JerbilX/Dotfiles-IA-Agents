# Referencia: Máquina de Estados de Projects v2 y Transiciones Regresivas

Guía procedimental y catálogo de transiciones para la máquina de estados desacoplada en GitHub Projects v2 (tablero central `Proyectos-IA-V3`), cubriendo el flujo progresivo ordinario y las acciones de compensación e higiene ante reversiones, reprocesos (*rework*) o cancelaciones.

---

## 1. Arquitectura de la Máquina de Estados

El campo `Status` en Projects v2 define 6 estados canónicos gobernados por el ciclo de vida nativo de Git/GitHub y los Built-in Workflows (Ref: `docs/adr/0030-desacoplamiento-de-maquina-de-estados-y-alineacion-al-ciclo-nativo-git-github.md`):

```
[📥 Backlog] ──> [🎯 Ready for Dev] ──> [📐 In Planning] ──> [⚙️ In Progress] ──> [👀 In Review / PR] ──> [Done]
```

* **Desacoplamiento Estricto:** Prohibido el uso de `gh project item-edit` por el agente. Las transiciones progresivas son activadas por eventos nativos de Git/GitHub (despacho local, apertura de PR con `Closes #<id>`, merge y cierre).
* **Compensación e Higiene:** Ante excepciones técnicas, observaciones de revisión o cancelaciones, el retroceso exige compensar el árbol de Git y el estado documental de los ADRs.

---

## 2. Matriz de Transiciones Progresivas (Forward)

Flujo secuencial estándar de avance de una tarea:

| Origen | Destino | Disparador / Evento | Condición de Entrada | Acción Operativa Inmediata |
| :--- | :--- | :--- | :--- | :--- |
| `📥 Backlog` | `🎯 Ready for Dev` | Priorización | Requerimiento maduro con especificación y criterios de aceptación. | Priorización humana (en UI) o asignación. |
| `🎯 Ready for Dev` | `📐 In Planning` | Despacho de tarea | Sesión de agente asignada al ticket vía instrucción directa o backlog. | Ingesta técnica (`gh issue view`). Fase local de análisis. |
| `📐 In Planning` | `⚙️ In Progress` | Aprobación de Plan | Aprobación humana explícita de `implementation_plan.md` o fast-path ejecutivo. | Promover ADR a `status: accepted`, iniciar codificación en rama efímera. |
| `⚙️ In Progress` | `👀 In Review / PR` | Fin de desarrollo | Código probado con `./build.sh check`, commits atómicos y push remoto. | Crear PR con `Closes #<id>` (ADR viaja como `accepted`). Built-in Workflow avanza tarjeta a `👀 In Review / PR`. |
| `👀 In Review / PR` | `Done` | Merge de PR | Orden ejecutiva en chat (*"aprobado, mergeá"*) o fusión manual en GitHub Web. | Fusión vía `gh pr merge <id> --squash --delete-branch` (o web); Built-in Workflow avanza a `Done`. Ejecutar encadenamiento atómico de higiene (`git-prune-gone --sync`). |
| `📐 In Planning` | `Done` | Conclusión de Spike | Tarea investigativa/auditoría sin cambios de código. | Informe técnico en `.issue_comment` y cierre con `gh issue close <id>`. Built-in Workflow avanza tarjeta a `Done`. |

---

## 3. Matriz de Transiciones Regresivas (Backward / Rework / Rollback)

Cuando una tarea enfrenta bloqueos, revisiones insatisfactorias o cambios de prioridad, el retroceso debe ejecutarse aplicando estrictamente las siguientes acciones de compensación:

| Origen | Destino | Causa / Disparador | Acciones de Compensación e Higiene |
| :--- | :--- | :--- | :--- |
| `👀 In Review / PR` | `⚙️ In Progress` | **Observaciones en Code Review (Rework moderado/mayor):** El revisor solicita cambios funcionales, refactors o tests adicionales antes de aprobar. | 1. Posicionarse en la rama del PR (`gh pr checkout <pr_id>` con `BypassSandbox: true`).<br>2. Resolver observaciones vía `gh-pr-review` y herramientas nativas.<br>3. Commitear, pushear y notificar.<br>4. Si las observaciones afectan la arquitectura, ajustar el ADR según corresponda.<br>*(Si está activo el Built-in Workflow 'Code changes requested', el evento de review solicita cambios y actualiza el tablero automáticamente)*. |
| `👀 In Review / PR` | `📐 In Planning` | **Cuestionamiento Arquitectónico o Fallo de Enfoque:** El revisor rechaza el diseño técnico, detecta inviabilidad o exige replantear la solución. | 1. Invalidar el `implementation_plan.md` previo.<br>2. Revertir ADR a `status: proposed` (o redactar reemplazo/enmienda).<br>3. Redactar nuevo plan de implementación con pausa bloqueante (`RequestFeedback: true`).<br>4. Prohibido tocar código hasta obtener nueva aprobación humana. |
| `⚙️ In Progress` | `📐 In Planning` | **Bloqueo Técnico o Inviabilidad en Desarrollo:** El agente descubre que el enfoque planificado no es viable o choca con restricciones no previstas. | 1. Aislar de forma reversible los cambios descartados mediante `git stash push -u -m abort-issue-<id>` (o commit WIP en la rama efímera). Prohibido ejecutar `git clean` o borrados destructivos sin confirmación humana explícita.<br>2. Actualizar `implementation_plan.md` justificando el cambio de rumbo.<br>3. Si hay ADR en curso, revertirlo a `status: proposed` o ajustar la propuesta.<br>4. Solicitar confirmación humana antes de reanudar codificación. |
| `📐 In Planning` | `🎯 Ready for Dev` | **Despriorización Temporal o Bloqueo Externo:** Se interrumpe la planificación por falta de insumos externos o cambio temporal de foco. | 1. Si se creó rama local efímera, posicionarse en la rama base (`git checkout <base_branch>`) y eliminarla (`git branch -D <rama>`) en pasos atómicos sin encadenar comandos.<br>2. Registrar comentario en el issue (`gh issue comment`) detallando el bloqueo o motivo de pausa. |
| `📐 In Planning` | `📥 Backlog` | **Descarte Temprano o Cancelación:** La exploración inicial concluye que la iniciativa es inviable o no prioritaria. | 1. Eliminar rama de trabajo si existiere.<br>2. Registrar diagnóstico en el issue (`gh issue comment`). Si se redactó borrador de ADR en rama, no ingresa a la rama troncal (`<base_branch>`). |
| `⚙️ In Progress` | `🎯 Ready for Dev` / `📥 Backlog` | **Aborto de Implementación:** Se decide cancelar el desarrollo ya iniciado. | 1. Posicionarse en la rama base (`git checkout <base_branch>`), eliminar la rama local (`git branch -D <rama>`) y la rama remota (`git push origin --delete <rama>`) en pasos atómicos.<br>2. Documentar en el issue el estado en que queda el requerimiento. |
| `👀 In Review / PR` | `📥 Backlog` / Cerrado | **Rechazo Definitivo de PR:** El PR se cierra sin merge por el usuario. | 1. Cerrar PR en GitHub.<br>2. Si contenía un nuevo ADR, el ADR nunca entra a la rama troncal (descartado con la rama). Si fue propuesto en documento independiente, marcar `status: rejected`.<br>3. Ejecutar `git-prune-gone` localmente. |

---

## 4. Invariantes de Compensación y Reversibilidad

1. **Reversibilidad Estricta:** Queda terminantemente prohibido ejecutar `git clean -fd` o eliminaciones destructivas de árbol de trabajo sin confirmación explícita del usuario. Ante cambios descartados en desarrollo, aislarlos con `git stash push -u -m abort-issue-<id>` o commits de preservación.
2. **Ciclo Documental de ADRs:**
   * Si una tarea regresa a `📐 In Planning`, el ADR vuelve a `status: proposed`.
   * Si un PR es rechazado definitivamente, el ADR no entra a la rama troncal (queda descartado con la rama) o se marca `status: rejected` si existía en rama base.
3. **Referencias Operativas:**
   * Ciclo E2E completo: [`references/branch-lifecycle.md`](branch-lifecycle.md).
   * Gestión de backlog e ingreso de tickets: [`references/issue-backlog.md`](issue-backlog.md).
   * Feedback loop de code review: [`references/code-review.md`](code-review.md).
