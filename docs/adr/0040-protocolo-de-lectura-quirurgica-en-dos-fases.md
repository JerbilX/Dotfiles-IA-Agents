---
status: accepted
date: 2026-10-29
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0040 - Protocolo Obligatorio de Lectura Quirúrgica en Dos Fases para Mitigación de Saturación de Contexto

## Contexto y Planteamiento del Problema

Las llamadas no delimitadas a la herramienta nativa de lectura `view_file` sobre archivos de mediana o gran extensión devuelven hasta 800 líneas completas por invocación. Este volcado íntegro ingresa inmediatamente al historial de la conversación del agente y se reenvía en cada turno subsiguiente de la sesión, provocando una penalización cuadrática en el consumo de tokens, acelerando el *context rot* y desplazando información operativa crítica.

En la gran mayoría de las tareas de inspección de código, diagnóstico de bugs y refactorización, el agente solo necesita examinar un bloque acotado (típicamente entre 20 y 80 líneas) alrededor de una función, clase o bloque lógico particular. La ausencia de una directiva basal explícita que imponga la delimitación de lecturas deriva en hábitos ineficientes donde se vuelcan archivos completos a ciegas sin aprovechar capacidades nativas de búsqueda estática.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación Estricta de Contexto:** Eliminar la penalización cuadrática en el consumo de tokens en sesiones multi-turno provocada por lecturas masivas no delimitadas.
* **Protocolo de Lectura en Dos Fases:** Imponer el flujo determinista: Fase 1 (localización de líneas con `grep_search` o inspección pasiva) -> Fase 2 (lectura quirúrgica delimitada con `view_file` usando `StartLine` y `EndLine`).
* **Prohibición Explícita:** Prohibir la invocación de `view_file` sin delimitación de rango en archivos que superen 100 líneas o de tamaño desconocido.
* **Justificación de Elevación Basal (Nivel 4):** La herramienta `view_file` es una API nativa de primer nivel utilizada transversalmente en cualquier etapa (análisis, planificación, desarrollo, tests) y en todos los repositorios. No puede resolverse únicamente mediante scripts (Nivel 1) o skills bajo demanda (Nivel 2).
* **Cumplimiento de Presupuestos de Palabras:** Asegurar que `core/06-engineering-standards.md` permanezca por debajo de 300 palabras y que el contexto basal compilado en `dist/antigravity/AGENTS.md` no sobrepase el límite estricto de 800 palabras.

## Opciones Consideradas

* **Opción 1: Restricción a Nivel de Tooling / Envoltura CLI (Nivel 1).**
  * Crear un wrapper o script para filtrar lecturas.
  * *Descarte:* El agente interactúa mediante APIs nativas de modelo (`view_file`), por lo que un script externo no impide que el modelo continúe llamando a `view_file` directamente.
* **Opción 2: Documentar la Regla Únicamente en un Skill Bajo Demanda (Nivel 2).**
  * Incluir la recomendación en `autonomous-learning` o un skill auxiliar.
  * *Descarte:* Los skills solo se consultan cuando se activan explícitamente; la lectura de archivos ocurre antes y durante cualquier tarea, dejando desprotegido el Turno 0 y las fases de análisis.
* **Opción 3: Elevación a Directiva Basal en `core/06-engineering-standards.md` y Sincronización Transversal (Elegida).**
  * Incorporar la prohibición formal y el protocolo en dos fases como directiva basal en `core/06-engineering-standards.md`.
  * Sincronizar estándares de entorno en `core/10-environment-standards.md` y documentación técnica en `docs/architecture.md`.
  * Ratificar con tests automatizados en `tests/test_progressive_disclosure.py`.

## Decisión Adoptada

Opción elegida: **Opción 3**. Se implementan los siguientes lineamientos:

1. **Protocolo en Dos Fases:** Toda inspección de archivos debe seguir la secuencia:
   - **Fase 1 (Localización):** Usar `grep_search` para ubicar el identificador, función o fragmento y obtener su número de línea.
   - **Fase 2 (Extracción Quirúrgica):** Invocar `view_file` especificando obligatoriamente `StartLine` y `EndLine` para acotar la ventana al rango estrictamente necesario (típicamente 20-80 líneas).
2. **Prohibición Expresa:** Queda prohibido invocar `view_file` sin `StartLine` y `EndLine` sobre archivos de más de 100 líneas.
3. **Sincronización:** Reflejar la directiva en `core/06-engineering-standards.md`, alinear `core/10-environment-standards.md`, actualizar el árbol Diátaxis en `docs/architecture.md` y verificar la preservación de invariantes en `tests/test_progressive_disclosure.py`.

## Consecuencias

### Positivas
* Reducción drástica del desperdicio de tokens por turno en sesiones largas.
* Mitigación del *context rot* y mayor agilidad atencional en modelos de contexto medio/largo.
* Comportamiento estandarizado y reproducible en todos los runtimes y repositorios anfitriones.

### Negativas / Compensaciones
* Requiere dos pasos (`grep_search` -> `view_file`) en lugar de uno cuando se desconoce la ubicación del código, compensado ampliamente por el ahorro cuadrático de tokens en el historial.
