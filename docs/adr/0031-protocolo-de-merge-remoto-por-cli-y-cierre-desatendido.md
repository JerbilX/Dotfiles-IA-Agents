---
status: accepted
date: 2026-10-23
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
---

# 0031 - Protocolo de Merge Remoto por CLI y Cierre Desatendido

## Contexto y Planteamiento del Problema

En el flujo canónico de trabajo gobernado por el skill `issue-driven-workflow` (documentado en `references/branch-lifecycle.md`, Paso 8 y `SKILL.md`), la aprobación y fusión de Pull Requests se describía operativamente como una tarea a realizar de forma manual por el PM / Tech Lead en la interfaz web de GitHub.

Esta prescripción generaba fricción operativa en dos escenarios clave:
1. **Flujo interactivo en chat (Antigravity):** Tras revisar el Pull Request creado por el agente, el usuario debe abrir un navegador web, navegar al repositorio y pulsar el botón de merge manualmente, para luego retornar al chat o terminal a ejecutar la higiene de ramas.
2. **Orquestación desatendida y multi-agente (Agent-Cockpit):** En arquitecturas orquestadas donde un supervisor humano o un loop de orquestación emite órdenes de aprobación ("aprobado, mergeá" o despacho de merge), la dependencia de una acción web externa fragmenta el ciclo de vida y bloquea la automatización del cierre y la higiene.

Dado que GitHub CLI provee soporte nativo para la fusión remota y eliminación de ramas remotas mediante `gh pr merge`, resulta necesario estandarizar el protocolo de merge remoto por CLI, salvaguardando la autoridad humana sobre el merge y encadenando de forma atómica la higiene local del workspace.

## Impulsores de la Decisión (Decision Drivers)

* **Reducción de Fricción Operativa:** Permitir que el ciclo de vida completo de un PR se cierre desde el chat interactivo o terminal sin obligar al usuario a cambiar de contexto al navegador web.
* **Invariante Human-in-the-Loop Estricto:** Preservar la regla basal (`core/09-issue-driven-workflow.md`): aprobación y merge son potestad exclusiva del usuario. Prohibición tajante de fusión autónoma por iniciativa propia del agente.
* **Higiene Atómica y Desatendida:** Garantizar que tras la fusión remota exitosa, el agente retorne a la rama base, sincronice referencias (`git pull --prune --ff-only`) y limpie ramas locales huérfanas (`git-prune-gone`) en una secuencia determinista.
* **Compatibilidad con Worktrees y Orquestadores:** Admitir la ejecución tanto en workspaces monolíticos estándar como en directorios de trabajo efímeros (`git worktree remove .worktrees/issue-<id>`).
* **Minimal Blast Radius (Nivel 2):** Resolver la necesidad a nivel de documentación operativa de skills (`skills/issue-driven-workflow/`), sin requerir modificaciones en directivas basales (`core/`).

## Opciones Consideradas

* **Opción 1:** Mantener exclusivamente la fusión manual en la interfaz web de GitHub.
* **Opción 2:** Permitir que el agente fusione autónomamente el PR una vez que los tests y checks pasen en verde.
* **Opción 3 (Adoptada):** Protocolo dual gobernado por orden ejecutiva en chat vía `gh pr merge <id> --squash --delete-branch` con encadenamiento atómico de higiene post-merge y preservación del fallback web.

## Decisión Adoptada

Se adopta la **Opción 3**, formalizando en el skill `issue-driven-workflow` el protocolo de merge remoto por CLI:

1. **Invariante Human-in-the-Loop:** La invocación de `gh pr merge` está estrictamente condicionada a la recepción de una orden ejecutiva explícita o confirmación del usuario en el chat (*"aprobado, mergeá"*, *"mergealo"*, *"procede con el merge"*). El agente jamás ejecutará `gh pr merge` sin esta instrucción previa.
2. **Comando Canónico:** La fusión remota se ejecuta con GitHub CLI (`BypassSandbox: true`):
   ```bash
   gh pr merge <id> --squash --delete-branch
   ```
   *(incorporando `--auto` en caso de requerir espera de checks obligatorios de CI).*
3. **Encadenamiento Atómico de Higiene Post-Merge:** Confirmado el merge remoto, el agente ejecuta secuencialmente:
   - `git checkout <base_branch>` (`BypassSandbox: true`)
   - `git pull --prune --ff-only` (`BypassSandbox: true`)
   - `git-prune-gone` (`BypassSandbox: true`)
   - Si aplica worktree efímero: `git worktree remove .worktrees/issue-<id>` (`BypassSandbox: true`)
4. **Verificación y Reporte:** El agente valida que la issue vinculada se haya cerrado y que Projects v2 haya avanzado a `Done` automáticamente, reportando el cierre limpio al usuario.
5. **Vía Alternativa Preservada:** El usuario conserva siempre la potestad de fusionar manualmente en la interfaz web de GitHub; ante dicha situación, el agente ejecuta el encadenamiento de higiene en la interacción subsiguiente.

### Consecuencias

* **Positivas:**
  * Cero fricción de cambio de contexto: el usuario puede aprobar y solicitar el merge en una sola orden en el chat interactivo o CLI.
  * Cierre integral y desatendido: ramas locales, remotas y tarjetas del tablero se limpian y actualizan sin pasos manuales adicionales.
  * Compatibilidad directa con herramientas de orquestación y testing multi-agente (Agent-Cockpit).
* **Negativas / Trade-offs:**
  * Requiere que el token de `gh` posea permisos de escritura (`repo` / `write`) sobre el repositorio para ejecutar `gh pr merge` (requisito estándar ya existente para `gh pr create` y `gh issue`).
  * Requiere rigurosidad en el parser comportamental del agente para no confundir comentarios de revisión con órdenes ejecutivas de merge.

### Pros y Contras de las Opciones

#### Opción 1: Exclusivamente Web
* **Pro:** Máxima fricción deliberada como barrera contra errores.
* **Contra:** Rompe la agilidad operativa, obliga al cambio de contexto y desalinea con orquestadores automatizados.

#### Opción 2: Merge Autónomo Desatendido
* **Pro:** Automatización completa sin intervención humana.
* **Contra:** Inaceptable; vulnera el principio Human-in-the-Loop y la regla basal de que aprobación y merge son potestad exclusiva del usuario.

#### Opción 3: Merge Remoto por CLI Condicionado a Orden Ejecutiva
* **Pro:** Equilibrio óptimo entre agilidad operativa, automatización higiénica y soberanía humana sobre el código en producción.
* **Contra:** Ninguna contrapartida técnica significativa.
