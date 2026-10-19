---
status: proposed
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0023 - Blindaje de Herramientas Nativas y Principio Git-First en Confinamiento de Workspace

## Contexto y Planteamiento del Problema

Durante el ciclo de desarrollo en la conversación `ace3c35b-60d4-4be2-a089-92512bf2aafe` sobre el repositorio `JerbilX/Agent-Cockpit` (Issue #1), el agente recibió la directiva ejecutiva `"avanza"` para iniciar el diseño de un entorno web local de orquestación multi-repo. Ante el requerimiento de diseñar un selector de repositorios de la organización, el agente intentó de forma no solicitada inspeccionar el directorio superior del host invocando la herramienta nativa:

```json
{
  "name": "list_dir",
  "args": {
    "DirectoryPath": "/home/jerbilx/Proyectos-IA-V3"
  }
}
```

Dado que el workspace activo estaba estrictamente delimitado a `/home/jerbilx/Proyectos-IA-V3/Agent-Cockpit`, el arnés del runtime Antigravity interceptó la operación como un acceso fuera de los límites de workspace, disparando un diálogo modal interactivo de confirmación de permisos en el IDE que interrumpió la ejecución autónoma por casi dos minutos hasta ser rechazado por el usuario.

El análisis inicial propuso agregar prohibiciones extensas e hiper-específicas en la capa basal (`core/`) y en las reglas de runtime (`antigravity/`). Durante la revisión de código (PR #76), se observó acertadamente que:
1. Agregar prohibiciones muy específicas en `core/` (mencionando listados de repos o fases de diseño) infla el contexto basal con bajo valor, violando el principio de poda sustractiva (ADR-0016).
2. Duplicar la frontera de workspace en las reglas de runtime de Antigravity es redundante.
3. El fallo conductual del agente radicaba en una carencia procedimental: ante una necesidad de contexto sobre repositorios, recurrió a inspeccionar carpetas en disco en vez de consultar los canales naturales de Git y GitHub. Es en el skill (`issue-driven-workflow`) donde debe definirse cómo debe operar el agente.

## Impulsores de la Decisión (Decision Drivers)

* **Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius - ADR-0017):** Resolver el comportamiento operativo en la capa de skills (Nivel 2) en lugar de sobrecargar la capa basal (Nivel 4).
* **Economía de Contexto y Poda Sustractiva (ADR-0016):** Mantener el Core basal limpio, universal y sintético, sin directivas de nicho.
* **Aislamiento Estricto de Workspace:** Evitar que herramientas nativas o comandos de terminal intenten acceder a rutas externas o directorios padre (`..`).
* **Principio Git/GitHub-First:** Forzar que toda interacción, contexto o descubrimiento de repositorios se canalice exclusivamente a través de Git y GitHub CLI (`gh repo list`).

## Opciones Consideradas

* **Opción 1: Prohibiciones Extensas Basales en Core y Runtime.**
  * Añadir cláusulas detalladas en `core/10-environment-standards.md` y una sección completa en `runtimes/antigravity/rules/01-sandbox.md`.
  * *Descarte:* Agrega sobrecarga de contexto innecesaria en cada turno para todos los repositorios y duplica invariantes que ya están cubiertos de forma conceptual.
* **Opción 2: Resolución Procedimental Guiada en Skill con Blindaje Basal Conciso.**
  * **Nivel 4 (Core Basal):** Ajustar la directiva de Límites de Workspace en una única línea universal que aclare que tanto herramientas nativas como terminal tienen prohibido acceder a rutas externas o directorios superiores (`..`).
  * **Nivel 3 (Runtime Antigravity):** Sin modificaciones redundantes; el arnés ya opera bajo la regla basal.
  * **Nivel 2 (Skill - `issue-driven-workflow`):** Incorporar la sección `2.4 Principio Git/GitHub-First para Interacción y Contexto de Repositorios`, estableciendo que el inventario, validación o descubrimiento de proyectos de la organización se realiza forzosamente mediante Git y GitHub CLI (`gh repo list`), prohibiendo el escaneo físico en disco.

## Decisión Adoptada

Opción elegida: **"Opción 2"**, articulada bajo la siguiente jerarquía:

1. **Ajuste Mínimo en Core Basal (`core/10-environment-standards.md`):**
   * Se unifica la directiva de aislamiento:
     > *"Límites de Workspace y Aislamiento: Toda operación de lectura o escritura (sea vía herramientas nativas o terminal) se restringe estrictamente al workspace activo. Prohibido acceder o inspeccionar rutas externas o directorios superiores (`..`)."*
2. **Definición Procedimental en Skill (`skills/issue-driven-workflow/SKILL.md`):**
   * Se establece la sección `2.4 Principio Git/GitHub-First para Interacción y Contexto de Repositorios`:
     - **Canal Exclusivo:** Toda consulta de repositorios se ejecuta mediante `gh repo list --limit 30 --json name,description,isPrivate` (`BypassSandbox: true`).
     - **Prohibición de Reconocimiento Físico:** Prohibido usar herramientas de archivos o comandos para sondear carpetas hermanas o `..`.
     - **Desacoplamiento en Diseño:** Proyectos con integración multi-repo deben diseñarse desacoplados mediante variables de entorno (ej. `WORKSPACE_ROOT`) sin requerir inspección del host.

### Consecuencias

* **Positivas:**
  * Se preserva el presupuesto de contexto basal manteniendo Core conciso e incontestable.
  * Se elimina el vector de escape en herramientas nativas al cerrar la ambigüedad sobre directorios superiores (`..`).
  * El agente adquiere una directiva procedimental inequívoca: cuando necesite contexto sobre repositorios, acude directamente a Git/GitHub.
* **Negativas / Trade-offs:**
  * Ninguna identificada; la jerarquía respeta estrictamente los principios de Minimal Blast Radius y economía de contexto.
