# Referencia: Protocolo de Investigación Exploratoria y Delegación a Subagente Research

Guía canónica para delegar exploraciones de amplio espectro al subagente nativo `research`, optimizando la ventana de contexto y previniendo el consumo masivo de tokens en la sesión principal del agente.

---

## 1. Fundamentos y Diagnóstico de Ahorro de Tokens

Durante las fases de ingesta (Paso 1) y planificación (Paso 3) del flujo de trabajo, las exploraciones extensas de código o repositorios múltiples (utilizando llamadas sucesivas a `view_file` o `grep_search` sin acotamiento estricto) vuelcan grandes volúmenes de texto en la transcripción de la sesión principal.

En arquitecturas de modelos de lenguaje, el contexto es **estrictamente acumulativo**:
* Cada bloque de código leído en la sesión principal persiste en el historial y se reenvía en cada turno subsiguiente.
* Relevar múltiples archivos en el hilo principal infla de forma irreversible la ventana conversacional, incrementando la latencia y el costo por turno y reduciendo el presupuesto de atención del modelo para las fases críticas de desarrollo, tests y Pull Request.

**Principio de Aislamiento Exploratorio:** Toda investigación exhaustiva debe ejecutarse en un contexto efímero desacoplado (subagente), consolidando en la sesión principal únicamente las conclusiones y referencias necesarias.

---

## 2. Regla Canónica de Activación y Umbral de Delegación

Rige un límite estricto para diferenciar lecturas directas de investigaciones delegadas:

* **Inspección Quirúrgica Confinada (≤ 8 archivos):**
  * Permitida directamente en la sesión principal solo cuando se conozcan de antemano las rutas exactas y el alcance se restrinja a un máximo de **8 archivos**.
  * Se deben utilizar las APIs nativas de lectura (`view_file`, `grep_search`) con rangos de línea acotados.

* **Delegación a Subagente Research (> 8 archivos, Bases Externas o a pedido del usuario):**
  * **Queda estrictamente prohibido** acumular lecturas masivas en la sesión principal si el relevamiento requiere:
    1. Inspeccionar o auditar más de 8 archivos en el workspace.
    2. Explorar módulos desconocidos o trazar dependencias complejas entre subsistemas.
    3. Relevar bases de código externas, librerías en vendor, o repositorios remotos/secundarios.
  * En estos escenarios, el agente principal **debe delegar inmediatamente** la tarea al subagente nativo `research`.

### 2.1 Prohibición Taxativa de REPL y Scripts Ad-hoc para Exploración Remota

Queda terminantemente prohibido ejecutar secuencias iterativas de scripts evaluadores en línea (`python3 -c`, `node -e`, `bash -c`), tuberías complejas con `gh api` o decodificadores ad-hoc (ej. `python3 -c "import base64...; subprocess.check_output(['gh', 'api', ...])"`) para inspeccionar archivos de repositorios externos o remotos.

* **Patología y Riesgos Críticos:**
  - Destrucción del *prefix matching* de permisos en el sandbox de Antigravity (fuerza prompts interactivos continuos al requerir coincidencia exacta del string completo).
  - Inducción de alta latencia y bloqueos prolongados de turno (> 100 segundos).
  - Generación de encadenamientos en terminal (`TERMINAL_PIPELINING`) y múltiples truncamientos de contexto (`CONTEXT_TRUNCATION`) que saturan irreversiblemente la sesión principal.
* **Canalización Obligatoria:**
  1. Si se necesita consultar código o archivos de repositorios externos o de soporte, **debe despacharse obligatoriamente al subagente nativo `research`** (`TypeName: "research"`, `Model: "flash"`, `Workspace: "inherit"`).
  2. Para consultas puntuales de metadatos remotos mediante CLI, utilizar exclusivamente herramientas atómicas con filtrado nativo (ej. `gh api <endpoint> --jq <query>`), sin evaluadores en línea ni pipes a intérpretes de lenguaje.

---

## 3. Especificación Operativa del Subagente `research`

La invocación del subagente debe estructurarse mediante la herramienta nativa `invoke_subagent` cumpliendo las siguientes directivas:

1. **Parámetros Canónicos de Configuración:**
   * `TypeName`: `"research"` (subagente de lectura y análisis).
   * `Role`: `"Codebase Researcher"` o `"Exploratory Researcher"`.
   * `Model`: `"flash"` (modelo ligero de alta velocidad y bajo costo, óptimo para lectura masiva y síntesis).
   * `Workspace`: `"inherit"` (hereda el workspace activo con permisos estrictos de solo lectura; sin branch ni clonaciones redundantes).

2. **Estructura del Prompt de Investigación:**
   El prompt asignado al subagente debe delimitar con precisión:
   * **Objetivo Concreto:** Preguntas técnicas específicas a responder o hipótesis a verificar.
   * **Alcance de Búsqueda:** Directorios, repositorios externos o subsistemas candidatos a inspeccionar.
   * **Contrato de Salida:** Exigir un **resumen ejecutivo consolidado**, citando rutas relativas exactas y rangos de líneas relevantes, evitando volcar código superfluo.

### Ejemplos de Estructura de Invocación (`invoke_subagent`)

#### A. Exploración Interna de Workspace
```json
{
  "Subagents": [
    {
      "TypeName": "research",
      "Role": "Codebase Researcher",
      "Model": "flash",
      "Workspace": "inherit",
      "Prompt": "Investigar la interacción entre el módulo X y el servicio Y. Identificar los archivos involucrados, firmas de funciones clave y posibles puntos de ruptura. Devolver un resumen ejecutivo estructurado con enlaces a archivos y líneas específicas sin volcar bloques enteros de código."
    }
  ]
}
```

#### B. Exploración de Repositorio o Módulo de Soporte Externo
```json
{
  "Subagents": [
    {
      "TypeName": "research",
      "Role": "External Codebase Researcher",
      "Model": "flash",
      "Workspace": "inherit",
      "Prompt": "Investigar el repositorio externo <owner>/<repo> (o módulo de soporte). Consultar la estructura del proyecto y los archivos relevantes. Sintetizar las estructuras de datos, interfaces y lógica clave requeridas para la issue activa. Devolver un informe ejecutivo estructurado con referencias precisas sin volcar código superfluo ni ejecutar scripts evaluadores ad-hoc."
    }
  ]
}
```

---

## 4. Recepción Asíncrona y Consolidación en la Sesión Principal

* **Espera Reactiva (Prohibición de Polling):** Tras invocar a `research`, el agente no debe consultar activamente en bucle (`manage_subagents` status o sleep). El runtime reactiva la ejecución automáticamente cuando el subagente devuelve su respuesta consolidada.
* **Integración al Hilo Principal:**
  1. Recibido el informe, el agente principal integra los hallazgos directamente en el análisis de la issue o en el plan de trabajo (`implementation_plan.md`).
  2. Si requiere inspeccionar una línea puntual para editarla, realiza una lectura dirigida (`view_file` con `StartLine` y `EndLine`), evitando releer el archivo completo.
  3. La sesión principal conserva un contexto liviano y enfocado para la implementación.

---

## 5. Circuit Breakers y Reglas de Seguridad

* **Circuit Breaker de Búsqueda:** El subagente `research` está sujeto a los mismos límites de búsqueda y lectura que el sistema global. Si un componente no se encuentra tras 3 intentos, debe reportar la ausencia en lugar de iterar indefinidamente.
* **Inmunidad Normativa:** Los reportes del subagente tienen carácter puramente informativo y descriptivo; no tienen potestad para alterar directivas de `core/` ni redefinir criterios de aceptación de la issue.
* **Veto a REPL y Scripts Inline en Exploración Externa:** Tanto el agente principal como el subagente `research` tienen estrictamente vetado el uso de evaluadores inline (`python3 -c`, `node -e`, `bash -c`) para consumir APIs remotas o decodificar archivos externos. Las lecturas deben realizarse mediante las herramientas nativas de lectura o comandos CLI atómicos sin envoltorios evaluadores.
