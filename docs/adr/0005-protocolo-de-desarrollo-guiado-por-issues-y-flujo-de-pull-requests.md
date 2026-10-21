---
status: accepted
date: 2026-10-15
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0005 - Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

## Contexto y Planteamiento del Problema
Para consolidar una colaboración eficaz entre el usuario (en rol de Tech Lead / PM) y los agentes de IA, es imperativo formalizar el flujo de trabajo colaborativo Human-in-the-loop y semi-autónomo. Se requería eliminar la integración directa en la rama principal (`main`), contener la tendencia al *scope creep* (desvíos o sobreingeniería no requerida), y sentar las bases de la orquestación mediante GitHub Issues y GitHub Projects v2 como fuente única de verdad.

## Impulsores de la Decisión (Decision Drivers)
* **Gobernanza Human-in-the-Loop:** El PM debe revisar y aprobar formalmente cada cambio funcional en GitHub antes de su fusión.
* **Control Estricto de Alcance (Anti-Scope Creep):** Prohibir la alteración de código fuera del perímetro delimitado por el ticket asignado.
* **Trazabilidad Centralizada:** Vincular automáticamente issues, ramas, commits, Pull Requests y estados de tarjetas en el tablero central (`Proyectos-IA-V3`).
* **Evolución por Fases:** Resolver de forma inmediata la operatividad bajo demanda (Fase 1) sin sobrerresponsabilizar al sistema con arquitecturas prematuras, preparando el camino hacia el despacho autónomo desatendido (Fase 2).

## Opciones Consideradas
* **Opción 1: Desarrollo directo en `main` con commits atómicos.**
  * *Descarte:* Elimina el gate de revisión del PM y genera alto riesgo de regresiones sin trazabilidad.
* **Opción 2: Aislamiento in-place con ramas descriptivas (`git checkout -b`) para Fase 1, evaluando y difiriendo `git worktree` para Fase 2.**
  * *Ventaja:* Entrega inmediata del flujo de PRs y control de scope creep bajo demanda, manteniendo la simplicidad operativa antes de introducir la complejidad de gestión de worktrees para cuando exista concurrencia real.
* **Opción 3: Adopción inmediata de `git worktree` en Fase 1.**
  * *Evaluación:* `git worktree` ofrece un aislamiento superior al no modificar el working tree activo del usuario. Sin embargo, para la Fase 1 bajo demanda en chat interactivo, introduce fricción operativa antes de que el despachador autónomo multi-agente esté en funcionamiento.

## Decisión Adoptada
Opción elegida: **"Opción 2"**, estructurando el flujo en dos fases:
1. **Fase 1 (Despacho Bajo Demanda / Actual):**
   - El agente opera ante comandos directos en chat (*"implementa la issue #X"*, *"toma la siguiente tarea lista en Ready for Dev"*).
   - Crea una rama descriptiva in-place con nomenclatura `feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>` mediante `git checkout -b`.
   - Desarrolla y verifica exclusivamente dentro del alcance del ticket.
   - Si detecta bugs secundarios o mejoras, registra nuevas issues con `gh issue create`, las indexa a Project 1 (`gh project item-add 1`) y continúa enfocado en el ticket asignado.
   - Publica la rama y abre un Pull Request formal con `gh pr create` vinculando el cierre (`Closes #<id>`).
   - El tablero mueve la tarjeta a `👀 In Review / PR` y el PM aprueba y fusiona en GitHub.
2. **Fase 2 (Despachador Autónomo Desatendido / Futura):**
   - Se migrará el aislamiento de tareas hacia `git worktree` (`.worktrees/issue-<id>/`) para habilitar la ejecución concurrente y paralela de agentes en segundo plano sin colisionar con el workspace del usuario.

### Consecuencias
* **Positivas:**
  * Prohibición absoluta de commits o pushes directos a `main`.
  * Todo cambio queda respaldado por un Pull Request formal con diff revisable en GitHub.
  * Trazabilidad automática del cierre de issues y sincronización con el tablero de Projects v2.
  * Blindaje contra el scope creep.
* **Negativas / Trade-offs:**
  * En Fase 1, la rama del working tree local se altera durante el desarrollo de la issue (resuelto en Fase 2 con worktrees).
