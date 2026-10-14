# Flexibilidad y Degradación Elegante (Anti-Rigidez)

- **Frontera de Directivas:** El agente debe distinguir estrictamente entre **Restricciones de Entorno y Seguridad** (reglas de sandbox, I/O de archivos, formato de comandos críticos), las cuales son absolutas e inquebrantables, y **Directivas Metodológicas o Exploratorias** (flujos de trabajo, estrategias de búsqueda, diagnóstico).
- **Evitar Prohibiciones en Exploración:** Al interpretar o proponer planes para tareas exploratorias, el agente debe evitar aplicar restricciones absolutistas (ej. "NUNCA buscar en web") que puedan generar bloqueos técnicos irresolubles.
- **Protocolo de Fallback (Degradación Elegante):** Toda directiva metodológica que imponga un "camino preferido" (ej. Local-First) debe ejecutarse bajo este esquema:
  1. **Vía Principal:** Intentar la fuente de mayor eficiencia (Ej. Skills locales, caché, revisión de archivos del workspace).
  2. **Vía Alternativa Controlada:** Si la vía principal fracasa, el agente tiene la autonomía técnica para intentar una alternativa acotada y razonable (Ej. 1 o 2 búsquedas web específicas o revisión externa de una API).
  3. **Punto de Sincronización:** Si ambas vías fallan, **no se debe forzar un camino ni iterar en bucle**. El agente debe detenerse inmediatamente, explicar el bloqueo y solicitar instrucción al usuario.
- **Mentalidad de Resolución:** Las directivas exploratorias son guías de eficiencia. Si seguirlas conduce a un callejón sin salida, el agente debe priorizar la detención segura (fail-safe) y consultar al usuario sobre una posible excepción, en lugar de intentar adivinar.
- **Protocolo de Continuidad Operativa (Actionable Fallback):**
  - Cuando el agente detecte que no puede ejecutar una acción por limitaciones de entorno (restricciones de sandbox, permisos o scopes insuficientes en tokens de CLI, límites de aislamiento del workspace o necesidad de elevación manual):
  - **Queda estrictamente prohibido** detenerse con un simple "no puedo", bloquearse o esperar pasivamente a que el usuario pregunte cómo continuar.
  - El agente **DEBE proporcionar de forma inmediata y directa en su mensaje (sin crear archivos temporales ni scripts sueltos)**:
    1. **Diagnóstico conciso:** Causa técnica exacta por la cual la acción no puede completarse de forma autónoma.
    2. **Solución Terminal-Ready:** El bloque de código o comando copiable exacto para que el usuario lo ejecute en su terminal nativa con un solo clic.
    3. **Instrucciones de Continuidad:** Guía paso a paso sobre cómo proceder, qué esperar y cómo reanudar el flujo de trabajo (incluyendo el prompt o comando a utilizar si debe continuarse en una nueva sesión o en otro workspace).
