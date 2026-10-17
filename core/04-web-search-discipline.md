# Disciplina de Búsqueda Web y Circuit Breaker Canónico

- **Local-First Mandatorio:** Antes de invocar búsquedas web (`search_web`), verificar proactivamente si la respuesta existe en skills locales o documentación del workspace.
- **Circuit Breaker de Búsqueda Web:** Máximo 3 consultas sucesivas sin respuesta técnica concluyente; al alcanzar el límite, detenerse inmediatamente y consultar al usuario (Stop & Ask).
- **Circuit Breaker de Red y Terminal:** Operaciones multi-repositorio o en lote deben usar preferentemente consultas agregadas (`gh api graphql` o batch). De requerirse iteración secuencial en terminal, rige un disyuntor estricto de máximo 3 a 5 iteraciones; si se supera el límite o se detecta latencia severa, detenerse inmediatamente y consultar al usuario.

