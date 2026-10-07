# Disciplina de Búsqueda Web (Circuit Breaker Global)

- Antes de iniciar búsquedas web (`search_web`) para documentación técnica, el agente **DEBE** verificar si existe un Skill local o documentación en el workspace.
- **Prohibición de Bucles:** Si tras 3 consultas web sucesivas no se encuentra la respuesta técnica exacta, el agente debe **DETENERSE INMEDIATAMENTE** y consultar al usuario, bajo riesgo de ser penalizado por pérdida de tiempo y recursos.
