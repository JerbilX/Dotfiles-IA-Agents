# Referencia: Feedback Loop y Resolución Autónoma de Code Review

Protocolo operativo determinista para atender observaciones, revisiones humanas y comentarios inline dejados en el diff de Pull Requests en GitHub utilizando tooling de Nivel 1 (`gh-pr-review`).

---

## 1. Criterios de Activación y Ámbito

- **Trigger Conversacional:** El agente activa este sub-protocolo cuando el usuario solicite atender, corregir o resolver observaciones de Code Review en un Pull Request activo (ej. *"resolvé los comentarios del PR #<id>"*, *"atendé el review del PR #<id>"*, *"revisá el feedback dejado en el diff de #<id>"*).
- **Aislamiento en Rama Activa:** Todas las correcciones solicitadas en la revisión de código deben realizarse estrictamente sobre la rama activa del Pull Request. Queda **terminantemente prohibido** crear ramas secundarias o abrir nuevos issues para abordar observaciones del code review del PR activo.

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
     *(Ejecutados con `BypassSandbox: true` obligatorio desde el primer intento).*

---

## 3. Fase 2: Ingesta Determinista de Feedback de Review (Tooling Nivel 1)

1. **Inspección de Reseñas Generales y Veredicto:**
   Consultar los comentarios globales y el estado de aprobación del Pull Request:
   ```bash
   gh pr view <pr_id> --comments
   ```
   *(Ejecutado con `BypassSandbox: true`).*

2. **Ingesta Unificada de Hilos de Revisión en el Diff (`gh-pr-review`):**
   Para obtener todos los hilos no resueltos en el diff del Pull Request sin riesgo de desborde de buffer ni pipes frágiles en terminal, invocar el CLI determinista de Nivel 1:
   ```bash
   gh-pr-review comments <pr_id>
   ```
   *(O alternativamente vía subcomando de gh: `gh pr-review comments <pr_id>`, ejecutado con `BypassSandbox: true`).*

   El comando retorna un JSON estructurado y compacto:
   ```json
   {
     "prNumber": 100,
     "totalThreads": 3,
     "unresolvedCount": 1,
     "truncated": false,
     "threads": [
       {
         "threadId": "PRRT_kwDOU_2SzM4A...",
         "path": "skills/issue-driven-workflow/SKILL.md",
         "line": 42,
         "originalLine": 40,
         "diffSide": "RIGHT",
         "isResolved": false,
         "commentCount": 2,
         "commentsTruncated": false,
         "rootComment": {
           "id": "PRRC_kw...",
           "databaseId": 12345678,
           "author": "TechLead",
           "body": "Ajustar redacción para clarificar el manejo de errores.",
           "createdAt": "2026-10-20T00:00:00Z"
         },
         "latestFeedback": {
           "id": "PRRC_kw...",
           "databaseId": 12345679,
           "author": "TechLead",
           "body": "Por favor verificar que no rompa prefijos.",
           "createdAt": "2026-10-20T00:05:00Z"
         }
       }
     ]
   }
   ```
   - Si se requiere incluir hilos históricos ya resueltos: `gh-pr-review comments <pr_id> --all`.
   - Si se requiere el historial completo de comentarios de cada hilo: `gh-pr-review comments <pr_id> --detailed`.

3. **Prohibición Categórica de Scripts Envoltorios o Tuberías:**
   Queda estrictamente prohibido crear scripts temporales (Python, Bash, Node, ej. `fetch_comments.py`) o encadenar tuberías con utilidades de terminal (`awk`, `sed`, `jq` externo). Todo el parseo y extracción de hilos debe canalizarse exclusivamente a través del CLI nativo `gh-pr-review`.

---

## 4. Fase 3: Flujo Atómico de Resolución

1. **Mapeo y Análisis Técnico:**
   - Inspeccionar el archivo afectado (`path`) y las líneas señaladas (`line` / `originalLine`) mediante la herramienta nativa `view_file`.
   - Contrastar la observación del revisor con el diseño del sistema y los invariantes del proyecto, identificando la solución con el menor radio de impacto posible (*Minimal Blast Radius*).
2. **Aplicación de Parches:**
   - Aplicar las correcciones solicitadas exclusivamente a través de las herramientas nativas de edición (`replace_file_content` o `write_to_file`). Prohibido usar comandos CLI de streaming (`sed`, `cat >`, `echo >>`) o scripts efímeros de parcheo.
3. **Verificación Estática y Local (Shift-Left):**
   - Ejecutar la suite de pruebas del proyecto y linters locales:
     ```bash
     ./build.sh check
     ```
     *(Ejecutado con `BypassSandbox: false` confinado).*
   - Validar que no existan errores (0 errores) y que el presupuesto de contexto se mantenga dentro de los umbrales definidos.
4. **Commit Atómico de Corrección:**
   - Preparar exclusivamente los archivos corregidos mediante staging explícito con rutas directas:
     ```bash
     git add <ruta1> <ruta2> ...
     ```
     *(Ejecutado con `BypassSandbox: true` desde el primer intento; prohibido usar `git add .` o `git add -A`).*
   - Redactar el mensaje en el archivo temporal `.commit_msg` mediante `write_to_file` siguiendo el estándar convencional:
     `fix(<alcance>): atender feedback de code review en PR #<id>`
   - Ejecutar el commit leyendo el archivo con `BypassSandbox: true`:
     ```bash
     git commit -F .commit_msg
     ```
   - Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
     ```bash
     rm -f .commit_msg
     ```
5. **Publicación Remota:**
   - Subir los commits a la rama del Pull Request:
     ```bash
     git push
     ```
     *(Ejecutado con `BypassSandbox: true`).*

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
   *(Ejecutado con `BypassSandbox: true`).*

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
   Al usar `--all <pr_id>`, incluye además `prNumber` y `totalFound`. Si algún hilo falla, se reporta en `errors` con su respectivo `threadId` y mensaje sin interrumpir los demás.

2. **Réplica Opcional a un Hilo de Revisión Específico:**
   Si se requiere dejar constancia explícita sobre un hilo puntual antes o después de resolverlo:
   ```bash
   gh-pr-review reply <thread_id> --body "Resuelto en commit <short_sha>: <descripción concisa>"
   ```
   *(O utilizando `--body-file .reply_body`, ejecutado con `BypassSandbox: true`).*

3. **Comentario Consolidado en el Pull Request:**
   Para notificar formalmente al revisor humano que todas las observaciones fueron atendidas:
   - Redactar el resumen en `.pr_comment` mediante `write_to_file`.
   - Publicar el comentario en el PR (`BypassSandbox: true`):
     ```bash
     gh pr comment <pr_id> --body-file .pr_comment
     ```
   - Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
     ```bash
     rm -f .pr_comment
     ```

4. **Gobernanza del Estado en Projects v2 y Resiliencia de ADRs:**
   - Para correcciones puntuales e iteraciones continuas de revisión, la tarjeta puede permanecer en `👀 In Review / PR` o transicionar a `⚙️ In Progress` durante el retrabajo si exige cambios sustanciales antes de solicitar una re-evaluación.
   - Si las observaciones cuestionan la arquitectura o enfoque estructural, aplicar la transición regresiva hacia `📐 In Planning`, invalidar el plan previo y redactar un nuevo `implementation_plan.md` con pausa bloqueante antes de modificar código.
   - Todo ADR asociado se mantiene rigurosamente en `status: proposed` a lo largo del proceso de revisión.
