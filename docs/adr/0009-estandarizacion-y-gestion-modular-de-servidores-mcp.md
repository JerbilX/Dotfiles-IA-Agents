---
status: proposed
date: 2026-10-15
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
---

# 0009 - Estandarización y Gestión Modular de Servidores MCP

## Contexto y Planteamiento del Problema

El aprovisionamiento de servidores MCP (Model Context Protocol) en el entorno de desarrollo y ejecución de Antigravity presentaba tres debilidades arquitectónicas:

1. **Configuración Fuera de Control de Versiones:** La definición de servidores residía manualmente en la ubicación canónica de Antigravity (`~/.gemini/config/mcp_config.json`), sin estar versionada en Git ni sujeta a mecanismos de respaldo automatizado o rollback.
2. **Fragilidad Sintáctica y Acoplamiento de Entorno:** Errores tipográficos en el JSON local provocaban la invalidación total de las herramientas MCP de la sesión. Adicionalmente, las definiciones basadas en transporte Stdio requerían rutas absolutas dependientes del anfitrión (`/home/.../venv/bin/python`), impidiendo su portabilidad entre máquinas.
3. **Desconexión con el Manifiesto de Runtime y la Suite de Auditoría:** Tras la implementación de `config.json` ([ADR 0006](0006-desacoplamiento-de-directivas-y-configuracion-de-runtimes.md)), validación formal con JSON Schema ([ADR 0007](0007-esquema-de-validacion-y-desacoplamiento-de-binarios-en-runtimes.md)) y el comando de verificación estática `check` ([ADR 0008](0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md)), los servidores MCP permanecían como una pieza no gobernada por el pipeline central de `build.sh`.

## Impulsores de la Decisión (Decision Drivers)

* **Catálogo Versionado y Modular (SoC):** Cada servidor MCP debe definirse en un archivo independiente y reutilizable, separando el catálogo disponible de la lista de servidores activados en un entorno dado.
* **Declaratividad y Contratos Tipados:** La activación debe realizarse en `config.json` y estar estrictamente tipada mediante esquemas canónicos JSON Schema con `additionalProperties: false`.
* **Portabilidad y Desacoplamiento de Rutas:** Soporte para macros de entorno (`$HOME`, `${HOME}`) expandidas en tiempo de compilación para no exponer datos específicos del usuario en el repositorio.
* **Idempotencia y Operación Segura:** Enlace simbólico atómico con respaldo `.bak.<timestamp>` hacia la ruta canónica `~/.gemini/config/mcp_config.json`.
* **Auditoría Estática Preventiva:** Integración nativa en `build.sh check` para validar esquemas, sintaxis, presencia de ejecutables en disco/PATH e integridad de enlaces simbólicos.

## Opciones Consideradas

* **Opción 1: Edición manual directa en `~/.gemini/config/mcp_config.json`.** Descartada por carecer de control de versiones, reproducibilidad y validación automática.
* **Opción 2: Monolito de configuración dentro de `config.json`.** Incrustar las especificaciones completas de cada servidor en `config.json`. Descartada porque infla el manifiesto de runtime y no permite compartir o modularizar servidores complejos.
* **Opción 3: Catálogo modular (`runtimes/antigravity/mcp/*.json`) con activación declarativa en `config.json`, compilación determinista y auditoría en `build.sh`.**

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes componentes:

1. **Catálogo Modular de Definiciones (`runtimes/antigravity/mcp/`):**
   - Cada servidor reside en `<server-name>.json`, gobernado por el nuevo esquema canónico `runtimes/schema/mcp-server.schema.json`.
   - Soporta transporte Stdio (`command`, `args`, `env`) y transporte SSE (`serverUrl`), eliminando metadatos innecesarios (`$schema`, `description`) durante la compilación.
2. **Activación Declarativa en `config.json`:**
   - Incorporación de la propiedad opcional `"mcp_servers": ["<server-name>", ...]` en `runtimes/antigravity/config.json`.
   - Extensión de `runtime-config.schema.json` para validar la propiedad bajo tipos estrictos y nombres con patrón slug.
3. **Pipeline de Compilación y Fusión en `build.sh`:**
   - `cmd_build` / `compile_mcp_config`: Fusiona los servidores activos en `dist/antigravity/mcp_config.json` bajo la clave `"mcpServers"`, expandiendo deterministamente variables de entorno (`$HOME`) con Python 3 estándar.
   - `cmd_link` / `link_mcp`: Respalda atómicamente configuraciones previas (`mcp_config.json.bak.<timestamp>`) y crea el enlace simbólico hacia `~/.gemini/config/mcp_config.json`.
   - `cmd_mcp`: Subcomando dedicado para compilar, enlazar y consultar estado exclusivamente de los servidores MCP.
4. **Auditoría Estática en `cmd_check`:**
   - Valida el manifiesto `config.json` y cada módulo MCP habilitado contra su esquema.
   - Verifica que los ejecutables declarados en `command` existan físicamente y tengan permisos de ejecución (+x) si son rutas absolutas, o que existan en `$PATH` si son nombres de binario.
   - Audita la integridad del enlace simbólico en `~/.gemini/config/mcp_config.json`.

### Consecuencias

* **Positivas:**
  - Control de versiones exhaustivo y modular para servidores MCP.
  - Portabilidad total en Git: sin rutas absolutas de usuario hardcodeadas.
  - Integración completa con `check`, `status` y `all`.
  - Respaldo automático antes de sobreescribir configuraciones en el entorno de Antigravity.
* **Negativas / Trade-offs:**
  - Los servidores MCP definidos en el catálogo deben compilarse (`./build.sh build` o `./build.sh mcp`) para que Antigravity tome los cambios en `~/.gemini/config/mcp_config.json`.
