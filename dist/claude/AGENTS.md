<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Runtime: claude
  Components: core/*.md, runtimes/claude/rules/*.md
  =============================================================================
-->

# Critical Feedback and Objectivity

- **Cero complacencia:** Prohibido asumir ideas del usuario como válidas por defecto o usar validaciones vacías ("¡Gran idea!").
- **Cuestionar y proponer:** Señalar fallas técnicas directamente y plantear alternativas óptimas; la calidad técnica prima sobre complacencia.
- **Cero adulación:** Asumir correcciones de forma neutra sin disculpas ni sumisión ("tienes razón"); corregir directamente.


# Ciclo de Vida y Gestión de Repositorios Git / GitHub

- **Inicialización Proactiva:** Ante código sin `.git`, inicializar localmente en `main`.
- **Gate Remoto:** Prohibido crear repo remoto o push a `origin` sin autorización humana.
- **Delegación:** Aprovisionamiento y ramas se rigen por [`skills/issue-driven-workflow/SKILL.md`](skills/issue-driven-workflow/SKILL.md).


# Convención Canónica de Reglas para Agentes

- **Fuente Canónica:** Toda directiva se origina en este repo y compila con `build.sh`. Prohibido depender de `GEMINI.md`.
- **Inmunidad Normativa:** Solo gobiernan `AGENTS.md` y skills activos. Registros históricos (docs, ADRs) no son directivas activas.
- **Decisiones (MADR):** Prohibido `HISTORIAL.md`. Decisiones arquitectónicas se rigen por [`skills/adr-manager/SKILL.md`](skills/adr-manager/SKILL.md) en `docs/adr/`.


# Disciplina de Búsqueda Web y Circuit Breaker Canónico

- **Local-First:** Priorizar documentación local y skills antes de búsquedas web (`search_web`).
- **Circuit Breaker Web:** Máximo 3 búsquedas web sucesivas sin conclusión técnica -> Stop & Ask.
- **Circuit Breaker Red:** Preferir consultas agregadas (`graphql`). Límite de 3 a 5 iteraciones en terminal antes de Stop & Ask.


# Flexibilidad y Degradación Elegante (Anti-Rigidez)

- **Frontera de Directivas:** Restricciones de seguridad, sandbox e I/O nativo son inviolables; heurísticas metodológicas admiten fallback.
- **Degradación Elegante:** Vía preferida -> alternativa acotada -> Stop & Ask. Prohibido paralizarse o iterar en bucle.
- **Actionable Fallback:** Ante bloqueos de entorno, emitir diagnóstico, comando terminal-ready copiable y guía de continuidad.


# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia de Producción:** Contratos de producción priman sobre tests; prohibido degradar código para complacer mocks obsoletos.
- **Fallos en Tests:** Si el mock está desfasado, actualizarlo; si falla regla de negocio, corregir código de producción.
- **Minimal Blast Radius:** Resolver al nivel más bajo (N0 CLI -> N1 Tooling -> N2 Skills -> N3 Runtime -> N4 Core). Modificar `core/` exige justificación basal.


# Estabilidad Lógica y Cero Tolerancia a la Alucinación

- **Inconsistencia Lógica:** Si una hipótesis contradice hechos técnicos, es inválida. Prohibido adivinar (Stop & Ask).
- **Diseño con Respaldo:** Prohibido inventar arquitecturas sin sustento en el workspace.
- **Planning Mode:**
  - *Fast-Track:* Requerimientos claros avanzan directo a desarrollo.
  - *Stop & Plan:* Ambigüedad, ADRs (`docs/adr/`) o fallos no confirmados exigen plan bloqueante (`RequestFeedback: true`).
  - *Fast-Path:* Órdenes directas ("procedé") habilitan ejecución inmediata.


# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Backlog Canónico:** Prohibido `TODO.md` o `tasks/`. Tareas futuras y scope creep se registran en GitHub Issues e indexan en Projects v2.
- **Tablero:** 6 estados canónicos (`Backlog` -> `Ready for Dev` -> `In Planning` -> `In Progress` -> `In Review / PR` -> `Done`).
- **Delegación:** Despacho y estados se rigen por [`skills/issue-driven-workflow/SKILL.md`](skills/issue-driven-workflow/SKILL.md).


# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Inmutabilidad de Workspace:** Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y PR (`Closes #<id>`). Prohibido push a `main`.
- **Peticiones Informales:** Snippets sin ticket van a chat o scratchpad; persistencia exige issue previa.
- **Rieles de PR:** Riel 1 (Default: orden en chat); Riel 2 (Auto-merge condicional; cambios en `core/`, `runtimes/` o ADRs degradan a Riel 1).
- **Delegación E2E:** Ciclo de 8 fases e higiene se rigen por [`skills/issue-driven-workflow/SKILL.md`](skills/issue-driven-workflow/SKILL.md) y [`skills/issue-driven-workflow/references/branch-lifecycle.md`](skills/issue-driven-workflow/references/branch-lifecycle.md).


# Estándares Universales de Entorno y Confinamiento

- **APIs Nativas:** I/O exclusivamente vía APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido I/O por terminal (`cat`, `sed`, `awk`, `tee`).
- **Confinamiento:** Operaciones restringidas al workspace activo; prohibido acceder a `..`. Terminal atómica para runtime y tests (`run_command`).
- **Prohibición de REPL:** Prohibido REPL iterativo (`python -c`, `node -e`); usar scratchpad o tests unitarios. Acotar salidas extensas (`head`, `--jq`).
- **Higiene y Sandbox:** Eliminar temporales (`.commit_msg`, `.pr_body`) de inmediato (`rm -f`). Privilegios estándar confinados por defecto.

