---
status: accepted
date: 2026-10-28
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0039 - Aislamiento de Servidores MCP de Dominio por Workspace y Conservación de Skills On-Demand

## Contexto y Planteamiento del Problema

Históricamente, la configuración global de Antigravity (`runtimes/antigravity/config.json` enlazada a `~/.gemini/config/mcp_config.json`) registraba de manera universal el servidor MCP `eso-mcp-server` con 18 herramientas especializadas de la API de Elder Scrolls Online ([ADR-0009](0009-estandarizacion-y-gestion-modular-de-servidores-mcp.md)).

Debido al funcionamiento de las APIs de LLMs, para que un modelo pueda invocar herramientas, el runtime está obligado a inyectar la especificación completa del esquema JSON de cada herramienta (`function calling`) en el System Prompt de **cada turno de cada conversación**. En repositorios ajenos a ESO (como proyectos web, scripts o repositorios de dotfiles), esta inyección ciega desperdicia ~2.500 tokens por turno sin aportar valor funcional.

A su vez, el skill especializado `eso-addon-development` opera bajo el estándar de **Progressive Disclosure** ([ADR-0036](0036-modularizacion-skill-eso-addon-development-y-progressive-disclosure.md)), consumiendo únicamente ~60 tokens de metadatos en el System Prompt basal y postergando la lectura de su contenido procedural hasta que el agente detecte explícitamente una tarea de desarrollo de ESO. Desacoplar el skill del catálogo global eliminaría la capacidad del agente de auto-descubrir y andamiar automáticamente la configuración de ESO en repositorios nuevos.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación Estricta de Contexto (Eliminación de Sobrecarga MCP):** Erradicar la inyección incondicional de las 18 herramientas de `eso-mcp-server` en el perfil global de Antigravity.
* **Conservación de la Inteligencia On-Demand (Skills Basados en Progressive Disclosure):** Mantener `eso-addon-development` disponible globalmente con costo despreciable (~60 tokens), permitiendo que el skill sea el encargado nativo de inicializar y andamiar el entorno de desarrollo en cualquier repositorio de ESO.
* **Aislamiento por Workspace de Servidores MCP:** Confinar `eso-mcp-server` exclusivamente a los repositorios de addons de ESO mediante archivos declarativos locales (`.agents/plugins/eso-addon-suite/mcp_config.json` para Antigravity y `.mcp.json` para Claude Code).
* **Cero Falsos Positivos en Verificaciones Globales:** Adecuar `build.sh check` para validar la ausencia de `eso-mcp-server` en el perfil global y auditar la plantilla declarativa sin generar advertencias espurias en entornos genéricos.

## Opciones Consideradas

* **Opción 1: Desacoplar tanto el Servidor MCP como el Skill de Forma Global.**
  * Retirar `eso-mcp-server` y `eso-addon-development` del perfil global de Antigravity.
  * *Descarte:* Genera un callejón sin salida (catch-22): si el skill se elimina globalmente, el agente en un repositorio nuevo no sabe cómo programar addons de ESO ni cómo andamiar los archivos de configuración de MCP requeridos.
* **Opción 2: Mantener la Configuración Global Inalterada.**
  * Aceptar el desperdicio continuo de ~2.500 tokens por turno en todos los proyectos.
  * *Descarte:* Ineficiencia técnica grave frente a sesiones paralelas en proyectos múltiples.
* **Opción 3: Aislamiento Quirúrgico de Servidores MCP por Workspace y Conservación Global de Skills On-Demand (Elegida).**
  * Eliminar `eso-mcp-server` del perfil global en `runtimes/antigravity/config.json`.
  * Mantener `eso-addon-development` en `skills` globales bajo Progressive Disclosure.
  * Extender el skill para que instruya al agente a andamiar `.agents/plugins/eso-addon-suite/mcp_config.json` (o `.mcp.json`) en workspaces de addons.

## Decisión Adoptada

Se adopta la **Opción 3**, estructurada en los siguientes componentes:

1. **Purificación del Perfil MCP Global (`runtimes/antigravity/config.json`):**
   - Se establece `"mcp_servers": []` en la configuración global de Antigravity.
   - `dist/antigravity/mcp_config.json` se compila a `{"mcpServers": {}}`.
   - Se erradica la inyección de las 18 herramientas de `eso-mcp-server` en sesiones genéricas.

2. **Preservación del Skill Global `eso-addon-development`:**
   - Permanece en el array `skills` de `runtimes/antigravity/config.json`.
   - Su coste basal permanece restringido a 46 palabras (~60 tokens de metadatos descriptivos).

3. **Capacidad de Andamiaje y Activación Local de Workspace:**
   - Se incorpora a `skills/eso-addon-development` la directiva procedimental para que el agente, al operar en un repositorio de addons de ESO, verifique y genere la configuración local de MCP si no existe:
     - Antigravity: `.agents/plugins/eso-addon-suite/plugin.json` y `mcp_config.json`.
     - Claude Code: `.mcp.json`.
   - Se provee la plantilla canónica de referencia en `modules/eso/template/`.

4. **Auditoría Estática en `cmd_check`:**
   - Valida que `runtimes/*/config.json` no contenga servidores de dominio en `mcp_servers`.
   - Valida la integridad sintáctica de la plantilla en `modules/eso/template/`.
   - Suprime advertencias de ejecutables MCP no encontrados cuando el servidor no esté habilitado en el runtime auditado.

## Consecuencias

### Positivas

* **Ahorro Cuantificable:** Se reducen ~2.500 tokens por turno en todos los proyectos generales sin perder capacidades de desarrollo en ESO.
* **Capacidad On-Demand Íntegra:** Al conservarse el skill, el agente sabe de inmediato cómo inicializar y desarrollar en un repositorio de ESO sin necesidad de scripts externos previos.
* **Auditoría Limpia:** Eliminación definitiva de advertencias falsas sobre `eso-mcp-server` en `build.sh check`.

### Negativas / Trade-offs

* Ninguna desventaja técnica significativa: los ~60 tokens de metadatos del skill representan una fracción insignificante del presupuesto total de contexto (< 0.05% de la ventana típica).
