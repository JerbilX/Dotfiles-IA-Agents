# Referencia: Convención de Ramas, Ciclo E2E y Gestión de Pull Requests

Guía procedimental canónica para el ciclo de vida completo de ramas de trabajo, ejecución de tareas guiadas por issues, higiene de Git, apertura de PRs y cierre de tickets.

---

## 1. Convención Canónica de Ramas de Trabajo

Todo desarrollo (código, scripts de entorno/tooling, lanzadores, configuraciones o documentación) debe aislarse en una rama dedicada creada antes de modificar o crear cualquier archivo en el workspace. Prohibido taxativamente escribir o mutar archivos directamente en `main` bajo el pretexto de utilidades auxiliares o conveniencia operativa.

### 1.1 Estrategia de Ramas Troncales (Categorías A y B)
La estructura de ramas responde a la configuración raíz declarada en `.repo-config.json`:
* **Categoría A (Predeterminada - Repositorios Compactos / Tooling / Dotfiles / Librerías):** Troncal única `main`. Las ramas efímeras nacen de `main` y los Pull Requests apuntan directamente a `main`.
* **Categoría B (Aplicaciones con Despliegue Físico):** Troncal de integración continua `dev` (staging) y troncal de producción `main`. Las ramas efímeras nacen de `dev`, los PRs apuntan a `dev` (`gh pr create --base dev`), y la promoción a `main` se formaliza exclusivamente mediante un *Release PR* con tag SemVer (`vX.Y.Z`).

*(En ausencia de `.repo-config.json` o si no se explicitan sus propiedades, se adopta por defecto Categoría A con `base_branch: "main"`, `project_number: 1` y `project_owner: "@me"`).*

### 1.2 Nomenclatura Canónica de Ramas Efímeras
* **Nomenclatura Obligatoria:**
  * Funcionalidades, refactors o tareas generales: `feat/issue-<id>-<slug>`
  * Corrección de errores o parches: `fix/issue-<id>-<slug>`
* **Creación in-place:**
  ```bash
  git checkout -b <nombre-de-rama>
  ```
* **Compatibilidad con Worktrees (Orquestadores / Entornos Paralelos):** En flujos multi-agente u orquestados (ej. `Agent-Cockpit`), la rama puede aislarse en un worktree dedicado (`git worktree add .worktrees/issue-<id> -b <nombre-de-rama>`). Las reglas de ciclo e higiene aplican idénticamente, sumando el desmonte en el Paso 8.

---

## 2. Ciclo de Vida E2E de la Tarea

Toda tarea despachada debe cumplir secuencialmente con las siguientes 8 fases:

```
[1. Ingesta] ──> [2. Higiene] ──> [3. Plan/ADR] ──> [4. Desarrollo] ──> [5. Commit] ──> [6. Push] ──> [7. PR] ──> [8. Cierre & Higiene]
```

### Paso 1: Ingesta Técnica
1. Lectura exhaustiva de requerimientos y criterios de aceptación:
   ```bash
   gh issue view <id>
   ```
2. **Protocolo de Investigación Exploratoria (Ahorro de Contexto):**
   * **Lecturas Acotadas (≤ 8 archivos):** Si la tarea requiere inspección quirúrgica de hasta 8 archivos conocidos, realizar lecturas directas en la sesión principal mediante herramientas nativas de lectura o búsqueda por contenido.
   * **Exploración Extensa (> 8 archivos, repositorios externos o a pedido del usuario):** Evitar saturar la sesión principal con lecturas masivas. Delegar el relevamiento al subagente de investigación (ej. `research` con modelo `flash` en Antigravity, o subagente equivalente del runtime), quien devuelve un resumen ejecutivo consolidado. Ver [`references/exploratory-research.md`](exploratory-research.md).
3. El análisis sitúa la tarea operativamente en fase de planificación local (`📐 In Planning`), sin mutaciones CLI en GitHub Projects v2.

### Paso 2: Aislamiento e Higiene del Workspace

#### 2.1 Camino Preferente de Aislamiento (≤ 2 llamadas)
Para minimizar turnos y prompts interactivos, el arranque de una nueva tarea no requiere conmutar a la rama base local ni podar ramas (la poda se posterga a la Fase 8 post-merge):
1. **Sincronizar referencias remotas con poda sin conmutar a la base:**
   ```bash
   git fetch --prune origin
   ```
   *(Canalizar toda poda remota vía fetch o pull con `--prune` en lugar de `git remote prune`).*
2. **Crear y conmutar a la rama efímera desacoplada desde `origin/<base_branch>`:**
   ```bash
   git switch --no-track -c <nombre-de-rama> origin/<base_branch>
   ```
   *(`--no-track` evita tracking espurio contra la base; la rama queda desacoplada hasta el push en el Paso 6).*

#### 2.2 Saneamiento Integral y Poda con `git-prune-gone --sync` (Vía Alternativa / Higiene Explícita)
Si el repositorio presenta ramas zombi preexistentes o se requiere sincronizar la base local antes de iniciar:
```bash
git-prune-gone --sync
```
*(Conmuta a `<base_branch>`, ejecuta `git pull --prune --ff-only` y clasifica y poda ramas `[gone]`. Soporta `--base <rama>` para Categoría B, `--dry-run`, `--json` y `-f` / `--force`).*
* Tras sincronizar, crear y cambiar a la rama: `git checkout -b <nombre-de-rama>`.
* **Fallback Determinista:** Si no está en `$PATH`, seguir el [Protocolo de Invocación y Resiliencia de git-prune-gone](#protocolo-de-invocación-y-resiliencia-de-git-prune-gone). Prohibido recurrir a búsquedas exploratorias (`find`, `which`).

### Paso 3: Planificación y Refinamiento (📐 In Planning)
* **Escala por Nivel:** N1 (cambio acotado, sin `core/`, `runtimes/` ni ADR) omite plan bloqueante, ADR y evaluación MBR escrita; N0 no entra al ciclo. Lo siguiente aplica a N2.
* **Fast-Track por Defecto:** Para requerimientos con especificación técnica completa y criterios de aceptación claros en `🎯 Ready for Dev`, el agente no genera un `implementation_plan.md` bloqueante; avanza directamente al desarrollo activo (Paso 4), concentrando el control humano en el gate del Pull Request.
* **Freno Obligatorio de Planificación (Stop & Plan):** Requieren obligatoriamente `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`) las tareas con ambigüedad de diseño, múltiples caminos técnicos posibles, cambios arquitectónicos que introduzcan o modifiquen un ADR (`docs/adr/`) con `status: proposed`, o diagnósticos donde la causa raíz aún no ha sido confirmada empíricamente.
* **Evaluación de Minimal Blast Radius:** Registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Modificar directivas basales (`core/`) exige obligatoriamente la sección **"Justificación de Elevación Basal"**.
* **Excepción de Fast-Path Ejecutivo:** Si la solución fue debatida y consensuada en el chat activo y el usuario emite orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), proceder de inmediato sin plan bloqueante redundante.

### Paso 4: Transición a Desarrollo y Verificación (⚙️ In Progress)
* Al aprobarse el plan o entrar en fast-path, la tarea entra en desarrollo activo (`⚙️ In Progress`) en la rama local, sin mutaciones CLI en Projects v2.
* Modificaciones de código exclusivamente mediante herramientas nativas de archivos (escritura, edición, lectura, búsqueda). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`).
* **Lectura Paginada Obligatoria:** Toda lectura de archivos exige delimitar rango o paginado (ventana ≤ 200 líneas) sin excepción; prohibidas lecturas no acotadas. Localizar previamente mediante búsqueda por contenido.
* **Granularidad Atómica en Ediciones:** Particionar cambios en bloques acotados de edición para prevenir truncamientos en la respuesta y degradación por latencia. Prohibido reemplazar archivos completos monolíticamente.
* Validar compilación, linters y suites de prueba locales (`./build.sh check`).
* **Promoción Atómica del ADR:** Al comenzar a codificar, actualizar el YAML frontmatter del ADR a `status: accepted` en la rama de trabajo para ratificación atómica al mergear.

### Paso 5: Commit Atómico
1. **Staging Explícito:**
   ```bash
   git add <ruta1> <ruta2>
   ```
   *(Indicar rutas explícitas; no usar `git add .` ni `git add -A`).*
2. **Redacción y Commit Atómico:**
   * Evitar `git commit -m "..."` (anula el prefix matching de permisos al contener comillas). Redactar mensaje convencional en `.commit_msg` con herramientas nativas de archivos.
   * Incluir obligatoriamente al final del mensaje (separado por una línea en blanco) el trailer canónico de atribución:
     ```gitcommit
     <tipo>(<alcance>): <descripción>

     Generated-by: <runtime> (<modelo>)
     ```
     *(Con el formato y valor exacto declarado en la directiva del runtime activo: `Antigravity (<modelo de la sesión>)` o `Claude Code (<modelo>)`).*
   * Ejecutar el commit:
     ```bash
     git commit -F .commit_msg
     ```
   * Limpiar el archivo temporal:
     ```bash
     rm -f .commit_msg
     ```
     *(Emitir `rm -f .commit_msg` en paralelo con la siguiente llamada del turno).*

### Paso 6: Publicación Remota
Subir la rama al repositorio remoto:
```bash
git push -u origin <nombre-de-rama>
```

### Paso 7: Apertura de Pull Request (👀 In Review / PR)
1. Redactar el cuerpo del PR en `.pr_body` mediante herramientas nativas de archivos, incluyendo obligatoriamente `Closes #<id>` (o vinculación múltiple si aplica).
2. Publicar mediante GitHub CLI:
   ```bash
   gh pr create --base <base_branch> --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
   ```
   *(Si `<base_branch>` es la default del repositorio, `--base` puede omitirse; en Categoría B explicitar `--base dev`).*
3. **Indexación de Salvaguarda en Projects v2:**
   Para asegurar el ingreso inmediato del PR al tablero central en repositorios de Categoría B (donde la base `dev` no dispara el workflow nativo de indexación automática) o repositorios donde `Auto-add to project` carece de reglas globales, ejecutar inmediatamente la indexación determinista utilizando la URL devuelta por `gh pr create`:
   ```bash
   gh project item-add <project_number> --owner <project_owner> --url <pr_url>
   ```
   *(Donde `<project_number>` y `<project_owner>` se resuelven dinámicamente desde `.repo-config.json`, aplicando `1` y `@me` por defecto cuando no estén declarados).*
4. La vinculación `Closes #<id>` activa el workflow nativo `Pull request linked to issue` en Projects v2, transicionando la tarjeta a `👀 In Review / PR` sin llamadas manuales de CLI.
5. Limpiar el archivo temporal (`rm -f .pr_body`, emitido en paralelo con el reporte del turno).

### Paso 8: Protocolo de Cierre e Higiene Post-Merge (Done)

La resolución del Pull Request puede operar por tres vías de ejecución:

#### Vía A1: Fusión Remota por CLI bajo Orden Ejecutiva (Riel 1 Default - Fast-Track)
Tras la apertura del PR en el flujo estándar de 1 Gate, el agente reporta el PR y espera la revisión humana. Si el usuario emite una **orden ejecutiva o aprobación explícita en el chat** (*"aprobado, mergeá"*, *"mergealo"*, *"procede con el merge"*):
1. **Fusión Remota por CLI (`gh pr merge`):**
   ```bash
   gh pr merge <id> --squash --delete-branch
   ```
   *(Incorporar `--auto` si existen checks de CI pendientes).*
2. **Higiene Atómica Post-Merge con `git-prune-gone --sync` (≤ 2 llamadas de fase):**
   ```bash
   git-prune-gone --sync
   ```
   *(Conmuta a la base, ejecuta `git pull --prune --ff-only` y poda ramas zombi con detección de squash merge).*
   * Si se usó worktree efímero, desmontarlo: `git worktree remove .worktrees/issue-<id>`.
   * Ante ausencia en `$PATH`, aplicar de inmediato el [Protocolo de Invocación y Resiliencia de git-prune-gone](#protocolo-de-invocación-y-resiliencia-de-git-prune-gone).
3. **Cierre Automático y Verificación Condicional:**
   * La directiva `Closes #<id>` y el merge exitoso activan Built-in Workflows (*Pull request merged* e *Item closed*), cerrando la issue y avanzando la tarjeta a `Done` en Projects v2 de forma desatendida.
   * `gh issue view` o `gh issue close` queda reservado como fallback condicional ante errores de cierre remoto.

#### Vía A2: Auto-Merge Autónomo por CLI (Riel 2 Opt-in - 0 Gates)
Si el issue cuenta con la etiqueta `automerge` en GitHub o la orden inicial del usuario en el chat lo declaró explícitamente (*"implementa y automergea el issue #<id>"*):
1. **Evaluación de Circuit Breakers (Frenos de Seguridad):**
   - El agente verifica el diff local y el blast radius.
   - Si el cambio modifica directivas basales (`core/`), reglas de runtime (`runtimes/`) o introduce/modifica un ADR (`docs/adr/`) (Niveles 3 y 4 de blast radius), o si `./build.sh check`/tests arrojaron cualquier fallo o advertencia, **el auto-merge se cancela de inmediato**. El agente degrada a **Vía A1**, reportando el PR abierto y solicitando revisión humana con el motivo de la degradación.
2. **Fusión Autónoma Inmediata:**
   - Si se superan todos los circuit breakers y los tests locales están en verde, el agente invoca de forma inmediata tras abrir el PR:
     ```bash
     gh pr merge <id> --squash --delete-branch
     ```
3. **Higiene Atómica Post-Merge:**
   - Ejecutar inmediatamente `git-prune-gone --sync` y reportar la culminación del ciclo E2E al usuario.

#### Vía B: Fusión Manual en GitHub Web (Vía Alternativa / Fallback)
1. El usuario revisa, aprueba y fusiona el PR en la interfaz web de GitHub.
2. Ante la siguiente interacción o confirmación en chat, el agente ejecuta la higiene atómica:
   ```bash
   git-prune-gone --sync
   ```
3. Built-in Workflows avanza la tarjeta a `Done` automáticamente al detectarse el merge.

* **Higiene Post-Merge:** Al iniciar la siguiente tarea de desarrollo o tras confirmarse un merge, si la rama actual trackea un PR fusionado/cerrado o `[gone]`, ejecutar este paso de higiene. No se ejecuta ante simples consultas.

#### Protocolo de Invocación y Resiliencia de `git-prune-gone`

Ante cualquier paso de saneamiento o higiene post-merge, seguir estrictamente este orden determinista:

1. **Vía Primaria (Estándar en `$PATH`):**
   ```bash
   git-prune-gone --sync
   ```
2. **Vía de Fallback Determinista (Ruta Canónica de Skill):**
   Si la terminal reporta `command not found` o ausencia en `$PATH`, resolver inmediatamente la ruta física sin exploraciones intermedias:
   - **En este repositorio (`Dotfiles-IA-Agents`):**
     ```bash
     ./skills/issue-driven-workflow/bin/git-prune-gone --sync
     ```
   - **En workspaces externos:**
     - En **Antigravity**:
       ```bash
       ${HOME}/.gemini/config/skills/issue-driven-workflow/bin/git-prune-gone --sync
       ```
     - En **Claude Code**:
       ```bash
       ${HOME}/.claude/skills/issue-driven-workflow/bin/git-prune-gone --sync
       ```
3. **Vía de Fallback Git Nativo y Detención Segura (*Stop & Ask*):**
   Si el script no está disponible en el sistema en ninguna de las rutas canónicas anteriores:
   - **Higiene Git Nativa Inmediata:**
     ```bash
     git checkout <base_branch>
     git pull --prune --ff-only
     git branch -D <rama-local-fusionada>
     ```
     *(Usar `-D` solo si `gh pr view <rama> --json state --jq .state` devuelve `MERGED`: tras un squash merge `git branch -d` falla con `not fully merged` porque la rama no es ancestro de la base. Si el estado no es `MERGED`, no borrar y reportar al usuario).*
   - **Alerta al Usuario (Actionable Fallback):** Notificar al usuario en el chat que ejecute `./build.sh link` (o `./build.sh skills`) en su terminal nativa dentro de `Dotfiles-IA-Agents` para restablecer los binarios en `~/.local/bin/`.
   - **Prohibición Expresa de Búsquedas Ciegas:** Prohibido iniciar búsquedas exploratorias (búsquedas por nombre de archivo, `find /`, `grep`, `which`, `ls`) para localizar `git-prune-gone` u otros binarios de skills.

---

## 3. Máquina de Estados (Forward & Enlaces)

El ciclo de vida en Projects v2 se rige por transiciones desacopladas gobernadas por Git/GitHub y Built-in Workflows:

| Origen | Destino | Disparador / Evento | Condición de Entrada | Acción Operativa Inmediata |
| :--- | :--- | :--- | :--- | :--- |
| `📥 Backlog` | `🎯 Ready for Dev` | Priorización | Requerimiento maduro con especificación y criterios de aceptación. | Priorización humana (en UI) o asignación. |
| `🎯 Ready for Dev` | `📐 In Planning` | Despacho de tarea | Sesión asignada vía instrucción directa o backlog. | Ingesta técnica (`gh issue view`). Fase local de análisis. |
| `📐 In Planning` | `⚙️ In Progress` | Aprobación de Plan | Aprobación humana explícita de `implementation_plan.md` o fast-path. | Promover ADR a `status: accepted`, iniciar codificación en rama efímera. |
| `⚙️ In Progress` | `👀 In Review / PR` | Fin de desarrollo | Código probado con `./build.sh check`, commits atómicos y push remoto. | Crear PR con `Closes #<id>` (ADR viaja como `accepted`). Built-in Workflow avanza tarjeta a revisión. |
| `👀 In Review / PR` | `Done` | Merge de PR | Orden ejecutiva en chat (*"mergeá"*) o fusión manual en GitHub Web. | Fusión vía `gh pr merge <id> --squash --delete-branch` (o web); Built-in Workflow avanza a `Done`. Higiene con `git-prune-gone --sync`. |
| `📐 In Planning` | `Done` | Conclusión de Spike | Tarea investigativa/auditoría sin cambios de código. | Informe técnico en `.issue_comment` y cierre con `gh issue close <id>`. Built-in Workflow avanza tarjeta a `Done`. |

> [!NOTE]
> **Progressive Disclosure:** Para la matriz completa de las 7 transiciones regresivas (backward / rework / rollback ante observaciones en review, cuestionamiento arquitectónico, bloqueos técnicos o cancelaciones) y sus acciones de compensación e higiene, consultar la referencia especializada [`references/state-machine.md`](state-machine.md).

---

## 4. Invariantes Mandatorios de Pull Requests

* **Prohibición de Push/Merge Directo:** Prohibido comitear o pushear cambios productivos directamente a `<base_branch>` (`main` o `dev`), o ejecutar `git merge` hacia la troncal sin pasar por Pull Request.
* **Vinculación Canónica de Cierre:** El cuerpo del PR debe incluir obligatoriamente `Closes #<id>` o `Fixes #<id>`. Para tickets múltiples (derivadas o investigaciones conjuntas):
  ```markdown
  Closes #<id_implementacion>
  Closes #<id_investigacion>
  ```
* **Transición Automatizada:** La vinculación canónica activa Built-in Workflows en Projects v2. Prohibido ejecutar `gh project item-edit`.
* **Gate de Aprobación Humana:** Aprobación y merge son potestad exclusiva del usuario.

---

## 5. Protocolo Especial: Tareas de Investigación, Auditoría o Spikes (Cierre Autónomo sin PR)

Cuando una tarea investigativa o spike concluya que **no se requieren cambios de código**:
1. **Cierre Activo:** No delegar el cierre al usuario; cerrar la issue de forma autónoma.
2. **Publicación del Informe Técnico:**
   Redactar reporte en `.issue_comment` con herramientas nativas de archivos y publicar con GitHub CLI:
   ```bash
   gh issue comment <id> --body-file .issue_comment
   ```
   Limpiar el temporal: `rm -f .issue_comment`.
3. **Cierre Autónomo:**
   ```bash
   gh issue close <id>
   ```
4. **Sincronización Automatizada:** El workflow nativo *Item closed* transiciona la tarjeta a `Done` automáticamente sin requerir `gh project item-edit`.
5. **Reporte Final:** Reportar enlace al issue cerrado y confirmación del estado en `Done`.

---

## 6. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarea (Pull Request vinculado a la issue en revisión).
5. Indicación explícita para que el usuario revise el diff y apruebe el PR (pudiendo indicar *"aprobado, mergeá"* en el chat para fusión remota e higiene desatendida, o fusionarlo en GitHub Web).

---

*(Para la configuración manual de Built-in Workflows en la interfaz web de GitHub Projects v2, consultar la guía de setup para humanos en [`docs/setup/projects-v2-workflows.md`](../../../docs/setup/projects-v2-workflows.md)).*
