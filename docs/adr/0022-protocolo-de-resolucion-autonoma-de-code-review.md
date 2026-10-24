---
status: superseded by ADR-0035
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: ["0035-unificacion-ingesta-review-y-resolucion-en-lote-gh-pr-review.md"]
---

# 0022 - Protocolo de Resolución Autónoma de Code Review en Pull Requests

## Contexto y Planteamiento del Problema
En el ciclo de vida guiado por issues formalizado en ADR-0005, ADR-0010 y ADR-0021, el desarrollo de funcionalidades o correcciones concluye operativamente con la apertura de un Pull Request y la transición de la tarjeta a `👀 In Review / PR`.

Sin embargo, durante el proceso de revisión humana (Code Review), el PM o Tech Lead suele dejar observaciones generales y comentarios específicos (*inline comments*) en el diff de archivos de GitHub, solicitando ajustes antes de autorizar el merge. Hasta ahora, el skill `issue-driven-workflow` carecía de directivas deterministas que instruyeran al agente sobre cómo ingerir, procesar y subsanar autónomamente dicho feedback de revisión sin desorientarse, sin crear ramas o issues redundantes, y sin recurrir a scripts envoltorios que violen las políticas de sandbox.

Se requiere formalizar un sub-protocolo atómico de atención de Code Review, evaluar si debe gestionarse como un micro-skill independiente, un servidor MCP o dentro del skill existente, y definir los comandos CLI deterministas para consultar e interactuar con los comentarios del diff de GitHub.

## Impulsores de la Decisión (Decision Drivers)
* **Principio de Mínima Intervención y Cohesión (Minimal Blast Radius - ADR-0017):** Evitar la fragmentación y proliferación innecesaria de micro-skills o servidores MCP para flujos que pertenecen naturalmente al ciclo de vida del PR.
* **Preservación de Políticas de Sandbox y Prefix Matching:** Asegurar que las consultas e interacciones de revisión utilicen comandos directos de GitHub CLI (`gh api`) sin tuberías intermediarias (`awk`, `sed`) ni scripts auxiliares (`fetch_comments.py`).
* **Determinismo y Trazabilidad:** Garantizar que los cambios solicitados en la revisión se apliquen sobre la misma rama del PR, respetando el estándar convencional de commits (`fix(...)`) y posibilitando respuestas trazables a los comentarios del revisor.
* **Economía de Contexto:** Permitir consultas estructuradas y compactas mediante filtrado server-side / `--jq` nativo para evitar la saturación de la ventana de contexto del agente.

## Opciones Consideradas
* **Opción 1: Desarrollo de un Servidor MCP para GitHub Reviews.**
  * Implementar o incorporar un servidor MCP especializado para leer diffs, comentarios y enviar respuestas de revisión en GitHub.
  * *Descarte:* Viola flagrantemente el principio de Minimal Blast Radius. Introduce sobrecarga de dependencias, procesos demonio y latencia de red para operaciones que la CLI oficial de GitHub (`gh`) resuelve de forma nativa en Nivel 0/2.
* **Opción 2: Creación de un Micro-Skill Separado (`code-review-resolver`).**
  * Crear una nueva carpeta en `skills/code-review-resolver/` con sus propias directivas independientes.
  * *Descarte:* Fragmenta artificialmente el ciclo de vida del PR. El tratamiento de revisiones es una fase constitutiva del flujo guiado por tareas y Pull Requests; separarlo dispersa el contexto e incrementa el costo de mantenimiento.
* **Opción 3: Consolidación Cohesiva del Sub-protocolo en `issue-driven-workflow` (Nivel 2).**
  * Integrar el sub-protocolo de Feedback Loop de Code Review directamente dentro de `skills/issue-driven-workflow/SKILL.md`.
  * Estandarizar el uso de `gh pr view --comments` para comentarios generales y `gh api repos/:owner/:repo/pulls/<pr_id>/comments` con `--jq` para comentarios inline estructurados.
  * Consolidar el flujo: ingesta -> checkout/pull de rama del PR -> aplicación con herramientas nativas -> verificación con `./build.sh check` -> commit `fix(...)` -> push -> respuesta o comentario en PR.

## Decisión Adoptada
Opción elegida: **"Opción 3"**, estructurando la resolución bajo las siguientes directivas:

1. **Gobernanza Unificada en `issue-driven-workflow`:**
   * La resolución de Code Review se consolida como una sección formal dentro de `skills/issue-driven-workflow/SKILL.md` (Nivel 2 de abstracción), descartando servidores MCP y micro-skills dedicados.
   * La atención de observaciones se ejecuta estrictamente sobre la rama activa del Pull Request; queda prohibido bifurcar en ramas secundarias o abrir nuevos issues para cambios solicitados en el review.

2. **Comandos Deterministas de GitHub CLI (`gh api`):**
   * Inspección general: `gh pr view <pr_id> --comments` (`BypassSandbox: true`).
   * Consulta estructurada de comentarios inline en el diff:
     ```bash
     gh api repos/:owner/:repo/pulls/<pr_id>/comments --jq '.[] | {id: .id, path: .path, line: (.line // .original_line), diff_hunk: .diff_hunk, body: .body}'
     ```
     *(Aprovecha el reemplazo contextual de `:owner/:repo` provisto por `gh`).*
   * Prohibición absoluta de scripts auxiliares efímeros o tuberías complejas.

3. **Flujo de Ejecución Atómica:**
   * **Sincronización:** Posicionarse en la rama del PR (`gh pr checkout <pr_id>` o `git pull --ff-only`).
   * **Modificación:** Parches aplicados exclusivamente vía herramientas nativas de archivos (`replace_file_content`, `write_to_file`).
   * **Validación Shift-Left:** Verificación estática local con `./build.sh check` (`BypassSandbox: false`).
   * **Commit & Push:** Commit convencional formateado en `.commit_msg` (`fix(<alcance>): atender feedback de code review en PR #<id>`) y push a la rama del PR.
   * **Cierre de Feedback:** Respuesta opcional a comentarios específicos vía API o comentario consolidado en el PR con `gh pr comment <pr_id> --body-file .pr_comment`.

### Consecuencias
* **Positivas:**
  * Ciclo de vida de PRs 100% completo, cubriendo desde la apertura hasta la iteración de revisión y aprobación final.
  * Cero dependencias adicionales ni servidores MCP huérfanos.
  * Cumplimiento estricto del confinamiento de sandbox y prefix matching de Antigravity.
  * Claridad total para agentes autónomos ante órdenes como *"atendé los comentarios del PR #X"*.
* **Negativas / Trade-offs:**
  * Incrementa levemente el tamaño de `skills/issue-driven-workflow/SKILL.md`, requiriendo mantener una redacción concisa y optimizada.

### Pros y Contras de las Opciones
#### Opción 1: Servidor MCP
* **Pro:** Interfaz de herramientas específicas.
* **Contra:** Sobreingeniería severa, consumo innecesario de memoria y recursos, viola Minimal Blast Radius.

#### Opción 2: Micro-Skill Separado
* **Pro:** Archivo aislado.
* **Contra:** Fragmentación del flujo de trabajo de Git/GitHub, duplicación de directivas de sandbox y commits.

#### Opción 3: Consolidación en `issue-driven-workflow` (Elegida)
* **Pro:** Flujo E2E cohesivo, sin dependencias externas, respeta jerarquía de niveles de resolución.
* **Contra:** Ninguna significativa; requiere mantener disciplina en la extensión de la documentación del skill.
