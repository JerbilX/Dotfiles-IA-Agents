---
name: issue-driven-workflow
description: >-
  Orchestrate task execution via GitHub Issues, Projects v2, branch lifecycles, and Pull Requests. ACTIVATE whenever creating issues, provisioning repos, implementing issues, querying the board, managing branches, opening PRs, closing audit tasks, or resolving Code Review comments. Operates with strict git hygiene and deterministic CLI tooling.
---

# Issue-Driven Workflow and Pull Request Management

Orquestador canónico para desarrollo guiado por GitHub Issues, Projects v2 y Pull Requests bajo Progressive Disclosure. Procedimientos exhaustivos en `references/`.

---

## 1. Invariantes y Referencias Basales

Subordinado a directivas universales de `core/` y `rules/`:

* **Backlog Canónico:** Prohibido `TODO.md` o `tasks/`; registro en Issues e indexación en Projects v2 (`core/08-task-backlog-management.md`).
* **Aislamiento y PRs:** Prohibido push directo a `main`. Ramas efímeras (`feat/` o `fix/`) y entrega vía PR (`core/09-issue-driven-workflow.md`).
* **Higiene y Atomicidad:** I/O solo con herramientas nativas, commits vía `.commit_msg` y eliminación inmediata de temporales (`core/10-environment-standards.md`).
* **Sandbox:** Subordinado a `runtimes/*/rules/01-sandbox.md`. Comandos de red, git mutadores (`init`, `checkout`, `switch`, `branch`, `add`, `commit`, `merge`, `push`, `pull`, `revert`), `gh` y tooling autorizado (`git-prune-gone`, `gh-pr-review`, `agent-audit`) operan con bypass (`BypassSandbox: true`). Validaciones locales, checks (`./build.sh check`), inspección git pasiva y remoción de archivos temporales (`rm -f`) operan en sandbox confinado (`BypassSandbox: false`).

---

## 2. Matriz de Ruteo y Referencias Especializadas

Procedimientos detallados y plantillas en `references/`:

| Dominio | Contenido | Referencia Especializada |
| :--- | :--- | :--- |
| **Backlog** | Criterios, Minimal Blast Radius (0-4), 6 estados y Projects v2. | [`references/issue-backlog.md`](references/issue-backlog.md) |
| **Aprovisionamiento** | `git init`, gate de origin y repo privado en GitHub. | [`references/repo-provisioning.md`](references/repo-provisioning.md) |
| **Ramas y PRs** | Cat. A/B, higiene, 8 fases E2E, apertura de PRs y cierre post-merge. | [`references/branch-lifecycle.md`](references/branch-lifecycle.md) |
| **Máquina de Estados** | Matriz de transiciones progresivas y regresivas (rework, bloqueos, rollback). | [`references/state-machine.md`](references/state-machine.md) |
| **Code Review** | Ingesta `gh-pr-review`, parches y resolución de hilos. | [`references/code-review.md`](references/code-review.md) |
| **Rollback** | Reversión con `git revert` y `build.sh rollback`. | [`references/rollback.md`](references/rollback.md) |

---

## 3. Despacho y Recepción de Tareas

> [!IMPORTANT]
> Consultas de coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*) no autorizan crear ramas ni modificar código. Sin embargo, la **higiene proactiva** (retornar a la rama base y podar ramas locales zombi si el PR previo fue fusionado o cerrado) es obligatoria ante cualquier interacción.

### 3.1 Consultas de Tablero (*"¿qué hay en el board?"*)
Filtrar activos del repo (Top 2-3 con justificación):
```bash
gh board <owner>/<repo>
```
*(Alias prefix-matchable. Fallback si el alias no está configurado: `gh project item-list <project_number> --owner <project_owner> --limit 100 --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'`, donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json` o aplican `1` y `@me` por defecto).*

### 3.2 Despacho Vía A: Instrucción Directa (*"implementa la issue #<id>"*)
1. Ingesta: `gh issue view <id>`.
2. Proceder al ciclo E2E (aislamiento local en rama efímera; sin mutaciones CLI de Project).

### 3.3 Despacho Vía B: Backlog (*"siguiente tarea lista"*)
1. Consultar listos:
```bash
gh board-ready <owner>/<repo>
```
*(Alias prefix-matchable. Fallback si el alias no está configurado: `gh project item-list <project_number> --owner <project_owner> --limit 100 --query 'repo:<owner>/<repo> status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'`, donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json` o aplican `1` y `@me` por defecto).*
2. Elegir ítem prioritario (Top 2-3) y proceder al ciclo E2E.

---

## 4. Ciclo de Vida E2E (Resumen Ejecutivo)

```
[1. Ingesta] ──> [2. Higiene] ──> [3. Plan/ADR] ──> [4. Desarrollo] ──> [5. Commit] ──> [6. Push] ──> [7. PR] ──> [8. Cierre & Higiene]
```

Guía paso a paso y máquina de estados: [`references/branch-lifecycle.md`](references/branch-lifecycle.md) y [`references/state-machine.md`](references/state-machine.md).

- [ ] **1. Ingesta:** `gh issue view <id>` (sin llamadas a `gh project item-edit`).
- [ ] **2. Higiene:** Aislamiento preferente en ≤ 2 llamadas (`git fetch --prune origin` y `git switch --no-track -c <rama> origin/<base>`); poda diferida a Fase 8.
- [ ] **3. Plan/ADR:** `implementation_plan.md` con gate bloqueante; ADR nace con `status: proposed`.
- [ ] **4. Desarrollo:** Promover ADR a `status: accepted` al iniciar desarrollo, I/O nativo y verificar con `./build.sh check`.
- [ ] **5. Commit:** Staging explícito (`git add <rutas>`; no usar `git add .`/`-A`), redactar en `.commit_msg`, `git commit -F .commit_msg` y limpiar `.commit_msg` en paralelo con la siguiente llamada en el mismo turno.
- [ ] **6. Push:** Publicar con `git push -u origin <rama>`.
- [ ] **7. PR:** PR con `Closes #<id>` vía `.pr_body` (ADR viaja como `accepted`); limpiar `.pr_body` en paralelo con el reporte del turno. Built-in Workflow avanza tarjeta a `👀 In Review / PR`.
- [ ] **8. Cierre & Higiene (Done):** Fusión remota con `gh pr merge <id> --squash --delete-branch` (requiere orden humana en chat) o web; Built-in Workflows cierran issue y avanzan a `Done`. Higiene atómica post-merge en ≤ 2 llamadas con `git-prune-gone --sync`. Ver [`references/branch-lifecycle.md`](references/branch-lifecycle.md).

---

## 5. Feedback Loop de Code Review (`gh-pr-review`)

Guía procedimental: [`references/code-review.md`](references/code-review.md).

1. **Posicionamiento:** `gh pr checkout <pr_id>`.
2. **Ingesta:** `gh-pr-review comments <pr_id>` (unifica veredicto, reviews, comentarios generales e hilos en una sola llamada).
3. **Resolución:**
   - I/O nativo y validación con `./build.sh check`.
   - Commit `fix(<alcance>): atender feedback de code review en PR #<id>` vía `.commit_msg` y `git push`.
4. **Cierre de Hilos:**
   - Resolver: `gh-pr-review resolve <thread_id>` (o `--all <pr_id>` en mutación por lotes).
   - Comentar PR con `.pr_comment` y mantener en `👀 In Review / PR`.

---

## 6. Cierre Autónomo sin PR (Spikes e Investigaciones)

Para tareas sin cambios de código ([`references/branch-lifecycle.md`](references/branch-lifecycle.md)):

1. Informe técnico: `gh issue comment <id> --body-file .issue_comment`.
2. Cerrar: `gh issue close <id>`.
3. La acción nativa de cierre transiciona automáticamente la tarjeta a `Done` en Projects v2 mediante Built-in Workflows (sin `gh project item-edit`).
4. Confirmar en chat; no delegar el cierre al usuario.
