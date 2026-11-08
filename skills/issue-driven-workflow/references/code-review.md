# Referencia: Feedback Loop y Resolución Autónoma de Code Review

Protocolo operativo determinista para atender observaciones, revisiones humanas y comentarios inline dejados en el diff de Pull Requests en GitHub utilizando tooling de Nivel 1 (`gh-pr-review`).

---

## 1. Criterios de Activación y Ámbito

- **Trigger Conversacional:** El agente activa este sub-protocolo cuando el usuario solicite atender, corregir o resolver observaciones de Code Review en un Pull Request activo (ej. *"resolvé los comentarios del PR #<id>"*, *"atendé el review del PR #<id>"*, *"revisá el feedback dejado en el diff de #<id>"*).
- **Aislamiento en Rama Activa:** Todas las correcciones solicitadas en la revisión de código deben realizarse sobre la rama activa del Pull Request. No crear ramas secundarias ni abrir nuevos issues para abordar observaciones del PR activo; trabajar sobre la rama existente.

---

## 2. Fase 1: Contexto y Sincronización de Rama

1. **Posicionamiento en la Rama del PR:**
   - Si el workspace ya se encuentra en la rama asociada al PR, sincronizar con el remoto para incorporar posibles commits o sugerencias aplicadas desde la web:
     ```bash
     git pull --ff-only
     ```
   - Si el workspace se encuentra en otra rama o se atiende el PR en una nueva sesión, posicionarse deterministamente en la rama del PR:
     ```bash
     gh pr checkout <pr_id>
     ```

---

## 3. Fase 2: Ingesta Determinista de Feedback de Review (Tooling Nivel 1)

1. **Ingesta Unificada de Contexto y Hilos de Revisión (`gh-pr-review`):**
   Para obtener en una única invocación el veredicto del PR (`reviewDecision`), las revisiones generales (`reviews`), los comentarios a nivel de Pull Request (`prComments`) y todos los hilos del diff sin desborde de buffer ni tuberías frágiles en terminal, invocar el CLI determinista de Nivel 1:
   ```bash
   gh-pr-review comments <pr_id>
   ```
   *(O alternativamente vía subcomando de gh: `gh pr-review comments <pr_id>`).*

   El comando retorna un JSON estructurado y consolidado:
   ```json
   {
     "prNumber": 100,
     "prTitle": "feat(issue-driven-workflow): optimizar Feedback Loop de Code Review",
     "prUrl": "https://github.com/owner/repo/pull/100",
     "reviewDecision": "CHANGES_REQUESTED",
     "reviews": [
       {
         "author": "TechLead",
         "state": "CHANGES_REQUESTED",
         "body": "Revisar los siguientes hilos de revisión en el diff antes de proceder al merge.",
         "submittedAt": "2026-10-24T10:00:00Z"
       }
     ],
     "prComments": [
       {
         "author": "ProjectLead",
         "body": "Buen progreso en esta rama, por favor atender las observaciones.",
         "createdAt": "2026-10-24T09:30:00Z"
       }
     ],
     "totalThreads": 3,
     "unresolvedCount": 1,
     "truncated": false,
     "returnedThreads": 1,
     "threads": [
       {
         "threadId": "PRRT_kwDOU_2SzM4A...",
         "path": "skills/issue-driven-workflow/SKILL.md",
         "line": 42,
         "originalLine": 40,
         "diffSide": "RIGHT",
         "isResolved": false,
         "isOutdated": false,
         "commentCount": 2,
         "commentsTruncated": false,
         "rootComment": {
           "id": "PRRC_kw...",
           "databaseId": 12345678,
           "author": "TechLead",
           "body": "Ajustar redacción para clarificar el manejo de errores.",
           "createdAt": "2026-10-20T00:00:00Z",
           "url": "https://github.com/owner/repo/pull/100#discussion_r12345678"
         },
         "latestFeedback": {
           "id": "PRRC_kw...",
           "databaseId": 12345679,
           "author": "TechLead",
           "body": "Por favor verificar que no rompa prefijos.",
           "createdAt": "2026-10-20T00:05:00Z",
           "url": "https://github.com/owner/repo/pull/100#discussion_r12345679"
         }
       }
     ]
   }
   ```
   - Si se requiere excluir hilos desactualizados en PRs con múltiples iteraciones (recomendado para optimizar el consumo de tokens de contexto): `gh-pr-review comments <pr_id> --exclude-outdated`.
   - Si se requiere incluir hilos históricos ya resueltos: `gh-pr-review comments <pr_id> --all`.
   - Si se requiere el historial completo de comentarios de cada hilo: `gh-pr-review comments <pr_id> --detailed`.
   - Si se desea omitir reviews y comentarios de nivel PR para consultar únicamente hilos: `gh-pr-review comments <pr_id> --threads-only`.

2. **Prohibición de Ingesta Duplicada o Tuberías:**
   Prohibido invocar `gh pr view <pr_id> --comments` (ingesta duplicada en texto no estructurado), crear scripts temporales (Python, Bash, Node, ej. `fetch_comments.py`) o encadenar tuberías con utilidades de terminal (`awk`, `sed`, `jq`). Todo el contexto de revisión se extrae a través de `gh-pr-review comments <pr_id>`.

---

## 4. Fase 3: Flujo Atómico de Resolución

1. **Mapeo y Análisis Técnico:**
   - Inspeccionar el archivo afectado (`path`) y las líneas señaladas (`line` / `originalLine`) mediante herramientas nativas de lectura.
   - Contrastar la observación del revisor con el diseño del sistema y los invariantes del proyecto, identificando la solución con el menor radio de impacto posible (*Minimal Blast Radius*).
2. **Aplicación de Parches:**
   - Aplicar las correcciones solicitadas exclusivamente a través de las herramientas nativas de edición y escritura de archivos. No usar comandos de terminal para edición (`sed`, `cat >`, `echo >>`) ni scripts de parcheo.
3. **Verificación Estática y Local (Shift-Left):**
   - Ejecutar la suite de pruebas del proyecto y linters locales:
     ```bash
     ./build.sh check
     ```
   - Validar que no existan errores (0 errores) y que el presupuesto de contexto se mantenga dentro de los umbrales definidos.
4. **Commit Atómico de Corrección:**
   - Preparar exclusivamente los archivos corregidos mediante staging explícito con rutas directas:
     ```bash
     git add <ruta1> <ruta2> ...
     ```
     *(Indicar rutas explícitas; no usar `git add .` ni `git add -A`).*
   - Redactar el mensaje en el archivo temporal `.commit_msg` mediante herramientas nativas de archivos siguiendo el estándar convencional:
     `fix(<alcance>): atender feedback de code review en PR #<id>`
   - Ejecutar el commit leyendo el archivo:
     ```bash
     git commit -F .commit_msg
     ```
   - Limpiar el archivo temporal en el mismo turno:
     ```bash
     rm -f .commit_msg
     ```
5. **Publicación Remota:**
   - Subir los commits a la rama del Pull Request:
     ```bash
     git push
     ```

---

## 5. Fase 4: Trazabilidad, Mutación y Cierre del Ciclo de Feedback

1. **Resolución Atómica y por Lotes de Hilos de Revisión Subsanados:**
   Por cada hilo de revisión cuyos requerimientos hayan sido corregidos y verificados con éxito, marcarlo como resuelto utilizando `gh-pr-review resolve`. Admite resolución individual, múltiple por IDs o en lote para todo el PR:
   ```bash
   # Resolución de un hilo individual
   gh-pr-review resolve <thread_id>

   # Resolución por lotes de múltiples hilos específicos en una sola llamada
   gh-pr-review resolve <thread_id_1> <thread_id_2> <thread_id_3>

   # Resolución total de todos los hilos pendientes de un Pull Request
   gh-pr-review resolve --all <pr_id>
   ```

   Retorna una respuesta JSON estructurada y consolidada:
   ```json
   {
     "success": true,
     "resolvedCount": 2,
     "resolvedThreads": [
       "PRRT_kwDOU_2SzM4A...",
       "PRRT_kwDOU_2SzM4B..."
     ],
     "errors": []
   }
   ```
   Al usar `--all <pr_id>`, incluye además `prNumber` y `totalFound`. La resolución múltiple y `--all` opera internamente en lotes de hasta 50 hilos mediante una única mutación GraphQL con alias (`t0`, `t1`, ...), ejecutando $\lceil N/50 \rceil$ llamadas en lugar de $N$. Si algún hilo falla (ej. ID inválido o eliminado), se reporta en `errors` con su respectivo `threadId` y mensaje sin interrumpir la resolución de los demás hilos del lote.

2. **Réplica Opcional a un Hilo de Revisión Específico:**
   Si se requiere dejar constancia explícita sobre un hilo puntual antes o después de resolverlo, redactar el texto en el archivo temporal `.reply_body` mediante herramientas nativas de archivos y enviarlo mediante `--body-file` para preservar el prefix matching en runtimes con permisos como Antigravity:
   ```bash
   gh-pr-review reply <thread_id> --body-file .reply_body
   ```
   *(Limpiar el archivo temporal con `rm -f .reply_body` en el mismo turno).*

3. **Comentario Consolidado en el Pull Request:**
   Para notificar formalmente al revisor humano que todas las observaciones fueron atendidas:
   - Redactar el resumen en `.pr_comment` mediante herramientas nativas de archivos.
   - Publicar el comentario en el PR:
     ```bash
     gh pr comment <pr_id> --body-file .pr_comment
     ```
   - Limpiar el archivo temporal en el mismo turno:
     ```bash
     rm -f .pr_comment
     ```

4. **Gobernanza del Estado en Projects v2 y Resiliencia de ADRs:**
   - Para correcciones puntuales e iteraciones continuas de revisión, la tarjeta puede permanecer en `👀 In Review / PR` o transicionar a `⚙️ In Progress` durante el retrabajo si exige cambios sustanciales antes de solicitar una re-evaluación.
   - Si las observaciones cuestionan la arquitectura o enfoque estructural, aplicar la transición regresiva hacia `📐 In Planning`, invalidar el plan previo y redactar un nuevo `implementation_plan.md` con pausa bloqueante antes de modificar código.
   - Todo ADR asociado permanece en `status: accepted` a lo largo del proceso de revisión; únicamente revierte a `status: proposed` (o se redacta reemplazo/enmienda) ante una transición regresiva por Cuestionamiento Arquitectónico hacia `📐 In Planning`.
