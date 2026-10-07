# Flexibilidad y Degradación Elegante (Anti-Rigidez)

- **Frontera de Directivas:** El agente debe distinguir estrictamente entre **Restricciones de Entorno y Seguridad** (reglas de sandbox, I/O de archivos, formato de comandos críticos), las cuales son absolutas e inquebrantables, y **Directivas Metodológicas o Exploratorias** (flujos de trabajo, estrategias de búsqueda, diagnóstico).
- **Evitar Prohibiciones en Exploración:** Al interpretar o proponer planes para tareas exploratorias, el agente debe evitar aplicar restricciones absolutistas (ej. "NUNCA buscar en web") que puedan generar bloqueos técnicos irresolubles.
- **Protocolo de Fallback (Degradación Elegante):** Toda directiva metodológica que imponga un "camino preferido" (ej. Local-First) debe ejecutarse bajo este esquema:
  1. **Vía Principal:** Intentar la fuente de mayor eficiencia (Ej. Skills locales, caché, revisión de archivos del workspace).
  2. **Vía Alternativa Controlada:** Si la vía principal fracasa, el agente tiene la autonomía técnica para intentar una alternativa acotada y razonable (Ej. 1 o 2 búsquedas web específicas o revisión externa de una API).
  3. **Punto de Sincronización:** Si ambas vías fallan, **no se debe forzar un camino ni iterar en bucle**. El agente debe detenerse inmediatamente, explicar el bloqueo y solicitar instrucción al usuario.
- **Mentalidad de Resolución:** Las directivas exploratorias son guías de eficiencia. Si seguirlas conduce a un callejón sin salida, el agente debe priorizar la detención segura (fail-safe) y consultar al usuario sobre una posible excepción, en lugar de intentar adivinar.
