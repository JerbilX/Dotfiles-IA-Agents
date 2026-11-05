# Referencia: Procedimientos de Build, Empaquetado y Sincronización

Guía técnica y operativa para la documentación de comandos, gestión de dependencias, empaquetado de artefactos y alineación entre código de producción y suites de pruebas en addons de Elder Scrolls Online.

---

## 1. Documentación Automática de Comandos Slash

* **Registro Mandatorio en `README.md`:** Cada vez que el addon defina, agregue o modifique un comando de chat propio mediante la tabla del motor (ej. `SLASH_COMMANDS["/comando"] = handler`), el agente **DEBE** documentarlo de forma inmediata en la sección correspondiente del `README.md` del proyecto.
* **Detalle Requerido:** La documentación debe detallar el comando exacto (incluyendo barra diagonal), argumentos esperados si aplica y una descripción concisa de su funcionalidad.
* **Exclusión Estricta:** Solo deben registrarse los comandos creados o expuestos por el propio addon. Queda terminantemente prohibido listar o alterar la documentación de comandos nativos de EsoUI (`/reloadui`, `/script`, etc.) o de addons de terceros, aun cuando el código los intercepte mediante hooks.

---

## 2. Sincronización de Dependencias (Manifiesto vs README)

* **Reflejo Inmediato:** Toda modificación (adición o eliminación) en la directiva `## DependsOn:` del archivo manifiesto del addon (`.txt`) debe reflejarse inmediatamente en la sección de dependencias del archivo `README.md`.
* **Fuente de Verdad y Manejo de Conflictos:**
  * El archivo manifiesto (`.txt`) constituye la autoridad técnica para el cliente de EsoUI.
  * Si durante la auditoría o exploración de un proyecto existente el agente detecta asimetrías (librerías presentes en el `README.md` pero ausentes en el manifiesto, o viceversa), **queda prohibido unificarlas de manera autónoma**.
  * El agente debe detenerse, señalar la discrepancia exacta con los nombres de las librerías afectadas y consultar al usuario cuál es el estado deseado antes de modificar los archivos.

---

## 3. Single Source of Truth (SSoT) para Metadatos e Inyección en Build

* **Manifiesto como Única Fuente de Versión:** El archivo manifiesto (`.txt`) es la autoridad exclusiva para la versión del addon mediante la directiva:
  ```
  ## Version: X.Y.Z
  ```
* **Prohibición de Versiones Quemadas en Código:** Queda estrictamente prohibido definir o actualizar cadenas de versión de forma estática dentro de los archivos `.lua`. En su lugar, el código fuente debe utilizar el token de compilación canónico:
  ```lua
  local VERSION = "@BUILD_VERSION@"
  -- o asignado al namespace del addon:
  MyAddon.version = "@BUILD_VERSION@"
  ```
* **Empaquetado Centralizado con Inyección en Build-Time:** Para empaquetar una release lista para distribución, se debe utilizar el script de empaquetado de este skill:
  ```bash
  ~/.gemini/config/skills/eso-addon-development/scripts/build_release.sh <ruta_al_directorio_del_addon>
  ```
  *(O mediante el comando registrado `eso-build <ruta_al_directorio_del_addon>` si se encuentra en `$PATH`).*
  * El script lee la versión del manifiesto, copia el código excluyendo archivos innecesarios (tests, git, docs internas), inyecta la versión real reemplazando el token `@BUILD_VERSION@` y genera un artefacto comprimido listo para distribución en `dist/`, dejando el código fuente de desarrollo inalterado.

---

## 4. Prevalencia del Motor de EsoUI sobre los Mocks de Pruebas (Anti-Test-Induced Damage)

* **Autoridad Canónica:** La autoridad técnica canónica de la API es Zenimax y su documentación oficial de interfaz (`references/ESOUIDocumentation.txt`).
* **Bifurcación ante Fallas en Tests:**
  * Si una llamada, signatura, constante o evento nativo válido de EsoUI (ej. `EVENT_MANAGER:AddFilterForEvent`, constantes tipadas `ITEMTYPE_*`) genera errores o aserciones fallidas en la suite de pruebas locales (`tests/`), el agente **DEBE actualizar y sincronizar los mocks y fixtures de prueba** para alinearlos con el contrato real de la API oficial.
  * Los mocks bajo LuaJIT son emulaciones artesanales de soporte; nunca deben dictar el diseño ni degradar la compatibilidad con el motor real.
* **Prohibición de Comprobaciones Defensivas Artificiales:** Queda terminantemente prohibido introducir comprobaciones defensivas artificiales en el código de producción (tales como `if API_EXISTS then`, comprobaciones de existencia de métodos nativos, o desactivación de filtros válidos) con el único fin de complacer un mock incompleto o desactualizado.

---

## 5. Estándares del Arnés de Pruebas (Test Harness Standards)

Para mitigar desbordes de buffer (`CONTEXT_TRUNCATION`) y saturación de la ventana de contexto durante el ciclo de desarrollo asistido por IA y pipelines CI/CD, las suites de pruebas locales (`tests/run.lua` o ejecutores afines) deben adherirse a los siguientes estándares de salida y arquitectura:

* **Reporter Conciso y Límite de Salida Estándar:**
  * En ejecuciones exitosas, el arnés de pruebas **DEBE** emitir un reporte compacto y sintético (estilo TAP resumido o recuento conciso: `N tests passed, 0 failed`), garantizando una salida total inferior a **50 líneas** en stdout.
  * Queda prohibido emitir logs informativos línea por línea (`print("Checking item X...")`) de forma predeterminada cuando las pruebas pasan satisfactoriamente.
* **Supresión de Volcados Masivos de Tablas (Anti-Table-Dumps):**
  * Queda estrictamente prohibido volcar estructuras de datos completas, tablas complejas o mocks crudos a stdout durante aserciones fallidas (evitar serializadores recursivos indiscriminados tipo `dumptable` o volcados de `_G`).
  * En caso de aserción fallida, el reporte de error debe limitarse exclusivamente a:
    1. Archivo y línea de la falla.
    2. Nombre o descripción concisa del test/aserción.
    3. Valor esperado vs. valor recibido (acotado a escalares o claves relevantes).
    4. Stack trace acotado y legible (sin bucles de inspección).
* **Modo Silencioso / Compacto por Defecto:**
  * La ejecución estándar del arnés (`luajit tests/run.lua` o `lua tests/run.lua`) debe operar en modo silencioso o conciso.
  * La verbosidad detallada o volcados adicionales deben quedar condicionados a una bandera explícita (ej. `--verbose` o `-v`), garantizando que las invocaciones por defecto desde herramientas de automatización (`run_command`) preserven la ventana de contexto.
* **Diseño y Actualización Atómica de Mocks (Anti-Ping-Pong):**
  * Para prevenir ciclos pendulares de edición fragmentaria (`PING_PONG_TOOL_LOOP`), queda prohibido realizar ediciones microscópicas sucesivas alternadas con ejecuciones de prueba para inferir gradualmente las dependencias faltantes en el arnés.
  * Los arneses de mock en `tests/` deben modelar desde su diseño inicial las entidades y métodos canónicos requeridos (`WINDOW_MANAGER`, `GuiRoot`, métodos de control: `SetAnchor`, `ClearAnchors`, `SetDimensions`, `SetHidden`, `SetHandler`, etc.).
  * Ante discrepancias con el contrato oficial, consultar la documentación canónica (`references/ESOUIDocumentation.txt`) y sincronizar el mock de forma atómica y completa en una sola edición.
* **Ejecución Atómica de Pruebas (Anti-Terminal-Pipelining):**
  * Queda prohibido ejecutar suites de pruebas mediante bucles de terminal (`for f in tests/test_*.lua; do luajit "$f"; done`), tuberías con wrappers o construcciones complejas. Estas estructuras rompen el prefix matching de comandos en sandbox y degradan la trazabilidad de auditoría.
  * Invocación Canónica: Ejecutar las pruebas siempre mediante comandos o runners CLI atómicos:
    * Runner centralizado: `luajit tests/run.lua`
    * Test puntual específico: `luajit tests/test_journal.lua`

