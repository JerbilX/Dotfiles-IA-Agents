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
| `TERMINAL_REPL_LOOP` | **ALTA** | Bucle REPL Iterativo en Terminal | Secuencia o alta densidad de ejecuciones de evaluación en línea en terminal (`python3 -c`, `node -e`, etc.) para pruebas iterativas o exploratorias. | Desalentar el uso de terminal como REPL e indicar la refactorización hacia un script de prueba dedicado en scratch (`<appDataDir>/brain/<conversation-id>/scratch/`) o tests unitarios locales. |
| `CONTEXT_TRUNCATION` | **ALTA** | Truncamiento de Contexto | Pasos con presencia de `truncated_fields`, reflejando lecturas desmedidas o volcados de logs masivos. | Reemplazar lecturas completas por búsquedas dirigidas (`grep_search`), flags compactos (`--jq`) o paginación. |
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
- Inspeccionar si existen antipatrones de `CONSECUTIVE_TOOL_ERRORS`, `REPETITIVE_TOOL_LOOP` o `TERMINAL_REPL_LOOP`.
- Revisar los pasos de mayor latencia y contrastarlos con las operaciones realizadas.

### Paso 4: Registro y Retroalimentación
- Si la auditoría revela un problema estructural o una directiva faltante, registrar una nueva issue en el backlog canónico (`gh issue create --body-file .issue_body`) para consolidar la mejora.
