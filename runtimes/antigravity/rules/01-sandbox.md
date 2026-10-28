# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false`):** Inspección pasiva (`status`, `log`, `diff`) opera confinada.
  - **Mutadores y Red (`BypassSandbox: true`):** `.git/` montado `ro` exige bypass en mutadores locales y remotos (`git`, `gh`) desde el primer intento.
  - **Commits Atómicos:** Prohibido `git commit -m "..."`; redactar en `.commit_msg` y commitear con `-F .commit_msg` y bypass.
- **Exclusividad de Bypass:**
  - Exclusivo para `git`, `gh` y CLIs autorizados ([`agent-audit`](skills/conversation-audit/bin/agent-audit), [`gh-pr-review`](skills/issue-driven-workflow/bin/gh-pr-review), [`git-prune-gone`](skills/issue-driven-workflow/bin/git-prune-gone)). Ignorar sugerencias para utilidades comunes.
  - Comandos atómicos sin tuberías (`|`) con bypass (usar filtrado de `gh`).
- **Aprovisionamiento:** `./build.sh build` y `check` corren confinados (`BypassSandbox: false`). Bootstrap es del usuario.
