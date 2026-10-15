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
│       └── 0005-protocolo-de-desarrollo-guiado-por-issues-y-flujo-de-pull-requests.md
├── runtimes/                            # Configuraciones y restricciones por entorno
│   └── antigravity/
│       ├── 01-sandbox.md                # Restricciones de sandbox, I/O nativo y comandos de red
│       └── config.md                    # Habilitación y configuración de skills de Antigravity
├── dist/                                # Artefactos compilados listos para distribución
│   └── antigravity/
│       └── AGENTS.md                    # Versión consolidada generada automáticamente
├── .gitignore                           # Exclusión de temporales (*.bak, *.tmp, .commit_msg)
├── build.sh                             # Script de compilación y gestión de enlaces simbólicos
└── README.md                            # Documentación y referencia de comandos
```

## Flujo de Trabajo y Comandos (`build.sh`)

El script `build.sh` permite compilar las directivas modulares y enlazar el resultado compilado con la ubicación canónica del sistema (`~/.gemini/config/AGENTS.md`):

### 1. Compilación (`build`)
Concatena en orden determinista los archivos de `core/*.md` y `runtimes/antigravity/*.md` en `dist/antigravity/AGENTS.md`, insertando un encabezado de autogeneración:
```bash
./build.sh build
```

### 2. Enlace Simbólico (`link`)
Verifica la existencia del directorio destino `~/.gemini/config/`, respalda de forma segura cualquier archivo o symlink preexistente con timestamp (`.bak.YYYYMMDD_HHMMSS`), y crea de manera atómica el enlace simbólico `ln -sfn`:
```bash
./build.sh link
```

### 3. Inspección (`status`)
Verifica el estado del symlink en `~/.gemini/config/AGENTS.md` reportando tipo, archivo de destino y validez del enlace:
```bash
./build.sh status
```

### 4. Flujo Completo (`all` / por defecto)
Ejecuta secuencialmente `build`, `link` y `status`:
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
