---
status: accepted
date: 2026-10-07
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0002 - Cero Tolerancia a la Alucinación y Freno Obligatorio

## Contexto y Planteamiento del Problema
Los agentes de IA tienden a recurrir a patrones heurísticos o "adivinanzas" técnicas cuando se enfrentan a lagunas de información, APIs no validadas o síntomas de error incompletos. Asimismo, se observó que asumían el estado de un entorno basándose únicamente en el hilo conversacional sin verificar activamente el disco, provocando errores en cascada y propuestas técnicas inválidas.

## Impulsores de la Decisión (Decision Drivers)
* **Precisión Técnica Senior:** Cero tolerancia al código inventado, flags inexistentes o supuestos erróneos.
* **Defensividad Operativa (Verify First):** Inspeccionar el sistema antes de ejecutar o planificar acciones.
* **Gobernanza del Planning Mode:** Exigir planes formales previos para cualquier diagnóstico o cambio arquitectónico.

## Opciones Consideradas
* **Opción 1:** Asumir un modelo reactivo donde el agente propone soluciones rápidas por aproximación.
* **Opción 2:** Imponer el protocolo estricto "Stop & Ask", el principio de verificación previa obligatoria en disco, y el blindaje mandatorio de planes de implementación (`implementation_plan.md`) para tareas de diagnóstico o arquitectura.

## Decisión Adoptada
Opción elegida: **"Opción 2"**, porque previene pérdidas de tiempo críticas, evita daños a repositorios existentes y alinea el comportamiento del agente con el estándar de un ingeniero de software senior.

### Consecuencias
* **Positivas:**
  * Se erradica la alucinación de comandos, opciones y arquitecturas sin contexto validado.
  * El agente se detiene de forma segura ante inconsistencias lógicas o falta de certeza.
  * Todo diagnóstico y refactor arquitectónico pasa por revisión previa del usuario.
* **Negativas / Trade-offs:**
  * Mayor interacción requerida cuando el contexto inicial es ambiguo (comportamiento fail-safe intencional).
