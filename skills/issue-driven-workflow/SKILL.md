---
name: issue-driven-workflow
description: >-
  Orchestrate end-to-end task execution driven by GitHub Issues and GitHub Projects v2, canonical backlog registration, repository provisioning, branch lifecycles, and Pull Request workflows. ACTIVATE this skill whenever creating future issues, provisioning repos, dispatched to implement an issue (e.g. 'implementa la issue #X'), querying the board, picking tasks from Ready for Dev, managing branch lifecycles, opening PRs, closing audit issues autonomously, or resolving Code Review comments. Operates with strict git hygiene, temporary file safety, and deterministic CLI commands.
---

# Issue-Driven Workflow and Pull Request Management

Orquestador canónico para el desarrollo guiado por tareas (GitHub Issues), aislamiento en ramas, sincronización con GitHub Projects v2, ciclo de Pull Requests y resolución autónoma de Code Review.

Aplica **Divulgación Progresiva (Progressive Disclosure)**: expone aquí los principios invariantes y el flujo ejecutivo, delegando procedimientos exhaustivos a `references/`.

---

## 1. Reglas de Oro e Invariantes del Entorno

1. **Prohibición de Push o Merge Directo a `main`:**
   Todo cambio productivo debe aislarse en rama dedicada (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) y canalizarse exclusivamente vía Pull Request formal. El merge es potestad exclusiva del usuario.
2. **Prohibición de Backlogs Locales:**
   Prohibido crear o depender de `TODO.md`, `backlog.md` o carpetas huérfanas (`prompts/`, `tasks/`). Toda tarea pendiente se formaliza en GitHub Issues e indexa en Projects v2.
3. **Formato Atómico de Commits:**
   Prohibido `git commit -m "..."`. Redactar el mensaje en `.commit_msg` con `write_to_file`, commitear con `git commit -F .commit_msg` (`BypassSandbox: true`) y limpiar con `rm -f .commit_msg` (`BypassSandbox: false`).
4. **Higiene Confinada y Cero Tuberías:**
   Sincronizar con `git pull --prune --ff-only` (`BypassSandbox: true`). Prohibido invocar `git remote prune` o pipes CLI (`awk`, `xargs`, `sed`). Podar ramas huérfanas `[gone]` en dos fases atómicas: inspección pasiva confinada (`git branch --format ...`) y poda directa con `git branch -d`.
5. **Gobernanza de Sandbox:**
   `BypassSandbox: true` se reserva exclusivamente para la suite de `git`, `gh` y el tooling determinista autorizado (`gh-pr-review`, `agent-audit`). Operaciones de lectura e I/O operan 100% confinadas.

---

## 2. Matriz de Ruteo y Referencias Especializadas

Para procedimientos detallados, plantillas y comandos paso a paso, consultar la referencia correspondiente:

| Dominio Operativo | Sub-Protocolo | Guía de Referencia Especializada |
| :--- | :--- | :--- |
| **Backlog y Tareas** | Especificación técnica, criterios, escala Minimal Blast Radius (0-4), elevación basal y consultas del tablero central. | [`references/issue-backlog.md`](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/issue-backlog.md) |
| **Aprovisionamiento** | Inicialización local (`git init`), gate obligatorio de origin, creación privada en GitHub y principio Git-First. | [`references/repo-provisioning.md`](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/repo-provisioning.md) |
| **Ramas, E2E y PRs** | Estrategia híbrida (Cat. A/B), higiene de Git, 7 fases E2E, apertura de PRs, vinculación canónica y cierre sin PR. | [`references/branch-lifecycle.md`](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/branch-lifecycle.md) |
| **Code Review** | Feedback loop autónomo, ingesta con `gh-pr-review`, parches nativos, resolución atómica y respuestas trazables. | [`references/code-review.md`](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/code-review.md) |
| **Rollback y Reversión** | Reversión atómica con `git revert`, reapertura de issues, deprecación de ADRs y restauración con `build.sh rollback`. | [`references/rollback.md`](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/rollback.md) |

---

## 3. Despacho y Recepción de Tareas

> [!IMPORTANT]
> Preguntas de coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*) son estrictamente consultivas. Prohibido mutar o cambiar de rama en Git hasta recibir una directiva explícita de implementación.

### 3.1 Consultas de Tablero (*"¿qué hay en el board?"*)
Filtrar ítems activos del repositorio actual:
```bash
gh project item-list 1 --owner "@me" --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'
```
*(BypassSandbox: true). Emitir el **Top 2 a 3** de tareas recomendadas con justificación técnica.*

### 3.2 Despacho Vía A: Instrucción Directa (*"implementa la issue #<id>"*)
1. Ingesta: `gh issue view <id>` (`BypassSandbox: true`).
2. Transicionar a `⚙️ In Progress`:
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "⚙️ In Progress"
   ```
3. Proceder al ciclo E2E.

### 3.3 Despacho Vía B: Instrucción de Backlog (*"toma la siguiente tarea en Ready for Dev"*)
1. Consultar ítems listos:
   ```bash
   gh project item-list 1 --owner "@me" --query 'repo:<owner>/<repo> status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'
   ```
2. Elegir ticket prioritario (Top 2-3), transicionar a `⚙️ In Progress` y proceder con `gh issue view <id>`.

---

## 4. Ciclo de Vida E2E (7 Fases)

1. **Ingesta:** Inspección de requerimientos y criterios en `gh issue view <id>`.
2. **Aislamiento e Higiene:**
   - Sincronizar: `git checkout main && git pull --prune --ff-only` (`BypassSandbox: true`).
   - Poda pasiva de huérfanas `[gone]`: `git branch --format "%(refname:short) %(upstream:track)"` (`BypassSandbox: false`). Si existen: `git branch -d <rama>` (`BypassSandbox: true`).
   - Crear rama: `git checkout -b feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>` (`BypassSandbox: true`).
3. **Planificación:** Diagnósticos de errores o cambios arquitectónicos requieren `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`). Evaluar Minimal Blast Radius. (*Excepción: fast-path ejecutivo directo tras acuerdo previo en chat*). Si aplica, redactar ADR en `docs/adr/` (`status: proposed`).
4. **Desarrollo y Verificación:** Modificar archivos solo mediante APIs nativas (`replace_file_content`, `write_to_file`). Validar con `./build.sh check` (`BypassSandbox: false`). Transicionar ADRs a `status: accepted` en la rama antes del commit.
5. **Commit Atómico:** Escribir mensaje en `.commit_msg`, commitear con `git commit -F .commit_msg` (`BypassSandbox: true`) y limpiar con `rm -f .commit_msg` (`BypassSandbox: false`).
6. **Push Remoto:** `git push -u origin <nombre-de-rama>` (`BypassSandbox: true`).
7. **Pull Request y Tablero:**
   - Escribir cuerpo en `.pr_body` declarando obligatoriamente `Closes #<id>` (o vinculación múltiple).
   - Publicar: `gh pr create --body-file .pr_body` (`BypassSandbox: true`) y limpiar `.pr_body`.
   - Transicionar ítem en Project 1 a `👀 In Review / PR`:
     ```bash
     gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "👀 In Review / PR"
     ```
   - Reportar resumen, pruebas, enlace al PR y estado del tablero.

---

## 5. Feedback Loop de Code Review (`gh-pr-review`)

Ante la orden de atender observaciones en un Pull Request:

1. **Posicionamiento:** `gh pr checkout <pr_id>` o `git pull --ff-only` (`BypassSandbox: true`).
2. **Ingesta de Hilos:**
   ```bash
   gh-pr-review comments <pr_id>
   ```
   *(BypassSandbox: true. Retorna JSON estructurado con hilos pendientes, archivo, línea y comentarios).*
3. **Resolución Atómica:**
   - Analizar con `view_file` y editar con `replace_file_content` / `write_to_file`.
   - Validar con `./build.sh check` (`BypassSandbox: false`).
   - Commit `fix(<alcance>): atender feedback de code review en PR #<id>` vía `.commit_msg` y `git push`.
4. **Mutación y Cierre:**
   - Resolver hilos subsanados: `gh-pr-review resolve <thread_id>` (múltiples: `gh-pr-review resolve <id1> <id2>` o en lote: `gh-pr-review resolve --all <pr_id>`) (`BypassSandbox: true`).
   - Réplica opcional: `gh-pr-review reply <thread_id> --body "..."`.
   - Publicar comentario consolidado: `gh pr comment <pr_id> --body-file .pr_comment` y mantener tarjeta en `👀 In Review / PR`.

---

## 6. Cierre Autónomo sin PR (Spikes, Auditorías e Investigaciones)

Si una tarea técnica o exploratoria concluye que **no requiere cambios de código**:
1. Publicar informe técnico en ticket: `gh issue comment <id> --body-file .issue_comment` (`BypassSandbox: true`).
2. Cerrar formalmente: `gh issue close <id>` (`BypassSandbox: true`).
3. Transicionar en Project 1 a `Done`:
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "Done"
   ```
4. Prohibido delegar pasivamente el cierre al usuario; reportar confirmación en el chat.
