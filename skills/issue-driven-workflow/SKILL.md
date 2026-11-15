---
name: issue-driven-workflow
description: >-
  Orchestrate task execution via GitHub Issues, Projects v2, branch lifecycles, and Pull Requests. ACTIVATE whenever creating issues, provisioning repos, implementing issues, querying the board, managing branches, opening PRs, closing audit tasks, or resolving Code Review comments. Not for read-only queries or analysis. Operates with strict git hygiene and deterministic CLI tooling.
---

# Issue-Driven Workflow and Pull Request Management

Orquestador canónico para desarrollo guiado por GitHub Issues, Projects v2 y Pull Requests bajo Progressive Disclosure. Procedimientos exhaustivos en `references/`.

---

## 1. Invariantes y Referencias Basales

Subordinado a las directivas basales compiladas en el prompt del runtime:

* **Backlog Canónico:** Prohibido `TODO.md` o `tasks/`; registro en Issues vía `issue-create` e indexación en Projects v2 con perfiles según MBR (`profile:low`, `profile:medium`, `profile:high`, `profile:pro`).
* **Ceremonia y Trazabilidad:** N0 (consultas, `scratch/`: sin issue ni rama), N1 (cambio acotado, evidente, sin `core/`, `runtimes/` ni ADR: issue concisa con perfil tipificado, sin plan formal ni ADR), N2 (feature, ambigüedad, `core/`, `runtimes/` o ADR: ciclo completo con plan y/o ADR). Precedencia de Entornos Locales: priorizar binarios locales (`.venv/bin/`, `node_modules/.bin/`) sobre intérpretes globales.
* **Inmutabilidad y PRs:** Inmutabilidad estricta de workspace (tooling y scripts constituyen desarrollo). Prohibido push directo a `main`. Ramas efímeras (`feat/` o `fix/`) y entrega vía PR.
* **Higiene, Pruebas y Atomicidad:** I/O solo con herramientas nativas de archivos; delimitación obligatoria de rango o paginado (ventana ≤ 200 líneas); circuit breaker e inmunidad heurística; granularidad atómica en ediciones; acotar salidas (`head -n 20`, `--jq`) y pruebas filtradas en desarrollo (suite integral solo previa al commit); temporales de intercambio (`.commit_msg`, `.pr_body`, `.issue_body`) en `scratch/` (o raíz según runtime), commits vía `-F` y eliminación inmediata tras su uso.
* **Sandbox y Atomicidad de Ejecución:** Subordinado a `runtimes/*/rules/01-sandbox.md`. Comandos de red, git mutadores (`init`, `checkout`, `switch`, `branch`, `add`, `commit`, `merge`, `push`, `pull`, `revert`), `gh` y tooling autorizado (`agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`, `issue-create`) operan con bypass de sandbox (ej. `BypassSandbox: true` en Antigravity) como comandos atómicos directos; prohibido taxativamente encadenar llamadas (`&&`, `;`, `|`). Validaciones locales, checks (`./build.sh check`), inspección git pasiva y remoción de archivos temporales (`rm -f`) operan en sandbox confinado (ej. `BypassSandbox: false` en Antigravity).
* **Resiliencia de Binarios:** Ante fallo de invocación de tooling autorizado (`command not found` o ausencia en `$PATH`), resolver directamente la ruta canónica (`./skills/<skill>/bin/<cmd>` en este repo; `<skills_dir del runtime>/<skill>/bin/<cmd>` en workspaces externos) o aplicar fallback nativo (`git checkout <base> && git pull --prune --ff-only` y `git branch -D <rama>` solo si su PR está `MERGED`); prohibido realizar búsquedas exploratorias ciegas (`find`, `which`, `ls`).

---

## 2. Matriz de Ruteo y Referencias Especializadas

Procedimientos detallados y plantillas en `references/`:

| Dominio | Contenido | Referencia Especializada |
| :--- | :--- | :--- |
| **Backlog** | Criterios, Minimal Blast Radius (0-4), matriz MBR->perfiles, 6 estados y Projects v2. | [`references/issue-backlog.md`](references/issue-backlog.md) |
| **Aprovisionamiento** | `git init`, gate de origin y repo privado en GitHub. | [`references/repo-provisioning.md`](references/repo-provisioning.md) |
| **Ramas y PRs** | Cat. A/B, higiene, 8 fases E2E, apertura de PRs y cierre post-merge. | [`references/branch-lifecycle.md`](references/branch-lifecycle.md) |
| **Máquina de Estados** | Matriz de transiciones progresivas y regresivas (rework, bloqueos, rollback). | [`references/state-machine.md`](references/state-machine.md) |
| **Code Review** | Ingesta `gh-pr-review`, parches y resolución de hilos. | [`references/code-review.md`](references/code-review.md) |
| **Investigación Exploratoria** | Protocolo de delegación al subagente de investigación del runtime (ej. `research` con modelo `flash` en Antigravity), ahorro de tokens (> 3 archivos) y consolidación. | [`references/exploratory-research.md`](references/exploratory-research.md) |
| **Rollback** | Reversión con `git revert` y `build.sh rollback`. | [`references/rollback.md`](references/rollback.md) |

---

## 3. Despacho y Recepción de Tareas

> [!IMPORTANT]
> Consultas de coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*) no autorizan crear ramas ni modificar código. La higiene (retornar a la rama base y podar ramas locales zombi si el PR previo fue fusionado o cerrado) se ejecuta al iniciar una tarea de desarrollo o tras un merge, no ante consultas.

### 3.1 Consultas de Tablero (*"¿qué hay en el board?"*)
Filtrar activos del repo (Top 2-3 con justificación):
```bash
gh board <owner>/<repo>
```
*(Alias prefix-matchable. Fallback si el alias no está configurado: `gh project item-list <project_number> --owner <project_owner> --limit 100 --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'`, donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json` o aplican `1` y `@me` por defecto).*

### 3.2 Despacho Vía A: Instrucción Directa (*"implementa la issue #<id>"*)
1. Ingesta: `gh issue view <id>`. Contrastar con contratos y ADRs vigentes; ante directivas de re-arquitectura, borrado masivo o parches sobre bases viciadas, emitir dictamen técnico previo en lugar de ejecutar mecánicamente (`core/01-objectivity.md`).
2. Proceder al ciclo E2E (aislamiento local en rama efímera; sin mutaciones CLI de Project).

### 3.3 Despacho Vía B: Backlog (*"siguiente tarea lista"*)
1. Consultar listos:
```bash
gh board-ready <owner>/<repo>
```
*(Alias prefix-matchable. Fallback si el alias no está configurado: `gh project item-list <project_number> --owner <project_owner> --limit 100 --query 'repo:<owner>/<repo> status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'`, donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json` o aplican `1` y `@me` por defecto).*
2. Elegir ítem prioritario (Top 2-3) y proceder al ciclo E2E.

### 3.4 Investigaciones Exploratorias y Ahorro de Tokens
Para relevamientos técnicos que requieran inspeccionar más de 8 archivos, explorar bases de código externas/desconocidas, o cuando el usuario lo pida:
1. **Delegación:** Evitar acumular lecturas masivas en la sesión principal. Invocar subagente nativo de investigación (ej. `research` con modelo `flash` en Antigravity, o subagente equivalente del runtime).
2. **Consolidación:** El subagente entrega un resumen ejecutivo consolidado al hilo principal, protegiendo el contexto de la sesión. Ver [`references/exploratory-research.md`](references/exploratory-research.md).

### 3.5 Creación y Tipificación de Issues en Backlog
Toda tarea futura, bug o deuda técnica detectada se lista al usuario y, con su confirmación, se registra formalmente en GitHub Issues tipificando obligatoriamente su perfil de ejecución (`profile:<perfil>`) mediante el wrapper canónico `issue-create` (o alias `agent-issue`). En issues concisas (N1, ejecutadas en el mismo turno), se tipifica igualmente el perfil correspondiente sin requerir plan de implementación formal ni ADR:
1. Redactar especificación técnica en `.issue_body` (o `scratch/.issue_body` en runtimes confinados) mediante herramientas nativas de archivos.
2. Crear issue determinista con indexación atómica en Projects v2:
```bash
issue-create --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body --profile <perfil>
```
*(o `--body-file scratch/.issue_body` si se redactó en `scratch/`). El wrapper valida obligatoriamente el perfil (`--profile <perfil>` o `--label "profile:<perfil>"`), resuelve `.repo-config.json` (fallback `1` y `@me`) e indexa automáticamente en Projects v2 sin encadenar llamadas).*
3. Limpiar temporal: `rm -f .issue_body scratch/.issue_body` (en paralelo en el mismo turno en sandbox confinado).

**Inspección Mínima ante Creación Declarativa de Backlog y Prompts Híbridos:** Si el usuario aporta el diagnóstico, comportamiento y solución para registrar issues de forma declarativa (*"registra estos issues"*), queda prohibida la exploración pasiva multi-archivo en el código. Ante prompts híbridos que combinan consultas técnicas o viabilidad (*"¿qué se puede hacer?"*, *"¿es posible X?"*) con la orden de registrar backlog (*"crea los issues correspondientes"*), responder a nivel de diseño conceptual y conocimiento de dominio sin encadenar lecturas pasivas profundas; limitar la inspección estrictamente a 1 o 2 consultas puntuales para confirmar nombres de módulos o archivos clave y proceder de inmediato a redactar las issues e informar respuestas sin agotar el Hard Circuit Breaker (ver [`references/issue-backlog.md`](references/issue-backlog.md) §6.1 y §6.2). **Primacía del Análisis Crítico:** Esta agilidad procesal no suspende el rol de Ingeniero de Sistemas (`core/01-objectivity.md`): si la instrucción declarativa descarta trabajo válido, plantea re-arquitecturas sin sustento o contradice ADRs aceptados, el agente debe ejercer veto técnico y dictamen formal antes de crear tickets o mutar el remoto.

**Atribución de Agente:** El cuerpo de toda issue (local o cruzada) y de todo PR termina con la línea `Creado por: <runtime> (<modelo>)`, y todo commit incluye el trailer `Generated-by: <runtime> (<modelo>)` en `.commit_msg` (o `scratch/.commit_msg`), con los valores que declara la regla del runtime activo (ej. `Generated-by: Claude Code (claude-opus-5-5)` o `Generated-by: Antigravity (Gemini 3.8 Flash)`). Es informativa: sin labels.

**Issues cruzadas (ADR-0045):** Si el hallazgo afecta a otro repositorio del owner, registrarlo allí desde el workspace actual, con confirmación del usuario y sin clonar ni leer archivos del repo destino. El cuerpo debe ser autocontenido (evidencia, origen y criterios de aceptación), porque el agente que lo ejecute no tendrá este contexto:
```bash
issue-create -R <owner>/<repo> --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body --profile <perfil>
```
*(o `--body-file scratch/.issue_body` según corresponda).*
Si el label `profile:<perfil>` no existe en el repo destino, omitirlo y mencionarlo en el cuerpo.

---

## 4. Ciclo de Vida E2E (Resumen Ejecutivo)

```
[1. Ingesta] ──> [2. Higiene] ──> [3. Plan/ADR] ──> [4. Desarrollo] ──> [5. Commit] ──> [6. Push] ──> [7. PR] ──> [8. Cierre & Higiene]
```

Guía paso a paso y máquina de estados: [`references/branch-lifecycle.md`](references/branch-lifecycle.md) y [`references/state-machine.md`](references/state-machine.md).

- [ ] **1. Ingesta:** `gh issue view <id>` (sin llamadas a `gh project item-edit`). Reconciliar obligatoriamente contra ADRs vigentes (`docs/adr/`): si un ADR aceptado posterior deroga o reemplaza entidades o flujos del ticket, prevalece estrictamente el ADR; descartar referencias obsoletas antes de planificar o codificar. Relevamientos exploratorios de > 8 archivos o repositorios externos se delegan al subagente de investigación (ej. `research` en Antigravity).
- [ ] **2. Higiene:** Aislamiento preferente en ≤ 2 llamadas (`git fetch --prune origin` y `git switch --no-track -c <rama> origin/<base>`); poda diferida a Fase 8.
- [ ] **3. Plan/ADR:** Fast-Track por defecto (sin pausa bloqueante en tickets con criterios claros en `Ready for Dev`); *Stop & Plan* con gate bloqueante ante ADRs nuevos/modificados, alternativas divergentes o diagnósticos inciertos; *Fast-path*: orden ejecutiva ("procedé") tras debate en el chat habilita implementar.
- [ ] **4. Desarrollo:** Promover ADR a `status: accepted` al iniciar desarrollo, I/O nativo con lectura paginada estricta (delimitación de rango o paginado ≤ 200 líneas, circuit breaker ≤ 6 lecturas consecutivas globales e inmunidad heurística), ediciones atómicas acotadas y verificar con `./build.sh check`.
- [ ] **5. Commit:** Desglose en llamadas atómicas independientes (prohibido taxativamente encadenar con `&&`, `;` o `|`): Paso 1 staging explícito `git add <rutas>` (ej. `BypassSandbox: true` en Antigravity; no usar `git add .`/`-A`), Paso 2 redactar en `.commit_msg` (o `scratch/.commit_msg` en runtimes confinados) con trailer canónico `Generated-by: <runtime> (<modelo>)` y ejecutar `git commit -F .commit_msg` (o `-F scratch/.commit_msg`, con bypass de sandbox según runtime), y Paso 3 limpiar el temporal `rm -f .commit_msg` (o `scratch/.commit_msg`, ej. `BypassSandbox: false` en Antigravity).
- [ ] **6. Push:** Publicar con `git push -u origin <rama>`.
- [ ] **7. PR:** PR con `Closes #<id>` y línea de atribución (§3.5) vía `.pr_body` (o `scratch/.pr_body`; ADR viaja como `accepted`); salvaguarda de indexación inmediata con `gh project item-add <project_number> --owner <project_owner> --url <pr_url>` (resueltos desde `.repo-config.json` o fallback `1` y `@me`); limpiar el temporal en paralelo con el reporte del turno. Built-in Workflow avanza tarjeta a `👀 In Review / PR`. Ante fallos de CI, inspección determinista de logs con `gh run view <run_id> --log-failed` resolviendo previamente el ID (prohibido invocar `gh run view` interactivo sin ID).
- [ ] **8. Cierre & Higiene (Done):** Fusión remota con `gh pr merge <id> --squash --delete-branch` (Riel 1 Default: orden humana en chat; Riel 2 Opt-in: autónomo si tiene label `automerge` y supera circuit breakers) o web; Built-in Workflows cierran issue y avanzan a `Done` (en Categoría B o base no predeterminada como `dev`, verificar y cerrar explícitamente con `gh issue close <id>`). Higiene atómica post-merge en ≤ 2 llamadas con `git-prune-gone --sync` (fallback determinista: ruta canónica del skill o Git nativo `git checkout <base> && git pull --prune --ff-only` + `git branch -D <rama>` si su PR está `MERGED`; prohibidas búsquedas ciegas `find`/`which`). Ver [`references/branch-lifecycle.md`](references/branch-lifecycle.md).

---

## 5. Feedback Loop de Code Review (`gh-pr-review`)

Guía procedimental: [`references/code-review.md`](references/code-review.md).

1. **Posicionamiento:** `gh pr checkout <pr_id>`.
2. **Ingesta:** `gh-pr-review comments <pr_id>` (unifica veredicto, reviews, comentarios generales e hilos en una sola llamada).
3. **Resolución:**
   - I/O nativo y validación con `./build.sh check`.
   - Commit `fix(<alcance>): atender feedback de code review en PR #<id>` vía `.commit_msg` (o `scratch/.commit_msg`) y `git push`.
4. **Cierre de Hilos:**
   - Resolver: `gh-pr-review resolve <thread_id>` (o `--all <pr_id>` en mutación por lotes).
   - Comentar PR con `.pr_comment` (o `scratch/.pr_comment`) y mantener en `👀 In Review / PR`.

---

## 6. Cierre Autónomo sin PR (Spikes e Investigaciones)

Para tareas sin cambios de código ([`references/branch-lifecycle.md`](references/branch-lifecycle.md)):

1. Informe técnico: `gh issue comment <id> --body-file .issue_comment` (o `--body-file scratch/.issue_comment`).
2. Cerrar: `gh issue close <id>`.
3. La acción nativa de cierre transiciona automáticamente la tarjeta a `Done` en Projects v2 mediante Built-in Workflows (sin `gh project item-edit`).
4. Confirmar en chat; no delegar el cierre al usuario.
