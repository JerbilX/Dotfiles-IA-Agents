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

* **Backlog Canónico:** Prohibido `TODO.md` o `tasks/`; registro en Issues e indexación en Projects v2 (`core/08-task-backlog.md`).
* **Aislamiento y PRs:** Prohibido push directo a `main`. Ramas efímeras (`feat/` o `fix/`) y entrega vía PR (`core/09-issue-driven-development.md`).
* **Higiene y Atomicidad:** I/O solo con herramientas nativas, commits vía `.commit_msg` y eliminación inmediata de temporales (`core/10-environment-standards.md`).
* **Sandbox:** `BypassSandbox: true` reservado a `git`, `gh` y tooling autorizado (`git-prune-gone`, `gh-pr-review`, `agent-audit`) (`runtimes/*/rules/01-sandbox.md`).

---

## 2. Matriz de Ruteo y Referencias Especializadas

Procedimientos detallados y plantillas en `references/`:

| Dominio | Contenido | Referencia Especializada |
| :--- | :--- | :--- |
| **Backlog** | Criterios, Minimal Blast Radius (0-4), 6 estados y Projects v2. | [`references/issue-backlog.md`](references/issue-backlog.md) |
| **Aprovisionamiento** | `git init`, gate de origin y repo privado en GitHub. | [`references/repo-provisioning.md`](references/repo-provisioning.md) |
| **Ramas y PRs** | Cat. A/B, higiene, 8 fases E2E, máquina bidireccional y PRs. | [`references/branch-lifecycle.md`](references/branch-lifecycle.md) |
| **Code Review** | Ingesta `gh-pr-review`, parches y resolución de hilos. | [`references/code-review.md`](references/code-review.md) |
| **Rollback** | Reversión con `git revert` y `build.sh rollback`. | [`references/rollback.md`](references/rollback.md) |

---

## 3. Despacho y Recepción de Tareas

> [!IMPORTANT]
> Consultas de coordinación (*"¿qué hay en el board?"*) son consultivas; prohibido mutar o cambiar de rama sin orden de implementación.

### 3.1 Consultas de Tablero (*"¿qué hay en el board?"*)
Filtrar activos del repo (Top 2-3 con justificación):
```bash
gh project item-list 1 --owner "@me" --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'
```
*(BypassSandbox: true).*

### 3.2 Despacho Vía A: Instrucción Directa (*"implementa la issue #<id>"*)
1. Ingesta: `gh issue view <id>` (`BypassSandbox: true`).
2. Mover a `📐 In Planning`:
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "📐 In Planning"
   ```
3. Proceder al ciclo E2E.

### 3.3 Despacho Vía B: Backlog (*"siguiente tarea lista"*)
1. Consultar listos:
```bash
gh project item-list 1 --owner "@me" --query 'repo:<owner>/<repo> status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'
```
2. Elegir ítem prioritario (Top 2-3), mover a `📐 In Planning` y proceder al ciclo E2E.

---

## 4. Ciclo de Vida E2E (Resumen Ejecutivo)

```
[1. Ingesta] ──> [2. Higiene] ──> [3. Plan/ADR] ──> [4. Desarrollo] ──> [5. Commit] ──> [6. Push] ──> [7. PR & Board] ──> [8. Reconciliación]
```

Guía paso a paso y máquina de estados: [`references/branch-lifecycle.md`](references/branch-lifecycle.md).

- [ ] **1. Ingesta:** `gh issue view <id>` y mover a `📐 In Planning` en Project 1.
- [ ] **2. Higiene:** Sincronizar `main`, podar con `git-prune-gone`, ratificar preventivamente con `./build.sh reconcile` y aislar en `feat/` o `fix/`.
- [ ] **3. Plan/ADR:** `implementation_plan.md` con gate bloqueante; ADR con `status: proposed`.
- [ ] **4. Desarrollo:** Mover a `⚙️ In Progress`, I/O nativo y verificar con `./build.sh check`.
- [ ] **5. Commit:** Redactar en `.commit_msg`, `git commit -F .commit_msg` y borrar temporal.
- [ ] **6. Push:** Publicar con `git push -u origin <rama>`.
- [ ] **7. PR & Tablero:** PR con `Closes #<id>` vía `.pr_body`, mover a `👀 In Review / PR` y reportar.
- [ ] **8. Reconciliación Post-Merge:** Tras merge en `main`, mover a `Done`, sincronizar rama base, ejecutar `git-prune-gone` y ratificar ADRs con `./build.sh reconcile`.

---

## 5. Feedback Loop de Code Review (`gh-pr-review`)

Guía procedimental: [`references/code-review.md`](references/code-review.md).

1. **Posicionamiento:** `gh pr checkout <pr_id>` (`BypassSandbox: true`).
2. **Ingesta:** `gh-pr-review comments <pr_id>` (`BypassSandbox: true`).
3. **Resolución:**
   - I/O nativo y validación con `./build.sh check` (`BypassSandbox: false`).
   - Commit `fix(<alcance>): atender feedback de code review en PR #<id>` vía `.commit_msg` y `git push`.
4. **Cierre de Hilos:**
   - Resolver: `gh-pr-review resolve <thread_id>` (o `--all <pr_id>`) (`BypassSandbox: true`).
   - Comentar PR con `.pr_comment` y mantener en `👀 In Review / PR`.

---

## 6. Cierre Autónomo sin PR (Spikes e Investigaciones)

Para tareas sin cambios de código ([`references/branch-lifecycle.md`](references/branch-lifecycle.md)):

1. Informe técnico: `gh issue comment <id> --body-file .issue_comment` (`BypassSandbox: true`).
2. Cerrar: `gh issue close <id>` (`BypassSandbox: true`).
3. Mover a `Done` en Project 1:
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "Done"
   ```
4. Confirmar en chat; prohibido delegar el cierre al usuario.
