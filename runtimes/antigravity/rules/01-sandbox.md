# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

<!-- rule: id=AGY_GIT_SANDBOX_BYPASS level=P0/P2 origin=legacy -->
- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch`) en sandbox.
  - **Mutadores Locales y Red (`BypassSandbox: true` directo):** Con `.git/` de solo lectura, mutadores locales (`init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y remotos (`git push`, `git pull`, `gh`) exigen `BypassSandbox: true` directo.
  - **Formato Atómico de Commits:** Prohibido `git commit -m "..."` (rompe prefix matching). Redactar en `.commit_msg` vía `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
<!-- rule: id=AGY_ATTRIBUTION level=P1 origin=legacy -->
- **Atribución:** En issues y PRs: `Creado por: Antigravity (<modelo de la sesión>)`. En commits (trailer Git): `Generated-by: Antigravity (<modelo de la sesión>)`.
<!-- rule: id=AGY_DELEGATED_EXPLORATION level=P1 origin=legacy -->
- **Exploración Delegada:** Relevamientos de > 8 archivos o código desconocido se delegan al subagente `research` (modelo `flash`, `Workspace: inherit`).
<!-- rule: id=AGY_DOTFILES_PROVISIONING level=P1/P2 origin=legacy -->
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan confinados (`BypassSandbox: false`).
  - Escrituras externas (`./build.sh link`, `./build.sh all`) son bootstrap exclusivo del usuario en terminal nativa.
<!-- rule: id=AGY_BYPASS_EXCLUSIVITY level=P0/P2 origin=legacy -->
- **Exclusividad de Bypass y Preservación de Prefix Matching:**
  - `BypassSandbox: true` exclusivo para `git`, `gh` y CLIs `agent-audit`, `agent-module`, `gh-pr-review`, `git-prune-gone`. Prohibido para comandos locales (`ls`, `cat`).
  - **Comandos Atómicos y Prohibición de Tuberías:** Comandos atómicos sin encadenamientos (`&&`, `||`) ni tuberías (`|`) externas (`jq`, `grep`, `awk`, `sed`) en bypass; usar filtrado nativo (`--jq`, `--json`, `--query`).
  - **Veto Absoluto a Evaluadores en Línea y Wrappers:** Prohibido usar evaluadores inline (`python3 -c`, `node -e`, `bash -c`) o envolver binarios autorizados en subshells/subprocess (rompe el prefix matching de "Always allow"). Scripts en `<appDataDir>/brain/<conversation-id>/scratch/` vía `write_to_file`, ejecutados confinados (`BypassSandbox: false`).



