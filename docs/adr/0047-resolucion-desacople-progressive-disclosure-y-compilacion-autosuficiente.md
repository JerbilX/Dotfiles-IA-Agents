---
status: accepted
date: 2026-11-05
decision-makers: [Usuario, Antigravity, Claude Code]
consulted: []
informed: []
supersedes: ["0038-arquitectura-de-progressive-disclosure-en-agents-md-y-modularizacion-de-reglas.md"]
superseded-by: []
---

# 0047 - Resolución del Desacople de Progressive Disclosure y Compilación Autosuficiente de Directivas Basales

## Contexto y Planteamiento del Problema

El ADR-0038 introdujo Progressive Disclosure para reducir el prompt basal: `lib/build_core.sh` compila solo `core/00-router.md` y `core/01-objectivity.md`, y el router ordenaba leer `core/02-…` a `core/10-…` antes de actuar. `./build.sh link` exponía esos módulos vía symlink (`~/.claude/core`, `~/.gemini/…/core`).

El mecanismo tiene un defecto de diseño, no de implementación puntual:

1. **Ruta ambigua:** `core/04-….md` es relativa a un archivo que vive fuera del workspace. En un repositorio cliente (ej. `ESORPQuestAddon`) se resuelve contra el workspace activo, donde no existe.
2. **Contradicción con el confinamiento:** Para leer el módulo, el agente debe acceder a una ruta fuera del workspace, que el mismo prompt prohíbe. Antigravity lo bloquea como violación de sandbox; Claude Code solo funcionó tras permitir la ruta real del symlink (#248, #250).
3. **Lectura voluntaria:** Cumplir la directiva dependía de que el agente decidiera leer el módulo. Si no lo leía, la regla no existía para él, sin señal de error.

Los runtimes ya ofrecen un mecanismo nativo de carga bajo demanda que no tiene estos defectos: las **skills** (nombre y descripción siempre en contexto, cuerpo cargado por el runtime desde cualquier workspace).

## Impulsores de la Decisión

* **Cero pérdida normativa:** Ninguna regla de `core/02`–`core/10` puede desaparecer; cada una debe quedar en el prompt compilado o en una skill.
* **Autosuficiencia del prompt basal:** Las conductas universales deben estar inyectadas, sin depender de archivos del workspace.
* **Confinamiento estricto:** Ninguna directiva puede inducir lecturas fuera del workspace.
* **Costo de contexto controlado:** El prompt viaja en cada turno; el límite debe ser explícito y justificado, no arbitrario.

## Opciones Consideradas

* **Opción 1: Rutas absolutas y permisos globales a `Dotfiles-IA-Agents/core/**`.** Descartada: contradice el confinamiento, acopla a una ruta fija y mantiene la lectura voluntaria.
* **Opción 2: Distribuir `core/` en cada proyecto (submódulo o symlink).** Descartada: contamina repositorios de terceros.
* **Opción 3: Comprimir todo en ≤ 800 palabras.** Descartada: la primera versión de este ADR la intentó y perdió reglas universales (prevalencia de producción, veto acumulativo, activación obligatoria de skills, entre otras). El límite de 800 era arbitrario.
* **Opción 4: Prompt basal autosuficiente con límite ampliado + skills como única carga bajo demanda.** Elegida.

## Decisión Adoptada

1. **Reglas universales en el prompt compilado:** `core/00-router.md` concentra todas las conductas que aplican en cualquier workspace, agrupadas en Entorno y Confinamiento, Ingeniería y Proporcionalidad, Estabilidad Lógica, Anti-Rigidez y Trazabilidad y Backlog.
2. **Procedimientos en skills con activación obligatoria:** El router declara cuándo **debe** cargarse cada skill (ej. `issue-driven-workflow` antes de editar archivos u operar Git/GitHub). El detalle procedimental (gate antes de crear el remoto, inicialización de repos, rieles de merge, estados del tablero, 8 fases) vive en la skill.
3. **Reglas propias de un runtime en `runtimes/<r>/rules/`:** La delegación al subagente `research` (modelo `flash`) pasa a la regla de Antigravity.
4. **Eliminación de `core/02`–`core/10`:** Su contenido queda redistribuido (ver mapa). `lib/link.sh` deja de crear el symlink `core` y retira el heredado; `runtimes/claude/settings.json` deja de permitir lecturas sobre `core/`.
5. **Presupuesto basal:** `MAX_CONTEXT_WORDS` sube de 800 a **1350** (compilado actual: antigravity 1251, claude 1209; ~1.670 tokens).
6. **Verificación:** `lib/check.sh` y `tests/test_progressive_disclosure.py` fallan ante cualquier mención `core/NN-` en el prompt compilado, `core/`, skills o reglas de runtime, y comprueban los marcadores de cada invariante.

### Mapa de Redistribución

| Módulo eliminado | Destino |
| :--- | :--- |
| 02 Git Lifecycle | Activación obligatoria de `issue-driven-workflow` (router); init local y gate de remoto en `references/repo-provisioning.md` |
| 03 Convención de Reglas | Inmunidad Normativa y Decisiones (MADR), incluido el veto a `GEMINI.md` (router); ciclo de ADRs en `adr-manager` |
| 04 Búsqueda Web | Local-First y Circuit Breaker de Búsqueda (router); subagente `research` en la regla de Antigravity |
| 05 Anti-Rigidez | Frontera de Directivas y Actionable Fallback (router) |
| 06 Ingeniería | Proporcionalidad y MBR con veto acumulativo, Prevalencia del Código de Producción, Lectura Paginada, Higiene de Salida y Pruebas (router) |
| 07 Anti-Alucinación | Inconsistencia Lógica y Stop & Ask, Issue como Propuesta, Planificación con Fast-Track, Stop & Plan y Fast-path (router) |
| 08 Backlog | Prohibición de Backlogs Locales con perfiles (router); 6 estados del tablero en `issue-driven-workflow` |
| 09 Issue-Driven | Inmutabilidad de Workspace con frontera ante pedidos informales (router); rieles de merge y 8 fases en `issue-driven-workflow` |
| 10 Entorno | Límites de Workspace, Anti-Reconocimiento, APIs Nativas, REPL, Entornos Locales, Higiene de Salida (router); gobernanza de sandbox en `runtimes/*/rules/` |

## Consecuencias

### Positivas
* Ninguna directiva induce lecturas fuera del workspace en ningún runtime.
* Las reglas universales se aplican siempre, sin depender de una lectura voluntaria.
* Una sola fuente de verdad por regla; los tests detectan regresiones de marcadores.

### Negativas / Mitigaciones
* **+~450 palabras (~600 tokens) por turno** respecto del prompt de 800. Se acepta frente a la pérdida de reglas; el límite de 1350 obliga a mover a skills cualquier procedimiento nuevo.
* **Los procedimientos dependen de que se active la skill.** Mitigado declarando la activación como obligatoria en el router, con disparadores concretos.
* En hosts ya enlazados, el symlink heredado `core` se retira en el próximo `./build.sh link`.
