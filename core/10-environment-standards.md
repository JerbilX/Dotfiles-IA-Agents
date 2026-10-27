# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de Herramientas Nativas de Archivos:** Operaciones de archivo deben usar estrictamente las APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`) o generar scripts temporales de parcheo (`patch_*.py`).
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`, `.issue_body`) deben eliminarse inmediatamente tras su uso (`rm -f <archivo>`) y contemplarse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Toda operación de lectura o escritura (sea vía herramientas nativas o terminal) se restringe estrictamente al workspace activo. Prohibido acceder o inspeccionar rutas externas o directorios superiores (`..`).
- **Terminal Confinada y Determinista:** `run_command` se reserva para procesos de runtime, compilación, pruebas y utilidades de entorno, en formato atómico y sin subshells complejas.
- **Prohibición de REPL Iterativo en Terminal:** Prohibido utilizar la terminal para cadenas de micro-ejecuciones de intérpretes (`python -c`, `node -e`, etc.) como REPL interactivo de ensayo y error para expresiones regulares o lógica de parsing. Es mandatorio consolidar la exploración en un único script unificado en `<appDataDir>/brain/<conversation-id>/scratch/` o implementar directamente pruebas unitarias parametrizadas en la suite de tests local.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación de permisos o bypass se rige por las directivas de especialización del runtime.

