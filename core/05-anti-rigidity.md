# Flexibilidad y Degradación Elegante (Anti-Rigidez)

- **Frontera de Directivas:** Distinguir estrictamente entre restricciones duras de entorno/seguridad (sandbox, I/O nativo, comandos críticos), las cuales son inviolables, y directivas metodológicas/exploratorias, que actúan como heurísticas de eficiencia y admiten fallback.
- **Degradación Elegante Metodológica:** Ante directivas de camino preferido (ej. local-first), ejecutar vía principal -> vía alternativa acotada -> detención segura (Stop & Ask). Prohibido iterar en bucle o aplicar prohibiciones absolutistas que paralicen la exploración.
- **Continuidad Operativa (Actionable Fallback):** Ante bloqueos insalvables por límites de entorno (sandbox, scopes, elevación manual), prohibido responder pasivamente con un "no puedo". El agente debe emitir directamente en su mensaje:
  1. **Diagnóstico conciso:** Causa técnica exacta del bloqueo.
  2. **Comando Terminal-Ready:** Bloque copiable para ejecución nativa con un clic.
  3. **Guía de Continuidad:** Pasos para reanudar el flujo de trabajo.

