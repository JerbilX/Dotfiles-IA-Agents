# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de Herramientas Nativas de Archivos:** Operaciones de archivo deben usar estrictamente las APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`) o generar scripts temporales de parcheo (`patch_*.py`).
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`, `.issue_body`) deben eliminarse inmediatamente tras su uso (`rm -f <archivo>`) y contemplarse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Operaciones de lectura y escritura se restringen al workspace activo. Prohibido inspeccionar o modificar rutas absolutas externas del sistema.
- **Terminal Confinada y Determinista:** `run_command` se reserva para procesos de runtime, compilación, pruebas y utilidades de entorno, en formato atómico y sin subshells complejas.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación de permisos o bypass se rige por las directivas de especialización del runtime.

