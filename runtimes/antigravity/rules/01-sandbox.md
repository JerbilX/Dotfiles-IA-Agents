# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

- **Ejecución de Git y Bypass de Sandbox:**
  - **Solo Lectura Confinado (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch` de consulta) debe ejecutarse 100% confinada en el sandbox estándar.
  - **Mutadores Locales y Red (`BypassSandbox: true` obligatorio desde el primer intento):** Dado que el kernel monta `.git/` como solo lectura (`ro`), todo mutador local (`git init`, `checkout`, `branch -d`, `add`, `commit`, `merge`, `reset`) y comando remoto (`git push`, `git pull`, `gh`) falla en sandbox; deben ejecutarse directamente con `BypassSandbox: true` desde el primer intento para evitar latencia de turnos fallidos.
  - **Formato Atómico de Commits:** Prohibido usar `git commit -m "..."` (rompe el prefix matching de permisos). Redactar siempre el mensaje en `.commit_msg` con `write_to_file` y ejecutar `git commit -F .commit_msg` con `BypassSandbox: true`.
- **Aprovisionamiento Hermético de Dotfiles:**
  - `./build.sh build` y `./build.sh check` operan dentro del workspace y deben ejecutarse confinados (`BypassSandbox: false`).
  - Comandos que escriben fuera del workspace (`./build.sh link`, `./build.sh all`) son responsabilidad exclusiva de bootstrap del usuario en terminal nativa.
- **Exclusividad de Bypass y Blindaje Anti-Sugerencias:**
  - `BypassSandbox: true` está reservado exclusivamente para la suite de `git` y `gh`. Prohibido usarlo para otros comandos locales (`ls`, `cat`, utilidades).
  - Si el sandbox sugiere *"run the command again with BypassSandbox set to true"* para un comando local no autorizado, ignorar la sugerencia por completo.
  - Mantener invocaciones atómicas sin operadores encadenados (`&&`, `||`) para preservar el prefix matching.



