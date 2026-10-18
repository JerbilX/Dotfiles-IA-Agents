---
status: accepted
date: 2026-10-17
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0020 - Protocolo Estandarizado de Rollback en Git y Subcomando de Restauración en build.sh

## Contexto y Planteamiento del Problema

Tras la fusión (merge) de un Pull Request en la rama principal (`main`), pueden manifestarse regresiones funcionales no anticipadas, roturas de compilación en herramientas o anomalías en la interacción entre runtimes de agentes de IA y sus dependencias.

Hasta el momento, el repositorio carecía de:
1. **Un protocolo formal de reversión en Git y GitHub:** La prohibición estricta de push directo a `main` y reescritura de historia ([`core/09-issue-driven-workflow.md`](../../core/09-issue-driven-workflow.md) y [`core/02-git-lifecycle.md`](../../core/02-git-lifecycle.md)) impedía con éxito acciones destructivas (`git reset --hard origin/main`), pero no establecía una convención tipificada para nombrar ramas de reversión (`fix/revert-pr-<id>-<slug>`), invocar `git revert -m 1` de forma no interactiva preservando el confinamiento del sandbox, reabrir los tickets afectados (`gh issue reopen`), reubicar tarjetas en GitHub Projects v2 a `🎯 Ready for Dev` ni gestionar el ciclo de vida de los Architectural Decision Records (MADR) que hubiesen sido aceptados prematuramente.
2. **Un mecanismo de recuperación local en el host (`build.sh`):** Si bien los subcomandos `link` y `mcp` generan copias de seguridad automáticas con sufijo `.bak.<timestamp>` en los directorios del anfitrión (`target.config_dir`), no existía un subcomando para revertir de manera determinista al último respaldo funcional (`./build.sh rollback [runtime]`).

## Impulsores de la Decisión (Decision Drivers)

* **Resiliencia Operativa y Rápida Recuperación:** Proveer un mecanismo inmediato para restablecer el estado funcional tanto en Git/GitHub (`main`) como en los entornos locales del sistema anfitrión.
* **Principio de Mínima Intervención (Minimal Blast Radius):** Resolver la necesidad exclusivamente en Nivel 1 (Tooling local en `build.sh`) y Nivel 2 (Skill en `skills/issue-driven-workflow/`), sin modificar directivas basales (`core/`).
* **Preservación del Prefix Matching y Confinamiento de Sandbox:** Asegurar que tanto los comandos de `git revert` como las mutaciones en `gh` operen de forma atómica, sin subshells interactivas ni pipes que anulen la seguridad de Antigravity.
* **Gobernanza Arquitectónica (MADR):** Mantener la inmutabilidad histórica documental: los ADRs asociados a cambios revertidos no se eliminan; se transicionan a `status: deprecated` o se complementan con un ADR compensatorio.

## Opciones Consideradas

* **Opción 1: Reescritura de historia en `main` (`git reset --hard` + push forzado).** (Descartada tajantemente por violar el núcleo basal `core/09`, desestabilizar clones remotos y constituir una mala práctica en entornos colaborativos).
* **Opción 2: Reversión ad-hoc e informal sin protocolo.** Dejar al criterio de cada agente o desarrollador cómo revertir commits y gestionar el backlog. (Descartada por generar inconsistencias en Projects v2, tickets huérfanos y posibles bloqueos de permisos en terminal).
* **Opción 3: Protocolo Desacoplado E2E (Subcomando en `build.sh` + Protocolo en `issue-driven-workflow`).** Implementar la reversión atómica en dos capas desacopladas:
  - Nivel 1: Subcomando `./build.sh rollback [runtime]` para restaurar respaldos `.bak.<timestamp>` más recientes en el anfitrión, integrado en `./build.sh check`.
  - Nivel 2: Procedimiento estandarizado en `skills/issue-driven-workflow/SKILL.md` que gobierna ramas `fix/revert-pr-<id>-<slug>`, invocación atómica de `git revert -m 1 <sha> --no-commit`, apertura de PR con `Reverts #<pr_id>`, reapertura de issues, sincronización en Projects v2 a `🎯 Ready for Dev` y deprecación formal de ADRs.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes componentes:

1. **Subcomando de Restauración en `build.sh` (Nivel 1):**
   - Función `rollback_runtime(runtime)` que inspecciona `target.config_dir`, detecta el archivo `.bak.<timestamp>` más reciente para directivas y servidores MCP, y los restaura atómicamente (`mv -f`).
   - Retorno de código de salida `1` ante la ausencia de archivos de respaldo.
   - Auditoría estática en `check_runtime` dentro de `./build.sh check` que verifica la disponibilidad de respaldos en cada runtime.
2. **Protocolo Formal de Rollback en `issue-driven-workflow` (Nivel 2):**
   - Rama dedicada: `fix/revert-pr-<id>-<slug>`.
   - Ejecución atómica desatendida: `git revert -m 1 <merge_commit_sha> --no-commit` con `BypassSandbox: true`.
   - Mensaje convencional vía `.commit_msg` y commit con `git commit -F .commit_msg`.
   - Pull Request con título `fix(revert): revert PR #<pr_id> - <motivo>` y vinculación `Reverts #<pr_id>`.
   - Reapertura del issue fallido (`gh issue reopen <id>`), adición de comentario técnico explicativo (`gh issue comment`) y reubicación de la tarjeta en Project 1 a `🎯 Ready for Dev`.
   - Transición del ADR asociado (si existiere) a `status: deprecated`.

## Consecuencias

### Positivas
* **Recuperación Determinista:** Ante incidentes en producción o desarrollo, la reversión se ejecuta mediante pasos exactos sin fricción ni ambigüedad.
* **Integridad del Tablero Central:** El backlog y Projects v2 reflejan con precisión qué tareas deben reintentarse (`🎯 Ready for Dev`) y qué PRs están en revisión (`👀 In Review / PR`).
* **Trazabilidad Documental MADR:** Preserva el registro histórico completo de decisiones sin alterar la inmutabilidad de `docs/adr/`.
* **Zero Overhead Basal:** Cumple estrictamente con el principio de mínima intervención, sin alterar el núcleo `core/`.

### Negativas / Trade-offs
* **Sobrecarga de Archivos de Respaldo:** El subcomando `link` genera copias `.bak.<timestamp>` que acumulan espacio con el tiempo si no se purgan periódicamente.
