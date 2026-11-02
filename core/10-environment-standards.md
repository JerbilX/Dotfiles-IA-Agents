# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones de archivo exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`) o parches.
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`) deben eliminarse tras su uso (`rm -f <archivo>`) e incluirse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Toda operación se restringe estrictamente al workspace activo. Prohibido inspeccionar rutas externas o superiores (`..`).
- **Blindaje Anti-Reconocimiento y Anti-Exfiltración:** Prohibido reconocimiento ciego del host (`find /`, `find $HOME`, barridos masivos o inspección de directorios `brain/` ajenos). Prohibido exfiltrar repositorios locales vía red (`gh api`, `curl`) con bypass para evadir el sandbox.
- **Degradación Elegante ante Ausencias (Stop & Ask):** Ante la ausencia de un archivo o comando esperado, activar inmediatamente Stop & Ask sin exploración descontrolada.
- **Terminal Confinada y Determinista:** `run_command` se reserva para runtime, compilación, pruebas y utilidades, de forma atómica y sin subshells complejas.
- **Higiene de Salida y Prevención de Truncamiento:** Acotar salidas exploratorias (`head -n 20`, paginación, `--jq`) y líneas (`StartLine`/`EndLine` en `view_file`), evitando saturar buffers o presupuesto de contexto.
- **Precedencia de Entornos Locales:** Verificar dependencias locales (`.venv/bin/`, `node_modules/.bin/`) antes de invocar intérpretes (`python`, `node`) o linters; priorizar binarios locales sobre globales.
- **Prohibición de REPL Iterativo y Evaluadores Inline en Terminal:** Prohibido usar terminal para evaluación en línea (`python3 -c`, `node -e`, `bash -c`), como REPL interactivo ad-hoc o como wrappers/pipes para procesar datos de CLIs autorizados. Toda exploración o procesamiento estructurado debe canalizarse mediante opciones nativas del CLI, scripts aislados en `scratch/` o pruebas locales.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación o bypass se rige por directivas de runtime.

