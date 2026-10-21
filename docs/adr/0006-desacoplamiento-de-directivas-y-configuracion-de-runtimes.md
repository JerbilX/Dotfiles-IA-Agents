---
status: accepted
date: 2026-10-15
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
---

# 0006 - Desacoplamiento de Directivas de Prompt y Configuración de Runtime

## Contexto y Planteamiento del Problema

En `runtimes/antigravity/` convivían originalmente dos tipos de archivos con naturaleza y ciclos de vida divergentes:
1. `01-sandbox.md`: Directiva normativa de comportamiento para el agente (estándares de ejecución en sandbox, comandos de red, I/O nativo).
2. `config.md`: Manifiesto operativo destinado al aprovisionamiento del entorno (declaración de skills a enlazar y binarios a exponer).

El compilador de `build.sh` (`cmd_build`) concatenaba de forma indiscriminada todos los archivos `*.md` dentro de `runtimes/antigravity/` hacia `dist/antigravity/AGENTS.md`. Como consecuencia, la sección de aprovisionamiento de Bash (`## Enabled Skills`) se inyectaba en el System Prompt de todos los agentes, consumiendo tokens de contexto de forma innecesaria y tratando un manifiesto de infraestructura local como si fuera una regla cognitiva del modelo. Adicionalmente, el formato Markdown requería expresiones regulares frágiles en Bash para extraer la lista de dependencias y carecía de extensibilidad estructurada para soportar futuras configuraciones de runtime (variables de entorno, servidores MCP, etc.).

## Impulsores de la Decisión (Decision Drivers)

* **Pureza del System Prompt (`AGENTS.md`):** Garantizar que solo directivas de comportamiento y estándares normativos para el agente ingresen al archivo compilado de contexto.
* **Separación de Responsabilidades (SoC):** Aislar físicamente las reglas normativas de los manifiestos operativos de aprovisionamiento de entorno.
* **Extensibilidad y Robustez Estructurada:** Adoptar un formato estándar de configuración que permita incorporar esquemas futuros (skills, MCPs, flags de entorno) sin colisionar con el motor de compilación Markdown ni depender de parsers frágiles en Bash.
* **Zero-Breaking Change en Flujo de Aprovisionamiento:** Mantener la idempotencia y el comportamiento esperado de `./build.sh build`, `./build.sh link` y `./build.sh skills`.

## Opciones Consideradas

* **Opción 1: Delimitadores / Marcadores en Markdown.** Mantener `config.md` pero usar directivas de exclusión (ej. etiquetas de comentarios HTML o prefijos de exclusión en `build.sh`).
* **Opción 2: Formato Estructurado no-Markdown en la raíz del runtime (`config.json`).**
* **Opción 3: Subestructura con Aislamiento Físico (`rules/` para directivas y `config.json` para aprovisionamiento).**

## Decisión Adoptada

Opción elegida: **Opción 3 ("Subestructura con Aislamiento Físico: `rules/` + `config.json`")**, porque:

1. **Aislamiento a nivel de File System:** Al ubicar las directivas dentro de `runtimes/antigravity/rules/*.md`, el glob de compilación de `cmd_build()` se acota estrictamente a este subdirectorio, imposibilitando por diseño que cualquier archivo de configuración sea absorbido en el System Prompt.
2. **Formato JSON Estructurado:** `config.json` elimina la fragilidad de parsing por regex en Markdown. Se parsea de forma determinista mediante `jq` (con fallback nativo a `python3`), soportando validación de esquemas y extensibilidad inmediata (ej. futura integración de `mcpServers` u opciones de entorno).
3. **Consistencia con el Ecosistema:** Antigravity y la suite de herramientas utilizan nativamente formatos JSON (`config.json`, `mcp_config.json`, etc.) para sus configuraciones de runtime.

### Consecuencias

* **Positivas:**
  * `dist/antigravity/AGENTS.md` queda completamente libre de ruido y texto de aprovisionamiento operativo.
  * Extracción determinista e idempotente de skills en `build.sh` sin riesgo de errores por variaciones de formato Markdown.
  * La jerarquía de carpetas en `runtimes/` comunica explícitamente el propósito de cada archivo (`rules/` vs `config.json`).
* **Negativas / Trade-offs:**
  * Requiere actualizar la documentación en `README.md` y migrar entornos locales preexistentes mediante `./build.sh all`.
