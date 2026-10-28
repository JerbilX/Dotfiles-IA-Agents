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
- **Cero adulación:** Asumir correcciones de forma neutra sin disculpas ni sumisión; corregir directamente.


# Ciclo de Vida y Gestión de Repositorios Git / GitHub

- **Inicialización Proactiva:** Ante código sin `.git`, inicializar localmente en `main`.
- **Gate Remoto:** Prohibido crear repo remoto o push a `origin` sin autorización humana.
- **Aprovisionamiento:** Al aprovisionar o conectar remotos, leer obligatoriamente [`skills/issue-driven-workflow/references/repo-provisioning.md`](skills/issue-driven-workflow/references/repo-provisioning.md).


# Convención Canónica de Reglas para Agentes

- **Fuente Canónica:** Toda directiva se origina en este repo y compila con `build.sh`. Prohibido depender de `GEMINI.md`.
- **Inmunidad Normativa:** Solo gobiernan `AGENTS.md` y skills activos; registros históricos no son directivas activas.
- **Decisiones (MADR):** Prohibido `HISTORIAL.md`. Al proponer arquitectura o dependencias, leer obligatoriamente [`skills/adr-manager/SKILL.md`](skills/adr-manager/SKILL.md).


# Disciplina de Búsqueda Web y Circuit Breaker Canónico

- **Local-First:** Priorizar documentación local y skills antes de búsquedas web (`search_web`).
- **Circuit Breakers:** Máximo 3 búsquedas web sucesivas sin conclusión técnica -> Stop & Ask. Máximo 3 a 5 iteraciones en terminal -> Stop & Ask; preferir consultas agregadas (`graphql`).
- **Auditoría:** Al auditar latencia o antipatrones en sesiones, leer obligatoriamente [`skills/conversation-audit/SKILL.md`](skills/conversation-audit/SKILL.md).


# Flexibilidad y Degradación Elegante (Anti-Rigidez)

- **Frontera de Directivas:** Restricciones de seguridad, sandbox e I/O nativo son inviolables; directivas metodológicas admiten fallback.
- **Degradación Elegante:** Vía preferida -> alternativa acotada -> Stop & Ask. Prohibido paralizarse.
- **Actionable Fallback:** Ante bloqueos de entorno, emitir diagnóstico, comando terminal-ready copiable y guía de continuidad.


# Integridad de Diseño y Estándares de Ingeniería

- **Prevalencia de Producción:** Contratos de producción priman sobre tests; prohibido degradar código por mocks obsoletos.
- **Fallos en Tests:** Si el mock está desfasado, actualizarlo; si falla regla de negocio, corregir código de producción.
- **Minimal Blast Radius:** Resolver al nivel más bajo (N0 CLI -> N1 Tooling -> N2 Skills -> N3 Runtime -> N4 Core). Modificar `core/` exige justificación basal; al clasificar tareas, leer [`skills/issue-driven-workflow/references/issue-backlog.md`](skills/issue-driven-workflow/references/issue-backlog.md).


# Estabilidad Lógica y Cero Tolerancia a la Alucinación

- **Inconsistencia Lógica:** Si una hipótesis contradice hechos técnicos, es inválida. Prohibido adivinar (Stop & Ask).
- **Diseño con Respaldo:** Prohibido inventar arquitecturas sin sustento empírico en el workspace.
- **Planning Mode:** Fast-Track para requerimientos claros en `Ready for Dev`; Stop & Plan (`RequestFeedback: true`) ante ambigüedad o ADRs; Fast-Path tras consenso. Al planificar, leer [`skills/issue-driven-workflow/references/branch-lifecycle.md`](skills/issue-driven-workflow/references/branch-lifecycle.md).


# Gestión de Backlog y Tareas (GitHub Issues y Projects)

- **Backlog Canónico:** Prohibido `TODO.md` o `tasks/`. Tareas futuras y scope creep se registran en GitHub Issues e indexan en Projects v2.
- **Estados del Tablero:** 6 estados canónicos (`Backlog` -> `Ready for Dev` -> `In Planning` -> `In Progress` -> `In Review / PR` -> `Done`).
- **Operativa:** Al crear issues o gestionar estados del tablero, leer obligatoriamente [`skills/issue-driven-workflow/references/issue-backlog.md`](skills/issue-driven-workflow/references/issue-backlog.md).


# Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests

- **Inmutabilidad de Workspace:** Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y PR (`Closes #<id>`). Prohibido push a `main`.
- **Peticiones Informales:** Snippets sin ticket van a chat o scratchpad; persistencia en workspace exige issue previa.
- **Rieles de PR:** Riel 1 (Default: orden en chat); Riel 2 (Auto-merge condicional; cambios en `core/`, `runtimes/` o ADRs degradan a Riel 1).
- **Ejecución E2E:** Al despachar tareas, ramas, PRs o reviews, leer [`skills/issue-driven-workflow/SKILL.md`](skills/issue-driven-workflow/SKILL.md) y [`skills/issue-driven-workflow/references/branch-lifecycle.md`](skills/issue-driven-workflow/references/branch-lifecycle.md).


# Estándares Universales de Entorno y Confinamiento

- **APIs Nativas:** I/O exclusivamente vía APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido I/O por terminal (`cat`, `sed`, `awk`, `tee`).
- **Confinamiento:** Operaciones restringidas al workspace activo; prohibido acceder a `..`. Terminal atómica para runtime y tests (`run_command`).
- **Prohibición de REPL:** Prohibido REPL iterativo (`python -c`, `node -e`); usar scratchpad o tests unitarios. Acotar salidas extensas (`head`, `--jq`).
- **Higiene y Sandbox:** Eliminar temporales (`.commit_msg`, `.pr_body`) de inmediato (`rm -f`). Privilegios estándar confinados por defecto.
- **Documentación:** Al estructurar documentación técnica, leer obligatoriamente [`skills/project-documentation/SKILL.md`](skills/project-documentation/SKILL.md).

