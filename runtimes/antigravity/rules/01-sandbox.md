# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch`) en sandbox estándar.
  - **Mutadores Locales y Red (`BypassSandbox: true` directo):** Al montar el kernel `.git/` de solo lectura (`ro`), mutadores locales (`init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y remotos (`git push`, `git pull`, `gh`) requieren `BypassSandbox: true` directo para evitar turnos fallidos.
  - **Formato Atómico de Commits:** Prohibido `git commit -m "..."` (rompe prefix matching). Redactar mensaje en `.commit_msg` con `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan en workspace confinado (`BypassSandbox: false`).
  - Escrituras fuera del workspace (`./build.sh link`, `./build.sh all`) son bootstrap exclusivo del usuario en terminal nativa.
- **Exclusividad de Bypass y Preservación de Prefix Matching:**
  - `BypassSandbox: true` se reserva exclusivamente para `git`, `gh` y los CLIs `agent-audit`, `agent-module`, `gh-pr-review` y `git-prune-gone` (en `$PATH` o fallback a `skills/*/bin/`). Prohibido para comandos locales (`ls`, `cat`). Ignorar sugerencias del sandbox de reintentar con bypass herramientas no autorizadas.
  - **Comandos Atómicos y Prohibición de Tuberías:** Comandos atómicos sin encadenamientos (`&&`, `||`) ni tuberías (`|`) hacia utilidades externas (`jq`, `grep`, `awk`, `sed`) en bypass; usar filtrado nativo (`--jq`, `--json`, `--query`).
  - **Veto Absoluto a Evaluadores en Línea y Wrappers:** Prohibido taxativamente el uso de evaluadores inline (`python3 -c`, `node -e`, `bash -c`) o envolver binarios autorizados (`agent-audit`, `git`, `gh`) en subshells/subprocess (rompe el prefix matching de "Always allow"). Todo procesamiento con script debe escribirse en `<appDataDir>/brain/<conversation-id>/scratch/` mediante `write_to_file` y ejecutarse confinado (`BypassSandbox: false`).



