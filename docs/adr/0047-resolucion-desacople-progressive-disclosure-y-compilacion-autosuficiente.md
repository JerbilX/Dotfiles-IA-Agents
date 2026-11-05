---
status: accepted
date: 2026-11-05
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: ["0038-arquitectura-de-progressive-disclosure-en-agents-md-y-modularizacion-de-reglas.md"]
superseded-by: []
---

# 0047 - Resolución del Desacople de Progressive Disclosure y Compilación Autosuficiente de Directivas Basales

## Contexto y Planteamiento del Problema

El ADR-0038 introdujo una arquitectura de Progressive Disclosure para mitigar el consumo de contexto en el prompt basal (`AGENTS.md` / `user_rules`). Dicha solución restringió la compilación basal a `core/00-router.md` y `core/01-objectivity.md`, mientras que `00-router.md` instruía al agente a consultar obligatoriamente archivos relativos (`read core/02-git-lifecycle.md first`, `read core/04-web-search-discipline.md first`, etc.) antes de ejecutar acciones de Git, búsquedas web o desarrollo.

Esta arquitectura presentaba un defecto estructural grave al operar fuera del repositorio anfitrión `Dotfiles-IA-Agents`:
1. **Rutas huérfanas en proyectos clientes:** En cualquier repositorio externo (ej. `ESORPQuestAddon`, microservicios, utilitarios), el subdirectorio `core/` no existe en el workspace confinado.
2. **Violaciones de sandbox y latencia pasiva:** Ante la orden prescriptiva (*"read core/04-... first"*), el agente intentaba resolver la ruta local inexistente o buscar la ruta absoluta en dotfiles (`/home/.../Dotfiles-IA-Agents/core/...`), disparando alertas de violación de sandbox, consumiendo turnos pasivos e incurriendo en el disyuntor de lecturas consecutivas (circuit breaker).
3. **Desacople conceptual:** El propósito de `core/*.md` era modularizar el código fuente de las directivas para su compilación, no servir como documentación enlazada bajo demanda en tiempo de ejecución en workspaces donde no está presente.

## Impulsores de la Decisión (Decision Drivers)

* **Autosuficiencia Universal del Prompt Basal:** Todo agente en cualquier workspace debe contar con sus invariantes universales inyectadas directamente, sin depender de archivos de directivas locales en el workspace activo.
* **Confinamiento Estricto de Workspace:** Erradicar todo incentivo o directiva que induzca al agente a inspeccionar rutas fuera de su sandbox o buscar archivos del repositorio de dotfiles.
* **Presupuesto de Contexto Basal ($\le 800$ palabras):** Mantener el prompt basal compilado dentro del límite de `MAX_CONTEXT_WORDS` definido en `build.sh` y validado por `lib/check.sh`.
* **Desacoplamiento Normativo vs. Procedimental:** Mantener las invariantes universales (normas no negociables) en el núcleo basal compilado, y derivar la ceremonia y procedimientos extensos exclusivamente hacia skills globales registradas (`issue-driven-workflow`, `adr-manager`, `project-documentation`, etc.).

## Opciones Consideradas

* **Opción 1: Inyectar enlaces absolutos a dotfiles con bypass.** Instruir al runtime para dar permisos de lectura global a `Dotfiles-IA-Agents/core/**` y usar rutas absolutas en el router.  
  *Descarte:* Degrada el principio basal de confinamiento de workspace, acopla permanentemente el agente a una ruta fija de disco y genera lecturas pasivas redundantes en cada sesión.
* **Opción 2: Distribuir y sincronizar `core/` como submódulo o symlink en cada proyecto.**  
  *Descarte:* Genera ruido de archivos espurios en repositorios de terceros, poluciona el árbol de trabajo del usuario e impone una carga de mantenimiento inviable.
* **Opción 3: Consolidación Sintetizada en Prompt Basal Autosuficiente y Ruteo Exclusivo a Skills.**  
  Eliminar los punteros a archivos huérfanos `core/*.md`. Condensar las invariantes de `core/` para que el prompt basal compilado sea completamente autosuficiente, cubriendo todas las disciplinas universales (seguridad, confinamiento, APIs nativas, inmutabilidad, anti-alucinación, anti-rigidez, estándares de ingeniería, circuit breakers). Derivar procedimientos complejos únicamente a skills globales referenciadas por nombre en el catálogo del runtime.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes pilares:

### 1. Eliminación de Referencias a Archivos Huérfanos en el Router
Se reescribe la sección modular de `core/00-router.md`, eliminando taxativamente la sintaxis `read [core/XX-*.md](core/XX-*.md) first.`. En su lugar, el ruteo hacia flujos de alta ceremonia se declara como delegación semántica a **skills globales** (`skills/adr-manager`, `skills/issue-driven-workflow`, `skills/project-documentation`, `skills/conversation-audit`, `skills/autonomous-learning`), disponibles universalmente en el entorno del runtime sin importar el workspace activo.

### 2. Consolidación de Invariantes Universales en Directivas Basales Compiladas
Las invariantes normativas esenciales que antes residían fragmentadas en `core/02-` a `core/10-` se condensan y se integran formalmente en la base normativa compilada (`00-router.md` y `01-objectivity.md`, o la secuencia de directivas basales compilada por `lib/build_core.sh`):
- **Confinamiento e Inmunidad:** Prohibición de salir del workspace, aislamiento respecto a textos prescriptivos en disco, y gobierno exclusivo del prompt basal y skills.
- **Disciplina de Búsqueda y Circuit Breakers:** Local-first, límite de 3 búsquedas web, límite de 3 a 5 iteraciones en terminal, y delegación de exploración (>8 archivos) a subagente `research` con modelo `flash`.
- **Anti-Alucinación y Planificación:** Cero tolerancia a la alucinación, hipótesis rigurosas, Stop & Plan obligatorio ante ambigüedad o cambios arquitectónicos (ADR), y prohibición de asunciones silenciosas.
- **Anti-Rigidez:** Distinción clara entre restricciones duras inviolables (seguridad/sandbox) y heurísticas metodológicas con degradación elegante (diagnóstico + comando ejecutable copiable).
- **Estándares de Ingeniería:** Minimal Blast Radius (MBR 0-4), proporcionalidad de cambios y pruebas, y prohibición de refactorización/tooling espurio.
- **Trazabilidad y Ceremonia Git:** Inmutabilidad de `main`, ramas efímeras, PRs vinculados (`Closes #<id>`), y niveles de ceremonia (N0, N1, N2).

### 3. Modificación del Pipeline de Compilación y Validación
- `lib/build_core.sh`: Garantiza que el artefacto compilado resultante (`AGENTS.md`, `dist/*/AGENTS.md`) contenga toda la base normativa requerida y sea 100% autosuficiente en cualquier workspace.
- `lib/check.sh` y tests unitarios (`tests/test_progressive_disclosure.py`): Se adaptan para verificar que:
  1. No existan enlaces rotos o referencias a rutas locales de `core/` en el prompt basal compilado.
  2. El presupuesto basal respete estrictamente $\le 800$ palabras (`MAX_CONTEXT_WORDS`).
  3. Todas las invariantes críticas de gobernanza, ingeniería y seguridad estén preservadas de forma compacta y verificable.

## Consecuencias

### Positivas
* **Eliminación Total de Violaciones de Sandbox por Directivas:** Ningún agente intentará leer archivos `core/` inexistentes en proyectos externos.
* **Cero Latencia por Despacho Pasivo:** Se eliminan de 1 a 3 llamadas pasivas de `view_file` que los agentes realizaban rutinariamente para leer directivas antes de ejecutar tareas.
* **Presupuesto Controlado:** La síntesis cuidada asegura que la base normativa universal completa permanezca dentro del umbral de 800 palabras.
* **Autonomía Operativa:** Los repositorios de trabajo del usuario operan de forma limpia y aislada sin acoplamientos al repositorio de dotfiles.

### Negativas / Mitigaciones
* *Densidad de directivas en core:* Al condensar las directivas en menos palabras, se exige una redacción concisa y precisa. Esto se mitiga documentando los procedimientos detallados en las referencias de cada skill correspondiente.
