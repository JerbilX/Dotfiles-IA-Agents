# Estabilidad Lógica y Cero Tolerancia a la Alucinación

- **Inconsistencia Lógica y Stop & Ask:** Si una hipótesis contradice cualquier síntoma o hecho técnico del entorno, es inválida por definición. Prohibido adivinar o forzar soluciones ante vacíos de contexto; el agente debe detenerse inmediatamente y solicitar aclaración (Stop & Ask).
- **Prohibición de Diseño Infundado:** Prohibido inventar protocolos, arquitecturas o lógicas de negocio sin respaldo empírico en el workspace.
- **Blindaje del Planning Mode y Fast-Track:**
  - *Fast-Track por Defecto:* Tareas en `🎯 Ready for Dev` con especificación técnica completa y criterios de aceptación verificables avanzan directamente a implementación y validación local sin pausa bloqueante de plan, consolidando el control humano en el gate del Pull Request.
  - *Freno Obligatorio de Planificación (Stop & Plan):* Requieren obligatoriamente `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`) las tareas con ambigüedad de diseño, alternativas técnicas divergentes, cambios arquitectónicos que introduzcan o modifiquen un ADR (`docs/adr/`), o diagnósticos con causa raíz no confirmada.
  - *Fast-Path Ejecutivo:* Órdenes ejecutivas directas ("procedé", "avanza", "aplicalo") tras debate previo en chat habilitan la implementación inmediata sin plan bloqueante.

