---
status: accepted
date: 2026-10-22
decision-makers: [Usuario, Agente]
supersedes: ["0027-reestructuracion-estados-board-maquina-estados-y-ciclo-vida-adrs.md"]
superseded-by: []
---

# 0030 - Desacoplamiento de la Máquina de Estados de CLI y Alineación al Ciclo Nativo de Git y GitHub

## Contexto y Planteamiento del Problema

El flujo de trabajo guiado por issues (`issue-driven-workflow`, ADR-0027, ADR-0029) prescribía que el agente modificara imperativamente el estado de las tarjetas en GitHub Projects v2 mediante comandos CLI (`gh project item-edit`) en cada micro-fase del ciclo E2E (`📐 In Planning`, `⚙️ In Progress`, `👀 In Review / PR`, `Done`).

Esta aproximación generó severas fricciones operativas en el trabajo diario del ecosistema de agentes:
1. **Desperdicio de Turnos de Inferencia y Alta Latencia:** Cada invocación de `gh project item-edit` desencadenaba entre 15 y 25 consultas GraphQL sucesivas (`ViewerOwner`, `ViewerProjectWithFields`, `GetProjectItemByURL`, etc.), agregando entre 5 y 10 segundos de latencia innecesaria por micro-transición.
2. **Fragilidad por Permisos de Token (`project` scope):** Los comandos de mutación sobre Projects v2 exigen privilegios administrativos de proyecto en el token de GitHub. Cuando un agente o subagente opera con tokens de alcance acotado al repositorio, las operaciones de desarrollo se bloqueaban injustificadamente.
3. **Acoplamiento Rígido y Fricción con Orquestadores Externos (`Agent-Cockpit`):** La manipulación forzada de estados por parte del agente colisionaba con la delegación de tareas y el monitoreo reactivo desde orquestadores externos como `Agent-Cockpit`.
4. **Redundancia Frente a Primitivos Nativos de Git y GitHub:** El estado real del ciclo de vida se deduce de forma natural y unívoca de los primitivos de Git y GitHub:
   - Issue abierta sin rama/PR: Backlog / Listo para desarrollo (`📥 Backlog` / `🎯 Ready for Dev`).
   - Rama activa de trabajo (`feat/` o `fix/`): Fase de planificación o desarrollo local (`📐 In Planning` / `⚙️ In Progress`).
   - Pull Request abierto (`gh pr create`): Revisión técnica activa (`👀 In Review / PR`).
   - Issue cerrada y PR fusionado (`Closes #<id>`): Tarea concluida (`Done`).

## Impulsores de la Decisión (Decision Drivers)

* **Eliminación de Latencia y Desperdicio de Turnos:** Suprimir llamadas burocráticas lentas a la API de Projects v2 durante la ejecución del agente.
* **Inmunidad y Aislamiento de Permisos:** Permitir que los agentes de desarrollo operen exclusivamente con permisos estándar sobre el repositorio de código, sin requerir acceso de escritura a Projects v2.
* **Alineación al Ciclo Nativo de Git/GitHub:** Emplear eventos de Git y Pull Requests como la fuente de verdad única del progreso de una tarea.
* **Compatibilidad Dual:** Garantizar un comportamiento idéntico y sin fricción tanto en sesiones interactivas locales asistidas por agente como en orquestaciones multi-agente delegadas desde `Agent-Cockpit`.
* **Automatización Desatendida del Tablero:** Aprovechar los *Built-in Workflows* de GitHub Projects v2 para que las tarjetas avancen automáticamente ante eventos nativos de GitHub (apertura de PR, vinculación y cierre por merge).

## Opciones Consideradas

* **Opción 1:** Mantener las mutaciones imperativas de `gh project item-edit` en cada micro-fase del ciclo E2E del agente.
* **Opción 2:** Desacoplar la máquina de estados de las mutaciones de CLI del agente, deduciendo el estado a partir de los primitivos nativos de Git/GitHub y delegando la actualización del tablero a los *Built-in Workflows* nativos de GitHub Projects v2.

## Decisión Adoptada

Opción elegida: **"Opción 2"**, porque erradica de raíz la latencia innecesaria y la fragilidad de tokens, simplifica radicalmente las directivas operativas del agente (`skills/issue-driven-workflow`), y preserva una perfecta sincronización del tablero mediante automatizaciones nativas de GitHub sin intervención manual del agente.

### 1. Eliminación de `gh project item-edit` en el Ciclo del Agente
* Queda terminantemente prohibido que el agente ejecute llamadas imperativas a `gh project item-edit` durante el ciclo E2E de desarrollo (`In Planning`, `In Progress`, `In Review / PR`, `Done`).
* Las consultas al tablero (`gh project item-list`) se preservan exclusivamente para responder consultas pasivas del usuario sobre el backlog o coordinación (*"¿qué hay en el board?"*).

### 2. Mapeo al Ciclo Nativo de Git y GitHub
* **`📥 Backlog` / `🎯 Ready for Dev`:** Determinado por el estado abierto del GitHub Issue sin rama asignada ni PR en curso.
* **`📐 In Planning` & `⚙️ In Progress`:** Fases locales de análisis, redacción de `implementation_plan.md`, borrador de ADR y codificación en rama efímera (`feat/issue-<id>-<slug>`). No requieren mutaciones en la nube.
* **`👀 In Review / PR`:** Se activa de forma automática cuando el agente publica el PR con `gh pr create --body-file .pr_body`.
* **`Done`:** Al fusionar el PR en `main`, la vinculación `Closes #<id>` cierra automáticamente el issue en GitHub, y el *Built-in Workflow* de Projects v2 transiciona automáticamente la tarjeta a `Done`. En investigaciones/spikes sin cambios de código, la ejecución de `gh issue close <id>` dispara idénticamente la automatización nativa a `Done`.

### 3. Configuración Canónica de Built-in Workflows en Projects v2
El tablero central se apoya en los 4 flujos nativos estándar de GitHub Projects v2 (Settings -> Workflows):
1. **Auto-add to project:** Incorpora issues y PRs del repositorio al crearse.
2. **Item closed:** Cuando un issue o PR se cierra, asigna `Status: Done`.
3. **Pull request merged:** Cuando un PR se fusiona en la rama base, asigna `Status: Done`.
4. **Code review requested / PR created:** Asigna `Status: 👀 In Review / PR` al abrirse un PR.

## Consecuencias

### Positivas
* **Reducción Drástica de Latencia:** Se eliminan hasta 4 bloqueos por GraphQL en cada tarea, ahorrando decenas de segundos y turnos de inferencia por ticket.
* **Robustez de Seguridad y Tokens:** Los agentes no requieren scope `project:write` para completar el ciclo E2E de desarrollo.
* **Interoperabilidad Total con `Agent-Cockpit`:** El orquestador puede consultar el estado de issues y branches vía API estándar de GitHub sin interferencias ni descalces de estado provocados por el agente.
* **Higiene Simplificada:** El Paso 8 se enfoca exclusivamente en verificar el merge/cierre, retornar a la rama base, sincronizar (`git pull --prune --ff-only`) y podar ramas huérfanas (`git-prune-gone`).

### Negativas / Trade-offs
* En tableros donde los *Built-in Workflows* no estén habilitados en la configuración de Projects v2, la tarjeta del issue en el tablero no avanzará de columna automáticamente hasta que el usuario o el administrador active los flujos nativos en GitHub; no obstante, el estado real de la tarea (Issue y PR) en GitHub y Git es siempre 100% veraz e inalterado.
