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

---

## 7. Centralización de Constantes y Metadatos

Para prevenir la dispersión de literales (*magic strings* y *magic numbers*) y facilitar el mantenimiento, todo addon debe consolidar sus metadatos y parámetros operativos en un módulo de constantes dedicado.

### 7.1 Carga Temprana en el Manifiesto (`.txt`)
El archivo de definición de constantes (ej. `src/Constants.lua`) debe posicionarse en el manifiesto antes de cualquier archivo de inicialización o lógica de negocio (ej. `src/Init.lua`, `src/Main.lua`):

```lua
## Title: MyAwesomeAddon
## APIVersion: 101044
## SavedVariables: MyAwesomeAddonSavedVars

# 1. Definición de Constantes y Metadatos (Carga temprana)
src/Constants.lua

# 2. Inicialización y Núcleo del Addon
src/Init.lua

# 3. Lógica de Dominio e Interfaz
src/UI.lua
src/Main.lua
```

### 7.2 Encapsulamiento en Namespace (Cero Polución Global)
Las constantes deben estructurarse exclusivamente bajo el subespacio del addon (`Addon.Constants` o `MyAddon.Constants`), garantizando estricto aislamiento de `_G`:

```lua
-- src/Constants.lua
MyAddon = MyAddon or {}

MyAddon.Constants = {
    -- Metadatos del Addon
    METADATA = {
        NAME = "MyAwesomeAddon",
        TITLE = "My Awesome Addon",
        VERSION = "1.0.0",
        AUTHOR = "AuthorName",
    },

    -- Parámetros de Persistencia (SavedVariables)
    SAVED_VARS = {
        NAME = "MyAwesomeAddonSavedVars",
        VERSION = 1,
    },

    -- UI, Chat e Interfaz
    UI = {
        CHAT_PREFIX = "|cFFD700[MyAddon]|r ",
        KEYBINDINGS = {
            TOGGLE = "MYADDON_TOGGLE_WINDOW",
        },
        COLORS = {
            SUCCESS = "22C55E",
            ERROR = "EF4444",
            WARNING = "F59E0B",
        },
    },

    -- Límites y Reglas de Dominio
    LIMITS = {
        MAX_TRACKED_ITEMS = 100,
        THROTTLE_MS = 250,
        DEFAULT_REFRESH_RATE_SEC = 5,
    },
}
```

### 7.3 Categorías Canónicas Obligatorias
Toda tabla de constantes debe clasificar sus valores según los siguientes dominios:
* **Metadatos del Addon:** Identificadores fundamentales del proyecto (`ADDON_NAME`, `ADDON_TITLE`, `ADDON_VERSION`, `ADDON_AUTHOR`).
* **Persistencia:** Nombre de tabla persistida (`SAVED_VARS_NAME`) y versión de esquema (`SAVED_VARS_VERSION`), referenciados directamente al invocar `ZO_SavedVars`.
* **UI / Chat / Interfaz:** Prefijos de consola formateados (`CHAT_PREFIX`), identificadores de enlaces de teclado (*keybindings*) y códigos hexadecimales de color para mensajería y controles.
* **Límites y Reglas de Dominio:** Capacidades máximas, frecuencias de refresco, tiempos de expiración (*timeouts*) y umbrales operacionales.

### 7.4 Inmutabilidad y Cero Magic Strings / Numbers
* **Prohibición de Literales Quemados:** Prohibido introducir cadenas de texto hardcodeadas o números mágicos en submódulos de eventos, cálculos o interfaces.
* **Consumo Canónico:** Los módulos de inicialización y lógica deben consumir las constantes exclusivamente mediante el namespace:

```lua
-- src/Init.lua
local Addon = MyAddon
local C = Addon.Constants

function Addon:Initialize()
    self.savedVars = ZO_SavedVars:NewAccountWide(
        C.SAVED_VARS.NAME,
        C.SAVED_VARS.VERSION,
        nil,
        self.defaults
    )

    d(C.UI.CHAT_PREFIX .. "Addon inicializado v" .. C.METADATA.VERSION)
end
```

---

## 8. Jerarquía y Creación de Controles de Interfaz (`EsoUI Controls`)

La creación dinámica de controles de interfaz mediante la API de Zenimax exige respetar las convenciones del motor de interfaz de EsoUI:

### 8.1 Creación y Jerarquía de Ventanas de Nivel Superior (`CT_TOPLEVELCONTROL`)
* **Vía Canónica Recomendada (`CreateTopLevelWindow`):** Para instanciar una ventana o control de nivel superior, la API dedicada y directa provista por el motor es `CreateTopLevelWindow`:
  ```lua
  local myWindow = WINDOW_MANAGER:CreateTopLevelWindow("MyAddonTopLevelWindow")
  ```
* **Uso de `CreateControl` con `GuiRoot`:** Si se crea mediante `WINDOW_MANAGER:CreateControl` (o `CreateControl`) utilizando el tipo `CT_TOPLEVELCONTROL`, EsoUI requiere que el control padre (`parent`) sea `GuiRoot`:
  ```lua
  local myWindow = WINDOW_MANAGER:CreateControl("MyAddonTopLevelWindow", GuiRoot, CT_TOPLEVELCONTROL)
  ```
  Evitar pasar paneles secundarios o controles nativos como argumento `parent` al crear un `CT_TOPLEVELCONTROL`.
* **Integración Visual y Anclaje (`SetAnchor`):** Para posicionar o integrar visualmente una ventana a un panel nativo (ej. `ZO_SharedRightPanelBackground`, paneles de inventario o diario), se debe mantener la ventana en el nivel superior y vincularla espacialmente mediante `:SetAnchor()`:
  ```lua
  myWindow:SetDimensions(350, 500)
  myWindow:ClearAnchors()
  myWindow:SetAnchor(TOPLEFT, ZO_SharedRightPanelBackground, TOPLEFT, 10, 10)
  ```
* **Controles Secundarios (`CT_CONTROL`):** Si se desea anidar controles directamente dentro de un contenedor o panel secundario existente sin crear una ventana independiente, se debe utilizar `CT_CONTROL` (o tipos derivados como `CT_LABEL`, `CT_BUTTON`, `CT_TEXTURE`), asignando el contenedor destino como `parent`.

