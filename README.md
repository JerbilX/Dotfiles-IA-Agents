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
│       └── 0009-estandarizacion-y-gestion-modular-de-servidores-mcp.md
├── runtimes/                            # Configuraciones y restricciones por entorno
│   ├── schema/                          # Esquemas JSON canónicos de validación
│   │   ├── runtime-config.schema.json   # JSON Schema para manifiestos de runtime
│   │   └── mcp-server.schema.json       # JSON Schema para módulos de servidores MCP
│   └── antigravity/
│       ├── rules/                       # Directivas y restricciones para el System Prompt
│       │   └── 01-sandbox.md            # Restricciones de sandbox, I/O nativo y comandos de red
│       ├── mcp/                         # Catálogo modular de servidores MCP
│       │   └── eso-mcp-server.json      # Definición de servidor MCP con transporte Stdio
│       └── config.json                  # Manifiesto estructurado (skills, binaries, mcp_servers)
├── skills/                              # Catálogo canónico de skills para agentes
│   └── issue-driven-workflow/           # Orquestación de desarrollo guiado por issues y PRs
│       └── SKILL.md
├── dist/                                # Artefactos compilados listos para distribución
│   └── antigravity/
│       ├── AGENTS.md                    # Versión consolidada de directivas de prompt
│       └── mcp_config.json              # Configuración MCP consolidada con macros resueltas
├── .gitignore                           # Exclusión de temporales (*.bak, *.tmp, .commit_msg)
├── build.sh                             # Script de compilación y gestión de enlaces simbólicos
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

### 2. Clonado de Repositorios Hermanos
El orquestador espera por defecto que los repositorios de Dotfiles y Skills residan en el mismo directorio de proyectos (ej. `~/Proyectos-IA-V3/`):

```bash
mkdir -p ~/Proyectos-IA-V3 && cd ~/Proyectos-IA-V3
git clone https://github.com/JerbilX/Dotfiles-IA-Agents.git
git clone https://github.com/JerbilX/AGY-Skills.git
```

*(Nota: si utilizas otra ruta para los skills, puedes exportar `AGY_SKILLS_PATH=/ruta/a/AGY-Skills/skills`).*

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

El script `build.sh` permite compilar las directivas modulares, aprovisionar dependencias de runtime, compilar la configuración de servidores MCP y enlazar el resultado compilado con las ubicaciones canónicas del sistema (`~/.gemini/config/AGENTS.md` y `~/.gemini/config/mcp_config.json`):

### 1. Compilación (`build`)
Concatena en orden determinista los archivos de `core/*.md` y `runtimes/antigravity/rules/*.md` en `dist/antigravity/AGENTS.md` (emitiendo telemetría de contexto y alertas de presupuesto) y compila las definiciones activas de servidores MCP en `dist/antigravity/mcp_config.json` resolviendo macros de rutas (`$HOME`):
```bash
./build.sh build
```

### 2. Enlace Simbólico (`link`)
Verifica la existencia del directorio destino `~/.gemini/config/`, respalda de forma segura cualquier archivo o symlink preexistente con timestamp (`.bak.YYYYMMDD_HHMMSS`), y crea de manera atómica los enlaces simbólicos `ln -sfn` tanto para `AGENTS.md` como para `mcp_config.json`:
```bash
./build.sh link
```

### 3. Aprovisionamiento de Skills (`skills`)
Valida `runtimes/antigravity/config.json` contra `runtimes/schema/runtime-config.schema.json` (fail-fast), purga symlinks obsoletos, aprovisiona los skills habilitados en `~/.gemini/config/skills/`, y expone sus scripts ejecutables en `~/.local/bin/` aplicando alias declarativos si se definen en `binaries`:
```bash
./build.sh skills
```

### 4. Servidores MCP (`mcp`)
Subcomando dedicado para compilar, respaldar, enlazar y auditar exclusivamente la configuración de servidores MCP hacia `~/.gemini/config/mcp_config.json`:
```bash
./build.sh mcp
```

### 5. Inspección (`status`)
Verifica el estado de los enlaces simbólicos en `~/.gemini/config/AGENTS.md` y `~/.gemini/config/mcp_config.json`, reportando tipo, archivo de destino y validez de cada enlace:
```bash
./build.sh status
```

### 6. Verificación Estática (`check`)
Ejecuta una auditoría de integridad estática y de **solo lectura** (read-only), ideal para pre-commit o CI/CD. Valida esquema y sintaxis de `config.json` y de los módulos MCP activos, existencia de skills y `SKILL.md` en disco, presencia y permisos de binarios y comandos MCP, ausencia de colisiones de prefijos numéricos o títulos H1, integridad de symlinks en el sistema y presupuesto de contexto:
```bash
./build.sh check
```

### 7. Flujo Completo (`all` / por defecto)
Ejecuta secuencialmente `build`, `link`, `skills`, `status` y la verificación final `check`:
```bash
./build.sh
# o
./build.sh all
```

## Convenciones Canónicas

- **Fuente Única de Verdad:** Las directivas globales residen exclusivamente en `~/.gemini/config/AGENTS.md`. No se admiten configuraciones divergentes sin versionar.
- **Prohibición de `GEMINI.md`:** Está estrictamente prohibido utilizar o crear archivos `GEMINI.md`. Cualquier ajuste debe efectuarse sobre los módulos de este repositorio y recompilarse.
- **Gestión de Decisiones Arquitectónicas (MADR):** Toda decisión técnica, cambio de diseño o evaluación de tradeoffs se gestiona exclusivamente a través de Architectural Decision Records en `docs/adr/` mediante el estándar MADR y el skill `adr-manager`. Se prohíben bitácoras informales o archivos `HISTORIAL.md`.
- **Desarrollo Guiado por Issues y Flujo de Pull Requests:** Los agentes operan bajo demanda a través de GitHub Issues, aíslan cambios en ramas `feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`, previenen el scope creep y entregan su trabajo obligatoriamente vía Pull Request (`gh pr create`) con gate de revisión humana por el PM. Queda vetado el push directo a `main`.
