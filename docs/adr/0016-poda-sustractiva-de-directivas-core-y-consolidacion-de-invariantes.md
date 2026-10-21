---
status: accepted
date: 2026-10-17
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0016 - Poda Sustractiva de Directivas Core y Consolidación de Invariantes

## Contexto y Planteamiento del Problema

El archivo compilado `dist/antigravity/AGENTS.md` alcanzó 3.080 palabras en el System Prompt basal. La auditoría técnica realizada sobre las sesiones operativas demostró que una carga basal sobredimensionada genera dilución atencional (*lost in the middle*), fatiga de instrucciones y fomenta un sesgo aditivo en los agentes (intentar corregir fallos agregando directivas defensivas adicionales en lugar de eliminar causas raíz).

Se detectaron tres problemas estructurales en la capa basal:
1. **Circuit Breaker triplicado:** La regla de parada ante iteraciones en red aparecía duplicada en `core/04-web-search-discipline.md` y `core/10-environment-standards.md`.
2. **Procedimientos CLI en el Core:** Módulos de gobernanza como `core/02-git-lifecycle.md` y `core/08-task-backlog-management.md` contenían secuencias detalladas de comandos de terminal (`git init`, `gh repo create`, `gh issue create`), redundantes con el skill bajo demanda `issue-driven-workflow` ([ADR-0013](0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md)).
3. **Solapamiento conceptual:** `core/05-anti-rigidity.md` (389 palabras) y `core/10-environment-standards.md` (364 palabras) sobre-explicaban las fronteras entre directivas duras y blandas y el inventario de herramientas nativas de archivos.

## Impulsores de la Decisión (Decision Drivers)

* **Maximización de Densidad de Señal:** Eliminar redundancias, ejemplos superfluos y sobre-explicaciones para maximizar la atención del modelo en los invariantes críticos.
* **Preservación Inquebrantable de Invariantes de Seguridad y Gobernanza:** Mantener intactas en la base las prohibiciones de push/merge a `main`, el gate humano para repositorios remotos, el confinamiento de sandbox y el uso de APIs nativas de archivos.
* **Separación de Responsabilidades (Core vs. Skills):** Las directivas core expresan políticas de gobernanza e invariantes normativos; los procedimientos de ejecución y plantillas CLI residen en skills bajo demanda.
* **Métrica Cuantificable:** Reducir el conteo basal de 3.080 palabras a ~1.400 - 1.600 palabras (reducción cercana al 50%).

## Opciones Consideradas

* **Opción 1: Mantener el contenido actual y aumentar el límite de contexto (`MAX_CONTEXT_WORDS`).** No resuelve la fatiga de instrucciones ni la dilución atencional.
* **Opción 2: Extracción total de módulos core a skills.** Deja la ventana basal sin invariantes de seguridad esenciales como el confinamiento del workspace o el gate de aprobación humana.
* **Opción 3: Poda sustractiva, unificación del Circuit Breaker y consolidación de invariantes en Core.** Preserva todas las reglas y políticas de seguridad pero redactadas con máxima concisión y señal pura, delegando la operativa al skill `issue-driven-workflow`.

## Decisión Adoptada

Se elige la **Opción 3**. Las acciones ejecutadas son:

1. **Unificación Canónica del Circuit Breaker:**
   - Centralizado exclusivamente en `core/04-web-search-discipline.md` (cubriendo búsquedas web con un máximo de 3 consultas y llamadas CLI de red con un máximo de 3 a 5 iteraciones).
   - Eliminada la copia redundante de `core/10-environment-standards.md`.

2. **Poda Procedimental en Core (`core/02` y `core/08`):**
   - Se removieron los bloques procedimentales y comandos CLI de creación de repositorios, configuración de ramas y redacción de issues en terminal.
   - Se mantuvieron los invariantes no negociables: gate humano de autorización previo a origin, prohibición de backlogs locales, registro formal de tareas futuras y scope creep en GitHub Issues/Projects.
   - Se formalizó la delegación de la ejecución técnica al skill `issue-driven-workflow`.

3. **Compactación Conceptual y Eliminación de Solapamiento (`core/05`, `core/10`, `rules/01`):**
   - En `core/05`, se condensó la distinción entre restricciones duras vs. blandas y el protocolo Actionable Fallback.
   - En `core/10`, se sintetizó el uso obligatorio de herramientas nativas de archivos y el confinamiento de terminal sin listas redundantes de herramientas.
   - En `runtimes/antigravity/rules/01-sandbox.md`, se compactó la categorización de comandos Git (solo lectura confinado vs. mutadores locales y comandos de red con bypass por `.git/` de solo lectura) y el formato atómico de commits (`.commit_msg`).

4. **Compactación Transversal de la Capa Core (`core/01`, `core/03`, `core/06`, `core/07`, `core/09`):**
   - Poda de frases de relleno y consolidación en listas concisas de alta densidad.

## Consecuencias

### Positivas
* **Reducción de Contexto:** El System Prompt basal pasa de 3.080 palabras a ~1.420 palabras, logrando una reducción neta del ~54%.
* **Eliminación de Dilución Atencional:** Menor propensión a sesgos aditivos y mayor precisión del modelo al seguir directivas normativas.
* **Cero Degradación de Seguridad:** Todos los invariantes de gobernanza, confinamiento de sandbox, permisos de Git y restricciones de workspace permanecen activos.
* **Mantenibilidad:** Menos superficie de texto redundante susceptible a inconsistencias futuras.

### Negativas / Trade-offs
* Al reducir explicaciones extensas, el agente depende de su razonamiento inherente sobre términos técnicos concisos (ej. "Actionable Fallback", "Stop & Ask", "Local-First").
