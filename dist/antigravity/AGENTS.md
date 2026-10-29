<!--
  =============================================================================
  AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
  Source repository: Dotfiles-IA-Agents
  Runtime: antigravity
  Components: core/00-router.md, core/01-objectivity.md, runtimes/antigravity/rules/*.md
  =============================================================================
-->

# Progressive Disclosure Router y Directivas Canónicas

## Invariantes Basales Universales

- **Confinamiento de Workspace:** Toda operación de lectura o escritura se restringe estrictamente al workspace activo. Prohibido acceder o inspeccionar rutas externas o directorios superiores (`..`).
- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones de archivo deben usar estrictamente las APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`).
- **Inmutabilidad de main:** Prohibido comitear o pushear directamente a `main`. Todo cambio exige issue previa, rama efímera (`feat/` o `fix/`) y entrega vía Pull Request (`Closes #<id>`).
- **Inmutabilidad de Workspace y Obligatoriedad de Issue Previa:** Toda propuesta de modificación, mejora, corrección o refactorización identificada en el proyecto exige OBLIGATORIAMENTE la creación previa de una GitHub Issue e indexación en el backlog. Queda terminantemente PROHIBIDO modificar archivos en el workspace sin ticket activo, así como proponer o consultar al usuario si se implementan los cambios directamente; ante cualquier diagnóstico o hallazgo técnico, la única vía válida es registrar el issue en el backlog canónico o consultar la prioridad de apertura de ticket.

## Progressive Disclosure Router (Directivas Modulares)

Para especificaciones operativas y procedimientos detallados, consultar obligatoriamente la directiva modular correspondiente antes de actuar:

- **Ciclo de Vida Git y Repositorios:** If initializing, configuring, or pushing to Git/GitHub repositories, read [core/02-git-lifecycle.md](core/02-git-lifecycle.md) first.
- **Convención de Reglas y Decisiones (MADR):** If defining agent rules, modifying architecture, or managing ADRs, read [core/03-agent-rules-convention.md](core/03-agent-rules-convention.md) and [skills/adr-manager/SKILL.md](skills/adr-manager/SKILL.md) first.
- **Disciplina de Búsqueda Web y Circuit Breakers:** If searching the web or consulting external documentation, read [core/04-web-search-discipline.md](core/04-web-search-discipline.md) first.
- **Flexibilidad y Degradación Elegante:** If encountering environment errors, tool failures, or rigid blocks, read [core/05-anti-rigidity.md](core/05-anti-rigidity.md) first.
- **Estándares de Ingeniería y Tests:** If writing code, updating tests, or evaluating blast radius, read [core/06-engineering-standards.md](core/06-engineering-standards.md) first.
- **Estabilidad Lógica y Planificación:** If formulating hypotheses, planning tasks, or resolving ambiguity, read [core/07-anti-hallucination.md](core/07-anti-hallucination.md) first.
- **Gestión de Backlog y Tareas:** If creating issues, indexing tasks, concluding audits/diagnostics, or proposing technical improvements, read [core/08-task-backlog-management.md](core/08-task-backlog-management.md) first.
- **Protocolo de Desarrollo Guiado por Issues y PRs:** If starting development, creating branches, opening PRs, reviewing code, or planning file modifications, read [core/09-issue-driven-workflow.md](core/09-issue-driven-workflow.md) and [skills/issue-driven-workflow/SKILL.md](skills/issue-driven-workflow/SKILL.md) first.
- **Entorno y Confinamiento Detallado:** If running terminal commands, managing temporary files, or handling CLI tooling, read [core/10-environment-standards.md](core/10-environment-standards.md) first.


# Critical Feedback and Objectivity

- **Cero complacencia:** Prohibido asumir que las ideas del usuario son buenas por defecto o usar frases de validación vacías ("¡Gran idea!", "Me parece perfecto").
- **Cuestionar y proponer:** Ante fallas técnicas, limitaciones o errores de diseño, señalarlas de forma directa y plantear alternativas más eficientes, estándar o seguras, priorizando la calidad técnica sobre la complacencia.
- **Cero adulación y disculpas:** Ante correcciones o mejoras aportadas por el usuario, asumirlas de manera neutra y técnica. Prohibido usar frases sumisas ("tienes toda la razón", "análisis impecable") o disculparse reiteradamente; proceder directamente a la corrección.



# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch` de consulta) debe ejecutarse 100% confinada en el sandbox estándar.
  - **Mutadores Locales y Red (`BypassSandbox: true` obligatorio desde el primer intento):** Dado que el kernel monta `.git/` como solo lectura (`ro`), todo mutador local (`git init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y comando remoto (`git push`, `git pull`, `gh`) falla en sandbox; deben ejecutarse directamente con `BypassSandbox: true` desde el primer intento para evitar latencia de turnos fallidos.
  - **Formato Atómico de Commits:** Prohibido usar `git commit -m "..."` (rompe el prefix matching de permisos). Redactar siempre el mensaje en `.commit_msg` con `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan dentro del workspace y deben ejecutarse confinados (`BypassSandbox: false`).
  - Comandos que escriben fuera del workspace (`./build.sh link`, `./build.sh all`) son responsabilidad exclusiva de bootstrap del usuario en terminal nativa.
- **Exclusividad de Bypass y Blindaje Anti-Sugerencias:**
  - `BypassSandbox: true` está reservado exclusivamente para la suite de `git` y `gh`, y para los CLIs `agent-audit`, `gh-pr-review` y `git-prune-gone` (priorizando su invocación en `$PATH` con fallback determinista a `skills/*/bin/`). Prohibido para otros comandos locales (`ls`, `cat`, utilidades).
  - Si el sandbox sugiere *"run the command again with BypassSandbox set to true"* para un comando local no autorizado, ignorar la sugerencia por completo.
  - **Invocaciones Atómicas y Prohibición de Tuberías:** Mantener comandos atómicos sin operadores encadenados (`&&`, `||`). Prohibido el uso de tuberías (`|`) hacia utilidades externas (`jq`, `grep`, `awk`, `sed`) en comandos con bypass por romper el prefix matching; es obligatorio usar el filtrado nativo de `gh` (`--jq`, `--json`, `--query`).




