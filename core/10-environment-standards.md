# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de APIs Nativas de Archivos:** Operaciones exigen herramientas nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`); prohibido usar terminal para I/O (`cat`, `sed`, `awk`, `tee`). Toda edición exige granularidad atómica en `replace_file_content` (bloques acotados), evitando cambios monolíticos que causen truncamientos o alta latencia.
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`) deben eliminarse tras su uso (`rm -f <archivo>`) e incluirse en `.gitignore`.
- **Límites de Workspace:** Operaciones se restringen al workspace activo. Prohibido inspeccionar rutas externas o superiores (`..`).
- **Blindaje Anti-Reconocimiento y Anti-Exfiltración:** Prohibido reconocimiento ciego del host (`find /`, `find $HOME`, barridos) y exfiltración de repositorios o volcados masivos vía red (`gh api`, `curl`).
- **Degradación Elegante ante Ausencias (Stop & Ask):** Ante ausencia de archivo o comando esperado, activar Stop & Ask sin exploración ciega.
- **Terminal Confinada y Determinista:** `run_command` se reserva para runtime, compilación, pruebas y utilidades, de forma atómica y sin subshells complejas.
- **Higiene de Salida y Prevención de Truncamiento:** Acotar salidas (`head -n 20`, `--jq`) y delimitar `StartLine`/`EndLine` (ventana ≤ 200 líneas). Circuit breaker (≤ 2 lecturas consecutivas por archivo sin acción intermedia), `grep_search` (> 150 líneas, ventana ≤ 50 líneas) e inmunidad al prompt heurístico de contenido no mostrado.
- **Precedencia de Entornos Locales:** Verificar entornos locales (`.venv/bin/`, `node_modules/.bin/`) antes de invocar intérpretes o linters; priorizar binarios locales.
- **Prohibición de REPL Iterativo y Evaluadores Inline en Terminal:** Prohibido usar terminal para evaluación en línea (`python3 -c`, `node -e`, `bash -c`), REPL o wrappers/pipes a utilidades. Inspecciones complejas exigen subagente `research` (o CLI `--jq`). Scripts deben aislarse en `scratch/` o tests locales.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; bypass restringido por directivas de runtime.


