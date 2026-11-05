# Estabilidad Lógica y Cero Tolerancia a la Alucinación

- **Inconsistencia Lógica y Stop & Ask:** Si una hipótesis contradice cualquier síntoma o hecho técnico del entorno, es inválida por definición. Prohibido adivinar o forzar soluciones ante vacíos de contexto; el agente debe detenerse inmediatamente y solicitar aclaración (Stop & Ask).
- **Prohibición de Diseño Infundado:** Prohibido inventar protocolos, arquitecturas o lógicas de negocio sin respaldo empírico en el workspace.
- **Issue como Propuesta:** El diagnóstico, la solución y los criterios de una issue (de un humano u otro agente) son hipótesis. Antes de implementar, validarlos contra el código y la evidencia. Si hay criterios sin sustento, contraproducentes o con causa no confirmada, reportarlo y hacer Stop & Ask antes de implementar o desviarse. Fast-Track no exime de esta validación.
- **Blindaje del Planning Mode y Fast-Track:**
  - *Fast-Track por Defecto:* Tareas en `🎯 Ready for Dev` con especificación técnica completa y criterios de aceptación verificables avanzan directamente a implementación y validación local sin pausa bloqueante de plan, consolidando el control humano en el gate del Pull Request.
  - *Freno de Planificación (Stop & Plan, solo N2):* Requieren obligatoriamente `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`) las tareas con ambigüedad de diseño, alternativas técnicas divergentes, cambios arquitectónicos que introduzcan o modifiquen un ADR (`docs/adr/`), o diagnósticos con causa raíz no confirmada.
  - *Fast-Path Ejecutivo:* Órdenes ejecutivas directas ("procedé", "avanza", "aplicalo") tras debate previo en chat habilitan la implementación inmediata sin plan bloqueante.

