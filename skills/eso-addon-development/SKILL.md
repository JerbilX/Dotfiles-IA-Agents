---
name: eso-addon-development
description: >-
  MANDATORY: You MUST read this skill BEFORE starting any task, lookup, or code change related to Elder Scrolls Online (ESO) addons. It defines the API lookup hierarchy (prioritizing eso-mcp-server tools before local fallback or text search), canonical reference paths, and strict guidelines for Zenimax (EsoUI) addon development. Do NOT skip reading this.
---

# Elder Scrolls Online (ESO) Addon Engineering

Guía de desarrollo y restricciones para la creación de addons en Lua para Elder Scrolls Online bajo el motor de interfaz de Zenimax (EsoUI).

## 1. Política de Información y Consulta (Caché Local First y Eficiencia)

Para acelerar las tareas y evitar demoras innecesarias por navegación web o restricciones de sandbox, rige un protocolo de consulta ágil y flexible:

1. **Nivel 1 — Contexto Local del Addon:**
   * El código del proyecto y módulos existentes son la referencia arquitectónica para patrones de diseño y convenciones internas. Si un patrón de diseño ya existe en producción, se toma como guía.
   * Las suites de pruebas (`tests/`) sirven como referencia para aserciones de regresión y validación de sintaxis, pero sus mocks locales bajo LuaJIT son emulaciones artesanales subordinadas a la documentación oficial de Zenimax (`references/ESOUIDocumentation.txt`). No constituyen la fuente de verdad de la API ni tienen prioridad sobre el motor.
2. **Nivel 2 — Conocimiento del Modelo y Ejecución:**
   * Proceder directamente con constantes y APIs estándar de ZOS y Lua conocidas.
   * La validación técnica se realiza ejecutando la suite de pruebas local (`luajit tests/...`), no mediante inspección previa remota.
3. **Nivel 3 — Referencias Canónicas de EsoUI (Servidor MCP y Archivos Locales):**
   * **3.1 Vía Preferente — Servidor MCP (`eso-mcp-server`):**
     * Si el servidor MCP `eso-mcp-server` está disponible en el entorno, priorizar el uso de sus herramientas especializadas antes de realizar búsquedas directas de texto:
       * **Búsqueda y Consulta de API/UI:**
         * `eso_search_api`: Búsqueda estructurada sobre funciones, eventos, enums y constantes.
         * `eso_get_constant`: Consulta directa del valor y metadatos de constantes específicas.
         * `eso_get_enum`: Inspección de enums y sus valores miembros.
         * `eso_get_function`: Consulta de signatura, parámetros y retornos de funciones del motor.
         * `eso_get_event`: Consulta de signatura de eventos y sus argumentos de callback.
         * `eso_search_strings`: Búsqueda de cadenas de texto y constantes `SI_*`.
         * `eso_api_stats`: Estadísticas y cobertura de la API indexada.
       * **Inspección de Estado y Persistencia (`SavedVariables`):**
         * Herramientas de solo lectura, diagnóstico e inspección estructural (sin mutación ni escritura en disco):
           * `eso_savedvars_inspect`: Resumen estructural y metadatos del archivo de variables guardadas.
           * `eso_savedvars_get_account_wide`: Lectura e inspección de configuraciones a nivel de cuenta (`ZO_SavedVars:NewAccountWide`).
           * `eso_savedvars_get_character`: Lectura e inspección de configuraciones a nivel de personaje (`ZO_SavedVars:NewCharacterIdSettings`).
           * `eso_savedvars_query`: Consultas dirigidas a claves o rutas específicas dentro de las tablas guardadas.
         * Utilizar estas herramientas para diagnosticar y verificar variables persistidas en lugar de parsear manualmente archivos `.lua` en disco.
   * **3.2 Vía Fallback — Referencias Canónicas Locales (Instantáneas y Auto-actualizables):**
     * Si las herramientas MCP no están disponibles o no devuelven resultados para una consulta, pasar de forma automática e inmediata al flujo local de búsqueda directa de texto (`grep_search` / `view_file`):
       * `~/.gemini/config/skills/eso-addon-development/references/ESOUIDocumentation.txt`: Documentación oficial de la API de C/Lua, funciones globales, enums y constantes del motor (ej. `ITEMTYPE_*`, `SPECIALIZED_ITEMTYPE_*`, eventos).
       * `~/.gemini/config/skills/eso-addon-development/references/localizegeneratedstrings.lua`: Mapeo oficial de cadenas legibles de la interfaz y tooltips en inglés a IDs de cadenas y enums (ej. `"Scroll"` -> `SI_SPECIALIZEDITEMTYPE105`).
     * **Flujo para textos visibles de la interfaz / Tooltips (vía local):**
       1. Si el usuario proporciona una captura o un texto en pantalla (ej. `"Scroll"`): buscar dicho texto en `~/.gemini/config/skills/eso-addon-development/references/localizegeneratedstrings.lua` mediante `grep_search` para obtener el identificador de string (ej. `SI_SPECIALIZEDITEMTYPE105`).
       2. Contrastar el número de enum o nombre resultante con `~/.gemini/config/skills/eso-addon-development/references/ESOUIDocumentation.txt` para obtener la constante Lua equivalente (`SPECIALIZED_ITEMTYPE_TROPHY_SCROLL`).
     * **Principio de Suficiencia y Corte Inmediato (Anti-Paranoia):**
       * Una vez identificada una constante candidata razonable (vía MCP o archivos locales), **asumirla como válida e implementarla directamente**.
       * No realizar búsquedas secundarias ni explorar árboles de GitHub para sobre-verificar el origen del string; la validación técnica corresponde a la suite de pruebas del proyecto (`luajit tests/...`).
     * **Sincronización Autónoma de Versión (Just-in-Time):**
       * La primera línea de `references/ESOUIDocumentation.txt` certifica la versión de API activa (ej. `h1. ESO UI Documentation for API Version 101051`).
       * Si el manifiesto del addon (`.txt`) declara una versión superior o se requiere una versión recién publicada por ZOS, ejecutar de forma autónoma `scripts/update_esoui_docs.sh` (con bypass de sandbox si requiere red) para refrescar ambos archivos locales.
4. **Nivel 4 — Failsafe, Circuit Breaker y Freno Obligatorio (Stop & Ask):**
   * Si tras agotar las herramientas del servidor MCP y los archivos locales de referencia un término, constante o API no aparece, o si tras implementarlo las pruebas fallan con un error no resuelto de la API:
     * **Disyuntor (Circuit Breaker):** Limitarse a un máximo de 1 consulta dirigida al repositorio oficial en GitHub (`https://github.com/esoui/esoui`) o al endpoint raw correspondiente.
     * **Freno Obligatorio (Stop & Ask):** Si tras agotar tanto el MCP como la documentación local y la consulta única de failsafe la API/constante no se encuentra, **detener la ejecución inmediatamente y consultar al usuario** antes de forzar soluciones, inventar signaturas o asumir parámetros.

### Criterio de Proporcionalidad y Flujo de Trabajo
* **Tareas Incrementales y Atómicas:** Adiciones como agregar una categoría a un filtro existente, sumar opciones a LibAddonMenu, manejar un evento conocido o ajustes lógicos menores son tareas rutinarias. **Proceder directamente a la edición de código y ejecución de pruebas**, reservando la creación formal de `implementation_plan.md` exclusivamente para refactorizaciones arquitectónicas mayores de múltiples módulos o si el usuario lo solicita expresamente.
* **Abstracción por tipos:** Priorizar la clasificación por categorías del motor (`ItemType`, `SpecializedItemType`). Evitar compilar listas manuales de `itemId` numéricos en wikis de terceros cuando el motor ya provee constantes tipadas.
* **Librerías de terceros:** Para dependencias declaradas (`LibAddonMenu-2.0`, `LibCharacterKnowledge`), consultar la documentación o código de la biblioteca específica.

## 2. Principios Arquitectónicos en Lua para ESO

1. **Aislamiento de Namespace (Zero Global Pollution):**
   * Todo addon debe encapsular su estado en una tabla única con su identificador:
     ```lua
     MyAddonName = MyAddonName or {}
     local MyAddon = MyAddonName
     ```
   * Prohibido declarar variables o funciones locales como globales sin prefijo.

2. **Ciclo de Vida y Carga (`EVENT_ADD_ON_LOADED`):**
   * Todo registro de evento de inicio debe validar estrictamente que el addon que disparó el evento sea el propio:
     ```lua
     local function OnAddOnLoaded(eventCode, addOnName)
         if addOnName ~= MyAddon.name then return end
         EVENT_MANAGER:UnregisterForEvent(MyAddon.name, EVENT_ADD_ON_LOADED)
         MyAddon:Initialize()
     end
     EVENT_MANAGER:RegisterForEvent(MyAddon.name, EVENT_ADD_ON_LOADED, OnAddOnLoaded)
     ```

3. **Persistencia de Datos (SavedVariables):**
   * Utilizar exclusivamente la API provista por el motor:
     * `ZO_SavedVars:NewAccountWide(...)` para configuraciones de cuenta.
     * `ZO_SavedVars:NewCharacterIdSettings(...)` para configuraciones por personaje.
   * Siempre definir y pasar una tabla de valores por defecto (`defaults`).
   * **Diagnóstico e Inspección:** Para auditar, depurar o verificar la estructura y datos de `SavedVariables` persistidas, priorizar las herramientas de solo lectura del MCP (`eso_savedvars_inspect`, `eso_savedvars_get_account_wide`, `eso_savedvars_get_character`, `eso_savedvars_query`) cuando estén disponibles, evitando el parseo manual de archivos `.lua` en disco. Prohibida cualquier asunción de escritura o mutación de variables guardadas a través del MCP (herramientas exclusivamente de lectura).

4. **Hooking No Destructivo:**
   * Utilizar `ZO_PreHook` y `ZO_PostHook` para interceptar funciones del sistema o de la UI.
   * Evitar sobrescribir directamente funciones globales a menos que sea estrictamente indispensable retornar valores custom en un pre-hook que cancele la ejecución original.

5. **Rendimiento y Recolección de Basura:**
   * Evitar la creación continua de tablas efímeras dentro de callbacks de eventos de alta frecuencia.
   * Reutilizar buffers o aplicar técnicas de estrangulamiento (throttling/debounce).

6. **Abstracción por Tipos Nativos vs Hardcoding de IDs:**
   * Clasificar y evaluar ítems mediante la jerarquía de tipos de ZOS (`ItemType`, `SpecializedItemType`, `FilterType`).
   * Prohibido hardcodear listas de `itemId` numéricos a menos que el requerimiento sea una excepción individual irreductible.

7. **Documentación Automática de Comandos Slash:**
   * Cada vez que el addon defina, genere o modifique un comando de chat propio (ej. mediante `SLASH_COMMANDS["/comando"] = funcion`), el agente **DEBE** registrarlo automáticamente en el archivo `README.md` del proyecto.
   * **Exclusión estricta:** Solo deben documentarse los comandos creados o expuestos por el propio addon. Queda prohibido listar comandos nativos de EsoUI o de otros addons, incluso si el código los intercepta o invoca.
   * El registro debe incluir el comando exacto y una breve descripción de su función.

8. **Sincronización de Dependencias (Manifest vs README):**
   * Toda modificación (adición o eliminación) en la directiva `## DependsOn:` del manifiesto del addon (`.txt`) **DEBE** reflejarse inmediatamente en la sección de dependencias del archivo `README.md`.
   * **Fuente de verdad y resolución de conflictos:** El manifiesto (`.txt`) es la autoridad técnica para el motor. Sin embargo, si al auditar un proyecto existente el agente detecta una asimetría (dependencias en el README que no están en el manifiesto, o viceversa), **NO debe unificarlas automáticamente**. Debe detenerse, reportar la discrepancia exacta y consultar al usuario cuál es el estado deseado antes de mutar los archivos.

9. **Single Source of Truth (SSoT) para Metadatos e Inyección en Build:**
   * **Manifiesto como Única Fuente:** El archivo manifiesto (`.txt`) del addon es la autoridad exclusiva para la versión (`## Version: X.Y.Z`).
   * **Prohibición de Hardcoding:** Queda estrictamente prohibido definir la versión explícitamente en los archivos `.lua`. En su lugar, el código debe utilizar un token estático de reemplazo:
     ```lua
     local VERSION = "@BUILD_VERSION@"
     -- o en la tabla global: MyAddon.version = "@BUILD_VERSION@"
     ```
   * **Empaquetado Centralizado (Build-Time Injection):** Para compilar o empaquetar una release del addon, el agente **DEBE** utilizar el script centralizado de esta skill. Este script genera un artefacto limpio en la carpeta `dist/` e inyecta la versión real (obtenida del manifiesto) reemplazando el token `@BUILD_VERSION@`, manteniendo el código fuente intacto.
     * **Comando de ejecución:** `~/.gemini/config/skills/eso-addon-development/scripts/build_release.sh <ruta_al_directorio_del_addon>`

10. **Prevalencia del Motor de EsoUI sobre los Mocks de Pruebas (Anti-Test-Induced Damage):**
    * **Autoridad Canónica:** La autoridad canónica de la API es Zenimax y su documentación oficial local (`references/ESOUIDocumentation.txt`).
    * **Protocolo ante Fallas en Tests:** Si una llamada, evento o filtro nativo válido del motor (ej. `EVENT_MANAGER:AddFilterForEvent`, filtrado estricto por `ITEMTYPE_WEAPON`/`ITEMTYPE_ARMOR`) falla en la suite de pruebas porque los mocks o fixtures de `tests/` carecen del método, propiedad o atributo, **el agente DEBE actualizar los mocks y fixtures de prueba** para alinearlos con la API oficial.
    * **Prohibición de Comprobaciones Defensivas Artificiales:** Queda terminantemente prohibido introducir comprobaciones defensivas artificiales (ej. `if API_EXISTS then`, `if EVENT_MANAGER.AddFilterForEvent then`) o degradar optimizaciones y filtros en el código de producción del addon para complacer un mock incompleto o desactualizado.

## 3. Protocolo de Mejora Continua (Self-Improvement)

Si durante el desarrollo se identifica:
* Una función nativa de EsoUI marcada como obsoleta (*deprecated*) o reemplazada en la versión de API actual.
* Una discrepancia crítica entre el comportamiento documentado y la ejecución real.
* Un patrón idiomático recurrente de la API de ZOS que no esté contemplado aquí.

El agente **DEBE alertar al usuario al concluir la tarea** y proponer la adición correspondiente para actualizar este skill en el repositorio `AGY-Skills`.
