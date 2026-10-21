---
status: accepted
date: 2026-10-16
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0012 - Optimización de Latencia y Eliminación de Fricción Operativa en Directivas

## Contexto y Planteamiento del Problema

La auditoría forense de telemetría realizada sobre sesiones operativas del agente (en particular durante la resolución de los [Issue #20](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/20) y [Issue #23](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/23)) reveló una acumulación crítica de latencia y fricción ceremonial de casi 20 minutos por tarea.

El desglose de los cuellos de botella aislados evidenció:
1. **Bucles de Red Secuenciales en Terminal:** Invocaciones de scripts bash iterativos (`for repo in ...; do gh repo view; done`) que tardaron casi 8 minutos debido a múltiples handshakes TLS y consultas HTTP individuales no agregadas.
2. **Rigidez de Planning Mode (Gate Humano Redundante):** La obligatoriedad absoluta de redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`) para temas de arquitectura forzó detenciones artificiales de 3 a 5 minutos, incluso cuando la solución ya había sido consensuada y validada empíricamente en el chat y el usuario había emitido una orden ejecutiva explícita de cierre o avance.
3. **Sobrecarga de Inspección en GitHub Projects v2:** Descarga iterativa de JSONs masivos (`item-list`) y mapeo exploratorio de campos (`field-list`) para buscar IDs hexadecimales internos, en lugar de utilizar invocaciones deterministas directas por nombre de campo y valor.
4. **Higiene de Archivos Temporales:** Falta de exclusión de archivos auxiliares (`.comment_body`, `.issue_body`, `.probe_*`) en `.gitignore`, provocando advertencias de cambios sin commitear y ciclos extra de limpieza.

## Impulsores de la Decisión (Decision Drivers)

* **Eficiencia Operativa y Latencia Mínima:** Reducir drásticamente los tiempos muertos de espera pasiva sin degradar la calidad técnica del software.
* **Agilidad Human-in-the-Loop sin Burocracia:** Mantener el control de decisiones críticas evitando gates redundantes cuando el consenso ya ha sido otorgado explícitamente en la conversación.
* **Determinismo en CLI y Conexiones Remotas:** Priorizar consultas agregadas y comandos directos que no dependan de introspección exploratoria costosa.
* **Preservación del Presupuesto de Contexto:** Formular directivas concisas y de alta densidad para no inflar innecesariamente el System Prompt basal.

## Opciones Consideradas

* **Opción 1: Mantener la burocracia rígida y tolerar latencias.** Exigir siempre `implementation_plan.md` y permitir bucles exploratorios en terminal. (Descartada por pérdida severa de productividad humana y de máquina).
* **Opción 2: Eliminar completamente los planes de implementación y gates humanos.** Pasar a un modelo puramente desatendido sin confirmación de planes. (Descartada por violar el principio de gobernanza y control de fallas en arquitectura).
* **Opción 3: Optimización Quirúrgica en 4 Capas (Fast-Path, Anti-Bucles Remotos, Comandos Deterministas e Higiene).** Incorporar excepciones de fast-path ante consenso previo, prohibir bucles secuenciales de red exigiendo GraphQL, fijar atajos directos en Projects v2 e incorporar exclusiones completas en `.gitignore`.

## Decisión Adoptada

Opción elegida: **"Opción 3"**, implementada mediante:
1. **Prevención de Bucles Remotos y Circuit Breaker (`core/04-web-search-discipline.md` y `runtimes/antigravity/rules/01-sandbox.md`):** Priorización obligatoria de consultas agregadas en un solo paso vía GraphQL (`gh api graphql`) o endpoints batch; autorización de iteraciones secuenciales en consola únicamente bajo un Circuit Breaker estricto de máximo 3 a 5 llamadas cuando la API carezca de soporte atómico, con freno mandatorio si se excede el umbral o se detecta lentitud.
2. **Fast-Path Ejecutivo ante Consenso Previo (`core/07-anti-hallucination.md` y `core/09-issue-driven-workflow.md`):** Exención de generar planes bloqueantes cuando el diagnóstico o diseño ya fue consensuado y el usuario emite una directiva ejecutiva directa (*"procedé"*, *"avanza"*, *"cerralo"*).
3. **Comandos Deterministas de Projects v2 (`core/09-issue-driven-workflow.md`):** Estandarización de `--field "Status" --value "..."` por URL directa, prohibiendo listados exploratorios de fields/items si la URL es conocida.
4. **Higiene de Temporales (`.gitignore` y `01-sandbox.md`):** Exclusión de `.comment_body`, `.issue_body` y `.probe_*`, y requerimiento de poda inmediata post-uso.

### Consecuencias

* **Positivas:**
  - Ahorro estimado de 15 a 18 minutos por ciclo de desarrollo E2E.
  - Supresión de pausas artificiales en el chat cuando la decisión técnica ya fue aprobada.
  - Eliminación de advertencias y estados sucios en Git por archivos auxiliares de CLI.
  - Consultas multi-repositorio instantáneas vía GraphQL en lugar de bucles lentos en bash.
* **Negativas / Trade-offs:**
  - Exige al agente mayor rigor para no invocar el Fast-Path cuando NO existe consenso previo o cuando el alcance de la tarea es ambiguo.
