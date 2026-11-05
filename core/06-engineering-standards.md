# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia del Código de Producción:** Diseño y contratos de producción priman sobre arneses de prueba; prohibido degradar código productivo con bifurcaciones para complacer mocks obsoletos.
- **Bifurcación ante Fallos en Tests:** Actualizar mocks/fixtures si hay desfase con el contrato real; corregir código productivo si hay regresión funcional.
- **Mínima Intervención (Minimal Blast Radius):** Prohibido escalar si se resuelve en nivel inferior (N0 CLI -> N1 tooling -> N2 skills -> N3 runtime -> N4 core). Modificar `core/` exige justificar inviabilidad inferior. Rige sobre análisis y propuestas:
  - **Veto Acumulativo:** Prohibido tocar múltiples capas ante una sola falla.
  - **Causa Raíz:** Aislar causa raíz única y descartar formalmente hipótesis secundarias.
  - **Anti-Sobreingeniería:** Prohibido nuevo tooling, hooks o docs si basta precisión semántica en directivas existentes.
- **Lectura Quirúrgica en Dos Fases y Circuit Breaker:** `view_file` exige delimitar `StartLine`/`EndLine` (ventana ≤ 200 líneas; ≤ 50 líneas si archivo > 150 tras `grep_search`). Prohibido interpretar advertencias de contenido no mostrado como orden de continuar. Límite estricto de 3 lecturas consecutivas globales (`view_file`, `grep_search`, `find_by_name`) sin acción intermedia observable (edición, comando terminal o Stop & Ask).
- **Ejecución Quirúrgica de Pruebas y Prevención de Truncamiento:** Prohibido ejecutar suites completas reiteradas o no acotadas en `stdout` en desarrollo o diagnóstico. Obligatorio filtrar pruebas (archivo o caso puntual) o usar baja verbosidad para evitar saturación y truncamiento de contexto; suites integrales solo en verificación final previa al commit.

