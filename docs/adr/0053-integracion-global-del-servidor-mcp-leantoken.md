---
status: accepted
date: 2026-11-08
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
references:
  - docs/adr/0009-estandarizacion-y-gestion-modular-de-servidores-mcp.md
  - docs/adr/0039-aislamiento-de-servidores-mcp-y-skills-de-dominio-por-workspace.md
  - docs/adr/0041-aislamiento-de-skills-de-dominio-por-workspace-y-optimizacion-del-catalogo-global.md
---

# 0053 - Integración Global del Servidor MCP LeanToken

## Contexto y Planteamiento del Problema

En los ADRs [0039](0039-aislamiento-de-servidores-mcp-y-skills-de-dominio-por-workspace.md) y [0041](0041-aislamiento-de-skills-de-dominio-por-workspace-y-optimizacion-del-catalogo-global.md) se estableció una política de "perfil global puro" en los manifiestos de runtime (`runtimes/*/config.json`), restringiendo `"mcp_servers": []` globalmente para evitar la inyección ciega e incondicional de esquemas de herramientas en el System Prompt de cada turno. Esta medida se diseñó para confinar servidores de dominio específico (como `eso-mcp-server` para desarrollo de addons de Elder Scrolls Online) a workspaces pertinentes mediante `agent-module`.

Sin embargo, **LeanToken** (https://github.com/morluto/leantoken) no es un servidor de nicho ni un framework de dominio específico, sino una herramienta transversal de inteligencia de código e indexación atómica con presupuesto estricto de tokens diseñada para mantener los contextos de los agentes de IA reducidos y eficientes. 

Para que los agentes de IA (Antigravity y Claude Code) dispongan de capacidades de recuperación acotada en cualquier repositorio de trabajo sin requerir activación manual repetitiva por workspace, se requiere su habilitación transversal en el perfil global de ambos runtimes.

## Impulsores de la Decisión (Decision Drivers)

* **Disponibilidad Transversal:** LeanToken debe estar disponible en todas las sesiones y repositorios de Antigravity y Claude Code como infraestructura basal de optimización de tokens.
* **Gobernanza y Cero Deriva:** La integración debe realizarse declarativamente a través del catálogo modular de `Dotfiles-IA-Agents` (`runtimes/*/mcp/leantoken.json`), evitando instaladores automáticos (`npx leantoken setup`) que destruyan o sobreescriban los enlaces simbólicos de dotfiles.
* **Coexistencia con el Aislamiento de Dominio:** Preservar el principio de aislamiento de servidores de nicho (ej. ESO): los servidores de dominio continúan confinados a `modules/`, mientras que LeanToken constituye una excepción explícita por ser utilidad transversal de infraestructura.
* **Verificación Automatizada e Idempotencia:** Compilación determinista mediante `./build.sh build` y validación estática en `./build.sh check` y la suite de pruebas unitarias (`tests/test_workspace_isolation.py`).

## Opciones Consideradas

* **Opción 1: Módulo bajo demanda (`modules/leantoken/`).** Requiere ejecutar `agent-module enable leantoken` proyecto por proyecto. Descartada por requerimiento expreso del usuario de disponer de LeanToken de manera universal.
* **Opción 2: Instalación interactiva externa (`npx leantoken setup`).** Descartada por vulnerar la fuente única de verdad, sobreescribir enlaces simbólicos gestionados por `build.sh` y generar inconsistencias en auditorías de integridad.
* **Opción 3: Declaración modular y habilitación en `config.json` global con actualización de contratos de prueba (Elegida).** Definir `runtimes/*/mcp/leantoken.json`, habilitar `"leantoken"` en `"mcp_servers"` de `antigravity` y `claude`, y actualizar la suite de pruebas para reconocer a LeanToken como servidor global transversal autorizado.

## Decisión Adoptada

Se adopta la **Opción 3**:

1. **Definición Modular (`runtimes/*/mcp/leantoken.json`):**
   - Configurado bajo transporte Stdio invocando `npx -y leantoken mcp`.
   - Gobernado por el esquema canónico `runtimes/schema/mcp-server.schema.json`.

2. **Habilitación en Manifiestos Globales (`runtimes/*/config.json`):**
   - Incorporación de `"leantoken"` en el array `"mcp_servers"` de `runtimes/antigravity/config.json` y `runtimes/claude/config.json`.
   - `build.sh` compilará la clave `"leantoken"` en `dist/antigravity/mcp_config.json` y `dist/claude/mcp_config.json`.

3. **Adaptación de la Suite de Pruebas (`tests/test_workspace_isolation.py`):**
   - Actualización de las aserciones para verificar que `mcp_servers` global contenga exclusivamente servidores transversales autorizados (`["leantoken"]`) y prohíba estrictamente servidores de dominio (`eso-mcp-server`).

## Consecuencias

### Positivas
* LeanToken disponible automáticamente en Antigravity y Claude Code para cualquier sesión de trabajo.
* Sin manipulación manual ni riesgo de rotura de symlinks en `$HOME`.
* Documentación y trazabilidad formal conforme a la taxonomía MADR y el estándar de dotfiles.

### Negativas / Trade-offs
* Se incorporan las herramientas de LeanToken al esquema basal de herramientas en cada turno, lo cual se compensa con su capacidad de presupuestar y reducir lecturas masivas de código.
