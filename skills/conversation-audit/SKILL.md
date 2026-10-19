---
name: conversation-audit
description: >-
  Auditoría sistemática, análisis de rendimiento y detección de antipatrones en sesiones y transcripciones de agentes de IA (Antigravity y Claude Code). Provee directivas metodológicas, catálogo de métricas y el CLI agent-audit para evaluar tiempos wall-clock, latencia por turno, desglose de herramientas, fallos de ejecución y vicios de comportamiento sin sobrecargar tokens de contexto.
---

# Auditoría de Conversaciones y Análisis de Rendimiento de Agentes

Guía metodológica, catálogo de métricas y protocolo operativo para la auditoría técnica de sesiones de agentes de Inteligencia Artificial (Google Antigravity y Claude Code), utilizando el CLI determinista `agent-audit` para optimizar latencias, consumo de contexto y calidad de ejecución.

---

## 1. Principios Fundamentales

1. **Ahorro de Presupuesto de Contexto (Context-Saving):**
   - Prohibido volcar transcripciones extensas (`transcript.jsonl`, JSON de sesiones) directamente al contexto del LLM mediante herramientas de lectura masiva (`view_file`, `cat`).
   - La ingesta y agregación de métricas debe delegarse de forma determinista al binario local `agent-audit`, ingresando al contexto del agente únicamente el informe procesado o resumen tabular.
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
| `CONTEXT_TRUNCATION` | **ALTA** | Truncamiento de Contexto | Pasos con presencia de `truncated_fields`, reflejando lecturas desmedidas o volcados de logs masivos. | Reemplazar lecturas completas por búsquedas dirigidas (`grep_search`), flags compactos (`--jq`) o paginación. |
| `COMPLACENCY_DETECTED` | **BAJA** | Complacencia o Adulación Vacía | Respuestas del modelo con frases serviles ("¡Gran idea!", "tienes toda la razón", "disculpa las molestias"). | Cumplir estrictamente `core/01-critical-feedback.md`. Mantener tono asertivo, objetivo y neutro. |

---

## 4. Protocolo Operativo de Auditoría

Cuando el usuario solicite auditar una conversación previa o cuando se requiera analizar el desempeño de una sesión reciente:

```
[1. Localización] -> [2. Invocación CLI] -> [3. Evaluación] -> [4. Reporte / Feedback]
```

### Paso 1: Localización del Archivo o ID de Sesión
- En **Antigravity**:
  - Las sesiones se encuentran en `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`.
  - El CLI acepta directamente la ruta al archivo o el `<conversation-id>` (UUID).
- En **Claude Code**:
  - Las sesiones residen en `~/.claude/` o archivos exportados `.json` / `.jsonl`.

### Paso 2: Invocación del CLI Determinista (`agent-audit`)
Ejecutar el comando de auditoría con `BypassSandbox: true` (requerido para acceder a las rutas externas al workspace donde residen los logs):

```bash
agent-audit <conversation-id-o-ruta>
```

#### Opciones Disponibles:
- Salida en texto tabular en consola (predeterminada):
  ```bash
  agent-audit <target>
  ```
- Salida en formato Markdown:
  ```bash
  agent-audit <target> --format markdown -o informe_auditoria.md
  ```
- Salida estructurada JSON (para análisis automatizado o scripts):
  ```bash
  agent-audit <target> --format json
  ```
- Ajuste de umbral de latencia:
  ```bash
  agent-audit <target> --threshold-latency 45.0
  ```
- Retorno estricto para CI (código 2 ante antipatrones críticos):
  ```bash
  agent-audit <target> --fail-on-antipattern
  ```

### Paso 3: Evaluación de Hallazgos
- Contrastar el desglose de herramientas: identificar si herramientas pesadas como `search_web` o `run_command` monopolizan el tiempo de ejecución.
- Inspeccionar si existen antipatrones de `CONSECUTIVE_TOOL_ERRORS` o `REPETITIVE_TOOL_LOOP`.
- Revisar los pasos de mayor latencia y contrastarlos con las operaciones realizadas.

### Paso 4: Registro y Retroalimentación
- Si la auditoría revela un problema estructural o una directiva faltante, registrar una nueva issue en el backlog canónico (`gh issue create --body-file .issue_body`) para consolidar la mejora.
