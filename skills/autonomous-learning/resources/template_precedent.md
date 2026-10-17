# Ficha de Análisis de Precedente y Lección Aprendida

Utiliza esta plantilla estructurada cuando documentes incidentes técnicos, post-mortems o aprendizajes empíricos para su posterior consulta por agentes.

---

## 1. Identificación y Metadatos
- **ID de Incidencia / Tarea:** [ej. ISSUE-42 o INCIDENT-20261017-01]
- **Fecha:** [YYYY-MM-DD]
- **Dominio Técnico:** [sandbox-permissions | git-workflow | architecture-modularity | testing-quality | context-budget | tooling-automation]
- **Componentes Afectados:** [Rutas o módulos involucrados, ej. build.sh, runtimes/antigravity]

---

## 2. Diagnóstico Empírico (Síntomas y Contexto)
- **Operación Ejecutada:** [Comando, test o procedimiento en ejecución]
- **Síntoma Observable:** [Error exacto en consola, stacktrace o comportamiento anómalo]
- **Condiciones de Contorno:** [Restricciones del entorno: kernel ro, variable de entorno ausente, etc.]

---

## 3. Causa Raíz
- **Mecanismo Subyacente:** [Explicación técnica detallada de por qué ocurrió la falla en el nivel más bajo de abstracción]
- **Hipótesis Iniciales Descartadas:** [Qué supuestos previos resultaron falsos tras la investigación]

---

## 4. Solución Técnica Verificada
- **Cambio Aplicado:** [Descripción de la modificación de código o configuración]
- **Comandos / Procedimiento Determinista:**
  ```bash
  [Comando atómico verificado]
  ```
- **Trade-offs Asumidos:** [Consecuencias colaterales o compromisos de diseño aceptados]

---

## 5. Invariante o Directiva Derivada
- **Mecanismo de Prevención Permanente:** [¿Se creó un check en build.sh, una regla en rules/, un ADR o un test?]
- **Referencia Canónica:** [Enlace a ADR o Pull Request, ej. docs/adr/0019-*.md]
