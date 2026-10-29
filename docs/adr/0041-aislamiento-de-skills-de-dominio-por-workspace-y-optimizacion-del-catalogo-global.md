---
status: accepted
date: 2026-10-29
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: ["0039-aislamiento-de-servidores-mcp-y-skills-de-dominio-por-workspace.md"]
superseded-by: []
---

# 0041 - Aislamiento de Skills de Dominio por Workspace y Optimización del Catálogo Global

## Contexto y Planteamiento del Problema

Históricamente, el aprovisionamiento global de dotfiles (`~/.gemini/config/skills/` y su equivalente en otros runtimes) exponía todas las skills del repositorio indiscriminadamente ([ADR-0014](0014-consolidacion-del-catalogo-de-skills-y-deprecacion-de-agy-skills.md)). Aunque en [ADR-0039](0039-aislamiento-de-servidores-mcp-y-skills-de-dominio-por-workspace.md) se logró aislar los servidores MCP especializados (`eso-mcp-server`) a nivel de workspace para evitar la inyección ciega de ~2.500 tokens por turno, se optó temporalmente por conservar el skill `eso-addon-development` en el catálogo global bajo la premisa de Divulgación Progresiva (Progressive Disclosure).

Sin embargo, en la práctica, el aprovisionamiento global masivo acumula un catálogo de hasta 14 skills (entre basales, plugins y de nicho). Al inicializar cada conversación, los metadatos y esquemas de descubrimiento consumen una cuota significativa de tokens basales (~8.000 a 12.000 tokens en el prompt inicial del sistema), penalizando el presupuesto semanal de tokens en todos los proyectos de tooling, infraestructura y desarrollo general donde las herramientas de nicho (ej. desarrollo de addons para Elder Scrolls Online o plugins multimedia específicos) carecen por completo de utilidad.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación Estricta de Contexto y Tokens:** Reducir la huella basal del System Prompt eliminando del catálogo global cualquier skill que no sea universal y transversal.
* **Taxonomía Canónica Bipartita de Skills:**
  - **Skills Globales Basales:** Herramientas universales de observabilidad, gobierno y flujo de trabajo (`issue-driven-workflow`, `adr-manager`, `project-documentation`, `conversation-audit`, `autonomous-learning`).
  - **Skills de Dominio Especializado:** Herramientas acotadas a un ecosistema técnico o framework específico (ej. `eso-addon-development`), confinadas exclusivamente a los workspaces pertinentes.
* **Activación On-Demand sin Fricción (`agent-module`):** Habilitar una herramienta CLI en `$PATH` (`~/.local/bin/agent-module`) que permita activar o desactivar módulos en el workspace actual (`$PWD`) mediante un pedido explícito en el chat o desde terminal, sin requerir invocaciones complejas de `build.sh` con rutas externas.
* **Detección Proactiva con Confirmación:** Permitir al agente detectar archivos indicadores de dominio (ej. `## APIVersion:` en addons de ESO) y ofrecer proactivamente la activación del módulo mediante un gate de confirmación humana.
* **Auditoría Estática de Pureza Global:** Incorporar en `./build.sh check` una verificación de pureza que impida que skills o binarios de dominio declarados en `modules/*/module.json` se filtren en los manifiestos globales `runtimes/*/config.json`.

## Opciones Consideradas

* **Opción 1: Mantener Skills de Dominio Globales (Status Quo post ADR-0039).**
  * Conservar `eso-addon-development` en el perfil global de Antigravity.
  * *Descarte:* Desperdicio recurrente de tokens basales en proyectos ajenos a ESO y riesgo de colisiones conceptuales en repositorios generales.
* **Opción 2: Aprovisionamiento Exclusivo con Rutas Absolutas en `build.sh workspace`.**
  * Exigir al usuario o agente situarse en dotfiles y ejecutar `./build.sh workspace eso /ruta/absoluta`.
  * *Descarte:* Fricción operativa severa; vulnera el principio de confinamiento del workspace y dificulta la activación conversacional.
* **Opción 3: Taxonomía Bipartita, Aislamiento por Workspace y Activación On-Demand con `agent-module` (Elegida).**
  * Purgar las skills de dominio de los perfiles globales (`runtimes/*/config.json`).
  * Confinar skills de dominio a `modules/<module>/` y `skills/<skill>/`.
  * Habilitar la herramienta `agent-module` en `$PATH` para aprovisionar y podar módulos in-place en `$PWD`.

## Decisión Adoptada

Se adopta la **Opción 3**, estructurada en los siguientes componentes:

1. **Purificación de Manifiestos Globales (`runtimes/*/config.json`):**
   - Se elimina `eso-addon-development` de `skills` en `runtimes/antigravity/config.json`.
   - Se elimina el alias `"build_release": "eso-build"` de `binaries` en `runtimes/antigravity/config.json`.
   - Se expone el CLI `"agent-module": "agent-module"` en `binaries` de los runtimes.
   - Se restringen los manifiestos globales a las skills basales transversales.

2. **Tooling de Activación On-Demand (`agent-module` en `$PATH`):**
   - Provisto por el skill basal `issue-driven-workflow` en `skills/issue-driven-workflow/bin/agent-module`.
   - Subcomandos:
     - `agent-module enable <modulo>`: Enlaza skills locales en `.agents/skills/`, `.gemini/skills/` y `.claude/skills/`, y copia/enlaza plugins y `.mcp.json`.
     - `agent-module disable <modulo>`: Poda las skills y configuraciones de dominio del workspace.
     - `agent-module status`: Muestra los módulos activos en el workspace actual.
     - `agent-module list`: Lista los módulos disponibles en dotfiles.
   - `./build.sh workspace` se alinea para admitir `$PWD` por defecto si no se pasa la ruta de destino.

3. **Protocolo de Activación Asistida:**
   - Ante la petición explícita en chat (*"activa el módulo eso"*), el agente ejecuta autónomamente `agent-module enable eso`.
   - Si el agente detecta marcadores de dominio en un workspace no inicializado, formula un gate directo al usuario ofreciendo su activación.

4. **Verificación Estática de Pureza Global (`check_global_skills_purity`):**
   - Integrada en `./build.sh check`.
   - Audita de forma automatizada que ninguna skill ni binario listado en `modules/*/module.json` figure en `runtimes/*/config.json`.

5. **Sustitución Parcial de ADR-0039:**
   - Este ADR sustituye formalmente la cláusula de ADR-0039 que disponía la permanencia global de `eso-addon-development`, manteniendo intacto el aislamiento de servidores MCP acordado en dicho ADR.

## Consecuencias

### Positivas
* **Reducción Cuantificable de Huella Basal:** Erradicación de metadatos y schemas irrelevantes en proyectos de propósito general, reduciendo tokens del prompt inicial.
* **Activación In-Place sin Fricción:** El usuario o el agente pueden activar cualquier módulo directamente desde el workspace activo con un simple comando o pedido conversacional.
* **Hermeticidad y Reversibilidad:** Cada proyecto dispone exclusivamente de las herramientas pertinentes y puede deshabilitarlas con `agent-module disable`.
* **Escalabilidad Modular:** Nuevos módulos de dominio pueden crearse en `modules/` sin impactar los perfiles globales.

### Negativas / Trade-offs
* Al iniciar el desarrollo de un addon de ESO en un repo limpio, se requiere un turno de confirmación o comando inicial (`agent-module enable eso`) para andamiar el soporte local.
