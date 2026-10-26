# Referencia: Arquitectura y Principios de Diseño en Lua para EsoUI

Guía técnica y procedimental de runtime y estándares de ingeniería para el desarrollo de addons en Lua bajo el motor de interfaz de Zenimax (EsoUI).

---

## 1. Aislamiento de Namespace (Zero Global Pollution)

Todo addon debe encapsular su estado interno, funciones y configuraciones en una única tabla global identificada con el nombre canónico del proyecto:

```lua
MyAddonName = MyAddonName or {}
local MyAddon = MyAddonName
```

* **Prohibición de Polución Global:** Prohibido declarar variables, tablas o funciones fuera del namespace del addon o sin el calificador `local`.
* **Exportación Controlada:** Solo la tabla raíz del addon debe exponerse al ámbito global para interoperabilidad con otros addons o comandos slash.

---

## 2. Ciclo de Vida y Carga (`EVENT_ADD_ON_LOADED`)

El evento `EVENT_ADD_ON_LOADED` se dispara secuencialmente para cada addon instalado durante el arranque del cliente y las recargas de interfaz (`/reloadui`):

```lua
local function OnAddOnLoaded(eventCode, addOnName)
    if addOnName ~= MyAddon.name then return end
    EVENT_MANAGER:UnregisterForEvent(MyAddon.name, EVENT_ADD_ON_LOADED)
    MyAddon:Initialize()
end

EVENT_MANAGER:RegisterForEvent(MyAddon.name, EVENT_ADD_ON_LOADED, OnAddOnLoaded)
```

* **Validación de Identidad Obligatoria:** Todo callback de `EVENT_ADD_ON_LOADED` debe verificar estrictamente que `addOnName` coincida con el nombre registrado del addon antes de ejecutar la inicialización.
* **Desregistro Inmediato:** Invocar `EVENT_MANAGER:UnregisterForEvent` inmediatamente tras confirmar la coincidencia para liberar memoria y evitar ejecuciones espurias.

---

## 3. Persistencia de Datos (`SavedVariables`)

La persistencia de configuraciones de usuario entre sesiones debe implementarse exclusivamente a través de la API oficial provista por EsoUI:

* **Configuraciones de Cuenta (Account-Wide):**
  ```lua
  MyAddon.savedVars = ZO_SavedVars:NewAccountWide(
      "MyAddonSavedVars", -- Nombre de tabla en archivo .lua
      1,                  -- Versión de esquema de variables
      nil,                -- Perfil (opcional)
      defaults            -- Tabla con valores por defecto
  )
  ```
* **Configuraciones por Personaje (Character-Specific):**
  ```lua
  MyAddon.savedVars = ZO_SavedVars:NewCharacterIdSettings(
      "MyAddonSavedVars",
      1,
      nil,
      defaults
  )
  ```
* **Tabla de Valores por Defecto (`defaults`):** Siempre definir una tabla inmutable con los valores iniciales para garantizar fallback determinista ante claves ausentes tras migraciones de versión.
* **Diagnóstico e Inspección Estructural:**
  * Para auditar, depurar o verificar la estructura y datos de `SavedVariables` persistidas, priorizar las herramientas de solo lectura del servidor MCP (`eso_savedvars_inspect`, `eso_savedvars_get_account_wide`, `eso_savedvars_get_character`, `eso_savedvars_query`) cuando estén disponibles, evitando el parseo manual de archivos `.lua` en disco.
  * **Invariante de Solo Lectura:** Prohibida cualquier asunción de escritura o mutación de variables guardadas a través de herramientas MCP (operan con estricta inmutabilidad).

---

## 4. Hooking No Destructivo

La interceptación de funciones nativas del motor o de componentes de la interfaz debe realizarse preservando la integridad del pipeline de ejecución:

* **Pre-Hooking (`ZO_PreHook`):**
  * Utilizar para validaciones o cancelaciones condicionales.
  * Si el callback retorna `true`, la ejecución de la función original se aborta; si retorna `false` o `nil`, la función original continúa normalmente.
* **Post-Hooking (`ZO_PostHook`):**
  * Utilizar para extender comportamiento o reaccionar a cambios en la interfaz tras la finalización de la función base.
* **Prohibición de Sobrescritura Destructiva:** Prohibido reasignar funciones globales (`TargetFunction = MyCustomFunction`) salvo cuando sea técnicamente imposible resolver la necesidad mediante los hooks del motor.

---

## 5. Rendimiento y Recolección de Basura

El recolector de basura de Lua puede introducir tirones de rendimiento (*frame drops*) si se generan asignaciones masivas en bucles críticos:

* **Eventos de Alta Frecuencia:** En eventos recurrentes (ej. `EVENT_RETICLE_TARGET_CHANGED`, `EVENT_COMBAT_EVENT`, actualizaciones por cuadro en `OnUpdate`), evitar instanciar tablas temporales o concatenar cadenas dinámicamente dentro del callback.
* **Reutilización de Buffers:** Reutilizar estructuras preasignadas y aplicar técnicas de estrangulamiento (*throttling*) o desrebote (*debouncing*) cuando el flujo de eventos exceda la tasa de refresco requerida por el usuario.

---

## 6. Abstracción por Tipos Nativos vs Hardcoding de IDs

* **Jerarquía Canónica del Motor:** Evaluar y clasificar ítems y entidades utilizando los enums tipados oficiales de ZOS (`ItemType`, `SpecializedItemType`, `FilterType`, `EquipType`).
* **Prohibición de Listas Quemadas de IDs:** Prohibido compilar o mantener listas manuales de identificadores numéricos (`itemId`) extraídas de bases de datos o wikis de terceros cuando el motor ya provee constantes semánticas y funciones de inspección (`GetItemType`, `GetItemLinkItemType`). Las excepciones individuales deben documentarse puntualmente como tales.
