---
status: accepted
date: 2026-10-17
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
---

# 0018 - Arquitectura Multi-Runtime y Pipeline de Compilación Desacoplado

## Contexto y Planteamiento del Problema

Históricamente, el pipeline de compilación y orquestación en `build.sh` se encontraba acoplado exclusivamente al entorno de Antigravity:
1. Variables globales con rutas cableadas (`dist/antigravity/`, `~/.gemini/config/`, `AGENTS.md`, `mcp_config.json`, `~/.gemini/config/skills`).
2. Comandos operativos (`build`, `link`, `skills`, `mcp`, `status`, `check`, `all`) sin parametrización para seleccionar entornos alternativos.
3. El esquema canónico `runtime-config.schema.json` carecía de una sección declarativa para especificar las rutas destino en el sistema anfitrión, obligando a codificar supuestos en Bash.

A medida que el ecosistema de desarrollo incorpora otros agentes de IA (como Claude Code, Codex, Cursor o agentes autónomos headless), mantener un pipeline acoplado a un único runtime obligaría a bifurcar repositorios, duplicar scripts de compilación o introducir lógica condicional dispersa.

Se requiere desacoplar el pipeline de `build.sh` para soportar de manera modular, extensible e idempotente la coexistencia de múltiples runtimes, compartiendo la base normativa universal de `core/` y permitiendo compilación, enlace, aprovisionamiento de skills y auditoría estática tanto de forma selectiva (por runtime) como unificada (lote).

## Impulsores de la Decisión (Decision Drivers)

* **Cero Duplicación de Directivas Base (DRY):** Las normas universales de ingeniería, objetividad, disciplina web y flujos git en `core/` deben compilarse de forma compartida hacia cada runtime sin clonar texto.
* **Principio de Responsabilidad Única y Declaratividad (SRP):** El orquestador `build.sh` debe ser un motor genérico. Las rutas canónicas del anfitrión (`config_dir`, `prompt_filename`, `mcp_filename`, `skills_dir`) deben declararse en los manifiestos `config.json` y validarse por esquema formal.
* **Extensibilidad Abierta (Open/Closed Principle):** Añadir un nuevo runtime al ecosistema debe requerir únicamente crear su directorio `runtimes/<nombre>/` con su respectivo `config.json`, sin necesidad de modificar el código ejecutable de `build.sh`.
* **Ergonomía CLI Parametrizada e Idempotente:** Soportar de forma uniforme la sintaxis `./build.sh <comando> [runtime]` para permitir flujos selectivos o masivos (`all`).
* **Preservación del Sandbox Hermético:** Las operaciones de lectura, validación estática y compilación operan estrictamente dentro del workspace (`BypassSandbox: false`), dejando los enlaces hacia rutas externas del anfitrión como responsabilidad exclusiva del usuario o bootstrap.
* **Auditoría Estática Integral:** El subcomando `check` debe evaluar la matriz completa de esquemas, existencia de recursos, colisiones y presupuestos de contexto de todos los runtimes configurados.

## Opciones Consideradas

* **Opción 1: Scripts de Compilación Independientes por Runtime (`build_antigravity.sh`, `build_claude.sh`).** Crear un script dedicado para cada agente.
* **Opción 2: Pipeline Monolítico con Condicionales Hardcodeados en Bash.** Mantener un único `build.sh` pero incorporar bloques `case "${runtime}" in antigravity) ... ;; claude) ... ;;` para resolver rutas y archivos de destino.
* **Opción 3: Pipeline Desacoplado con Descubrimiento Dinámico de Runtimes y Mapeo Declarativo en `config.json`.** Motor genérico en `build.sh` con descubrimiento automático de directorios en `runtimes/`, extensión del esquema `runtime-config.schema.json` con el bloque opcional `target`, y parametrización CLI selectiva/unificada.

## Decisión Adoptada

Opción elegida: **Opción 3 ("Pipeline Desacoplado con Descubrimiento Dinámico y Mapeo Declarativo")**, estructurada en los siguientes pilares:

### 1. Extensión del Contrato de Datos (`runtime-config.schema.json`)
Se incorpora el objeto opcional `target` dentro del JSON Schema Draft 2020-12, permitiendo que cada runtime defina formalmente sus rutas de despliegue en el host:
* `config_dir`: Directorio base en el anfitrión (ej. `${HOME}/.gemini/config` o `${HOME}/.claude`).
* `prompt_filename`: Nombre del archivo de directivas en destino (ej. `AGENTS.md` o `CLAUDE.md`).
* `mcp_filename`: Nombre del archivo de configuración MCP en destino (default `mcp_config.json`).
* `skills_dir`: Directorio para enlaces simbólicos de skills (ej. `${HOME}/.gemini/config/skills`).

### 2. Descubrimiento Dinámico de Runtimes en `build.sh`
Se implementa `get_available_runtimes()`, el cual escanea recursivamente `runtimes/*`, excluye metadatos (`schema`) y reconoce automáticamente como runtime válido cualquier carpeta que contenga `config.json`. La función `resolve_target_runtimes "$1"` valida argumentos específicos o retorna el conjunto total ante invocaciones unificadas.

### 3. Parametrización CLI de Subcomandos
Todos los subcomandos de `build.sh` adoptan la firma `<comando> [runtime]`:
* `./build.sh build [runtime]`: Compila `dist/<runtime>/AGENTS.md` (con telemetría de palabras y tokens) y `dist/<runtime>/mcp_config.json`.
* `./build.sh link [runtime]`: Enlaza hacia las rutas declaradas en `target`, respaldando archivos preexistentes mediante `.bak.<timestamp>`.
* `./build.sh skills [runtime]`: Provisiona enlaces de skills en `skills_dir` y unifica scripts ejecutables en `~/.local/bin/`.
* `./build.sh mcp [runtime]`: Compila y enlaza exclusivamente la configuración de servidores MCP del runtime.
* `./build.sh status [runtime]`: Reporta el estado de validez de symlinks por runtime.
* `./build.sh check [runtime]`: Ejecuta la matriz de auditoría estática (read-only) evaluando esquemas, scripts, MCPs, colisiones de prefijos, unicidad de H1 y presupuestos de palabras.
* `./build.sh all [runtime]`: Ejecuta el flujo E2E completo.

### 4. Integración del Runtime de Referencia (`claude`)
Se crea `runtimes/claude/` con `config.json`, directivas locales (`rules/`) y catálogo MCP (`mcp/`), configurado para generar `CLAUDE.md` en `~/.claude/`, validando la arquitectura multi-runtime en paralelo a `antigravity`.

## Consecuencias

### Positivas
* **Modularidad Completa:** Soporte para cualquier agente de IA sin bifurcar repositorios ni duplicar código base.
* **Cero Acoplamiento en Bash:** `build.sh` no contiene rutas fijas de herramientas específicas ni listas cerradas de runtimes.
* **Validación Temprana (Fail-Fast):** Argumentos de runtime inválidos abortan inmediatamente con código de salida `1` y mensaje explícito.
* **Trazabilidad y Presupuesto de Contexto:** Cada runtime mide y audita de forma aislada su volumen de tokens y palabras frente al umbral de 4.000 palabras de ADR-0008.

### Negativas / Trade-offs
* **Mantenimiento de Manifiestos:** Cada nuevo runtime requiere mantener su propio archivo `config.json` alineado al esquema canónico.

## Pros y Contras de las Opciones

#### Opción 1: Scripts Independientes por Runtime
* **Pro:** Aislamiento absoluto por archivo.
* **Contra:** Duplicación masiva de lógica en Bash (parsers, validadores, symlinks), alto riesgo de desincronización y deuda técnica severa.

#### Opción 2: Pipeline Monolítico Hardcodeado
* **Pro:** Un único script.
* **Contra:** Viola el principio de responsabilidad única (repite el problema erradicado en ADR-0007), obliga a editar `build.sh` ante cada nueva herramienta y genera rigidez operativa.

#### Opción 3: Pipeline Desacoplado y Declarativo
* **Pro:** Máxima cohesión, extensibilidad dinámica, validación por esquemas y código genérico limpio.
* **Contra:** Requiere definir formalmente el bloque `target` en los manifiestos de runtime.
