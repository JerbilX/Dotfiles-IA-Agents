---
name: conversation-audit
description: >-
  Auditoría sistemática, análisis de rendimiento y detección de antipatrones en sesiones y transcripciones de agentes de IA (Antigravity y Claude Code). Provee directivas metodológicas, catálogo de métricas, el CLI agent-audit y protocolo de delegación a subagente en background (modelo flash) para evaluar tiempos wall-clock, latencia por turno, desglose de herramientas, fallos de ejecución y vicios de comportamiento sin sobrecargar tokens de contexto.
---

# Auditoría de Conversaciones y Análisis de Rendimiento de Agentes

Guía metodológica, catálogo de métricas y protocolo operativo para la auditoría técnica de sesiones de agentes de Inteligencia Artificial (Google Antigravity y Claude Code), utilizando el CLI determinista `agent-audit` para optimizar latencias, consumo de contexto y calidad de ejecución.

---

## 1. Principios Fundamentales

1. **Ahorro de Presupuesto de Contexto (Context-Saving):**
   - Prohibido volcar transcripciones extensas (`transcript.jsonl`, JSON de sesiones) directamente al contexto del LLM mediante herramientas de lectura masiva (`view_file`, `cat`).
   - La ingesta y agregación de métricas debe delegarse de forma determinista al binario local `agent-audit`, ingresando al contexto del agente únicamente el informe procesado o resumen tabular.
   - En auditorías extensas, históricas o en lote, la ejecución y análisis de `agent-audit` debe desacoplarse hacia un subagente en background (modelo `flash`), preservando el hilo de chat principal libre de trazas intermedias.
2. **Agnosticismo de Runtime:**
   - La arquitectura separa el modelo de datos normalizado (`NormalizedStep`, `NormalizedToolCall`) de los formatos físicos de cada runtime mediante adaptadores (`AntigravityAdapter`, `ClaudeAdapter`), permitiendo auditar indistintamente sesiones de Antigravity o Claude Code.
3. **Cero Dependencias Externas:**
   - El motor de cálculo y el CLI operan 100% sobre la biblioteca estándar de Python 3 (`json`, `datetime`, `argparse`, `dataclasses`, `pathlib`), asegurando reproducibilidad inmediata y ejecución confiable en entornos confinados o de CI/CD.
4. **Trazabilidad y Mejora Continua:**
   - Las anomalías recurrentes detectadas durante las auditorías deben retroalimentar el backlog canónico como nuevas GitHub Issues para su refinamiento en reglas de runtime (`rules/*.md`) o directivas basales (`core/*.md`).

---

## 2. Catálogo Canónico de Métricas

| Categoría | Métrica | Unidad | Definición Técnica |
| :--- | :--- | :---: | :--- |
| **Identificación** | **Título / Objetivo** | Texto | Resumen o requerimiento inicial normalizado del usuario para identificación inequívoca de la sesión. |
| **Tiempo** | **Wall-Clock Duration** | Segundos / Minutos | Tiempo transcurrido total entre la marca de tiempo del primer paso y el último paso registrado. |
| **Tiempo** | **Step Latency (Promedio / Máxima)** | Segundos | Delta temporal calculado entre eventos consecutivos. Refleja el tiempo de inferencia del modelo y la ejecución de herramientas. |
| **Ejecución** | **Turnos por Fuente** | Conteo | Cantidad de pasos desglosados en: Usuario (`USER`), Agente (`MODEL`) y Sistema/Herramientas (`SYSTEM`). |
| **Herramientas** | **Invocaciones por Tool** | Conteo | Total de llamadas acumuladas por cada herramienta nativa o MCP (`view_file`, `replace_file_content`, `run_command`, etc.). |
| **Herramientas** | **Tasa de Falla (Error Rate)** | Porcentaje (%) | Porcentaje de invocaciones que concluyeron en estado `ERROR` o con excepciones reportadas en el resultado. |
| **Razonamiento** | **Pasos con Thinking** | Conteo | Cantidad de turnos donde el modelo emitió cadenas de razonamiento previo (`thinking` / chain-of-thought). |
| **Razonamiento** | **Volumen de Thinking** | Caracteres | Promedio y total de caracteres dedicados a planificación interna por turno. |
| **Contexto** | **Truncamientos** | Conteo | Cantidad de pasos con campos truncados (`truncated_fields`), indicador directo de desbordes de buffer o I/O excesivo. |

---

## 3. Taxonomía de Antipatrones de Conversación

| Código | Severidad | Nombre | Diagnóstico Técnico | Acción Correctiva Recomendada |
| :--- | :---: | :--- | :--- | :--- |
| `REPETITIVE_TOOL_LOOP` | **ALTA** | Bucle Repetitivo de Herramienta | Dos o más invocaciones consecutivas de la misma herramienta con argumentos idénticos sin progreso intermedio. | Detenerse y verificar si el agente no leyó el output previo o quedó atrapado en un ciclo ciego de reintento. |
| `CONSECUTIVE_TOOL_ERRORS` | **CRÍTICA** | Errores Consecutivos en Herramientas | Dos o más fallos de ejecución de herramientas consecutivos. | Activar de inmediato el disyuntor de seguridad (Stop & Ask). Prohibido seguir probando variaciones sin hipótesis fundada. |
| `HIGH_LATENCY_STEP` | **MEDIA** | Paso de Alta Latencia | Pasos con duración individual superior al umbral configurado (ej. > 60s). | Investigar llamadas bloqueantes de red, búsquedas sin filtro o procesamiento excesivo en terminal. |
| `TERMINAL_PIPELINING` | **MEDIA** | Encadenamiento en Terminal | Uso de operadores (`&&`, `\|`, `;`, tuberías) en comandos de terminal (`run_command`), rompiendo el *prefix matching* de permisos. | Desacoplar en llamadas CLI atómicas o utilizar herramientas nativas de archivos (`write_to_file`, `replace_file_content`). |
| `TERMINAL_REPL_LOOP` | **ALTA** | Bucle REPL Iterativo en Terminal | Secuencia o alta densidad de ejecuciones de evaluación en línea en terminal (`python3 -c`, `node -e`, `bash -c`) o wrappers vía `subprocess` para pruebas, exploración o filtrado de utilidades. | Desalentar el uso de terminal como REPL/wrapper e indicar el consumo de flags nativos del CLI, refactorización hacia un script dedicado en scratch (`<appDataDir>/brain/<conversation-id>/scratch/`) o tests locales. |
| `CONTEXT_TRUNCATION` | **ALTA** | Truncamiento de Contexto | Pasos con presencia de `truncated_fields`, reflejando lecturas desmedidas o volcados de logs masivos. | Reemplazar lecturas completas por búsquedas dirigidas (`grep_search`), flags compactos (`--jq`) o paginación. |
| `UNPAGINATED_FILE_READ` | **ALTA** | Lectura No Paginada de Archivos | Invocación de herramientas de lectura de archivos (`view_file` o equivalentes) sin delimitar `StartLine`/`EndLine` o con ventanas excesivas (> 200 líneas). | Utilizar `grep_search` para localización previa y acotamiento de ventana mediante `StartLine` y `EndLine`. |
| `READ_ONLY_LOOP` | **ALTA** | Bucle de Solo Lectura / Parálisis | Secuencia de 4 o más lecturas pasivas consecutivas (`view_file`, `grep_search`, `find_by_name`, `list_dir`) sin acción observable intermedia (mutación o comando). | Detener lecturas exploratorias, formular hipótesis y proceder a mutar código, ejecutar pruebas o detenerse con síntesis. |
| `PING_PONG_TOOL_LOOP` | **ALTA** | Bucle Cíclico Alternante | Patrón cíclico repetitivo entre 2 o 3 llamadas alternantes (ej. A -> B -> A -> B) eludiendo límites por archivo. | Romper la alternancia ciega entre archivos; aplicar disyuntor de seguridad y solicitar clarificación o validar hipótesis en tests. |
| `COMPLACENCY_DETECTED` | **BAJA** | Complacencia o Adulación Vacía | Respuestas del modelo con frases serviles ("¡Gran idea!", "tienes toda la razón", "disculpa las molestias"). | Cumplir estrictamente `core/01-critical-feedback.md`. Mantener tono asertivo, objetivo y neutro. |

---

## 4. Protocolo Operativo de Auditoría

Cuando el usuario solicite auditar una conversación previa o cuando se requiera analizar el desempeño de una sesión reciente:

```
[1. Identificación] -> [2. Invocación CLI] -> [3. Evaluación] -> [4. Reporte / Feedback]
```

### Paso 1: Identificación del Objetivo
- La resolución de rutas físicas (`resolve_path`) está completamente encapsulada dentro del adaptador correspondiente a cada runtime (`TranscriptAdapter`).
- El agente o usuario no requiere conocer ni inspeccionar las rutas internas del host; basta con proporcionar el identificador de la sesión (`<conversation-id>` / UUID) o una ruta directa en caso de procesar archivos de exportación externa.

### Paso 2: Invocación del CLI Determinista (`agent-audit`)

La invocación debe ejecutarse con `BypassSandbox: true` (requerido para acceder a las rutas externas al workspace donde residen los logs del runtime).

- **Consumo Exclusivo de Opciones Nativas y Veto a Wrappers:**
  - Toda la extracción, filtrado e inspección de telemetría debe consumirse exclusivamente mediante las opciones nativas de `agent-audit` (`--format`, `--inspect-step`, `--inspect-steps`, `--filter-tool`, `--failed-steps`, `--metadata-only`, etc.).
  - Prohibido taxativamente envolver `agent-audit` en llamadas intermedias vía `subprocess` dentro de scripts en subshell o evaluadores (`python3 -c`, `bash -c`), así como canalizar su salida por tuberías hacia scripts ad-hoc. El procesamiento debe operar sobre la salida directa del CLI o aislarse en un script formal en `scratch/` confinado (`BypassSandbox: false`).

#### Jerarquía Determinista de Invocación (Degradación Elegante):

1. **Vía Canónica Principal (Estándar en `$PATH`):**
   Invocar directamente el comando estándar expuesto en `$PATH`:
   ```bash
   agent-audit <target>
   ```
   *(Esta es la forma canónica recomendada. Asegura que el motor de permisos de Antigravity reconozca un único prefijo global permanente mediante la Opción 4).*

2. **Vía de Fallback Determinista (Ante ausencia en `$PATH` o `command not found`):**
   Si la subshell no incluye `~/.local/bin` o no se ha ejecutado `./build.sh skills` en el host, resolver directamente la ruta sin recurrir a búsquedas ciegas (`find_by_name`, `ls`):
   - **Dentro de este repositorio (`Dotfiles-IA-Agents`):**
     ```bash
     ./skills/conversation-audit/bin/agent-audit <target>
     ```
   - **En workspaces externos (otros proyectos):**
     - En **Antigravity**:
       ```bash
       ${HOME}/.gemini/config/skills/conversation-audit/bin/agent-audit <target>
       ```
     - En **Claude Code**:
       ```bash
       ${HOME}/.claude/skills/conversation-audit/bin/agent-audit <target>
       ```

3. **Detención Segura (*Stop & Ask* - Actionable Fallback):**
   Solo si el binario no existe físicamente en el sistema en ninguna de las rutas anteriores:
   - **Diagnóstico:** El CLI `agent-audit` no se encuentra disponible ni en `$PATH` ni en las rutas canónicas del skill.
   - **Acción Externa:** Solicitar al usuario que posicione su terminal en la raíz de su repositorio de Dotfiles y ejecute `./build.sh all` para aprovisionar las herramientas en el anfitrión.

#### Opciones Disponibles:
- Salida en texto tabular en consola (predeterminada):
  ```bash
  agent-audit <target>
  ```
- Consulta rápida de metadatos (título, fechas, runtime) sin procesar pasos:
  ```bash
  agent-audit <target> --metadata-only
  ```
- Salida de metadatos rápidos en JSON:
  ```bash
  agent-audit <target> --metadata-only --format json
  ```
- Salida en formato Markdown:
  ```bash
  agent-audit <target> --format markdown -o informe_auditoria.md
  ```
- Salida estructurada JSON (para análisis automatizado o scripts):
  ```bash
  agent-audit <target> --format json
  ```
- Inspección detallada y acotada de un paso específico:
  ```bash
  agent-audit <target> --inspect-step <N>
  ```
- Inspección de secuencias y rangos de pasos (soporta rangos `N-M`, sintaxis `N..M`, listas `A,B,C` o mixtas):
  ```bash
  agent-audit <target> --inspect-steps 87-105
  agent-audit <target> --inspect-steps 87..105
  agent-audit <target> --inspect-steps 87,88,92,100
  agent-audit <target> --inspect-steps 1-5,87-90,105
  ```
- Inspección quirúrgica de pasos en Markdown o JSON:
  ```bash
  agent-audit <target> --inspect-step <N> --format markdown
  agent-audit <target> --inspect-step <N> --format json
  agent-audit <target> --inspect-steps 87-105 --format markdown
  agent-audit <target> --inspect-steps 87-105 --format json
  ```
- Filtrado nativo avanzado por herramienta (aislado o en combinación con rangos o fallos, sin scripts evaluadores):
  ```bash
  agent-audit <target> --filter-tool run_command
  agent-audit <target> --inspect-steps 87-105 --filter-tool run_command
  agent-audit <target> --failed-steps --filter-tool run_command
  ```
- Listado exclusivo de pasos con errores o excepciones en herramientas:
  ```bash
  agent-audit <target> --failed-steps
  ```
- Listado de pasos con errores en Markdown o JSON:
  ```bash
  agent-audit <target> --failed-steps --format markdown
  agent-audit <target> --failed-steps --format json
  ```
- Ajuste de umbral de latencia:
  ```bash
  agent-audit <target> --threshold-latency 45.0
  ```
- Ajuste de umbral de líneas para lecturas de archivo:
  ```bash
  agent-audit <target> --threshold-file-lines 150
  ```
- Retorno estricto para CI (código 2 ante antipatrones críticos):
  ```bash
  agent-audit <target> --fail-on-antipattern
  ```

### Paso 3: Evaluación de Hallazgos
- Contrastar el desglose de herramientas: identificar si herramientas pesadas como `search_web` o `run_command` monopolizan el tiempo de ejecución.
- Inspeccionar si existen antipatrones de `CONSECUTIVE_TOOL_ERRORS`, `REPETITIVE_TOOL_LOOP`, `TERMINAL_REPL_LOOP` o `UNPAGINATED_FILE_READ`.
- Revisar los pasos de mayor latencia y contrastarlos con las operaciones realizadas.

### Paso 4: Registro y Retroalimentación
- Si la auditoría revela un problema estructural o una directiva faltante, registrar una nueva issue en el backlog canónico (`gh issue create --body-file .issue_body`) para consolidar la mejora.

---

## 5. Modo de Auditoría Desacoplada en Background vía Subagente

Para auditorías de sesiones extensas, análisis por lotes de múltiples conversaciones históricas o evaluaciones periódicas de rendimiento:

### 5.1 Umbral y Criterio de Activación (Preservación Extrema de Contexto)
- **Auditoría Directa Confinada (Sesión Activa o Rápida):**
  - Permitida en el hilo principal cuando se audita una única sesión reciente con consulta rápida (`--metadata-only`) o inspección acotada.
- **Delegación Mandatoria a Subagente en Background:**
  - Cuando se requiera auditar sesiones históricas o extensas (> 20 turnos).
  - Cuando se evalúe rendimiento en lote (múltiples sesiones o diagnósticos comparativos).
  - Cuando la conversación principal esté en fases activas de desarrollo o revisión y no deba ensuciarse con salidas extensas de CLI o cómputo intermedio de antipatrones.

### 5.2 Especificación y Contrato del Subagente
La delegación al subagente se estructura con la herramienta nativa `invoke_subagent`:

1. **Parámetros de Configuración del Subagente:**
   - `TypeName`: `"self"` (hereda el entorno y herramientas completas del agente para invocar `run_command` con `BypassSandbox: true`).
   - `Role`: `"Session Performance Auditor"` o `"Session Auditor"`.
   - `Model`: `"flash"` (modelo ligero de alta velocidad y bajo costo, óptimo para parsear CLI, analizar antipatrones y sintetizar reportes).
   - `Workspace`: `"inherit"` (hereda el workspace sin branching ni duplicación de storage).

2. **Contrato Operativo y Reglas de Blindaje:**
   - **Restricción Estricta de Herramientas (Exclusividad de `agent-audit`):**
     - Prohibido taxativamente al subagente ejecutar comandos de terminal ajenos a `agent-audit` (veto absoluto de `python3`, `python3 -c`, `node`, `ruby`, `cat`, `grep`, `bash`, scripts ad-hoc o wrappers vía `subprocess`).
     - Prohibido el uso de herramientas nativas de lectura o búsqueda (`view_file`, `grep_search`) sobre transcripciones externas. Toda la telemetría se extrae de forma 100% determinista mediante `agent-audit`.
   - **Presupuesto Finito de Herramientas (Tool Budget):**
     - Presupuesto máximo estricto de **2 a 3 invocaciones de herramientas** en toda la sesión: 1 ejecución global (`agent-audit <target> --format markdown`) y hasta 2 quirúrgicas opcionales (`agent-audit <target> --failed-steps` o `agent-audit <target> --inspect-step <N>`).
   - **Disyuntor Autónomo de Seguridad (Circuit Breaker - Stop & Synthesize):**
     - Si `agent-audit` arroja un error o si se alcanza el presupuesto de herramientas (3 llamadas), el subagente debe detenerse inmediatamente (Stop & Synthesize) y emitir su diagnóstico consolidado con los datos disponibles, sin reintentar ni entrar en bucles de evaluación.
   - **Contrato de Salida Limpia:** El subagente tiene estrictamente prohibido reenviar trazas crudas, transcripciones enteras o tablas intermedias excesivas. Emite únicamente un **Diagnóstico Ejecutivo Consolidado**.
   - **Canal de Emisión:** Envía el reporte consolidado directamente en su mensaje de respuesta de finalización o mediante `send_message` hacia la sesión principal.

### 5.3 Estructura de Invocación (`invoke_subagent`)

```json
{
  "Subagents": [
    {
      "TypeName": "self",
      "Role": "Session Performance Auditor",
      "Model": "flash",
      "Workspace": "inherit",
      "Prompt": "Ejecuta 'agent-audit <target> --format markdown' con BypassSandbox: true. Presupuesto estricto: máximo 3 tool calls (puedes usar --failed-steps o --inspect-step <N> si hay errores). Prohibido ejecutar comandos de terminal ajenos a agent-audit (vetado python3 -c, cat, grep, bash). Circuit breaker: si hay error o alcanzas 3 llamadas, Stop & Synthesize de inmediato. Devuelve únicamente el Diagnóstico Ejecutivo Consolidado al hilo principal. Ver directivas en skills/conversation-audit/templates/subagent_prompt.md."
    }
  ]
}
```

### 5.4 Plantilla y Directiva de Prompt para el Subagente
Para garantizar resultados deterministas, consultar la plantilla canónica [`templates/subagent_prompt.md`](templates/subagent_prompt.md). El prompt debe delimitar:
1. **Objetivo:** Identificador de la conversación objetivo (`<conversation-id>` o ruta de transcripción).
2. **Ejecución:** Invocación de `agent-audit <target> --format markdown`.
3. **Estructura de Retorno Exigida:**
   - **Metadatos y Resumen:** Target, runtime, duración wall-clock, turnos totales, latencia media/máx, tasa de errores de herramientas y pasos con thinking.
   - **Veredicto de Antipatrones:** Detalle de antipatrones detectados (código, severidad, paso y recomendación correctiva) o confirmación explícita de ausencia.
   - **Cuellos de Botella:** Herramientas y pasos con mayor latencia acumulada.
   - **Conclusiones y Próximos Pasos:** Recomendaciones técnicas sintéticas (ej. registrar issue si hay antipatrón estructural recurrente).

### 5.5 Recepción Asíncrona y Consolidación en la Sesión Principal
- **Espera Reactiva (Prohibición de Polling):** Tras invocar al subagente, el agente principal entra en espera reactiva sin ejecutar bucles de sondeo (`manage_subagents` status o comandos sleep). El runtime reactiva la ejecución automáticamente al recibir el reporte consolidado.
- **Aislamiento de Contexto:** El hilo de chat principal solo incorpora el diagnóstico ejecutivo consolidado, preservando su presupuesto de tokens y manteniendo un historial limpio enfocado en la tarea principal.

