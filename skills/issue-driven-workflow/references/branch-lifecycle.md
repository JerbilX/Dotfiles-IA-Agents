# Referencia: Convención de Ramas, Ciclo E2E y Gestión de Pull Requests

Guía procedimental canónica para el ciclo de vida completo de ramas de trabajo, ejecución de tareas guiadas por issues, higiene de Git, apertura de PRs y cierre de tickets.

---

## 1. Convención Canónica de Ramas de Trabajo

Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código del workspace.

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
2. El análisis sitúa la tarea operativamente en fase de planificación local (`📐 In Planning`), sin mutaciones CLI en GitHub Projects v2.

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
* **Fallback Determinista:** Si no está en `$PATH`, invocar `skills/issue-driven-workflow/bin/git-prune-gone`.

### Paso 3: Planificación y Refinamiento (📐 In Planning)
* **Blindaje del Planning Mode:** Diagnóstico de errores (bug fixing) o cambios arquitectónicos requieren obligatoriamente `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
* **Evaluación de Minimal Blast Radius:** Registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Modificar directivas basales (`core/`) exige obligatoriamente la sección **"Justificación de Elevación Basal"**.
* **Excepción de Fast-Path Ejecutivo:** Si la solución fue debatida y consensuada en el chat activo y el usuario emite orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), proceder de inmediato sin plan bloqueante.
* **Registro de ADRs:** Cambios arquitectónicos o estructurales exigen registrar un ADR en `docs/adr/NNNN-titulo.md` con `status: proposed` vía skill `adr-manager`.

### Paso 4: Transición a Desarrollo y Verificación (⚙️ In Progress)
* Al aprobarse el plan o entrar en fast-path, la tarea entra en desarrollo activo (`⚙️ In Progress`) en la rama local, sin mutaciones CLI en Projects v2.
* Modificaciones de código exclusivamente mediante herramientas nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`).
* Validar compilación, linters y suites de prueba locales (`./build.sh check`).
* **Promoción Atómica del ADR:** Al comenzar a codificar, actualizar el YAML frontmatter del ADR a `status: accepted` en la rama de trabajo para ratificación atómica al mergear.

### Paso 5: Commit Atómico
1. **Staging Explícito:**
   ```bash
   git add <ruta1> <ruta2>
   ```
   *(Indicar rutas explícitas; no usar `git add .` ni `git add -A`).*
2. **Redacción y Commit Atómico:**
   * Evitar `git commit -m "..."` (anula el prefix matching de permisos al contener comillas). Redactar mensaje convencional en `.commit_msg` con `write_to_file`.
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
1. Redactar el cuerpo del PR en `.pr_body` con `write_to_file`, incluyendo obligatoriamente `Closes #<id>` (o vinculación múltiple si aplica).
2. Publicar mediante GitHub CLI:
   ```bash
   gh pr create --base <base_branch> --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
   ```
   *(Si `<base_branch>` es la default del repositorio, `--base` puede omitirse; en Categoría B explicitar `--base dev`).*
3. La vinculación `Closes #<id>` activa el workflow nativo `Pull request linked to issue` en Projects v2, transicionando la tarjeta a `👀 In Review / PR` sin llamadas manuales de CLI.
4. Limpiar el archivo temporal (`rm -f .pr_body`, emitido en paralelo con el reporte del turno).

### Paso 8: Protocolo de Cierre e Higiene Post-Merge (Done)

La resolución del Pull Request puede operar por dos vías de ejecución:

#### Vía A: Fusión Remota por CLI (Vía Preferente ante Orden Ejecutiva)
Tras la apertura del PR, si el usuario emite una **orden ejecutiva o aprobación explícita en el chat** (*"aprobado, mergeá"*, *"mergealo"*, *"procede con el merge"*):
1. **Fusión Remota por CLI (`gh pr merge`):**
   ```bash
   gh pr merge <id> --squash --delete-branch
   ```
   *(Incorporar `--auto` si existen checks de CI pendientes).*
   > [!IMPORTANT]
   > **Invariante Human-in-the-Loop:** Prohibido invocar `gh pr merge` de forma autónoma. Exige orden ejecutiva explícita en el chat.
2. **Higiene Atómica Post-Merge con `git-prune-gone --sync` (≤ 2 llamadas de fase):**
   ```bash
   git-prune-gone --sync
   ```
   *(Conmuta a la base, ejecuta `git pull --prune --ff-only` y poda ramas zombi con detección de squash merge).*
   * Si se usó worktree efímero, desmontarlo: `git worktree remove .worktrees/issue-<id>`.
3. **Cierre Automático y Verificación Condicional:**
   * La directiva `Closes #<id>` y el merge exitoso activan Built-in Workflows (*Pull request merged* e *Item closed*), cerrando la issue y avanzando la tarjeta a `Done` en Projects v2 de forma desatendida.
   * `gh issue view` o `gh issue close` queda reservado como fallback condicional ante errores de cierre remoto.

#### Vía B: Fusión Manual en GitHub Web (Vía Alternativa / Fallback)
1. El usuario revisa, aprueba y fusiona el PR en la interfaz web de GitHub.
2. Ante la siguiente interacción o confirmación en chat, el agente ejecuta la higiene atómica:
   ```bash
   git-prune-gone --sync
   ```
3. Built-in Workflows avanza la tarjeta a `Done` automáticamente al detectarse el merge.

* **Invariante de Higiene Proactiva:** Ante cualquier consulta o interacción subsiguiente, si el agente detecta que la rama actual trackea un PR ya fusionado/cerrado o tracking `[gone]`, ejecuta inmediatamente este paso de higiene sin esperar una nueva orden de desarrollo.

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
   Redactar reporte en `.issue_comment` con `write_to_file` y publicar con GitHub CLI:
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
