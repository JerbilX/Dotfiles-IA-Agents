---
status: accepted
date: 2026-11-05
decision-makers: [Usuario, Claude]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0045 - Operación Multi-Runtime sin Fricción e Issues Cruzadas entre Repositorios

## Contexto y Planteamiento del Problema
Este repositorio es la fuente central de las directivas basales para todos los agentes y workspaces. El trabajo extenso se hace en Antigravity, y las mejoras técnicas en Claude Code (CLI y VS Code). Se detectaron estas fricciones:
* El router usa rutas relativas (`core/`, `skills/`) que Claude no resuelve fuera de este repo, y `~/.claude/core` podía no existir.
* La regla de confinamiento prohíbe leer rutas externas. Eso choca con leer las directivas globales y con crear issues en otros repositorios, aunque este repo afecte a todos.
* Claude Code no tiene permisos preconfigurados: cada `git`/`gh`/CLI propio pide confirmación.
* `dist/` versionado provoca conflictos entre ramas de distintos runtimes y exige reconstruir a mano después de cada merge.

## Impulsores de la Decisión (Decision Drivers)
* Una sola fuente de verdad para las directivas en todos los runtimes.
* Trazabilidad entre repositorios: cualquier workspace puede registrar una issue en el repo afectado.
* Mínima intervención manual después de cada merge.
* Mantener el presupuesto de 800 palabras del `AGENTS.md` compilado.

## Opciones Consideradas
* **Opción 1:** Generar un `CLAUDE.md` independiente con las directivas reescritas para Claude.
* **Opción 2:** Mantener el build único con una capa de runtime fina, excepciones explícitas al confinamiento y automatización local del build.
* **Opción 3:** Empaquetar las directivas como plugin de Claude Code para cubrir también Cowork y la web.

## Decisión Adoptada
Opción elegida: **"Opción 2"**.
* **Confinamiento:** dos excepciones explícitas. (a) Lectura de directivas y skills del directorio de configuración del runtime. (b) Creación de issues en cualquier repositorio del owner con `gh issue create -R <owner>/<repo>`, siempre con confirmación del usuario y sin leer archivos del repo destino. Se indexan en el tablero central compartido.
* **Runtime Claude:** la regla de runtime resuelve las rutas del router en `~/.claude/`. El circuit breaker queda como regla, sin hook, hasta resolver #239. Los permisos (`runtimes/claude/settings.json`) se combinan en `~/.claude/settings.json` durante `link` sin pisar las claves del usuario. Se combina en vez de enlazar porque Claude Code escribe en ese archivo.
* **`dist/`:** sale del control de versiones. Los hooks de git `post-merge` y `post-checkout` (`.githooks/`, activados con `core.hooksPath` en `link`) lo regeneran con `./build.sh build`.
* **Alcance:** Claude Code CLI y extensión de VS Code (comparten `~/.claude`). Cowork y la web quedan diferidos (Opción 3).

### Consecuencias
* **Positivas:** Mismas directivas en ambos runtimes sin duplicarlas, issues cruzadas trazables, sin conflictos en `dist/` y sin rebuild manual tras un merge.
* **Negativas / Trade-offs:** Un clon nuevo requiere `./build.sh all` para generar `dist/` y activar los hooks. El symlink `~/.claude/mcp_config.json` sigue existiendo aunque Claude Code no lo lea (inocuo, se difiere su retiro). Las excepciones al confinamiento dependen del criterio del agente para no leer el repo destino.
