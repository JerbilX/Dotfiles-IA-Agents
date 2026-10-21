---
status: accepted
date: 2026-10-21
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: ["0029-ciclo-atomico-de-adrs-e-higiene-proactiva-del-workspace.md"]
---

# 0027 - Reestructuración de Estados del Board, Máquina de Estados Bidireccional y Ciclo de Vida de ADRs

## Contexto y Planteamiento del Problema

El flujo de trabajo previo gobernado por `issue-driven-workflow` y los estados del tablero central en GitHub Projects v2 (`Proyectos-IA-V3`) presentaban fricción y desacoples operativos frente a escenarios reales de desarrollo multi-agente y la integración con el orquestador `Agent-Cockpit`:

1. **Ausencia del Estado de Planificación:** El tablero saltaba directamente de `🎯 Ready for Dev` a `⚙️ In Progress`. En la práctica, el primer paso de un agente despachado consiste en exploración, análisis de dependencias y redacción del plan de implementación (`implementation_plan.md`) y/o borrador de ADR. `Agent-Cockpit` no podía distinguir si el agente estaba codificando activamente o detenido esperando la aprobación humana del plan.
2. **Inestabilidad del Ciclo de Vida de ADRs:** Bajo directivas previas, los ADRs transicionaban a `status: accepted` dentro de la rama efímera antes de abrir el Pull Request. Si la tarea sufría un retroceso (revisión insatisfactoria, rediseño o descarte de la rama), el ADR quedaba falsamente aceptado en el historial, distorsionando la verdad arquitectónica. Además, persistían ADRs históricos en `status: proposed` en `main` por falta de reconciliación formal.
3. **Máquina de Estados Unidireccional:** El flujo prescribía únicamente el avance lineal, sin protocolos estandarizados para transiciones regresivas (rework por feedback de review, replanteo arquitectónico, bloqueo técnico en progreso o despriorización en planning).
4. **Ausencia de Reconciliación Post-Merge:** Tras el merge del PR por el gate humano, no existía un paso estandarizado para validar cierre del ticket, mover la tarjeta a `Done`, podar ramas locales y ratificar formalmente los ADRs en `main`.

## Impulsores de la Decisión (Decision Drivers)

* **Visibilidad Operativa:** Diferenciar inequívocamente las fases de análisis/planificación de las de codificación activa tanto en GitHub Projects v2 como en `Agent-Cockpit`.
* **Resiliencia Documental (Anti-Autoaceptación Prematura):** Garantizar que ningún ADR figure como `accepted` en ramas de trabajo o PRs en revisión; la ratificación debe ser consecuencia estricta del merge en `main`.
* **Gobernanza Bidireccional y Acciones de Compensación:** Establecer reglas claras de higiene de Git, reversión de planes y preservación de estados ante cualquier retroceso operativo.
* **Tooling Determinista de Nivel 1:** Proveer un subcomando nativo en `build.sh` (`reconcile`) para ratificar ADRs post-merge sin fricción ni turnos manuales repetitivos.
* **Minimal Blast Radius:** Preservar la compatibilidad con runtimes (`antigravity`, `claude`) y respetar estrictamente los presupuestos modulares y de contexto.

## Opciones Consideradas

* **Opción 1:** Mantener el tablero lineal de 5 estados y la auto-aceptación de ADRs previa al PR.
* **Opción 2:** Reestructurar a 6 estados con `📐 In Planning`, formalizar la máquina de estados bidireccional, mantener ADRs en `status: proposed` durante todo el ciclo de PR y automatizar la ratificación post-merge con `./build.sh reconcile`.

## Decisión Adoptada

Opción elegida: **"Opción 2"**, porque resuelve integralmente la divergencia entre el tablero y el ciclo de vida real del agente, previene la contaminación de decisiones no ratificadas y dota al ecosistema de un protocolo robusto y determinista de reconciliación post-merge.

### Estructura Canónica de Estados en Projects v2
1. `📥 Backlog` (GRAY): Tareas registradas sin priorizar.
2. `🎯 Ready for Dev` (BLUE): Tareas con especificación y listas para ser tomadas.
3. `📐 In Planning` (PINK): Tarea despachada en análisis, exploración técnica y redacción de plan/ADR.
4. `⚙️ In Progress` (YELLOW): Desarrollo activo tras aprobación humana del plan o fast-path.
5. `👀 In Review / PR` (ORANGE): Código finalizado y PR abierto esperando revisión/merge.
6. `Done` (PURPLE): PR fusionado en `main`, ticket cerrado y reconciliación completada.

### Ciclo E2E de 8 Fases
`[1. Ingesta] -> [2. Higiene] -> [3. Plan/ADR (In Planning)] -> [4. Desarrollo (In Progress)] -> [5. Commit] -> [6. Push] -> [7. PR & Tablero (In Review)] -> [8. Reconciliación Post-Merge (Done)]`

### Reingeniería del Ciclo de Vida de ADRs
* Los ADRs nacen y permanecen en `status: proposed` a lo largo de las fases `In Planning`, `In Progress` e `In Review / PR`.
* Ante retrocesos de estado, el ADR se mantiene consistentemente en `status: proposed` (o pasa a `status: rejected` si se descarta formalmente).
* Al fusionarse el PR en `main`, el subcomando `./build.sh reconcile` ratifica formalmente el frontmatter a `status: accepted`.

### Consecuencias

* **Positivas:**
  * Claridad total en `Agent-Cockpit` y GitHub Projects sobre el estado real de la tarea (planificando vs codificando).
  * Inmunidad documental frente a branches descartadas o PRs rechazados: ningún ADR entra a `main` como `accepted` sin merge efectivo.
  * Higiene automatizada post-merge mediante sincronización, poda con `git-prune-gone` y ratificación con `./build.sh reconcile`.
  * **Reconciliación Just-In-Time (JIT):** El Paso 2 de Higiene ejecuta `./build.sh reconcile` preventivamente sobre `main` al despachar cualquier nueva tarea, garantizando que los ADRs fusionados se ratifiquen de forma automática incluso si la sesión previa se cerró sin reconciliación manual.
* **Negativas / Trade-offs:**
  * Incorpora una fase explícita post-merge (Paso 8) para ratificar los ADRs y limpiar referencias tras la fusión en `main`.
