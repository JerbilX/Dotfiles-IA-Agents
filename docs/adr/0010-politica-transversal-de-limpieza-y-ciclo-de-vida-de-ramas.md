---
status: proposed
date: 2026-10-15
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0010 - Política Transversal de Limpieza y Ciclo de Vida de Ramas

## Contexto y Planteamiento del Problema
En el flujo de trabajo guiado por issues y Pull Requests (formalizado en ADR-0005 y `core/09-issue-driven-workflow.md`), cada requerimiento técnico o corrección se desarrolla en una rama efímera dedicada (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`).

Tras la revisión, aprobación y fusión (*merge*) del Pull Request correspondiente en GitHub, dichas ramas cumplen su ciclo y quedan obsoletas. Sin un mecanismo de limpieza automática, el ecosistema acumula ramas zombi (*stale branches*) tanto en los repositorios remotos de GitHub como en los clones locales, saturando el autocompletado de la consola, dificultando la visibilidad del estado de los proyectos y generando deuda técnica operativa.

## Impulsores de la Decisión (Decision Drivers)
* **Higiene Operativa Continua:** Erradicar la acumulación de ramas obsoletas sin depender de limpiezas manuales periódicas ("olvidarse del problema").
* **Alcance Transversal Multi-Repositorio:** La política debe aplicar tanto a los proyectos gestionados desde el tablero central (`Proyectos-IA-V3`) como a cualquier nuevo repositorio creado en el futuro.
* **Preservación Estricta del Historial:** Asegurar que ninguna información, discusión o hash de commit se pierda al eliminar ramas efímeras.
* **Seguridad Local (Anti-Data Loss):** Evitar la eliminación accidental de ramas locales con trabajo en desarrollo no integrado.

## Opciones Consideradas
* **Opción 1: Retención temporal con limpiezas manuales periódicas.**
  * *Descarte:* Genera incertidumbre sobre qué ramas están activas o abandonadas, requiere mantenimiento manual repetitivo y no escala en un ecosistema multi-repositorio.
* **Opción 2: Automatización integral en 3 capas (GitHub Remoto + Git Global + Protocolo de Agente).**
  * *Ventaja:* Automatización completa, determinista y segura que aborda el ciclo de vida en servidor remoto, transporte y entorno local.

## Decisión Adoptada
Opción elegida: **"Opción 2"**, estructurando la política en 3 capas complementarias:

1. **Capa 1: GitHub Remoto (Eliminación Inmediata Post-Merge):**
   - Configuración de la directiva nativa `delete_branch_on_merge` en todos los repositorios vinculados al tablero central `Proyectos-IA-V3`.
   - Incorporación obligatoria en `core/02-git-lifecycle.md` para que todo nuevo repositorio aprovisionado por el agente ejecute de forma inmediata `gh repo edit <repo> --delete-branch-on-merge`.
   - Integridad: GitHub preserva permanentemente los Pull Requests cerrados/fusionados, incluyendo metadatos, discusiones, diffs y el SHA de commit head original (con opción nativa "Restore branch" si se requiriera).

2. **Capa 2: Git Global del Anfitrión (Sincronización y Poda de Tracking):**
   - Configuración en el entorno del anfitrión de `git config --global fetch.prune true`.
   - Todo comando de transporte (`git fetch` o `git pull`) invocado sin restricción de refspec poda automáticamente las referencias remotas `remotes/origin/*` que ya no existan en GitHub.

3. **Capa 3: Protocolo del Agente (Higiene Local y Sincronización Determinista):**
   - Incorporación en `skills/issue-driven-workflow/SKILL.md` del protocolo de sincronización libre de restricciones de refspec al inicio de cualquier tarea:
     ```bash
     git checkout main
     git pull --prune --ff-only
     ```
   - **Mecánica de Refspec y Erradicación de `git merge`:** Se prohíbe el uso de `git pull origin main` (cuyo refspec acotado omite la poda remota de ramas efímeras) y de `git merge --ff-only origin/main` (cuya invocación como subcomando independiente dispara alertas interactivas de confirmación de permisos en Antigravity y tensiona la prohibición de merge directo a `main`). La invocación de `git pull --prune --ff-only` resuelve ambos problemas de forma atómica: procesa el refspec estándar completo, poda referencias remotas obsoletas (`remotes/origin/*`) y avanza `main` en fast-forward sin modales de confirmación.
   - **Prohibición de `git remote prune`:** Se prohíbe taxativamente la invocación aislada de `git remote prune origin`, la cual dispara alertas interactivas de confirmación de permisos en Antigravity y rompe la ejecución autónoma.
   - Poda de ramas locales fusionadas:
     ```bash
     git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d
     ```
   - Uso estricto de `-d` (minúscula) como salvaguarda: Git rechaza el borrado si la rama posee commits pendientes que no hayan sido integrados a la rama principal.

### Consecuencias
* **Positivas:**
  * Eliminación inmediata y desatendida de ramas efímeras tras el merge.
  * Ecosistema limpio en GitHub y en el espacio de trabajo local en todos los proyectos vinculados al tablero.
  * Cero riesgo de pérdida de historial gracias a la inmutabilidad de los PRs en GitHub.
  * Cero riesgo de borrado de trabajo pendiente local por la salvaguarda de `git branch -d`.
* **Negativas / Trade-offs:**
  * Si un repositorio es creado manualmente desde la interfaz web de GitHub (fuera del flujo del agente), nace por defecto en `deleteBranchOnMerge: false` (restricción de cuentas personales de GitHub), requiriendo un comando puntual `gh repo edit` para adherirse al estándar.
