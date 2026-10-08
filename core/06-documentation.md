# Documentación y Registro de Decisiones

- **Registro en HISTORIAL.md (Log de Aprendizaje):**
  - Todo agente **DEBE** proponer el registro de cualquier decisión importante (arquitectónica, de seguridad, de diseño o metodológica) para mantener el archivo `HISTORIAL.md` actualizado.
  - **Gate de Aprobación Obligatorio:** El agente **TIENE ESTRICTAMENTE PROHIBIDO** escribir nuevos conocimientos o lecciones en el historial de manera autónoma. Antes de escribir, el agente debe presentarle al usuario un resumen sintetizado de la "lección aprendida" o decisión tomada, y preguntar explícitamente: *"¿Apruebas que registre este aprendizaje en el HISTORIAL.md?"*.
  - **Sintetización:** El registro debe ser un resumen definitivo y conclusivo (fecha, contexto, decisión y justificación). El objetivo es que las lecturas futuras sean directas y no requieran que el agente vuelva a procesar lógicamente o debatir la misma decisión.
  - Solo tras la aprobación explícita del usuario, el agente procederá a ejecutar la escritura en el archivo.
