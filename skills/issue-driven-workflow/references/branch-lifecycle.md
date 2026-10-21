# Referencia: Convención de Ramas, Ciclo E2E y Gestión de Pull Requests

Guía procedimental detallada para el ciclo de vida completo de ramas de trabajo, ejecución de tareas guiadas por issues, higiene de Git, apertura de PRs y cierre de tickets.

---

## 1. Convención Canónica de Ramas de Trabajo

Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código del workspace.

### 1.1 Estrategia Híbrida Contextual (Ref: docs/adr/0021-estrategia-de-ramas-troncales-y-promocion-de-entornos.md)
La estructura de ramas troncales responde a la naturaleza del proyecto según su archivo de configuración raíz (`.repo-config.json` o `config.json`):

1. **Categoría A (Predeterminada - Repositorios Compactos / Dotfiles / Tooling / Librerías):**
   - **Troncal única:** `main`.
   - **Ramas efímeras:** Se originan en `main` (`git checkout -b feat/issue-<id>-<slug>`).
   - **Pull Requests:** Apuntan directamente a `main`. Cero ramas troncales intermedias.
2. **Categoría B (Aplicaciones con Ambientes de Despliegue Físicos):**
   - **Troncal de integración continua:** `dev` (desplegada a entorno de staging/dev).
   - **Troncal de producción:** `main` (desplegada a producción).
   - **Ramas efímeras:** Se originan en `dev` (`git checkout -b feat/issue-<id>-<slug> dev`).
   - **Pull Requests:** Apuntan a `dev` (`gh pr create --base dev ...`).
   - **Promoción a Producción:** Se formaliza exclusivamente mediante un *Release Pull Request* de `dev` a `main` con tag de versión SemVer (`vX.Y.Z`).

### 1.2 Detección Declarativa de la Estrategia del Repositorio
Al iniciar el trabajo en un repositorio, el agente inspecciona el archivo de configuración en la raíz (`.repo-config.json` o `config.json`):
```json
{
  "repository_type": "category_a",
  "base_branch": "main"
}
```
En ausencia de archivo de configuración o si no se explicita `repository_type`, se adopta por defecto **Categoría A** (`base_branch: "main"`).

### 1.3 Nomenclatura Canónica de Ramas Efímeras
- **Nomenclatura Obligatoria:**
  - Para nuevas funcionalidades, refactors o tareas generales: `feat/issue-<id>-<slug>`
  - Para corrección de errores o parches: `fix/issue-<id>-<slug>`
- **Creación in-place:**
  ```bash
  git checkout -b <nombre-de-rama>
  ```
  *(Ejecutado con `BypassSandbox: true` desde el primer intento debido al montaje `ro` de `.git/`).*

---

## 2. Ciclo de Vida E2E de la Tarea

Cualquier tarea despachada debe cumplir secuencialmente con las siguientes 8 fases:

```
[1. Ingesta] -> [2. Higiene de Ramas] -> [3. Planificación (In Planning)] -> [4. Desarrollo (In Progress)] -> [5. Commit] -> [6. Push] -> [7. PR & Tablero (In Review)] -> [8. Reconciliación Post-Merge (Done)]
```

### Paso 1: Ingesta Técnica
1. Lectura profunda de los requerimientos, contexto, diagnóstico y criterios de aceptación en `gh issue view <id>` (`BypassSandbox: true`).
2. Transicionar el ticket al estado formal `📐 In Planning` en el tablero central (Project 1):
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "📐 In Planning"
   ```
   *(Ejecutado con `BypassSandbox: true`).*

### Paso 2: Aislamiento e Higiene del Workspace
1. Posicionarse en la rama base del repositorio (`main` por defecto, o `dev` en Categoría B) y sincronizar cambios podando referencias remotas obsoletas:
   ```bash
   git checkout <base_branch>
   git pull --prune --ff-only
   ```
   *(Ejecutados con `BypassSandbox: true` desde el primer intento).*
   - **Mecánica de Transporte de Git:** Invocado sin argumentos posicionales de remoto o rama (`origin main`), `git pull --prune --ff-only` procesa el refspec estándar completo (`+refs/heads/*:refs/remotes/origin/*`), poda de forma automática las referencias zombi (`remotes/origin/*`) y avanza la rama base exclusivamente en modo fast-forward sin modales interactivos en Antigravity.
   - **Prohibición Categórica de `git remote prune`:** Queda terminantemente prohibido ejecutar `git remote prune` (ej. `git remote prune origin`). Toda poda de tracking remoto debe canalizarse exclusivamente a través del transporte estándar de sincronización (`git pull --prune --ff-only` o `git fetch --prune origin`).
2. Ejecutar la poda de higiene local en un único paso atómico mediante el CLI determinista de Nivel 1 `git-prune-gone`:
   ```bash
   git-prune-gone
   ```
   *(Ejecutado con `BypassSandbox: true` desde el primer intento debido al montaje `ro` de `.git/`).*
   - **Fallback Determinista:** Si el binario no está disponible en `$PATH`, invocar directamente `skills/issue-driven-workflow/bin/git-prune-gone`.
   - **Mecánica Interna:** Inspecciona las ramas locales mediante formato estructurado (`%(HEAD)|%(refname:short)|%(upstream:track)`), detecta aquellas con tracking zombi `[gone]` y ejecuta la poda segura (`git branch -d`) sin requerir turnos intermedios del LLM ni pipes de shell.
3. **Reconciliación Pre-Flight Just-In-Time (JIT):**
   Ejecutar el subcomando determinista de reconciliación para ratificar cualquier ADR pendiente que haya ingresado a la rama base tras merges anteriores sin reconciliación manual:
   ```bash
   ./build.sh reconcile
   ```
   *(Ejecutado con `BypassSandbox: false`).*
   - Si existieron merges previos que incorporaron ADRs en `status: proposed`, esta fase preventiva los ratifica de forma atómica a `status: accepted` en `main` antes de ramificar, garantizando que el workspace no herede decisiones no ratificadas sin requerir procesos demonio residentes ni depender de la memoria del usuario.
4. Crear y cambiar a la rama descriptiva (`git checkout -b feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) con `BypassSandbox: true` desde el primer intento.

### Paso 3: Planificación y Refinamiento (📐 In Planning)
- **Blindaje del Planning Mode:** Toda tarea que implique diagnóstico de errores (bug fixing) o modificaciones arquitectónicas requiere obligatoriamente redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
- **Evaluación Obligatoria de Minimal Blast Radius:** Todo plan de implementación debe evaluar y registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Si la propuesta plantea modificar directivas basales (`core/`), debe incorporar obligatoriamente la sección **"Justificación de Elevación Basal"** acreditando la inviabilidad técnica en los niveles 0 a 3.
- **Excepción de Fast-Path Ejecutivo:** Si la solución técnica o cambio ya fue debatido y consensuado explícitamente en el chat y el usuario emitió una orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), el agente **NO DEBE** pausar con un plan bloqueante; procede de inmediato a la implementación.
- **Registro de ADRs:** Si se toman decisiones arquitectónicas o estructurales, registrar un nuevo ADR con `status: proposed` mediante el skill `adr-manager` (`docs/adr/NNNN-titulo.md`). El ADR permanece estrictamente en `status: proposed` durante todo el desarrollo de la rama.

### Paso 4: Transición a Desarrollo y Verificación (⚙️ In Progress)
- Al aprobarse el plan o entrar en fast-path ejecutivo, transicionar el ticket a `⚙️ In Progress`:
  ```bash
  gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "⚙️ In Progress"
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Aplicar cambios atómicos exclusivamente mediante las APIs nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`).
- Ejecutar compilaciones locales, linters y suites de prueba del proyecto para validar que no existan regresiones (`./build.sh check` con `BypassSandbox: false`).
- **Invariante de ADR en Rama:** Todo nuevo ADR permanece en `status: proposed` en la rama de trabajo. Queda prohibido pasarlo a `status: accepted` dentro de la rama antes del PR.

### Paso 5: Commit Atómico
- Debido a que el evaluador de permisos anula el prefijo con comillas, **queda estrictamente prohibido** usar `git commit -m "..."`.
- Redactar el mensaje convencional en `.commit_msg` con `write_to_file`.
- Ejecutar el commit leyendo el archivo con `BypassSandbox: true` desde el primer intento:
  ```bash
  git commit -F .commit_msg
  ```
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
  ```bash
  rm -f .commit_msg
  ```

### Paso 6: Publicación Remota
- Subir la rama al repositorio remoto (`BypassSandbox: true`):
  ```bash
  git push -u origin <nombre-de-rama>
  ```

### Paso 7: Apertura de Pull Request (👀 In Review / PR)
- Redactar el cuerpo del PR en `.pr_body` con `write_to_file` y publicarlo mediante GitHub CLI (`BypassSandbox: true`):
  ```bash
  gh pr create --base <base_branch> --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
  ```
  *(Si `<base_branch>` es la rama por defecto del repositorio en GitHub, ej. `main` en Categoría A, el flag `--base` puede omitirse; en Categoría B debe especificarse explícitamente `--base dev`).*
- Sincronizar el ítem en Project 1 a `👀 In Review / PR`:
  ```bash
  gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "👀 In Review / PR"
  ```
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
  ```bash
  rm -f .pr_body
  ```

### Paso 8: Protocolo de Limpieza y Reconciliación Post-Merge (Done)
Tras la fusión (merge) del Pull Request en GitHub por el gate humano:
1. **Validar Cierre de la Issue:** Verificar que el merge haya cerrado automáticamente la issue vinculada (`gh issue view <id>`). Si permanece abierta por omisión en el PR body, cerrarla (`gh issue close <id>`).
2. **Sincronizar Tablero Central:** Transicionar la tarjeta en Project 1 a `Done`:
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "Done"
   ```
   *(Ejecutado con `BypassSandbox: true`).*
3. **Sincronizar Rama Base:** Retornar a la rama troncal y sincronizar en fast-forward podando referencias remotas obsoletas:
   ```bash
   git checkout <base_branch>
   git pull --prune --ff-only
   ```
   *(Ejecutados con `BypassSandbox: true`).*
4. **Poda Atómica de Ramas Locales:** Ejecutar `git-prune-gone` (`BypassSandbox: true`) para limpiar las ramas locales que trackeaban remotos ya fusionados y borrados.
5. **Ratificación Formal de ADRs Fusionados:** Ejecutar el subcomando de reconciliación para promover los ADRs fusionados en `main` de `status: proposed` a `status: accepted`:
   ```bash
   ./build.sh reconcile
   ```
   *(Ejecutado con `BypassSandbox: false`).*

---

## 3. Máquina de Estados Bidireccional (Matriz de Transiciones)

El tablero de Projects v2 opera como una máquina de estados formal bidireccional. Cada transición responde a un evento operativo y exige acciones concretas de compensación e higiene para garantizar la consistencia entre el tablero, las ramas de Git y el estado documental de los ADRs.

### 3.1 Matriz de Transiciones Progresivas (Forward)

| Origen | Destino | Disparador / Evento | Condición de Entrada | Acción Operativa Inmediata |
| :--- | :--- | :--- | :--- | :--- |
| `📥 Backlog` | `🎯 Ready for Dev` | Priorización | Requerimiento maduro con especificación y criterios de aceptación. | Transicionar tarjeta en Project 1. |
| `🎯 Ready for Dev` | `📐 In Planning` | Despacho de tarea | Sesión de agente asignada al ticket vía instrucción directa o backlog. | Ingesta técnica (`gh issue view`), mover a `📐 In Planning`. |
| `📐 In Planning` | `⚙️ In Progress` | Aprobación de Plan | Aprobación humana explícita de `implementation_plan.md` o fast-path ejecutivo. | Mover a `⚙️ In Progress`, iniciar codificación. ADR permanece en `proposed`. |
| `⚙️ In Progress` | `👀 In Review / PR` | Fin de desarrollo | Código probado con `./build.sh check`, commits atómicos y push remoto. | Crear PR con `Closes #<id>`, mover a `👀 In Review / PR`. |
| `👀 In Review / PR` | `Done` | Merge de PR | Gate humano de revisión, aprobación y fusión en `main`. | Ejecutar Paso 8 (Reconciliación Post-Merge y `./build.sh reconcile`). |
| `📐 In Planning` | `Done` | Conclusión de Spike | Tarea investigativa/auditoría sin cambios de código. | Informe técnico, cierre de issue, mover a `Done` (Sección 5). |

### 3.2 Matriz de Transiciones Regresivas (Backward / Rework / Rollback)

Cuando una tarea enfrenta bloqueos, revisiones insatisfactorias o cambios de prioridad, el retroceso debe ejecutarse aplicando estrictamente las siguientes acciones de compensación:

| Origen | Destino | Causa / Disparador | Acciones de Compensación e Higiene |
| :--- | :--- | :--- | :--- |
| `👀 In Review / PR` | `⚙️ In Progress` | **Observaciones en Code Review (Rework moderado/mayor):** El revisor solicita cambios funcionales, refactors o tests adicionales antes de aprobar. | 1. Mover tarjeta a `⚙️ In Progress` si el retrabajo requiere iteraciones locales significativas.<br>2. Posicionarse en la rama del PR (`gh pr checkout <pr_id>`).<br>3. Resolver observaciones vía `gh-pr-review` y herramientas nativas.<br>4. Commitear, pushear y regresar la tarjeta a `👀 In Review / PR`.<br>5. El ADR permanece consistentemente en `status: proposed`. |
| `👀 In Review / PR` | `📐 In Planning` | **Cuestionamiento Arquitectónico o Fallo de Enfoque:** El revisor rechaza el diseño técnico, detecta inviabilidad o exige replantear la solución. | 1. Mover tarjeta a `📐 In Planning`.<br>2. Invalidar el `implementation_plan.md` previo.<br>3. Mantener ADR existente en `status: proposed` (o redactar reemplazo/enmienda).<br>4. Redactar nuevo plan de implementación con pausa bloqueante (`RequestFeedback: true`).<br>5. Prohibido tocar código hasta obtener nueva aprobación humana. |
| `⚙️ In Progress` | `📐 In Planning` | **Bloqueo Técnico o Inviabilidad en Desarrollo:** El agente descubre que el enfoque planificado no es viable o choca con restricciones no previstas. | 1. Mover tarjeta a `📐 In Planning`.<br>2. Descartar cambios locales no viables (`git checkout .` / `git clean -fd`).<br>3. Actualizar `implementation_plan.md` justificando el cambio de rumbo.<br>4. Si hay ADR en curso, mantenerlo en `status: proposed` o ajustar la propuesta.<br>5. Solicitar confirmación humana antes de reanudar codificación. |
| `📐 In Planning` | `🎯 Ready for Dev` | **Despriorización Temporal o Bloqueo Externo:** Se interrumpe la planificación por falta de insumos externos o cambio temporal de foco. | 1. Mover tarjeta a `🎯 Ready for Dev`.<br>2. Si se creó rama local efímera, eliminarla (`git checkout main && git branch -D <rama>`).<br>3. Registrar comentario en el issue (`gh issue comment`) detallando el bloqueo o motivo de pausa. |
| `📐 In Planning` | `📥 Backlog` | **Descarte Temprano o Cancelación:** La exploración inicial concluye que la iniciativa es inviable o no prioritaria. | 1. Mover tarjeta a `📥 Backlog`.<br>2. Eliminar rama de trabajo si existiere.<br>3. Registrar diagnóstico en el issue (`gh issue comment`). Si se redactó borrador de ADR en rama, no ingresa a `main`. |
| `⚙️ In Progress` | `🎯 Ready for Dev` / `📥 Backlog` | **Aborto de Implementación:** Se decide cancelar el desarrollo ya iniciado. | 1. Mover tarjeta al destino correspondiente.<br>2. Eliminar rama local y rama remota (`git push origin --delete <rama>`).<br>3. Documentar en el issue el estado en que queda el requerimiento. |
| `👀 In Review / PR` | `📥 Backlog` / Cerrado | **Rechazo Definitivo de PR:** El PR se cierra sin merge por el usuario. | 1. Cerrar PR en GitHub.<br>2. Si contenía un nuevo ADR, el ADR nunca entra a `main` (descartado con la rama). Si fue propuesto en documento independiente, marcar `status: rejected`.<br>3. Ejecutar `git-prune-gone` localmente y transicionar tarjeta en Project 1. |

---

## 4. Flujo Mandatorio de Pull Requests y Projects v2

- **Prohibición Total de Push/Merge a `main`:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
- **Vinculación Canónica de Cierre (Simple y Múltiple):** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse el PR. Si el Pull Request resuelve conjuntamente una issue de implementación y una issue previa de investigación/auditoría o spike que motivó el cambio, debe listar cada una de forma independiente en líneas contiguas:
  ```markdown
  Closes #<id_implementacion>
  Closes #<id_investigacion>
  ```
- **Sincronización Determinista con el Tablero Central:** Asegurar que el estado del ítem en Project 1 pase a `👀 In Review / PR` mediante el comando directo por nombre de campo:
  ```bash
  gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "👀 In Review / PR"
  ```
  *(Queda prohibido ejecutar consultas exploratorias de `field-list` o `item-list` para resolver IDs cuando el comando directo es determinista).*
- **Gate de Aprobación Humana:** La revisión del diff, aprobación y fusión del PR es responsabilidad exclusiva del PM / Tech Lead en la interfaz de GitHub.

---

## 5. Protocolo Especial: Tareas de Investigación, Auditoría o Spikes (Cierre Autónomo sin PR)

Cuando una tarea despachada tenga por objeto una auditoría forense (`audit(...)`), investigación técnica, diagnóstico o spike exploratorio, y su conclusión técnica determine que **no se requieren cambios de código**:

1. **Prohibición de Delegación Pasiva de Cierre:**
   - Queda **terminantemente prohibido** que el agente finalice la tarea emitiendo una recomendación pasiva de cierre (ej. *"Se recomienda proceder al cierre de la issue #X"*), dejando la tarjeta abierta en el backlog para que el usuario la cierre manualmente.
2. **Publicación Determinista del Informe Técnico:**
   - Redactar el reporte técnico o justificación de resolución en `.issue_comment` mediante la herramienta nativa `write_to_file`.
   - Publicar el comentario en el ticket mediante GitHub CLI (`BypassSandbox: true`):
     ```bash
     gh issue comment <id> --body-file .issue_comment
     ```
   - Limpiar inmediatamente el archivo temporal (`BypassSandbox: false`):
     ```bash
     rm -f .issue_comment
     ```
3. **Cierre Autónomo Inmediato:**
   - Cerrar formalmente la issue de manera autónoma con GitHub CLI (`BypassSandbox: true`):
     ```bash
     gh issue close <id> --comment "Cierre automatizado tras concluir la investigación/auditoría técnica."
     ```
4. **Sincronización con Projects v2:**
   - Sincronizar el tablero a `Done` si GitHub CLI no lo realiza automáticamente:
     ```bash
     gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "Done"
     ```
5. **Reporte Final al Usuario:**
   - Reportar al usuario la conclusión del análisis, el enlace al issue cerrado y la confirmación del estado de la tarjeta en `Done`.

---

## 6. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.
