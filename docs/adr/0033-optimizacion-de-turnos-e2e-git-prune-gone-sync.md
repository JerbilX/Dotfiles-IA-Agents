---
status: accepted
date: 2026-10-24
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0033 - Optimización de Turnos del Ciclo E2E con git-prune-gone --sync y Fases Compactas

## Contexto y Planteamiento del Problema

En entornos de ejecución con privilegios confinados (sandbox de Antigravity), las operaciones sobre `.git/` y los llamados remotos de red (`gh`, `git push`, `git pull`, `git fetch`) requieren `BypassSandbox: true`. Cada invocación con bypass consume un turno completo de interacción y, cuando no está pre-aprobada por prefix matching, genera un prompt modal de autorización que degrada la experiencia de usuario y eleva la latencia acumulada.

El flujo de trabajo canónico gobernado por `issue-driven-workflow` (ADR-0005, ADR-0026, ADR-0031, ADR-0032) requería aproximadamente 14 llamadas bypass en el camino feliz:
1. **Fase 2 (Higiene y Aislamiento, 4 llamadas):** `git checkout <base>` → `git pull --prune --ff-only` → `git-prune-gone` → `git checkout -b <rama>`.
2. **Fase 8 (Post-merge, 4–5 llamadas):** `gh pr merge` → `git checkout <base>` → `git pull --prune --ff-only` → `git-prune-gone` → `gh issue view <id>`. En Categoría A, `gh pr merge --delete-branch` ya elimina la rama remota y local y posiciona el workspace en `main`, tornando redundante el checkout posterior. La comprobación `gh issue view` es igualmente innecesaria cuando el PR incluye palabras clave canónicas de cierre (`Closes #<id>`) y el merge reportó éxito.
3. **Limpieza de temporales:** Invocaciones aisladas para `rm -f .commit_msg` y `rm -f .pr_body` consumían turnos dedicados en lugar de despacharse en paralelo con llamadas independientes del mismo turno.

## Impulsores de la Decisión (Decision Drivers)

* **Minimal Blast Radius (ADR-0017):** Resolver la sobrecarga en Nivel 1 (tooling determinista `git-prune-gone`) y Nivel 2 (documentación de skill `issue-driven-workflow`), sin modificar directivas basales (`core/`).
* **Minimización de Latencia y Reducción de Turnos (ADR-0012):** Reducir el número de llamadas con bypass de ~14 a 6–7 llamadas en el camino feliz sin sacrificar la seguridad de los datos.
* **Integridad y Detección Precisa de Squash Merges (ADR-0032):** Asegurar que la clasificación de squash merges en `git-prune-gone` evalúe las ramas candidatas contra la base ya sincronizada con el remoto, eliminando falsos negativos de ramas no integradas.
* **Tolerancia a Fallos y Errores Estructurados:** Abortar de forma atómica y limpia ante árboles de trabajo con cambios pendientes o divergencias de fast-forward, exponiendo diagnósticos consistentes tanto en texto plano como en `--json`.

## Opciones Consideradas

* **Opción 1: Encadenar comandos en una sola línea de shell (`git checkout <base> && git pull && git-prune-gone`).**
  * *Descarte:* Inviable en el entorno confinado. Los operadores de control de shell (`&&`, `||`, `;`) anulan el prefix matching del sandbox en Antigravity, forzando modales interactivos repetitivos para cada comando compuesto.
* **Opción 2: Mantener `git-prune-gone` enfocado solo en poda y crear un script bash auxiliar para la sincronización.**
  * *Descarte:* Introduce un nuevo binario, mayor dispersión y no resuelve la integración directa entre la sincronización de la base y la posterior verificación de árboles squash en Python.
* **Opción 3: Extender `git-prune-gone` con el flag `--sync` (Nivel 1) y compactar las Fases 2 y 8 del skill (Nivel 2).**
  * *Selección:* Óptima. `--sync` encapsula de forma atómica la validación del árbol, la conmutación a la base, el fast-forward con poda remota y la clasificación de ramas locales integradas contra el estado remoto fresco. Paralelamente, la Fase 2 adopta `git fetch --prune origin` + `git switch --no-track -c <rama> origin/<base>` (2 llamadas), y la Fase 8 se reduce a `gh pr merge` + `git-prune-gone --sync` (2 llamadas).

## Decisión Adoptada

Se adopta la **Opción 3**:

1. **Flag `--sync` en `git-prune-gone` (Nivel 1):**
   * Realiza pre-flight checks: valida repositorio Git e inspecciona que el working tree no contenga cambios pendientes (`git status --porcelain`). Si existen cambios pendientes, aborta con código 1 y error estructurado (`status: dirty_worktree`).
   * Posicionamiento en base: si la rama actual difiere de la base resuelta (`--base` / `.repo-config.json` / `main`), conmuta a ella (`git checkout <base>`).
   * Sincronización fast-forward: ejecuta `git pull --prune --ff-only` contra el upstream de la rama base. Si el fast-forward falla, aborta con código 1 y diagnóstico estructurado (`status: pull_failed`).
   * Poda atómica: ejecuta la clasificación y poda de ramas `[gone]` (con soporte para squash merges y merges tradicionales) contra la base recién actualizada.
   * Telemetría estructurada: incluye metadatos de sincronización en la salida `--json`.

2. **Compactación de Fase 2 en 2 Llamadas (Nivel 2):**
   * Camino preferente: `git fetch --prune origin` seguido de `git switch --no-track -c <rama> origin/<base>`.
   * Poda diferida a Fase 8, reduciendo el arranque de tarea a 2 llamadas bypass sin alterar la rama base local ni requerir checkout intermedio.

3. **Compactación de Fase 8 en 2 Llamadas (Nivel 2):**
   * Paso 1: `gh pr merge <id> --squash --delete-branch`.
   * Paso 2: `git-prune-gone --sync` (cubre automáticamente la conmutación a `dev` en repositorios de Categoría B y la sincronización de `main` en Categoría A).
   * Verificación condicional de cierre (`gh issue view <id>`): reservada como fallback únicamente si el PR omitió la directiva `Closes #<id>` o el merge remitió error.

4. **Despacho Concurrente de Temporales (C7 - Nivel 2):**
   * Documentar que `rm -f <temporal>` (confinado en sandbox) se despache en paralelo dentro del mismo turno junto a la llamada subsiguiente independiente (`git push` o reporte final), eliminando turnos ociosos.

### Consecuencias

* **Positivas:**
  * Reducción de ~14 a 6–7 llamadas bypass en el ciclo E2E completo.
  * Detección infalible de squash merges al clasificar siempre contra la base sincronizada.
  * Preservación estricta de las reglas universales de `core/` y respeto de Minimal Blast Radius.
  * Cobertura mediante pruebas automatizadas unitarias en `tests/test_git_prune_gone.py` integradas en `./build.sh check`.
* **Negativas / Trade-offs:**
  * `--sync` requiere conexión remota y upstream tracking configurado en la rama base para completar la fase de pull. Si no hay conexión o no hay upstream remoto, reporta el error correspondiente.
