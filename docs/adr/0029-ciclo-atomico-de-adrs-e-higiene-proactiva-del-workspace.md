---
status: accepted
date: 2026-10-21
decision-makers: [Usuario, Agente]
supersedes: ["0027-reestructuracion-estados-board-maquina-estados-y-ciclo-vida-adrs.md"]
superseded-by: []
---

# 0029 - Ciclo Atómico de ADRs e Higiene Proactiva del Workspace

## Contexto y Planteamiento del Problema

La implementación previa del ciclo de vida de ADRs y la reconciliación post-merge (introducida en ADR-0027) presentaba dos fricciones sistémicas críticas detectadas en el uso operativo diario a través de `Agent-Cockpit` y `Dotfiles-IA-Agents`:

1. **Paradoja de Reconciliación Post-Merge y Deadlock en `main`:**
   - Para evitar la presunta "auto-aceptación prematura", el ADR se mantenía en `status: proposed` dentro de la rama y viajaba así en el Pull Request.
   - Tras el merge del PR en GitHub, el archivo ingresaba a `origin/main` todavía con `status: proposed`.
   - La ratificación exigía modificar los archivos localmente en `main` mediante `./build.sh reconcile`.
   - Dado que las directivas basales prohíben taxativamente comitear o pushear directamente a `main`, dicha modificación quedaba como cambio sucio sin comitear en el árbol de trabajo local.
   - En proyectos externos del ecosistema como `Agent-Cockpit` (los cuales no poseen `build.sh`), el comando no existe, rompiendo la gobernanza documental y forzando intervenciones manuales o desincronización permanente.
2. **Parálisis de Higiene y Retención en Ramas Muertas:**
   - Al finalizar el desarrollo y abrir el PR (Paso 7), el agente finalizaba su turno posicionado en la rama de trabajo.
   - El usuario revisaba y fusionaba el PR en la interfaz web de GitHub.
   - Al retomar la conversación consultando *"¿con qué seguimos?"*, la regla *"Consultas exploratorias, de tablero o de coordinación no autorizan mutaciones ni preparaciones en Git"* era interpretada rígidamente por el agente, negándose a retornar a `main` y podar la rama cerrada.

## Impulsores de la Decisión (Decision Drivers)

* **Atomicidad de Git (Single-Phase Commit):** Alinear la decisión arquitectónica con el código que la implementa. La aprobación humana del plan y el merge del PR constituyen el acto único y ratificado de aceptación.
* **Inmutabilidad y Limpieza de `main`:** Erradicar modificaciones sucias post-merge en la rama base local y eliminar la dependencia de subcomandos de ratificación (`build.sh reconcile`) inexistentes en proyectos externos.
* **Continuidad Operativa e Higiene Proactiva:** Garantizar que el agente nunca quede congelado en ramas cerradas/fusionadas ante consultas de coordinación o dispatching.
* **Minimal Blast Radius:** Preservar la estructura de 6 estados del tablero central y la máquina de estados bidireccional de ADR-0027, ajustando exclusivamente la semántica de transición de ADRs y el invariante de higiene.

## Opciones Consideradas

* **Opción 1:** Mantener el ciclo de dos fases de ADR-0027 y forzar un bot/webhook o commit automático post-merge en `main` con bypass de protección de ramas.
* **Opción 2:** Alinear el ciclo de vida al estándar de atomicidad de Git: el ADR nace en `status: proposed` en `📐 In Planning`, pasa a `status: accepted` al aprobarse el plan e iniciar desarrollo (`⚙️ In Progress`), viaja en el PR como `accepted` y entra a `main` ya ratificado. Complementariamente, instituir la higiene proactiva del workspace ante cualquier interacción al detectar PRs cerrados/mergeados.

## Decisión Adoptada

Opción elegida: **"Opción 2"**, porque resuelve de raíz el deadlock de Git, garantiza la compatibilidad universal en todos los repositorios del ecosistema (`Agent-Cockpit`, dotfiles, librerías y aplicaciones), asegura que `main` sea siempre un reflejo limpio y fiel de decisiones ratificadas, y erradica la fricción de ramas huérfanas en el diálogo con el usuario.

### 1. Ciclo Atómico de Vida de ADRs
* **En `📐 In Planning`:** El nuevo ADR nace con `status: proposed` mientras se redacta y evalúa el `implementation_plan.md`.
* **En `⚙️ In Progress`:** La aprobación humana del plan (o fast-path ejecutivo) ratifica la decisión técnica. El ADR transiciona a `status: accepted` en la propia rama efímera.
* **En `👀 In Review / PR`:** El PR viaja con el ADR en `status: accepted`.
* **Fusión en `main`:** Al hacer merge del PR, el código, los tests y el ADR aceptado ingresan de forma atómica y ratificada a `main`. No se requieren pasos de reconciliación posteriores ni tooling especializado.
* **Resiliencia ante Descarte:** Si el PR es rechazado o la rama se borra sin merge, la decisión **jamás ingresa a `main`**, garantizando la integridad arquitectónica por la propia naturaleza aislada de Git.

### 2. Invariante de Higiene Proactiva del Workspace
* Las consultas de coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*) no autorizan crear ramas de desarrollo ni modificar código de producción.
* Sin embargo, el retorno a la rama base (`git checkout <base_branch>`), la sincronización (`git pull --prune --ff-only`) y la poda de ramas locales zombi (`git-prune-gone`) es un deber de **higiene obligatorio y proactivo** ante cualquier interacción si se detecta que la rama actual trackea un PR ya fusionado/cerrado o su upstream figura como `[gone]`.

## Consecuencias

### Positivas
* **Cero Dirty State en `main`:** No se vuelve a requerir la edición de archivos en `main` tras el merge; `origin/main` y el árbol local permanecen 100% limpios e idénticos.
* **Universalidad Ecosistémica:** Funciona de forma idéntica en cualquier proyecto (`Dotfiles-IA-Agents`, `Agent-Cockpit`, etc.) sin requerir bash scripts particulares.
* **Eliminación de Fricción Dialógica:** El usuario nunca vuelve a ver al agente varado en una rama vieja tras haber mergeado un PR.
* **Simplificación del Ciclo E2E:** El Paso 8 pasa a ser estrictamente validación de cierre en tablero e higiene de workspace, eliminando la fase de mutación documental.

### Negativas / Trade-offs
* En caso de un cuestionamiento técnico radical durante el Code Review del PR, el ADR debe revertirse a `status: proposed` dentro de la rama si el cambio amerita retornar la tarjeta a `📐 In Planning`.
