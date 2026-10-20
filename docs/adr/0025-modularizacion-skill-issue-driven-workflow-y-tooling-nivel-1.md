---
status: accepted
date: 2026-10-20
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0025 - Modularización del Skill issue-driven-workflow y Tooling Determinista de Nivel 1

## Contexto y Planteamiento del Problema

El skill canónico `issue-driven-workflow` (`skills/issue-driven-workflow/SKILL.md`) gobernaba el ciclo de vida completo de desarrollo, registro de backlog, aprovisionamiento de repositorios, convención de ramas, ciclo de Pull Requests y resolución de Code Review. Con el tiempo y la adición sucesiva de directivas (ADR-0005, ADR-0010, ADR-0021, ADR-0022), el archivo alcanzó **6.234 palabras y ~46 KB**, representando el 51% del volumen total de todos los skills del repositorio combinados.

Auditorías de sesiones reales (`agent-audit` sobre `95026746-260d-4143-8394-c1e1404bcbfb` y `48d75d1b-3a6b-4fab-8901-78d5c1545161`) revelaron patologías críticas provocadas por este volumen:
1. **Dilución de Atención (*Lost in the Middle*):** El modelo pierde visibilidad sobre reglas específicas y comete errores lógicos al atender subtareas puntuales (ej. ingesta y resolución de comentarios de revisión en PRs).
2. **Truncamiento Sistemático de Contexto (`CONTEXT_TRUNCATION`):** Hasta 21 eventos de desborde de buffer en sesiones de 26 minutos debido a comandos largos de GraphQL en bash y respuestas no encapsuladas.
3. **Fragilidad de Nivel 2:** Inyección de consultas GraphQL de 10 líneas con pipes de `jq` y escapes complejos dentro del texto markdown del skill, violando el principio de mínima intervención (forzando Nivel 2 en lugar de Nivel 1 tooling) y quebrando el *prefix matching* de permisos en sandbox.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación del Presupuesto de Contexto y Foco de Atención:** Reducir la sobrecarga en cada turno donde se active el skill, aplicando el patrón de **Divulgación Progresiva (Progressive Disclosure)**.
* **Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius - ADR-0017):** Resolver la complejidad técnica en el nivel de abstracción más bajo posible (Nivel 1 Tooling) en lugar de inyectar scripts inline en Nivel 2 (Skills).
* **Robustez de Sandbox y Prefix Matching:** Garantizar que las interacciones con GitHub CLI (`gh api graphql`) se ejecuten mediante comandos atómicos estandarizados sin tuberías (`|`), redirecciones ni escapes frágiles.
* **Compatibilidad Multi-Runtime y Desacoplamiento:** Permitir la ejecución transparente en Antigravity y Claude Code con la biblioteca estándar de Python 3 (sin dependencias externas).

## Opciones Consideradas

* **Opción 1: Mantener el Skill Monolítico con Poda Superficial.**
  * Reducir palabras editando el texto existente sin alterar la estructura de archivo único.
  * *Descarte:* Insuficiente. El volumen de especificaciones requeridas para el ciclo E2E, ramas, backlog, aprovisionamiento y code review no puede comprimirse a menos de 1.200 palabras sin perder directivas críticas ni comprometer la seguridad.
* **Opción 2: Fragmentar en Múltiples Micro-Skills Independientes.**
  * Separar en `issue-backlog`, `repo-provisioning`, `branch-lifecycle`, `code-review-resolver` y `emergency-rollback`.
  * *Descarte:* Fragmenta artificialmente un único flujo de trabajo cohesivo. Dispersa el catálogo de skills, confunde al orquestador ante consultas de alto nivel y duplica reglas transversales de sandbox y commits.
* **Opción 3: Orquestador Canónico con `references/` y Tooling de Nivel 1 (`gh-pr-review`).**
  * Conservar `skills/issue-driven-workflow/SKILL.md` como orquestador compacto (<= 1.200 palabras) con la matriz de ruteo y reglas de oro.
  * Modularizar los sub-protocolos exhaustivos en archivos de referencia dedicados en `skills/issue-driven-workflow/references/` (`issue-backlog.md`, `repo-provisioning.md`, `branch-lifecycle.md`, `code-review.md`, `rollback.md`).
  * Implementar el CLI determinista `skills/issue-driven-workflow/bin/gh-pr-review` para encapsular la interacción GraphQL con GitHub, devolviendo JSON limpio y estructurado.

## Decisión Adoptada

Se adopta la **Opción 3**, estructurada en los siguientes niveles:

1. **Nivel 1 (Tooling Determinista - `bin/gh-pr-review`):**
   * Creación del ejecutable `skills/issue-driven-workflow/bin/gh-pr-review` en Python 3 estándar (sin dependencias externas).
   * Subcomandos:
     - `comments <pr_id>`: Ingesta unificada de hilos pendientes en el diff, extrayendo `threadId`, `path`, `line`, `rootComment` y `latestFeedback`.
     - `resolve <thread_id>`: Mutación atómica `resolveReviewThread`.
     - `unresolve <thread_id>`: Mutación atómica `unresolveReviewThread`.
     - `reply <thread_id>`: Réplica directa a hilos de revisión.
   * Salida JSON limpia, determinista y compacta, protegiendo el *prefix matching* de permisos en sandbox.
2. **Nivel 2 (Skills Canónicos y Progressive Disclosure):**
   * Reducción de `skills/issue-driven-workflow/SKILL.md` de 6.234 a 1.124 palabras (reducción del 82%), preservando invariantes de oro, flujo ejecutivo y matriz de ruteo.
   * Creación de 5 guías de referencia especializadas en `skills/issue-driven-workflow/references/`:
     - `issue-backlog.md`: Gestión canónica de backlog, minimal blast radius y consultas de Projects v2.
     - `repo-provisioning.md`: Aprovisionamiento de repositorios y gate de origin.
     - `branch-lifecycle.md`: Estrategia de ramas (Cat. A/B), 7 fases E2E, apertura de PRs y tareas sin PR.
     - `code-review.md`: Feedback loop autónomo guiado por `gh-pr-review`.
     - `rollback.md`: Protocolo de emergencia y reversión con `git revert`.
3. **Nivel 3 (Reglas y Configuración de Runtime):**
   * Registro del binario `gh-pr-review` en `binaries` de `runtimes/antigravity/config.json` y `runtimes/claude/config.json`.
   * Autorización expresa de `gh-pr-review` en `runtimes/antigravity/rules/01-sandbox.md` para ejecución desatendida con `BypassSandbox: true`.

### Consecuencias

* **Positivas:**
  * Reducción masiva del contexto basal del skill (-82% de palabras en `SKILL.md`), mitigando el efecto *Lost in the Middle*.
  * Erradicación de eventos `CONTEXT_TRUNCATION` provocados por comandos extensos de terminal y pipes complejos de GraphQL en bash.
  * Preservación estricta del *prefix matching* en Antigravity y zero dependencias de paquetes externos de PyPI.
  * Separación limpia de responsabilidades: los procedimientos exhaustivos se consultan bajo demanda sin saturar la ventana de contexto general.
* **Negativas / Trade-offs:**
  * Los agentes deben consultar los archivos en `references/` cuando requieran especificaciones procedimentales profundas.

### Pros y Contras de las Opciones

#### Opción 1: Mantener Monolito
* **Pro:** Archivo único sin referencias secundarias.
* **Contra:** Inviable por saturación de contexto (6.234 palabras), pérdida de atención y truncamiento recurrente.

#### Opción 2: Fragmentar en Micro-Skills
* **Pro:** Desacoplamiento total en carpetas independientes.
* **Contra:** Fragmentación del ciclo E2E, dispersión del catálogo y sobrecarga cognitiva de ruteo.

#### Opción 3: Progressive Disclosure + Tooling Nivel 1 (Elegida)
* **Pro:** Respeta la jerarquía de niveles de resolución, reduce el contexto en 82%, encapsula GraphQL en tooling robusto y mantiene la cohesión metodológica del flujo.
* **Contra:** Requiere lectura de `references/` para tareas procedimentales específicas.
