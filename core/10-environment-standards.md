# Estándares Universales de Entorno y Confinamiento

- **Uso Exclusivo de Herramientas Nativas de Archivos:** Operaciones de archivo exigen APIs nativas (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar terminal para I/O (`cat`, `sed`, `awk`, `tee`, `echo >>`) o scripts de parcheo.
- **Higiene de Archivos Temporales:** Archivos auxiliares (`.commit_msg`, `.pr_body`) deben eliminarse tras su uso (`rm -f <archivo>`) e incluirse en `.gitignore`.
- **Límites de Workspace y Aislamiento:** Toda operación se restringe estrictamente al workspace activo. Prohibido inspeccionar rutas externas o superiores (`..`).
- **Blindaje Anti-Reconocimiento y Anti-Exfiltración:** Prohibido el reconocimiento ciego del anfitrión (`find /`, `find $HOME`, barridos masivos en el sistema o inspección de directorios `brain/` de otras sesiones). Prohibido exfiltrar recursos o repositorios locales vía red (`gh api`, `curl`) con bypass para evadir el confinamiento del sandbox local.
- **Degradación Elegante ante Ausencias (Stop & Ask):** Ante la ausencia de un archivo o comando esperado, activar inmediatamente degradación elegante (Stop & Ask) sin exploración descontrolada.
- **Terminal Confinada y Determinista:** `run_command` se reserva para runtime, compilación, pruebas y utilidades, de forma atómica y sin subshells complejas.
- **Higiene de Salida y Prevención de Truncamiento:** Acotar salidas exploratorias (`head -n 20`, paginación, `--jq`) y líneas (`StartLine`/`EndLine` en `view_file`), evitando saturar buffers o presupuesto de contexto.
- **Precedencia de Entornos Locales:** Verificar dependencias locales (`.venv/bin/`, `node_modules/.bin/`) antes de invocar intérpretes (`python`, `node`) o linters; priorizar binarios locales sobre globales.
- **Prohibición de REPL Iterativo en Terminal:** Prohibido usar terminal para evaluación en línea (`python -c`, `node -e`) como REPL ad-hoc. Consolidar exploración en scripts bajo `scratch/`, CLI formal o pruebas locales.
- **Gobernanza de Sandbox:** Ejecutar bajo privilegios estándar confinados por defecto; la escalación o bypass se rige por directivas de runtime.

