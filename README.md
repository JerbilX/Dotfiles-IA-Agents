# Dotfiles-IA-Agents

Repositorio centralizado y modular de configuración, estándares y directivas de comportamiento para agentes de Inteligencia Artificial.

## Arquitectura Modular

El proyecto organiza las reglas de agentes desacoplando la lógica transversal (principios, flujos de trabajo) de los entornos de ejecución específicos (runtimes):

```
Dotfiles-IA-Agents/
├── core/                                # Directivas agnósticas al runtime
│   ├── 01-objectivity.md                # Feedback crítico, cero complacencia y calidad técnica
│   ├── 02-git-lifecycle.md              # Ciclo de vida de Git, commit atómico y gates remotos
│   └── 03-agent-rules-convention.md     # Convención canónica de AGENTS.md (prohibición de GEMINI.md)
├── runtimes/                            # Configuraciones y restricciones por entorno
│   └── antigravity/
│       └── 01-sandbox.md                # Restricciones de sandbox, I/O nativo y workspace
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
