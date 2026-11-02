# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia del Código de Producción:** El diseño, rendimiento y contratos de producción priman sobre la conveniencia del arnés de pruebas. Prohibido degradar código productivo con bifurcaciones artificiales para complacer mocks obsoletos.
- **Bifurcación ante Fallos en Tests:**
  1. **Mocks o Fixtures Desactualizados:** Si la falla se debe a desfase del test double respecto al contrato real, actualizar el mock/fixture.
  2. **Regresión Funcional:** Si se incumple una regla legítima de negocio, corregir inmediatamente el código de producción.
- **Mínima Intervención y Radio de Impacto Acotado (Minimal Blast Radius):** Prohibido escalar a niveles superiores de abstracción si el problema se resuelve en un nivel inferior (Nivel 0 CLI/flags -> Nivel 1 tooling/scripts -> Nivel 2 skills bajo demanda -> Nivel 3 reglas runtime -> Nivel 4 core basal). Modificar directivas en `core/` exige justificación técnica de inviabilidad en niveles inferiores.
- **Lectura Quirúrgica en Dos Fases:** Prohibido invocar `view_file` sin acotar (`StartLine` y `EndLine`, con ventana ≤ 200 líneas) sobre cualquier archivo sin excepción. Es mandatorio ejecutar previamente `grep_search` (o inspección pasiva) para localizar los números de línea exactos del símbolo, función o bloque de interés, restringiendo la lectura a la ventana mínima necesaria (típicamente 20 a 80 líneas) para prevenir la penalización cuadrática de tokens y saturación del contexto en sesiones multi-turno.

