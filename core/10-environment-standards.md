# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones de archivo exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar terminal para I/O (`cat`, `sed`, `awk`, `tee`) o parches.
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`) deben eliminarse tras su uso (`rm -f <archivo>`) e incluirse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Toda operación se restringe estrictamente al workspace activo. Prohibido inspeccionar rutas externas o superiores (`..`).
- **Blindaje Anti-Reconocimiento y Anti-Exfiltración:** Prohibido reconocimiento ciego del host (`find /`, `find $HOME`, barridos o inspección de directorios `brain/`). Prohibido exfiltrar repositorios locales vía red (`gh api`, `curl`) o iterar scripts en terminal para volcar repositorios remotos.
- **Degradación Elegante ante Ausencias (Stop & Ask):** Ante la ausencia de un archivo o comando esperado, activar inmediatamente Stop & Ask sin exploración descontrolada.
- **Terminal Confinada y Determinista:** `run_command` se reserva para runtime, compilación, pruebas y utilidades, de forma atómica y sin subshells complejas.
- **Higiene de Salida y Prevención de Truncamiento:** Acotar salidas (`head -n 20`, `--jq`) y líneas (`StartLine`/`EndLine` en `view_file`), evitando saturar contexto.
- **Precedencia de Entornos Locales:** Verificar entornos locales (`.venv/bin/`, `node_modules/.bin/`) antes de invocar intérpretes o linters; priorizar binarios locales.
- **Prohibición de REPL Iterativo y Evaluadores Inline en Terminal:** Prohibido taxativamente usar terminal para evaluación en línea (`python3 -c`, `node -e`, `bash -c`), como REPL ad-hoc, wrappers/pipes o para consumir APIs remotas (ej. `python3 -c` con `gh api`). Toda inspección de repositorios externos o de soporte exige delegación al subagente `research` (o CLI atómico con `--jq`). Procesamiento estructurado debe aislarse en scripts en `scratch/` o pruebas locales.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación o bypass se rige por directivas de runtime.

