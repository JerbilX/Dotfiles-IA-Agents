# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false`):** Inspección pasiva (`status`, `log`, `diff`) opera confinada.
  - **Mutadores y Red (`BypassSandbox: true`):** `.git/` montado `ro` exige bypass en mutadores locales y remotos (`git`, `gh`) desde el primer intento.
  - **Commits Atómicos:** Prohibido `git commit -m "..."`. Redactar en `.commit_msg` y ejecutar `git commit -F .commit_msg` con bypass.
- **Exclusividad de Bypass:**
  - Exclusivo para `git`, `gh` y CLIs autorizados ([`agent-audit`](skills/conversation-audit/bin/agent-audit), [`gh-pr-review`](skills/issue-driven-workflow/bin/gh-pr-review), [`git-prune-gone`](skills/issue-driven-workflow/bin/git-prune-gone)). Ignorar sugerencias de bypass para utilidades comunes.
  - Comandos atómicos sin tuberías (`|`) con bypass (usar filtrado nativo de `gh`).
- **Aprovisionamiento:** `./build.sh build` y `./build.sh check` corren confinados (`BypassSandbox: false`). Bootstrap (`link`, `all`) es responsabilidad del usuario.
