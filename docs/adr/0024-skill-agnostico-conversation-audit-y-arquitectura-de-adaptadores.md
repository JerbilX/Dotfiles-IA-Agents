---
status: accepted
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0024 - Skill Agnóstico conversation-audit y Arquitectura Desacoplada de Adaptadores para Auditoría de Rendimiento

## Contexto y Planteamiento del Problema

Con el despliegue de múltiples runtimes de IA (Google Antigravity y Claude Code) gobernados por Dotfiles-IA-Agents, surge la necesidad constante de evaluar el desempeño técnico de las conversaciones de los agentes: latencia por paso, duración total wall-clock, uso y tasa de fallos de herramientas, volumen de razonamiento (thinking) y detección de antipatrones (bucles de reintento, fallos consecutivos, encadenamiento de comandos en terminal, truncamiento de contexto o complacencia).

Hasta el momento, la inspección de sesiones previas presentaba serias deficiencias:
1. **Desperdicio Crítico de Contexto:** Al solicitar una auditoría o diagnóstico, el agente intentaba leer directamente archivos extensos de transcripción (`transcript.jsonl` de cientos de KB o MB) mediante `view_file` o `cat`, consumiendo decenas de miles de tokens de contexto innecesariamente.
2. **Ausencia de Métricas Reproducibles:** Las evaluaciones manuales del LLM resultaban subjetivas, cualitativas y carentes de precisión temporal (tiempos de reloj, cálculo de deltas entre pasos, ratios porcentuales de error de herramientas).
3. **Acoplamiento de Formatos:** Antigravity y Claude Code almacenan sus trazas en esquemas propietarios incompatibles (JSONL con `step_index` en el brain de Antigravity vs. mensajes JSON con bloques `tool_use`/`tool_result` en Claude Code).

## Impulsores de la Decisión (Decision Drivers)

* **Preservación del Presupuesto de Contexto (Context-Saving):** Extraer y agregar métricas fuera del contexto del LLM, inyectando únicamente informes compactos o tabulares.
* **Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius - ADR-0017):** Implementar la solución en la capa de skills (Nivel 2) y tooling (Nivel 1), con una excepción acotada en reglas de runtime (Nivel 3), sin alterar directivas basales (`core/`).
* **Agnosticismo de Runtime y Desacoplamiento:** Soporte unificado para Antigravity y Claude Code bajo un modelo de eventos normalizado.
* **Zero Dependencias Externas:** Operación basada exclusivamente en la biblioteca estándar de Python 3, garantizando portabilidad y velocidad sin requerir paquetes de PyPI.
* **Confinamiento de Seguridad y Sandbox:** Excepción explícita y acotada para el binario `agent-audit` en el arnés de Antigravity para permitir la lectura de logs de sesión fuera del workspace.

## Opciones Consideradas

* **Opción 1: Análisis Dinámico Prompt-Driven por el Agente.**
  * Delegar la auditoría a instrucciones en el system prompt para que el LLM lea e interprete el archivo JSONL con sus herramientas nativas de lectura.
  * *Descarte:* Degrada drásticamente el presupuesto de tokens, sufre truncamiento en archivos mayores a 45 KB y carece de cálculo reproducible de métricas numéricas.
* **Opción 2: Script Monolítico Específico para Antigravity.**
  * Implementar un script de Bash o Python rígido que solo reconozca el formato `transcript.jsonl` de Antigravity.
  * *Descarte:* Viola la visión multi-runtime de Dotfiles-IA-Agents (ADR-0018), imposibilitando auditar sesiones generadas por Claude Code.
* **Opción 3: Skill Canónico `conversation-audit` con Arquitectura de Adaptadores y CLI Determinista.**
  * Crear `skills/conversation-audit/` autocontenido, estructurado en:
    - **Capa de Adaptadores (`adapters/`):** Interfaz abstracta `TranscriptAdapter` con implementaciones concretas para `AntigravityAdapter` y `ClaudeAdapter`.
    - **Motor de Cálculo (`audit_engine.py`):** Agregación de tiempos wall-clock, latencias por paso, métricas de herramientas y motor de reglas para detección de antipatrones.
    - **CLI Determinista (`bin/agent-audit`):** Punto de entrada en Python estándar expuesto en `~/.local/bin/agent-audit` vía `build.sh skills`.
    - **Plantilla Estándar (`templates/audit_report.md`):** Formato uniforme de informe técnico.
    - **Especialización de Sandbox:** Incorporar la excepción para `agent-audit` en `runtimes/antigravity/rules/01-sandbox.md`.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes niveles:

1. **Nivel 1 (Tooling / `build.sh`):**
   * Se amplía `cmd_skills()` y `cmd_check()` en `build.sh` para soportar ejecutables ubicados en `skills/<skill>/bin/*` además de `skills/<skill>/scripts/*.sh`, permitiendo que scripts en Python con shebang se enlacen directamente en `~/.local/bin/`.
2. **Nivel 2 (Skills Canónicos / `skills/conversation-audit/`):**
   * Creación del skill con su respectivo `SKILL.md` (metodología, catálogo de métricas y taxonomía de antipatrones).
   * Modelo de dominio normalizado (`NormalizedStep`, `NormalizedToolCall`, `ConversationMetadata`).
   * Motor de auditoría con detección de 6 familias de antipatrones: `REPETITIVE_TOOL_LOOP`, `CONSECUTIVE_TOOL_ERRORS`, `HIGH_LATENCY_STEP`, `TERMINAL_PIPELINING`, `CONTEXT_TRUNCATION` y `COMPLACENCY_DETECTED`.
3. **Nivel 3 (Reglas de Runtime y Configuración):**
   * Registro de `conversation-audit` en `runtimes/antigravity/config.json` y `runtimes/claude/config.json`.
   * Declaración de `"agent-audit": "agent-audit"` en la sección `binaries` de ambos runtimes.
   * Actualización de `runtimes/antigravity/rules/01-sandbox.md` delimitando la excepción de `BypassSandbox: true` para `agent-audit`.

### Consecuencias

* **Positivas:**
  - Reducción drástica en el consumo de tokens durante auditorías técnicas (de miles de tokens a un resumen tabular de ~50 líneas).
  - Reproducibilidad matemática de métricas de rendimiento y detección automatizada de vicios conductuales.
  - Compatibilidad transparente entre Antigravity y Claude Code.
  - Extensibilidad sencilla a futuros runtimes mediante nuevos adaptadores.
* **Negativas / Trade-offs:**
  - Requiere mantener la sincronización de parsers si los runtimes modifican la estructura interna de sus logs de eventos.
