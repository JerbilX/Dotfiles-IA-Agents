# Integridad de Diseño y Relación Producción-Tests (Anti-Test-Induced Damage)

- **Prevalencia del Dominio y Código de Producción:** El diseño, rendimiento y contratos del software en producción priman sobre la conveniencia del arnés de pruebas. Queda estrictamente prohibido contaminar el código de producción con ramas artificiales, comprobaciones defensivas innecesarias o degradación de optimizaciones con el único fin de evitar adaptar tests unitarios o mocks obsoletos.
- **Protocolo de Bifurcación ante Fallos en Tests:**
  1. **Fallas por Test Doubles o Fixtures Desactualizados:** Si una modificación canónica rompe una prueba porque el mock, stub o fixture no implementa métodos de la API real o carece de datos válidos requeridos por el contrato, **se deben actualizar el mock y el fixture de prueba** para reflejar fielmente la realidad del entorno.
  2. **Fallas por Reglas de Negocio o Comportamiento:** Si la prueba falla porque una aserción funcional legítima del producto se incumple, se asume una regresión técnica en el código de producción y este debe corregirse de inmediato.
