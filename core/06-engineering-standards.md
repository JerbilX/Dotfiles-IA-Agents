# Integridad de Diseño y Relación Producción-Tests (Anti-Test-Induced Damage)

- **Prevalencia del Código de Producción:** El diseño, rendimiento y contratos de producción priman sobre la conveniencia del arnés de pruebas. Prohibido degradar código productivo con bifurcaciones artificiales para complacer mocks obsoletos.
- **Bifurcación ante Fallos en Tests:**
  1. **Mocks o Fixtures Desactualizados:** Si la falla se debe a desfase del test double respecto al contrato real, actualizar el mock/fixture.
  2. **Regresión Funcional:** Si se incumple una regla legítima de negocio, corregir inmediatamente el código de producción.

