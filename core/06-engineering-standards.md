# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia del Código de Producción:** El diseño, rendimiento y contratos de producción priman sobre la conveniencia del arnés de pruebas. Prohibido degradar código productivo con bifurcaciones artificiales para complacer mocks obsoletos.
- **Bifurcación ante Fallos en Tests:**
  1. **Mocks o Fixtures Desactualizados:** Si la falla se debe a desfase del test double respecto al contrato real, actualizar el mock/fixture.
  2. **Regresión Funcional:** Si se incumple una regla legítima de negocio, corregir inmediatamente el código de producción.
- **Mínima Intervención y Radio de Impacto Acotado (Minimal Blast Radius):** Prohibido escalar a niveles superiores de abstracción si el problema se resuelve en un nivel inferior (Nivel 0 CLI/flags -> Nivel 1 tooling/scripts -> Nivel 2 skills bajo demanda -> Nivel 3 reglas runtime -> Nivel 4 core basal). Modificar directivas en `core/` exige justificación técnica de inviabilidad en niveles inferiores.
- **Lectura Quirúrgica en Dos Fases y Circuit Breaker:** Prohibido invocar `view_file` sin acotar (`StartLine` y `EndLine`, ventana ≤ 200 líneas). En archivos > 150 líneas, la localización de funciones, clases o variables se realiza exclusivamente con `grep_search`, restringiendo `view_file` a ventana quirúrgica (≤ 50 líneas). Prohibido interpretar advertencias de contenido no mostrado como orden de seguir leyendo; rige límite estricto de máximo 3 lecturas consecutivas globales de herramientas de inspección (`view_file`, `grep_search`, `find_by_name`) sin acción intermedia observable (edición, comando terminal o Stop & Ask/síntesis), independientemente de si alternan archivos.

