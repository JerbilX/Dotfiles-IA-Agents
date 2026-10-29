# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de Herramientas Nativas de Archivos:** Operaciones de archivo exigen APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`) o scripts temporales de parcheo (`patch_*.py`).
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`, `.issue_body`) deben eliminarse tras su uso (`rm -f <archivo>`) e incluirse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Toda lectura o escritura (vía herramientas nativas o terminal) se restringe estrictamente al workspace activo. Prohibido inspeccionar rutas externas o directorios superiores (`..`).
- **Terminal Confinada y Determinista:** `run_command` se reserva para runtime, compilación, pruebas y utilidades de entorno, de forma atómica y sin subshells complejas.
- **Higiene de Salida y Prevención de Truncamiento:** Acotar la salida de comandos exploratorios o archivos extensos mediante filtros (`head -n 20`, slices `[:20]`, paginación o `--jq`), evitando volcados masivos en stdout que desborden los buffers del runtime.
- **Precedencia de Entornos Locales:** Verificar entornos virtuales o dependencias locales (`.venv/bin/`, `node_modules/.bin/`, `vendor/bin/`) antes de invocar intérpretes (`python`, `node`), scripts, tareas de runtime, migraciones, pruebas o linters; priorizar siempre el binario local del proyecto frente a ejecutables globales del sistema.
- **Prohibición de REPL Iterativo en Terminal:** Prohibido usar la terminal para micro-ejecuciones o evaluación en línea (`python -c`, `node -e`) como REPL ad-hoc, introspección, consultas de base de datos, modelos o lógica de negocio. Consolidar la exploración en scripts en `<appDataDir>/brain/<conversation-id>/scratch/`, comandos formales del CLI del proyecto o pruebas unitarias parametrizadas locales.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación de permisos o bypass se rige por las directivas de especialización del runtime.

