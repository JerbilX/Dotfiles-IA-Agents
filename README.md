# Dotfiles-IA-Agents

Repositorio centralizado y modular de configuración, estándares y directivas de comportamiento para agentes de Inteligencia Artificial.

## Arquitectura Modular

El proyecto organiza las reglas de agentes desacoplando la lógica transversal (principios, flujos de trabajo) de los entornos de ejecución específicos (runtimes):

```
Dotfiles-IA-Agents/
├── core/                                # Directivas agnósticas al runtime
│   ├── 01-objectivity.md                # Feedback crítico, cero complacencia y calidad técnica
│   ├── 02-git-lifecycle.md              # Ciclo de vida de Git, commit atómico y gates remotos
│   ├── 03-agent-rules-convention.md     # Convención canónica de AGENTS.md y estándar MADR
│   ├── 04-web-search-discipline.md      # Circuit breaker y disciplina de búsquedas web
│   ├── 05-anti-rigidity.md              # Degradación elegante y protocolo de fallback
│   ├── 06-engineering-standards.md      # Prevalencia de producción sobre tests e inmunidad normativa
│   ├── 07-anti-hallucination.md         # Estabilidad lógica, Stop & Ask y blindaje de planes
│   ├── 08-task-backlog-management.md    # Backlog en GitHub Projects/Issues y control de scope creep
│   └── 09-issue-driven-workflow.md      # Flujo guiado por issues, ramas y Pull Requests obligatorios
├── docs/                                # Documentación de ingeniería y arquitectura
│   └── adr/                             # Architectural Decision Records (estándar MADR)
│       ├── 0001-blindaje-de-sandbox-y-gestion-de-permisos.md
│       ├── 0002-cero-tolerancia-a-la-alucinacion-y-freno-obligatorio.md
│       ├── 0003-jerarquia-de-produccion-sobre-tests-e-inmunidad-normativa.md
│       ├── 0004-adopcion-del-estandar-madr-y-skill-adr-manager.md
│       ├── 0005-protocolo-de-desarrollo-guiado-por-issues-y-flujo-de-pull-requests.md
│       ├── 0006-desacoplamiento-de-directivas-y-configuracion-de-runtimes.md
│       ├── 0007-esquema-de-validacion-y-desacoplamiento-de-binarios-en-runtimes.md
│       ├── 0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md
│       ├── 0009-estandarizacion-y-gestion-modular-de-servidores-mcp.md
│       ├── 0010-politica-transversal-de-limpieza-y-ciclo-de-vida-de-ramas.md
│       ├── 0011-ratificacion-de-bypass-en-git-y-gh-por-restricciones-del-sandbox.md
│       ├── 0012-optimizacion-de-latencia-y-eliminacion-de-friccion-operativa.md
│       ├── 0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md
│       ├── 0014-consolidacion-del-catalogo-de-skills-y-deprecacion-de-agy-skills.md
│       ├── 0015-composicion-y-especializacion-de-directivas-por-runtime.md
│       ├── 0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md
│       ├── 0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md
│       ├── 0018-arquitectura-multi-runtime-y-pipeline-desacoplado.md
│       ├── 0019-skill-de-aprendizaje-autonomo-basado-en-decisiones-pasadas.md
│       └── 0020-protocolo-de-rollback-y-subcomando-de-restauracion.md
├── runtimes/                            # Configuraciones y adaptadores por entorno
│   ├── schema/                          # Esquemas JSON canónicos de validación
│   │   ├── runtime-config.schema.json   # JSON Schema para manifiestos de runtime
│   │   └── mcp-server.schema.json       # JSON Schema para módulos de servidores MCP
│   ├── antigravity/
│   │   ├── rules/                       # Especializaciones normativas del runtime
│   │   │   └── 01-sandbox.md            # Restricciones de sandbox y permisos
│   │   ├── mcp/                         # Catálogo modular de servidores MCP
│   │   │   └── eso-mcp-server.json      # Módulo MCP con transporte Stdio
│   │   └── config.json                  # Manifiesto estructurado (skills, binaries, mcp_servers, target)
│   └── claude/
│       ├── rules/                       # Reglas locales específicas de Claude Code
│       ├── mcp/                         # Catálogo modular de servidores MCP para Claude
│       └── config.json                  # Manifiesto de Claude Code (target: ~/.claude/CLAUDE.md)
├── skills/                              # Catálogo canónico y autocontenido de skills para agentes
│   ├── adr-manager/                     # Gestión de Architecture Decision Records (MADR)
│   ├── autonomous-learning/             # Aprendizaje autónomo y consulta de precedentes arquitectónicos
│   ├── eso-addon-development/           # Estándares y utilidades para addons de ESO
│   └── issue-driven-workflow/           # Orquestación de desarrollo guiado por issues y PRs
├── dist/                                # Artefactos compilados listos para distribución
│   ├── antigravity/
│   │   ├── AGENTS.md                    # Versión consolidada de directivas de prompt
│   │   └── mcp_config.json              # Configuración MCP con macros resueltas
│   └── claude/
│       ├── AGENTS.md                    # Versión consolidada de directivas para Claude
│       └── mcp_config.json              # Configuración MCP compilada para Claude
├── .gitignore                           # Exclusión de temporales (*.bak, *.tmp, .commit_msg)
├── build.sh                             # Script de compilación y orquestación multi-runtime
└── README.md                            # Documentación y referencia de comandos
```

## Puesta en Marcha en Nueva Máquina (Quickstart / Bootstrap)

Para configurar todo el entorno de directivas, skills, binarios y servidores MCP en una máquina nueva o tras un formateo:

### 1. Precondiciones
- **Bash** y utilidades estándar POSIX (`ln`, `mkdir`, `date`, `wc`).
- **Python 3** (módulo estándar `json`, sin dependencias adicionales) o `jq`.
- **Git** y **GitHub CLI (`gh`)** configurados.
- Asegurar que `~/.local/bin` esté en tu `$PATH` (añadir a `~/.bashrc` o `~/.zshrc` si aún no está presente):
  ```bash
  export PATH="${HOME}/.local/bin:${PATH}"
  ```

### 2. Clonado del Repositorio
El repositorio es 100% autocontenido y aloja directivas, configuraciones de runtime y el catálogo canónico de skills:

```bash
mkdir -p ~/Proyectos-IA-V3 && cd ~/Proyectos-IA-V3
git clone https://github.com/JerbilX/Dotfiles-IA-Agents.git
```

### 3. Aprovisionamiento Automático E2E
Ingresa al repositorio y ejecuta el orquestador principal:

```bash
cd Dotfiles-IA-Agents
./build.sh
```

Este comando ejecuta el flujo completo (`all`): compila `AGENTS.md` y `mcp_config.json`, respalda archivos previos con `.bak.<timestamp>`, crea los enlaces simbólicos atómicos (`AGENTS.md`, `mcp_config.json`, `~/.gemini/config/skills/`, y binarios en `~/.local/bin/`), y corre la suite de auditoría estática.

### 4. Verificación de Salud
Si en cualquier momento deseas auditar la integridad de la configuración sin alterar archivos ni enlaces:

```bash
./build.sh check
```

## Flujo de Trabajo y Comandos (`build.sh`)

El script `build.sh` permite compilar directivas modulares, aprovisionar dependencias de runtime, compilar la configuración de servidores MCP y enlazar los artefactos con las ubicaciones canónicas del sistema anfitrión declaradas en `target` (ej. `~/.gemini/config/` para Antigravity, `~/.claude/` para Claude Code, etc.).

Todos los subcomandos aceptan opcionalmente el parámetro `[runtime]` (`antigravity`, `claude`, etc.). Si se omite o se especifica `all`, la operación se ejecuta de forma unificada sobre todos los runtimes configurados en `runtimes/`:

### 1. Compilación (`build`)
Concatena en orden determinista los archivos de `core/*.md` y `runtimes/<runtime>/rules/*.md` en `dist/<runtime>/AGENTS.md` (emitiendo telemetría de palabras y tokens) y compila las definiciones activas de servidores MCP en `dist/<runtime>/mcp_config.json`:
```bash
./build.sh build            # Compila todos los runtimes
./build.sh build antigravity # Compila exclusivamente Antigravity
./build.sh build claude      # Compila exclusivamente Claude Code
```

### 2. Enlace Simbólico (`link`)
Verifica la existencia del directorio destino declarado en `target.config_dir`, respalda de forma segura cualquier archivo o symlink preexistente con timestamp (`.bak.YYYYMMDD_HHMMSS`), y crea de manera atómica los enlaces simbólicos `ln -sfn` hacia las rutas canónicas del host:
```bash
./build.sh link             # Enlaza todos los runtimes
./build.sh link antigravity # Enlaza exclusivamente Antigravity (~/.gemini/config/)
./build.sh link claude      # Enlaza exclusivamente Claude Code (~/.claude/)
```

### 3. Aprovisionamiento de Skills y Binarios (`skills`)
Valida `runtimes/<runtime>/config.json` contra `runtimes/schema/runtime-config.schema.json` (fail-fast), purga symlinks obsoletos, aprovisiona los skills habilitados en la ruta declarada en `target.skills_dir` (si aplica), y expone sus scripts ejecutables en `~/.local/bin/` aplicando alias declarativos si se definen en `binaries`:
```bash
./build.sh skills             # Expone skills y binarios de todos los runtimes
./build.sh skills antigravity # Expone skills y binarios (~/.local/bin/) para Antigravity
```
> **Nota de Bootstrap y Mantenimiento:** Siempre que se incorpore un nuevo skill que provea herramientas CLI (como `agent-audit` en `conversation-audit` o `eso-build` en `eso-addon-development`), se debe ejecutar `./build.sh skills` en el anfitrión para garantizar que los enlaces simbólicos se creen en `~/.local/bin/` y las herramientas estén inmediatamente disponibles en el `$PATH`.


### 4. Servidores MCP (`mcp`)
Subcomando dedicado para compilar, respaldar y enlazar exclusivamente la configuración de servidores MCP de uno o todos los runtimes:
```bash
./build.sh mcp
./build.sh mcp antigravity
```

### 5. Inspección (`status`)
Verifica el estado de los enlaces simbólicos en las rutas destino de cada runtime, reportando tipo, archivo de destino y validez de cada enlace:
```bash
./build.sh status
./build.sh status antigravity
```

### 6. Restauración de Emergencia (`rollback`)
Inspecciona de forma determinista el directorio destino (`target.config_dir`) y revierte atómicamente el estado del runtime al último respaldo disponible (`.bak.<timestamp>`) generado durante el despliegue previo (`link` o `mcp`), tanto para directivas (`AGENTS.md`) como para servidores MCP (`mcp_config.json`). Si no existen respaldos previos, retorna código de salida `1`:
```bash
./build.sh rollback             # Restaura todos los runtimes que posean respaldos
./build.sh rollback antigravity # Restaura exclusivamente Antigravity (~/.gemini/config/)
./build.sh rollback claude      # Restaura exclusivamente Claude Code (~/.claude/)
```

### 7. Verificación Estática (`check`)
Ejecuta una auditoría de integridad estática y de **solo lectura** (read-only), ideal para pre-commit o CI/CD. Valida esquema y sintaxis de `config.json` y de los módulos MCP activos, existencia de skills y `SKILL.md` en disco, presencia y permisos de binarios y comandos MCP, ausencia de colisiones de prefijos numéricos o títulos H1, integridad de symlinks en el sistema, presupuesto de contexto y disponibilidad de archivos de respaldo para rollback en cada runtime:
```bash
./build.sh check            # Audita todos los runtimes configurados
./build.sh check antigravity # Audita exclusivamente Antigravity
./build.sh check claude      # Audita exclusivamente Claude Code
```

### 8. Flujo Completo (`all` / por defecto)
Ejecuta secuencialmente `build`, `link`, `skills`, `status` y la verificación final `check`:
```bash
./build.sh                  # Flujo completo para todos los runtimes
./build.sh all antigravity  # Flujo completo exclusivamente para Antigravity
```

## Extensibilidad: Cómo Agregar un Nuevo Runtime

Agregar un nuevo agente de IA al ecosistema es 100% declarativo y no requiere modificar `build.sh`:
1. Crear el directorio `runtimes/<nuevo-runtime>/`.
2. Crear `runtimes/<nuevo-runtime>/config.json` cumpliendo `runtimes/schema/runtime-config.schema.json`:
   ```json
   {
     "$schema": "../schema/runtime-config.schema.json",
     "skills": ["adr-manager", "issue-driven-workflow"],
     "binaries": {},
     "mcp_servers": [],
     "target": {
       "config_dir": "${HOME}/.mi-agente",
       "prompt_filename": "AGENTS.md",
       "mcp_filename": "mcp_config.json",
       "skills_dir": "${HOME}/.mi-agente/skills"
     }
   }
   ```
3. Opcionalmente añadir reglas locales en `runtimes/<nuevo-runtime>/rules/` o módulos MCP en `runtimes/<nuevo-runtime>/mcp/`.
4. Ejecutar `./build.sh check` para validar y `./build.sh build` para compilar.

## Convenciones Canónicas

- **Compilación Centralizada y Desacoplada:** Las directivas globales se compilan deterministamente a partir de `core/` y las especializaciones de runtime (`runtimes/<runtime>/rules/`) hacia los destinos declarados en cada manifiesto `config.json`.
- **Prohibición de Archivos Huérfanos o No-Estándar:** Prohibido crear o depender de directivas dispersas como `GEMINI.md`. Todo ajuste de comportamiento debe canalizarse a través de los módulos de este repositorio y compilarse con `build.sh`.
- **Gestión de Decisiones Arquitectónicas (MADR):** Toda decisión técnica, cambio de diseño o evaluación de tradeoffs se gestiona exclusivamente a través de Architectural Decision Records en `docs/adr/` mediante el estándar MADR y el skill `adr-manager`. Se prohíben bitácoras informales o archivos `HISTORIAL.md`.
- **Desarrollo Guiado por Issues y Flujo de Pull Requests:** Los agentes operan bajo demanda a través de GitHub Issues, aíslan cambios en ramas `feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`, previenen el scope creep y entregan su trabajo obligatoriamente vía Pull Request (`gh pr create`) con gate de revisión humana por el PM. Queda vetado el push directo a `main`.
