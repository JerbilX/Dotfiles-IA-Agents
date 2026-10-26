---
status: accepted
date: 2026-10-25
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
---

# 0037 - Flujo Híbrido Fast-Track y Auto-Merge Condicional

## Contexto y Planteamiento del Problema

El flujo de trabajo canónico gobernado por las directivas basales (`core/07-anti-hallucination.md`, `core/09-issue-driven-workflow.md`), el skill `issue-driven-workflow` y formalizado en ADR-0005 y ADR-0031 establecía tres puntos de control humano secuenciales (*gates*) para cada issue:
1. **Gate 1 (Planificación):** Aprobación bloqueante obligatoria de `implementation_plan.md` en Fase 3 (`📐 In Planning`) para todo diagnóstico de errores o cambio de código.
2. **Gate 2 (Revisión):** Verificación humana del Pull Request tras su apertura en Fase 7 (`👀 In Review / PR`).
3. **Gate 3 (Fusión):** Emisión de una orden ejecutiva explícita de confirmación en el chat (*"aprobado, mergeá"*) para autorizar la invocación de `gh pr merge` en Fase 8 (`Done`).

Esta multiplicidad de compuertas provocaba fatiga operativa y fricción innecesaria ante tareas rutinarias, mejoras acotadas o issues maduros con criterios de aceptación unívocos previamente priorizados en `🎯 Ready for Dev`.

No obstante, una automatización ciega de punta a punta (0 gates sin salvaguardas) que delegue en el propio LLM la decisión subjetiva de evaluar cuándo un cambio es "crítico" o "ambiguo" introduce una vulnerabilidad estructural: los modelos de lenguaje tienden a la sobreconfianza (*hallucinated certainty*), asumiendo certezas en escenarios de ambigüedad de dominio y pudiendo fusionar código erróneo o regresivo directamente sobre `main`.

Resulta necesario diseñar un protocolo híbrido escalonado (*Tiered Execution Flow*) que colapse la fricción en un único gate final para el flujo estándar y habilite una vía completamente autónoma (0 gates) gobernada exclusivamente por metadatos deterministas y barreras de contención objetivas (*circuit breakers*).

## Impulsores de la Decisión (Decision Drivers)

* **Reducción Drástica de Fricción Operativa:** Disminuir las interrupciones del operador humano entre un 66% y un 100% según la naturaleza de la tarea.
* **Gobernanza Objetiva vs. Subjetividad del Modelo:** Blindar la toma de decisiones evitando que el LLM decida autónomamente qué es "crítico"; las condiciones de auto-merge y los frenos deben ser deterministas y verificables mediante código y metadatos.
* **Preservación de la Rama Troncal (`main`):** Salvaguardar la estabilidad de `main` asegurando que cambios de alto impacto arquitectónico o basales mantengan siempre revisión humana.
* **Degradación Elegante (Anti-Rigidez):** Permitir que el flujo desatendido descienda automáticamente a un flujo con revisión humana ante la menor anomalía técnica o de alcance.

## Opciones Consideradas

* **Opción 1: Mantener el flujo canónico de 3 gates intacto.**
  * *Descarte:* Perpetúa la fatiga de interacción y ralentiza el ciclo de desarrollo en tareas rutinarias bien especificadas.
* **Opción 2: Auto-merge desatendido universal con frenos basados en el juicio del agente.**
  * *Descarte:* Alto riesgo de regresión silenciosa en `main` debido a la incapacidad intrínseca de los LLMs para reconocer sus propias brechas de conocimiento (*unknown unknowns*). Convierte al PR en un mero trámite y equivale a push directo a `main`.
* **Opción 3 (Adoptada): Flujo Híbrido Escalonado (Riel 1 Fast-Track por Defecto + Riel 2 Auto-Merge Condicional Opt-in con Circuit Breakers).**
  * *Evaluación:* Provee el equilibrio óptimo entre agilidad operativa y seguridad formal de ingeniería.

## Decisión Adoptada

Se adopta la **Opción 3**, estructurando el ciclo de desarrollo guiado por issues en dos rieles operativos:

### 1. Riel 1: Fast-Track (Comportamiento por Defecto - 1 Solo Gate)
* **Supresión del Plan Bloqueante Redundante:** Para issues en `🎯 Ready for Dev` que cuenten con especificación técnica suficiente y criterios de aceptación claros, el agente no emite `implementation_plan.md` bloqueante. Pasa directamente de la ingesta y aislamiento de rama al desarrollo activo (`⚙️ In Progress`), pruebas locales y apertura de PR.
* **Excepción de Freno en Planificación (*Stop & Plan*):** El plan bloqueante (`RequestFeedback: true`) se reserva obligatoriamente para:
  - Tareas con ambigüedad de diseño o múltiples alternativas divergentes.
  - Modificaciones estructurales que introduzcan o modifiquen un ADR (`docs/adr/`).
  - Diagnósticos con causa raíz no confirmada.
* **Gate Único Consolidado en el PR:** El agente desarrolla, valida con `./build.sh check`, comitea, pushea y abre el Pull Request formal con `Closes #<id>`. La ejecución concluye reportando el PR al usuario. El usuario revisa el diff consolidado y autoriza la fusión mediante orden ejecutiva en chat o interfaz web.

### 2. Riel 2: Auto-Merge Condicional (Opt-in - 0 Gates)
* **Activación Determinista:** Se activa únicamente si el issue incluye la etiqueta de GitHub `automerge` o si la instrucción de despacho en el chat lo ordena explícitamente (*"implementa y automergea el issue #<id>"*).
* **Ciclo E2E Autónomo:** El agente ejecuta secuencialmente:
  1. Ingesta y aislamiento en rama efímera.
  2. Desarrollo y ejecución de pruebas locales (`./build.sh check`).
  3. Commits atómicos con `.commit_msg` y publicación remota.
  4. Creación de PR formal con vinculación `Closes #<id>` vía `.pr_body`.
  5. Fusión remota inmediata mediante `gh pr merge <id> --squash --delete-branch`.
  6. Encadenamiento atómico de higiene post-merge con `git-prune-gone --sync`.
  7. Reporte final de cierre exitoso al usuario.

### 3. Circuit Breakers y Degeneración Elegante (Downgrade a Riel 1)
La ejecución en Riel 2 queda revocada de inmediato, degradando automáticamente al Gate de Revisión de Riel 1 (sin invocar `gh pr merge`), si se produce cualquiera de las siguientes condiciones:
1. **Infracción de Minimal Blast Radius:** El PR modifica directivas basales (`core/`), reglas de runtime (`runtimes/`) o introduce/altera decisiones arquitectónicas (`docs/adr/`) (Niveles 3 y 4).
2. **Fallo en Verificación:** `./build.sh check`, linters o suites de pruebas automatizadas fallan o emiten advertencias bloqueantes.
3. **Incertidumbre o Ambigüedad:** Si durante la codificación surge una discrepancia o caso de borde no contemplado en el ticket, rige *Stop & Ask* inmediato.

## Consecuencias

### Positivas
* **Agilidad Operativa:** El flujo estándar se reduce a una única intervención humana por tarea (revisión y merge del PR listo).
* **Desatención Segura:** Las tareas mecánicas, de tooling, documentación o mantenimiento etiquetadas como `automerge` se resuelven de forma 100% autónoma.
* **Integridad de `main`:** Ningún cambio de nivel arquitectónico o basal puede fusionarse sin aprobación explícita gracias a los circuit breakers deterministas.

### Negativas / Trade-offs
* Requiere disciplina en el etiquetado de issues (`automerge`) para habilitar el Riel 2 de forma consciente.
* Requiere que el skill `issue-driven-workflow` documente rigurosamente las transiciones de degradación elegante hacia Riel 1.
