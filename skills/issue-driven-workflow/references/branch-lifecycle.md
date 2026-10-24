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
- **Compatibilidad con Worktrees (Orquestadores / Entornos Paralelos):**
  En flujos gobernados por orquestadores externos (ej. `Agent-Cockpit`) o agentes en paralelo, la rama efímera puede aislarse en un worktree dedicado (`git worktree add .worktrees/issue-<id> -b <nombre-de-rama>`). El ciclo de vida y las reglas de higiene aplican idénticamente, sumando el desmonte del worktree en el Paso 8.

---

## 2. Ciclo de Vida E2E de la Tarea

Cualquier tarea despachada debe cumplir secuencialmente con las siguientes 8 fases:

```
[1. Ingesta] -> [2. Higiene de Ramas] -> [3. Planificación (In Planning)] -> [4. Desarrollo (In Progress)] -> [5. Commit] -> [6. Push] -> [7. PR (In Review)] -> [8. Cierre e Higiene (Done)]
```

### Paso 1: Ingesta Técnica
1. Lectura profunda de los requerimientos, contexto, diagnóstico y criterios de aceptación en `gh issue view <id>` (`BypassSandbox: true`).
2. La asignación e inicio de análisis sitúa la tarea operativamente en fase de planificación local (`📐 In Planning`), sin requerir mutaciones por CLI en GitHub Projects v2.

### Paso 2: Aislamiento e Higiene del Workspace

#### 2.1 Camino Preferente de Aislamiento (≤ 2 llamadas con bypass)
Para minimizar turnos de interacción y prompts de autorización, el aislamiento de una nueva tarea no requiere conmutar a la rama base local ni podar ramas en este paso (la poda se delega a la Fase 8 post-merge):

1. **Sincronizar referencias remotas con poda sin conmutar a la base:**
   ```bash
   git fetch --prune origin
   ```
   *(Ejecutado con `BypassSandbox: true` desde el primer intento).*
   - **Mecánica:** Actualiza `remotes/origin/*` y poda referencias zombi en el transporte remoto sin modificar la rama de trabajo activa ni alterar el árbol local.
   - **Prohibición Categórica de `git remote prune`:** Toda poda remota debe canalizarse exclusivamente vía `git fetch --prune origin` o `git pull --prune --ff-only`.
2. **Crear y cambiar a la rama efímera desacoplada originada en `origin/<base_branch>`:**
   ```bash
   git switch --no-track -c <nombre-de-rama> origin/<base_branch>
   ```
   *(Ejecutado con `BypassSandbox: true` desde el primer intento).*
   - **Mecánica de `--no-track`:** Impide que la nueva rama efímera configure tracking espurio contra `origin/<base_branch>`. La rama queda completamente desacoplada localmente hasta que en el Paso 6 se ejecute `git push -u origin <nombre-de-rama>`.
   - **Delegación de Poda a Fase 8:** Al postergar la poda a la Fase 8 (donde `git-prune-gone --sync` higieniza el árbol tras el merge), el arranque de tarea se completa en exactamente 2 llamadas bypass.

#### 2.2 Saneamiento Integral y Poda con `git-prune-gone --sync` (Vía Alternativa / Higiene Explícita)
Si el repositorio presenta ramas zombi preexistentes o se desea sincronizar la base local antes de comenzar, se ejecuta:
```bash
git-prune-gone --sync
```
*(Ejecutado con `BypassSandbox: true` desde el primer intento).*
- **Sincronización y Poda Atómica:** `git-prune-gone --sync` verifica que no existan cambios pendientes (`git status --porcelain`), conmuta automáticamente a `<base_branch>` (detectada de `--base`, `.repo-config.json` o `main`), ejecuta `git pull --prune --ff-only` y clasifica y poda ramas `[gone]`.
- **Compatibilidad con Squash Merge y Salvaguarda de Integridad:** `git-prune-gone` clasifica ramas locales con tracking `[gone]` contra la rama base:
  - `merged`: Ascendencia directa confirmada por merge tradicional (se poda de forma segura con `git branch -d`).
  - `squash-merged`: Integración de árbol comprobada en memoria vía `git merge-tree --write-tree` contra la base ya sincronizada (se poda de forma segura con `git branch -D` al estar verificada su integración total).
  - `unmerged`: Cambios no integrados o en conflicto respecto a la base. Se preservan intactas y se reportan con código de salida 1; solo se eliminan si se explicita `--force` (`-f`).
- **Flags Operativos:** Soporta `--sync` para sincronización y poda en una sola invocación, `--base <rama>` para repositorios de Categoría B, `--dry-run` para inspección pasiva sin borrado, `--json` para telemetría estructurada y `-f` / `--force` para forzar la eliminación de ramas descartadas.
- **Fallback Determinista:** Si el binario no está disponible en `$PATH`, invocar directamente `skills/issue-driven-workflow/bin/git-prune-gone`.
- Tras la sincronización, crear y cambiar a la rama con `git checkout -b <nombre-de-rama>` (`BypassSandbox: true`).

### Paso 3: Planificación y Refinamiento (📐 In Planning)
- **Blindaje del Planning Mode:** Toda tarea que implique diagnóstico de errores (bug fixing) o modificaciones arquitectónicas requiere obligatoriamente redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
- **Evaluación Obligatoria de Minimal Blast Radius:** Todo plan de implementación debe evaluar y registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Si la propuesta plantea modificar directivas basales (`core/`), debe incorporar obligatoriamente la sección **"Justificación de Elevación Basal"** acreditando la inviabilidad técnica en los niveles 0 a 3.
- **Excepción de Fast-Path Ejecutivo:** Si la solución técnica o cambio ya fue debatido y consensuado explícitamente en el chat y el usuario emitió una orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), el agente **NO DEBE** pausar con un plan bloqueante; procede de inmediato a la implementación.
- **Registro de ADRs:** Si se toman decisiones arquitectónicas o estructurales, registrar un nuevo ADR con `status: proposed` mediante el skill `adr-manager` (`docs/adr/NNNN-titulo.md`). Permanece en `status: proposed` durante la fase de análisis y redacción del plan.

### Paso 4: Transición a Desarrollo y Verificación (⚙️ In Progress)
- Al aprobarse el plan o entrar en fast-path ejecutivo, la tarea entra en desarrollo activo (`⚙️ In Progress`) en la rama efímera local, sin requerir mutaciones por CLI en Projects v2.
- Aplicar cambios atómicos exclusivamente mediante las APIs nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`).
- Ejecutar compilaciones locales, linters y suites de prueba del proyecto para validar que no existan regresiones (`./build.sh check` con `BypassSandbox: false`).
- **Promoción Atómica del ADR:** Al comenzar el desarrollo, el YAML frontmatter del ADR se actualiza a `status: accepted` en la rama de trabajo. Queda preparado para entrar a la rama troncal (`<base_branch>`) ya ratificado y de forma atómica junto con la implementación.

### Paso 5: Commit Atómico
1. **Staging Explícito de Cambios:**
   - Preparar exclusivamente los archivos modificados o creados para la tarea utilizando rutas explícitas:
     ```bash
     git add <ruta1> <ruta2> ...
     ```
     *(Ejecutado con `BypassSandbox: true` desde el primer intento por mutación del índice en `.git/`).*
   - **Prohibición Categórica de Staging Masivo:** Queda terminantemente prohibido utilizar `git add .`, `git add -A` o comodines globales indiscriminados durante el ciclo E2E (salvo de forma excepcional durante el commit inicial de aprovisionamiento en repositorios nuevos). El staging debe ser selectivo y explícito para evitar capturar archivos temporales o cambios ajenos al alcance.
2. **Redacción y Creación del Commit:**
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
     - **Emisión Concurrente (C7):** Para no consumir un turno exclusivo para la limpieza, emitir `rm -f .commit_msg` en paralelo dentro del mismo turno junto con la siguiente llamada independiente (`git push -u origin <nombre-de-rama>` con `BypassSandbox: true`), garantizando la higiene inmediata sin turnos ociosos.

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
- La vinculación `Closes #<id>` y el flujo nativo `Pull request linked to issue` en Projects v2 avanza automáticamente la tarjeta a `👀 In Review / PR` sin llamadas manuales de CLI.
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
   ```bash
   rm -f .pr_body
   ```
   - **Emisión Concurrente (C7):** Emitir `rm -f .pr_body` en paralelo dentro del mismo turno junto con el reporte final al usuario o la siguiente acción independiente.

### Paso 8: Protocolo de Cierre e Higiene Post-Merge (Done)

La resolución final del Pull Request puede operar por dos vías de ejecución:

#### Vía A: Fusión Remota por CLI (Vía Preferente ante Orden Ejecutiva)
Tras la apertura del PR y la revisión por el usuario, si este emite una **orden ejecutiva o aprobación explícita en el chat** (*"aprobado, mergeá"*, *"mergealo"*, *"procede con el merge"*):

1. **Fusión Remota por CLI (`gh pr merge`):**
   ```bash
   gh pr merge <id> --squash --delete-branch
   ```
   *(incorporar `--auto` si existen checks obligatorios de CI pendientes: `gh pr merge <id> --squash --delete-branch --auto`)* con `BypassSandbox: true` desde el primer intento.
   > [!IMPORTANT]
   > **Invariante Human-in-the-Loop:** Queda terminantemente prohibido que el agente invoque `gh pr merge` por iniciativa propia o de forma autónoma. La ejecución exige una orden ejecutiva explícita o confirmación humana en el chat.
   >
   > **Comportamiento de `gh pr merge --delete-branch`:** GitHub CLI elimina la rama remota, borra la rama local seleccionada y deja el workspace en la rama predeterminada de GitHub (habitualmente `main`).

2. **Higiene Atómica Post-Merge con `git-prune-gone --sync` (≤ 2 llamadas totales de fase):**
   Inmediatamente tras la confirmación exitosa del merge remoto, el agente ejecuta en un único paso determinista:
   ```bash
   git-prune-gone --sync
   ```
   *(BypassSandbox: true desde el primer intento).*
   - **Sincronización y Poda Integrada:** Conmuta a la base del repositorio si no está seleccionada (cubriendo automáticamente `dev` en Categoría B), ejecuta `git pull --prune --ff-only` y clasifica y poda ramas `[gone]`.
   - **Detección de Squash sobre Base Sincronizada:** Al actualizar la base con los commits remotos antes de evaluar los árboles, `git-prune-gone --sync` detecta con total fiabilidad la integración vía squash (`git merge-tree --write-tree`).
   - **Desmontaje de Worktree (Entornos Aislados / Agent-Cockpit):** Si el desarrollo se ejecutó en un worktree efímero (patrón orquestadores multi-agente), desmontar y limpiar el directorio de trabajo con:
     ```bash
     git worktree remove .worktrees/issue-<id>
     ```
     *(BypassSandbox: true).*

3. **Cierre Automático y Verificación Condicional (C8):**
   - Cuando el PR contiene directivas de cierre canónicas (`Closes #<id>` o `Fixes #<id>`) y `gh pr merge` reporta éxito (código 0), GitHub Built-in Workflows (*Pull request merged* e *Item closed*) cierran automáticamente la issue y avanzan la tarjeta a `Done` en Projects v2.
   - **Fallback Condicional:** La verificación explícita con `gh issue view <id>` (o cierre con `gh issue close <id>`) queda reservada exclusivamente como fallback si el PR omitió la directiva de cierre o si el comando de merge arrojó error. Confirmar en el chat el cierre exitoso y la higiene del workspace.

#### Vía B: Fusión Manual en GitHub Web (Vía Alternativa / Fallback)
Si el usuario prefiere fusionar manualmente desde la interfaz web de GitHub (o ante conflictos/políticas de merge de ramas que requieran UI web):
1. El usuario revisa, aprueba y fusiona el PR en la interfaz web de GitHub.
2. Tras la fusión, ante la siguiente interacción o confirmación en chat, el agente ejecuta la higiene atómica post-merge:
   ```bash
   git-prune-gone --sync
   ```
   *(BypassSandbox: true).*
   - Si aplica worktree efímero: `git worktree remove .worktrees/issue-<id>` (`BypassSandbox: true`).
3. El Built-in Workflow avanza la tarjeta a `Done` al detectarse el merge.

- **Invariante de Higiene Proactiva:** Ante cualquier consulta o interacción subsiguiente del usuario (sea una pregunta exploratoria como *"¿con qué seguimos?"* o despacho de nueva tarea), si el agente detecta que la rama actual trackea un PR ya fusionado/cerrado o tracking `[gone]`, ejecuta inmediatamente este paso de higiene sin esperar una nueva orden de desarrollo.

---

## 3. Máquina de Estados Bidireccional (Matriz de Transiciones)

El tablero de Projects v2 opera como una máquina de estados formal bidireccional. Cada transición responde a un evento operativo y exige acciones concretas de compensación e higiene para garantizar la consistencia entre el tablero, las ramas de Git y el estado documental de los ADRs.

### 3.1 Matriz de Transiciones Progresivas (Forward)

| Origen | Destino | Disparador / Evento | Condición de Entrada | Acción Operativa Inmediata |
| :--- | :--- | :--- | :--- | :--- |
| `📥 Backlog` | `🎯 Ready for Dev` | Priorización | Requerimiento maduro con especificación y criterios de aceptación. | Priorización humana (en UI) o asignación. |
| `🎯 Ready for Dev` | `📐 In Planning` | Despacho de tarea | Sesión de agente asignada al ticket vía instrucción directa o backlog. | Ingesta técnica (`gh issue view`). Fase local de análisis. |
| `📐 In Planning` | `⚙️ In Progress` | Aprobación de Plan | Aprobación humana explícita de `implementation_plan.md` o fast-path ejecutivo. | Promover ADR a `status: accepted`, iniciar codificación en rama efímera. |
| `⚙️ In Progress` | `👀 In Review / PR` | Fin de desarrollo | Código probado con `./build.sh check`, commits atómicos y push remoto. | Crear PR con `Closes #<id>` (ADR viaja como `accepted`). Built-in Workflow avanza tarjeta a `👀 In Review / PR`. |
| `👀 In Review / PR` | `Done` | Merge de PR | Orden ejecutiva en chat (*"mergeá"*) o fusión manual en GitHub Web. | Fusión vía `gh pr merge <id> --squash --delete-branch` (o web); Built-in Workflow avanza a `Done`. Ejecutar encadenamiento atómico de higiene (Paso 8). |
| `📐 In Planning` | `Done` | Conclusión de Spike | Tarea investigativa/auditoría sin cambios de código. | Informe técnico en `.issue_comment` y cierre con `gh issue close <id>`. Built-in Workflow avanza tarjeta a `Done` (Sección 5). |

### 3.2 Matriz de Transiciones Regresivas (Backward / Rework / Rollback)

Cuando una tarea enfrenta bloqueos, revisiones insatisfactorias o cambios de prioridad, el retroceso debe ejecutarse aplicando estrictamente las siguientes acciones de compensación:

| Origen | Destino | Causa / Disparador | Acciones de Compensación e Higiene |
| :--- | :--- | :--- | :--- |
| `👀 In Review / PR` | `⚙️ In Progress` | **Observaciones en Code Review (Rework moderado/mayor):** El revisor solicita cambios funcionales, refactors o tests adicionales antes de aprobar. | 1. Posicionarse en la rama del PR (`gh pr checkout <pr_id>`).<br>2. Resolver observaciones vía `gh-pr-review` y herramientas nativas.<br>3. Commitear, pushear y notificar.<br>4. Si las observaciones afectan la arquitectura, ajustar el ADR según corresponda.<br>*(Si está activo el Built-in Workflow 'Code changes requested', el evento de review solicita cambios y actualiza el tablero automáticamente)*. |
| `👀 In Review / PR` | `📐 In Planning` | **Cuestionamiento Arquitectónico o Fallo de Enfoque:** El revisor rechaza el diseño técnico, detecta inviabilidad o exige replantear la solución. | 1. Invalidar el `implementation_plan.md` previo.<br>2. Revertir ADR a `status: proposed` (o redactar reemplazo/enmienda).<br>3. Redactar nuevo plan de implementación con pausa bloqueante (`RequestFeedback: true`).<br>4. Prohibido tocar código hasta obtener nueva aprobación humana. |
| `⚙️ In Progress` | `📐 In Planning` | **Bloqueo Técnico o Inviabilidad en Desarrollo:** El agente descubre que el enfoque planificado no es viable o choca con restricciones no previstas. | 1. Aislar de forma reversible los cambios descartados mediante `git stash push -u -m abort-issue-<id>` (o commit WIP en la rama efímera). Prohibido ejecutar `git clean` o borrados destructivos sin confirmación humana explícita.<br>2. Actualizar `implementation_plan.md` justificando el cambio de rumbo.<br>3. Si hay ADR en curso, revertirlo a `status: proposed` o ajustar la propuesta.<br>4. Solicitar confirmación humana antes de reanudar codificación. |
| `📐 In Planning` | `🎯 Ready for Dev` | **Despriorización Temporal o Bloqueo Externo:** Se interrumpe la planificación por falta de insumos externos o cambio temporal de foco. | 1. Si se creó rama local efímera, posicionarse en la rama base (`git checkout <base_branch>`) y eliminarla (`git branch -D <rama>`) en pasos atómicos sin encadenar comandos.<br>2. Registrar comentario en el issue (`gh issue comment`) detallando el bloqueo o motivo de pausa. |
| `📐 In Planning` | `📥 Backlog` | **Descarte Temprano o Cancelación:** La exploración inicial concluye que la iniciativa es inviable o no prioritaria. | 1. Eliminar rama de trabajo si existiere.<br>2. Registrar diagnóstico en el issue (`gh issue comment`). Si se redactó borrador de ADR en rama, no ingresa a la rama troncal (`<base_branch>`). |
| `⚙️ In Progress` | `🎯 Ready for Dev` / `📥 Backlog` | **Aborto de Implementación:** Se decide cancelar el desarrollo ya iniciado. | 1. Posicionarse en la rama base (`git checkout <base_branch>`), eliminar la rama local (`git branch -D <rama>`) y la rama remota (`git push origin --delete <rama>`) en pasos atómicos.<br>2. Documentar en el issue el estado en que queda el requerimiento. |
| `👀 In Review / PR` | `📥 Backlog` / Cerrado | **Rechazo Definitivo de PR:** El PR se cierra sin merge por el usuario. | 1. Cerrar PR en GitHub.<br>2. Si contenía un nuevo ADR, el ADR nunca entra a la rama troncal (descartado con la rama). Si fue propuesto en documento independiente, marcar `status: rejected`.<br>3. Ejecutar `git-prune-gone` localmente. |

---

## 4. Flujo Mandatorio de Pull Requests y Projects v2

- **Prohibición Total de Push/Merge a Ramas Troncales:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama troncal (`<base_branch>`, sea `main` o `dev`), o que ejecute `git merge` hacia la troncal por su cuenta.
- **Vinculación Canónica de Cierre (Simple y Múltiple):** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse el PR. Si el Pull Request resuelve conjuntamente una issue de implementación y una issue previa de investigación/auditoría o spike que motivó el cambio, debe listar cada una de forma independiente en líneas contiguas:
  ```markdown
  Closes #<id_implementacion>
  Closes #<id_investigacion>
  ```
- **Transición Automatizada del Tablero Central:** La vinculación canónica (`Closes #<id>`) activa el Built-in Workflow `Pull request linked to issue` en Projects v2, situando el ítem automáticamente en `👀 In Review / PR`. Queda terminantemente prohibido que el agente ejecute llamadas manuales de mutación (`gh project item-edit`).
- **Gate de Aprobación Humana e Invariante Human-in-the-Loop:** La revisión del diff y la aprobación del PR es potestad exclusiva del usuario. La fusión del PR puede realizarse manualmente por el usuario en la interfaz web de GitHub o ejecutarse desatendidamente por el agente mediante `gh pr merge <id> --squash --delete-branch` (`BypassSandbox: true`) ÚNICAMENTE tras recibir la orden ejecutiva o aprobación explícita en el chat (*"aprobado, mergeá"*, *"procede con el merge"*). Prohibido el merge autónomo sin instrucción previa.

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
     gh issue close <id>
     ```
4. **Sincronización Automatizada con Projects v2:**
   - Al ejecutarse `gh issue close`, el Built-in Workflow *Item closed* de GitHub Projects v2 transiciona automáticamente la tarjeta a `Done` sin requerir invocaciones a `gh project item-edit`.
5. **Reporte Final al Usuario:**
   - Reportar al usuario la conclusión del análisis, el enlace al issue cerrado y la confirmación del estado de la tarjeta en `Done`.

---

## 6. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarea (Pull Request vinculado a la issue en revisión).
5. Indicación explícita para que el usuario revise el diff y apruebe el PR (pudiendo indicar *"aprobado, mergeá"* en el chat para que el agente ejecute la fusión remota y la higiene de forma desatendida, o fusionarlo directamente en GitHub).

---

## 7. Configuración Canónica de Built-in Workflows en Projects v2

Para garantizar que el tablero central (`Proyectos-IA-V3`) sincronice automáticamente el ciclo de vida sin que el agente deba ejecutar comandos burocráticos de CLI, el proyecto se configura en la interfaz web de GitHub (**Project Settings -> Workflows**):

| Workflow Nativo | Disparador (Trigger) | Acción (Set value) | Propósito |
| :--- | :--- | :--- | :--- |
| **`Auto-add to project`** | `When filter matches` (`is:issue,pr is:open` por repo) | Add item to project | Indexación desatendida de issues y PRs en repositorios bajo su filtro (con `item-add` como salvaguarda fuera de él). |
| **`Pull request linked to issue`** | `When a pull request is linked to an issue` | `Status: 👀 In Review / PR` | Transición a revisión al publicar PR con `Closes #<id>`. |
| **`Pull request merged`** | `When a pull request is merged` | `Status: Done` | Cierre automático de PR cards al mergear en rama base. |
| **`Item closed`** | `When an item is closed` | `Status: Done` | Cierre automático de issue cards al mergear PR o cerrar spikes. |
| **`Code changes requested`** | `When review requests changes` | `Status: ⚙️ In Progress` | Retorno automático a progreso si el review exige correcciones. |
| **`Item reopened`** | `When an item is reopened` | `Status: 🎯 Ready for Dev` | Reactivación de tickets reabiertos para nuevo ciclo E2E. |

