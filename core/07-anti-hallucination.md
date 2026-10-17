# Estabilidad Lógica y Cero Tolerancia a la Alucinación

- **Inconsistencia Lógica y Stop & Ask:** Si una hipótesis contradice cualquier síntoma o hecho técnico del entorno, es inválida por definición. Prohibido adivinar o forzar soluciones ante vacíos de contexto; el agente debe detenerse inmediatamente y solicitar aclaración (Stop & Ask).
- **Prohibición de Diseño Infundado:** Prohibido inventar protocolos, arquitecturas o lógicas de negocio sin respaldo empírico en el workspace.
- **Blindaje del Planning Mode y Fast-Path:** Diagnósticos de errores (bug fixing) y cambios arquitectónicos requieren obligatoriamente `implementation_plan.md` con pausa bloqueante de aprobación.
  - *Excepción de Fast-Path:* Si la solución ya fue debatida, validada y acordada en el chat activo y el usuario emite orden ejecutiva directa ("procedé", "avanza", "aplicalo"), no generar plan bloqueante redundante; proceder directo a implementación, commit y PR.

