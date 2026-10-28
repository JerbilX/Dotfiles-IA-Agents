# Estándares Universales de Entorno y Confinamiento

- **APIs Nativas:** I/O exclusivamente vía APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido I/O por terminal (`cat`, `sed`, `awk`, `tee`).
- **Confinamiento:** Operaciones restringidas al workspace activo; prohibido acceder a `..`. Terminal atómica para runtime y tests (`run_command`).
- **Prohibición de REPL:** Prohibido REPL iterativo (`python -c`, `node -e`); usar scratchpad o tests unitarios. Acotar salidas extensas (`head`, `--jq`).
- **Higiene y Sandbox:** Eliminar temporales (`.commit_msg`, `.pr_body`) de inmediato (`rm -f`). Privilegios estándar confinados por defecto.
- **Documentación:** Al estructurar documentación técnica, leer obligatoriamente [`skills/project-documentation/SKILL.md`](skills/project-documentation/SKILL.md).
