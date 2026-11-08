---
status: accepted
date: 2026-11-08
decision-makers: [JerbilX, Antigravity]
consulted: []
informed: []
references:
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
---

# 0050 - Vocabulario Neutral de Herramientas en el Prompt Basal Universal

## Contexto y Problemática

En la arquitectura previa, las directivas basales compiladas en `core/00-router.md` nombraban explícitamente herramientas nativas de Antigravity (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`, `find_by_name`). Esto generó dos problemas principales identificados en ADR-0048 (§6.4) e Issue #288:
1. **Acoplamiento de runtime e inflación de contexto:** Runtimes como Claude Code requerían una regla específica (`CLAUDE_TOOL_EQUIVALENCES` en `runtimes/claude/rules/01-claude-tools.md`) de 53 palabras únicamente para mapear herramientas ajenas hacia sus propias primitivas (`Read`, `Grep`, `Glob`, `Write`, `Edit`, `Bash`).
2. **Fragilidad por desincronización de herramientas:** Los nombres fijos de herramientas en el prompt inducían a fallos operativos cuando el entorno no exponía una herramienta particular (por ejemplo, en sesiones donde la herramienta `Grep` no estaba disponible en Claude Code).

## Opciones Consideradas

* **Opción 1: Vocabulario neutral funcional.** El núcleo universal (`core/`) prescinde de nombres propios de herramientas y se formula mediante verbos y capacidades semánticas ("herramientas nativas de archivos (escritura, edición, lectura paginada, búsqueda)", "delimitación de rango o paginado", "localizar por búsqueda de contenido").
* **Opción 2: Reemplazo en compilación mediante plantillas.** El núcleo introduce placeholders (`{{tool_read}}`, `{{tool_search}}`, ...) que el compilador (`lib/build_core.sh`) resuelve a partir de un mapa declarado en `runtimes/<r>/config.json`.

## Decisión Adoptada

Se adopta la **Opción 1 (Vocabulario neutral)**:
1. **Neutralidad en `core/00-router.md`:** Se eliminan todas las menciones a identificadores de herramientas específicas en las reglas de I/O de archivos (`ENV_NATIVE_FILE_API`) y lectura paginada / circuit breaker (`ENV_PAGED_READ_CIRCUIT_BREAKER`).
2. **Eliminación del bloque de equivalencias:** Se retira completamente la regla `CLAUDE_TOOL_EQUIVALENCES` de `runtimes/claude/rules/01-claude-tools.md`, ahorrando 53 palabras netas en el prompt compilado de Claude Code.
3. **Control estático en `build.sh check`:** Se incorpora una verificación estática automatizada que falla si algún prompt compilado contiene placeholders sin resolver (`{{...}}`) o nombres cruzados de herramientas pertenecientes a otros entornos.

### Justificación Técnica
* La Opción 1 logra un desacoplamiento basal estricto sin añadir complejidad de plantillas en shell ni extender el esquema `runtime-config.schema.json`.
* Orienta a los modelos hacia la semántica requerida (paginación, atomicidad, preservación de contexto) permitiendo invocar las herramientas que su esquema nativo realmente exponga en cada sesión.

## Consecuencias

### Positivas
* **Reducción medible del presupuesto de contexto:** Disminución inmediata de ~53 palabras en Claude Code y reducción de palabras en el prompt basal universal.
* **Inmunidad ante cambios de interfaces de herramientas:** Desacopla las directivas de versiones o perfiles de runtime donde ciertas herramientas puedan estar ausentes o renombradas.
* **Garantía mecánica de pureza:** `./build.sh check` y la suite de pruebas unitarias impiden regresiones de nombres cruzados en artefactos compilados.

### Negativas / Trade-offs
* Las reglas del router basal describen la operación de forma funcional ("delimitación de rango o paginado") en vez de nombrar los argumentos exactos (`StartLine`/`EndLine` u `offset`/`limit`), delegando los parámetros específicos al esquema formal de herramientas de cada runtime y a sus respectivas especializaciones.
