# Estándares de Entorno y Ejecución (Sandbox)

- **Uso Exclusivo de Herramientas Nativas de Archivos:**
  - Crear archivos con `write_to_file`.
  - Modificar archivos existentes de forma atómica con `replace_file_content`.
  - Inspeccionar y leer código con `view_file`.
  - Buscar texto o patrones en el código con `grep_search`.
  - **PROHIBIDO** usar comandos de consola (`run_command`) para operaciones de I/O de archivos (`cat`, `sed`, `awk`, `echo >>`, `tee`, etc.).
  - **PROHIBIDO** generar scripts auxiliares temporales de parcheo (e.g., `patch_*.py`) para alterar código; todo cambio debe ser aplicado directamente con `replace_file_content`.
- **Restricción de Comandos de Consola (`run_command`):**
  - La terminal está reservada estrictamente para la ejecución de procesos de runtime, compilación, pruebas y utilidades de entorno (e.g., `dotnet`, `python`, `pytest`, `cargo`, `git status`).
  - Mantener las invocaciones en formatos atómicos y deterministas (evitar heredocs multilínea o subshells complejas que rompan las políticas de permisos del entorno).
- **Límites de Workspace y Aislamiento:**
  - Todas las operaciones de lectura y escritura deben circunscribirse al workspace activo del proyecto.
  - **PROHIBIDO** intentar inspeccionar o modificar rutas absolutas externas al workspace (e.g., `/mnt/...`, particiones ajenas, prefijos de Wine, directorios del sistema operativo).
  - Cualquier integración con recursos externos debe resolverse dentro del workspace mediante configuración explícita o enlaces simbólicos (symlinks) gestionados localmente.
- **Ejecución de Git y Bypass de Sandbox:**
  - Debido a que el evaluador de permisos de Antigravity anula el *prefix matching* si se utilizan comillas o caracteres especiales, **ESTÁ ESTRICTAMENTE PROHIBIDO** usar `git commit -m "..."`. El agente debe escribir siempre el mensaje del commit en un archivo temporal en disco (ej. `.commit_msg`) mediante su API de archivos (`write_to_file`) y luego ejecutar `git commit -F .commit_msg`. Esto asegura que el comando pase limpiamente por las políticas de seguridad (Always Allow).
  - **Comandos de Red y Remotos:** Los comandos que interactúan con servicios remotos (`git push`, `git fetch`, `git pull`, `gh repo ...`) requieren salida a internet y fallan por política dentro del sandbox estándar (`403 not allowed by policy`). El agente **DEBE ejecutarlos directamente con `BypassSandbox: true` desde el primer intento**, sin intentar probarlos previamente dentro del sandbox.
  - Mantener siempre invocaciones atómicas y sin operadores lógicos (`&&`, `||`) para preservar el prefix matching del motor de permisos, tanto para comandos locales como remotos.
