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
* **Diferenciación Canónica de Anclaje y Anti-Patrón Multicolumna:**
  Al posicionar o integrar visualmente una ventana de nivel superior dentro de escenas nativas (ej. el diario de misiones `ZO_QuestJournal` o escenas de inventario), es crítico distinguir entre el contenedor de escena completo y los fondos secundarios de columna derecha:
  * **Anti-patrón de Anclaje Multicolumna (`ZO_SharedRightPanelBackground`):** En el motor EsoUI, `ZO_SharedRightPanelBackground` corresponde exclusivamente al fondo apergaminado de la columna derecha de detalles (iniciada en X ≈ 560 px). Anclar un panel completo de 2 columnas (ancho típico ~1000 px: navegación a la izquierda y detalles a la derecha) a `ZO_SharedRightPanelBackground` desplaza la lista de navegación al centro-derecha, deja vacío el 40-50% izquierdo del diario nativo y desborda la columna de detalles fuera de la pantalla.
  * **Anclaje de Escena Completa / Multicolumna:** Ventanas o paneles que abarcan la escena completa del diario (layout de dos columnas, ancho ~1000 px) deben anclarse al contenedor de escena principal (`ZO_QuestJournal`) o a la huella derecha completa (`ZO_RightPanelFootPrint`):
    ```lua
    -- Correcto: Panel completo de 2 columnas anclado al contenedor de escena nativo
    myJournalWindow:SetDimensions(1000, 700)
    myJournalWindow:ClearAnchors()
    myJournalWindow:SetAnchor(TOPLEFT, ZO_QuestJournal, TOPLEFT, 0, 0)
    myJournalWindow:SetAnchor(BOTTOMRIGHT, ZO_QuestJournal, BOTTOMRIGHT, 0, 0)
    ```
  * **Anclaje de Sub-Panel de Columna Derecha (Unicolumna):** El anclaje a `ZO_SharedRightPanelBackground` es válido exclusivamente para sub-paneles o vistas de una sola columna (ancho ~450-500 px) diseñadas para residir dentro del panel de detalles derecho:
    ```lua
    -- Correcto: Sub-panel de detalles (1 sola columna) anclado al fondo apergaminado derecho
    myDetailsSubPanel:SetDimensions(450, 600)
    myDetailsSubPanel:ClearAnchors()
    myDetailsSubPanel:SetAnchor(TOPLEFT, ZO_SharedRightPanelBackground, TOPLEFT, 10, 10)
    ```
* **Controles Secundarios (`CT_CONTROL`):** Si se desea anidar controles directamente dentro de un contenedor o panel secundario existente sin crear una ventana independiente, se debe utilizar `CT_CONTROL` (o tipos derivados como `CT_LABEL`, `CT_BUTTON`, `CT_TEXTURE`), asignando el contenedor destino como `parent`.

---

## 9. Controles de Entrada Interactiva de Texto (`CT_EDITBOX`)

La captura de texto dinámico del usuario (formularios, notas, títulos, descripciones de misiones) mediante controles `CT_EDITBOX` exige configuraciones explícitas de motor y arneses herméticos para evitar fallos de renderizado o pérdida de foco:

### 9.1 Configuración Obligatoria en Runtime EsoUI
* **Jerarquía con Fondo (`CT_BACKDROP`):** En EsoUI, los controles `CT_EDITBOX` son invisibles per se y carecen de bordes. Deben crearse como hijos de un `CT_BACKDROP` (ej. instanciado con plantilla nativa como `ZO_DefaultBackdrop` o configurado con texturas de borde/centro) para delimitar el área interactiva:
  ```lua
  local bg = WINDOW_MANAGER:CreateControl("MyAddonEditBackdrop", parentContainer, CT_BACKDROP)
  bg:SetDimensions(300, 32)
  bg:SetAnchor(TOPLEFT, parentContainer, TOPLEFT, 0, 0)

  local editBox = WINDOW_MANAGER:CreateControl("MyAddonEditBox", bg, CT_EDITBOX)
  editBox:SetAnchorFill()
  ```
* **Tipografía Obligatoria (`SetFont`):** Todo `CT_EDITBOX` debe definir explícitamente una fuente del motor (`ZoFontGame`, `ZoFontEditBox`, `ZoFontGameLarge`). Omitir `SetFont` provoca que el texto ingresado sea invisible o genere fallos de métricas en el renderizado.
* **Límite de Longitud (`SetMaxInputChars`):** Es imperativo acotar la longitud máxima de entrada (`editBox:SetMaxInputChars(maxLength)`) para proteger la integridad de las `SavedVariables` y prevenir desbordamientos visuales o saturación de memoria.
* **Modo Multilínea (`SetMultiLine`):** Para entradas narrativas, notas o descripciones extensas, habilitar explícitamente `editBox:SetMultiLine(true)`. Por defecto, los editboxes son de una sola línea (`SetMultiLine(false)`).
* **Control de Foco y Habilitación:**
  * Invocar `editBox:SetEditEnabled(true)` para habilitar edición.
  * Gestionar el foco mediante `editBox:TakeFocus()` y `editBox:LoseFocus()`. Para entradas en pantalla completa o ventanas modales, interceptar `OnFocusLost` para confirmar o cancelar la edición.
* **Manejador de Cambios (`OnTextChanged`):**
  * Registrar siempre el callback `OnTextChanged` evaluando el parámetro booleano `isUserInteraction`:
    ```lua
    editBox:SetHandler("OnTextChanged", function(control, isUserInteraction)
        if not isUserInteraction then return end -- Ignorar actualizaciones programáticas via SetText
        local text = control:GetText()
        MyAddon:OnUserInput(text)
    end)
    ```
  * Distinguir `isUserInteraction` evita bucles infinitos de sincronización entre el estado del modelo y la vista.

### 9.2 Emulación y Mocks Herméticos en Pruebas Unitarias (`eso_ui_mock.lua`)
En suites unitarias herméticas ejecutadas fuera del cliente (ej. CLI de Lua o Busted):
* **Firma de Métodos Requerida:** El mock de `CT_EDITBOX` debe implementar como mínimo:
  * `SetText(text)` y `GetText()` -> string.
  * `SetFont(font)` y `GetFont()` -> string.
  * `SetMaxInputChars(max)` y `GetMaxInputChars()` -> number.
  * `SetMultiLine(multiLine)` y `IsMultiLine()` -> boolean.
  * `SetEditEnabled(enabled)` y `IsEditEnabled()` -> boolean.
  * `TakeFocus()`, `LoseFocus()` y `HasFocus()` -> boolean.
  * `SelectAll()` -> nil.
  * `SetCursorPosition(pos)` y `GetCursorPosition()` -> number.
* **Comportamiento Fiel del Mock:**
  * Al invocar `SetText(text)`, el mock debe aplicar el límite de caracteres si `maxInputChars` fue definido (truncar con `string.sub(text, 1, max)`).
  * Al disparar eventos registrados con `SetHandler("OnTextChanged", callback)`, el harness debe proveer `(control, isUserInteraction)` de forma determinista para verificar que los callbacks ignoran mutaciones programáticas.

### 9.3 Patrón Canónico de Copiado In-Place y Antipatrón de Modales Secundarios
* **Copiado In-Place Asistido (`TakeFocus` + `SelectAll` + `SetCursorPosition(0)`):** Dado que EsoUI carece de una API nativa para escribir directamente al portapapeles del sistema operativo, el patrón canónico para exportar cadenas de texto, serializaciones compactadas o comprobantes de completitud consiste en:
  1. Utilizar un control `CT_EDITBOX` interactivo o de solo lectura que contenga la información a transferir.
  2. Al interactuar con el control o pulsar el disparador de copiado (ej. botón *"Copiar"*), enfocar el campo, reiniciar el desplazamiento visual y seleccionar todo el texto:
     ```lua
     editBox:TakeFocus()
     editBox:SetCursorPosition(0) -- Previene que cadenas extensas queden visualmente desplazadas o recortadas a la derecha
     editBox:SelectAll()
     ```
  3. Acompañar el elemento con una indicación visual estática e intuitiva (ej. `[Presiona Ctrl+C para copiar al portapapeles]`) para guiar inmediatamente la acción del usuario sin requerir alertas invasivas.
* **Antipatrón de Diseño — Modales Secundarios para Copiado:**
  * Queda estrictamente catalogado como antipatrón de diseño la apertura de ventanas emergentes o diálogos modales secundarios (`ZO_Dialogs_ShowDialog` o toplevels dedicados) cuya única finalidad sea presentar un texto para copiado manual.
  * Estos modales introducen fricción innecesaria, desorientación espacial en la pantalla y obligan al usuario a confirmar o cerrar ventanas superpuestas, en contraste con la fluidez de la selección in-place directa en el contenedor activo.

---

## 10. Ciclo de Vida y Formalización de Borradores (`Draft Lifecycle`)

En componentes interactivos que permiten a los jugadores o directores de rol redactar y configurar misiones o contenidos antes de su publicación o inicio, se debe aplicar un ciclo de vida de borrador estricto para prevenir fugas de estado, colisiones de identificadores y confusión visual en la interfaz:

### 10.1 Contrato de Identificador Único (`id`)
* **Estado en Preparación:** Durante la edición, el borrador puede operar con un identificador provisional o mantener `id = nil` mientras se construyen sus objetivos y datos narrativos.
* **Gate de Formalización Obligatorio:** Antes de invocar la activación de la misión (`StartQuest`) o consolidarla en la tabla persistente de misiones activas:
  1. Debe garantizarse la resolución o asignación de un `id` único determinista (o correlativo autoincremental protegido contra colisiones).
  2. Prohibido formalizar una misión con identificador vacío, `nil` o colisionante con registros existentes en `SavedVariables`.

### 10.2 Limpieza Proactiva y Aislamiento de Colecciones
* **Métodos de Saneamiento Explícitos:** El módulo de gestión de borradores debe proveer funciones atómicas de limpieza para toda colección auxiliar temporal:
  * `ClearDraftObjectives()`: Vía canónica para vaciar la lista de objetivos en preparación.
  * `ClearDraftAreas()` / `ClearDraftSteps()`: Limpieza de áreas de interés o etapas asociadas.
  * `ResetDraftState()`: Saneamiento integral del formulario de preparación tras formalizar o descartar.
* **Invariante Post-Formalización:** Inmediatamente tras guardar, publicar o iniciar una misión a partir de un borrador, se debe disparar la limpieza de las colecciones de borrador. Prohibido conservar residuos de objetivos o pasos previos que puedan filtrarse en la edición de un borrador posterior.

### 10.3 Convención Visual Canónica en Listas (`|c3399FF[✎]|r `)
* Para diferenciar nítidamente en listas de interfaz (árboles de navegación, selector de misiones del diario) las misiones formalizadas de aquellas en estado de borrador o preparación:
  * **Prefijo Canónico:** `|c3399FF[✎]|r ` (código de color `#3399FF` / azul claro con glifo de edición `[✎]`).
  * **Formato de Renderizado:**
    ```lua
    local displayName = isDraft and ("|c3399FF[✎]|r " .. questTitle) or questTitle
    ```
  * **Ergonomía:** Provee retroalimentación visual inmediata al usuario sin requerir columnas adicionales ni alterar el ancho de los controles de texto en listas compactas.

---

## 11. Integración Idiomática en ModeBar de Quest Journal (`ZO_QuestJournal_Keyboard.modeBar` y `ZO_SceneFragmentBar`)

Para añadir paneles personalizados a la ventana nativa del diario de misiones (`ZO_QuestJournal_Keyboard`):

### 11.1 Anti-Patrón: Inyección en `MAIN_MENU_KEYBOARD.sceneGroupInfo["journalSceneGroup"]`
* **Problema:** Inyectar una escena raíz directamente en `journalSceneGroup` hace que compita con el menú superior principal (top bar) de EsoUI, corrompiendo la selección visual y el estado de los botones de la barra de pestañas.
* **Solución Canónica:** Tratar la escena de misiones (`questJournal`) como un contenedor unificado y extender exclusivamente la barra de sub-modos interna (`QUEST_JOURNAL_KEYBOARD.modeBar`).

### 11.2 Encapsulamiento en `ZO_FadeSceneFragment` y Sub-Pestañas en `modeBar`
* **Fragmentos de Escena:** Encapsular los paneles o controles del addon dentro de un `ZO_FadeSceneFragment` (o control derivado) y agregarlo como fragmento secundario a la escena `questJournalScene`:
  ```lua
  local fragment = ZO_FadeSceneFragment:New(MyAddonPanelControl)
  QUEST_JOURNAL_SCENE:AddFragment(fragment)
  ```
* **Registro de Sub-Pestaña en `modeBar`:** Utilizar la barra de botones `ZO_SceneFragmentBar` nativa (`QUEST_JOURNAL_KEYBOARD.modeBar`) para agregar la nueva pestaña con su descriptor de botón, callback y fragmentos asociados:
  ```lua
  QUEST_JOURNAL_KEYBOARD.modeBar:Add(MY_ADDON_MODE, fragment, buttonData)
  ```

### 11.3 Hooking Defensivo de `ZO_QuestJournal_Keyboard.OnShowing`
* **Lógica Binaria Nativa:** El manejador nativo `OnShowing` de `ZO_QuestJournal_Keyboard` asume un flujo binario entre misiones estándar y rumores (`Quests` vs `Rumors`). Al abrir el diario, si el modo actual no es `QUEST_JOURNAL_KEYBOARD_MODE_QUESTS`, la lógica de ZOS restablece o selecciona incorrectamente el modo de rumores.
* **Protección de Modo Personalizado:** Hookear preventivamente `OnShowing` (o `ZO_PreHook`) para preservar el modo activo cuando pertenezca al addon, evitando que ZOS sobreescriba la navegación del usuario al alternar entre menús o pestañas.

---

## 12. Calibración de Radio Cartográfico y Normalización en EsoUI (`WorldMap Custom Pins`)

En el sistema cartográfico de EsoUI, las coordenadas y radios operan normalizados en el rango de `[0.0, 1.0]`:

### 12.1 Extensión de Radio y Submapas Urbanos vs Provinciales
* **Normalización Global:** Dado que el plano del mapa abarca de `0.0` a `1.0`, un radio de `0.50` cubre el 100% del diámetro cartográfico disponible.
* **Submapas Urbanos e Interiores (`IsUrbanSubmap`):** En submapas de ciudades o interiores de escala reducida, radios mayores (hasta `0.50`) son válidos para delimitar perímetros amplios del recinto o distrito.
* **Mapas de Zona Provinciales:** En mapas extensos provinciales o regionales (ej. Western Skyrim, Deshaan, Glenumbra), los radios deben calibrarse estrictamente a rangos de exploración locales (típicamente $\le 0.08$ o radios proporcionales de punto de interés) para prevenir que un área de misión cubra la provincia entera.

### 12.2 Jerarquía y Convención de Texturas de Mapas en Capítulos y DLCs Multi-Zona
* **Agrupación en DLCs y Capítulos:** En capítulos y expansiones multi-zona de The Elder Scrolls Online (ej. Greymoor/Western Skyrim, The Reach, Northern/Southern Elsweyr, Thieves Guild, Dark Brotherhood, High Isle, Necrom), ZOS agrupa zonas provinciales completas bajo carpetas compartidas utilizando el sufijo `_base_0` (ej. `maps/skyrim/westernskyrim_base_0`, `maps/skyrim/reach_base_0`, `maps/thieves/hewsbane_base_0`).
* **Discriminación de Mapas Base vs Submapas Urbanos:**
  * **Mapas Provinciales Base (`_base_`):** La presencia de la subcadena `_base_` en la ruta o nombre de la textura identifica invariablemente un mapa de zona provincial o exterior por defecto.
  * **Submapas Urbanos e Interiores Legítimos:** Se caracterizan por carecer de `_base_` en sus sufijos (ej. `maps/skyrim/solitude_0`, `maps/deshaan/mournhold_0`) o por coincidir con identificadores urbanos o recintos tipados (`IsUrbanSubmap`).
* **Prevención de Falsos Positivos Cartográficos:** Queda estrictamente prohibido asumir heurísticas simplistas basadas en que cualquier textura cuyo nombre difiera del nombre de la carpeta contenedora (`maps/<folder>/<folder>_base_0`) es un submapa urbano interior (`SUBMAP_RADIUS = 0.50`). Dicha suposición errónea provoca que la selección de un objetivo al aire libre desborde la provincia entera al asignar un radio metropolitano a una zona provincial completa.

### 12.3 Transición Transparente de Borradores a Misiones Activas y Refresco de Pines
* **Sincronización de Pines con el Ciclo de Vida:** Al formalizar misiones activas y purgar el borrador (`draftAreas` / `draftObjectives`), los gestores de pines deben alternar transparentemente sus fuentes de datos:
  1. Dejar de referenciar las estructuras efímeras del borrador.
  2. Apuntar de inmediato a las áreas y objetivos consolidados de la misión activa.
* **Forzado Obligatorio de Redibujado:** Para sincronizar la interfaz cartográfica inmediatamente sin esperar a que el jugador cambie de mapa o zona:
  ```lua
  ZO_WorldMap_RefreshCustomPins(pinType)
  ```
  Esto garantiza la remoción inmediata de pines/áreas temporales de preparación y el renderizado fiel de los nuevos pines de exploración activos.

---

## 13. Soberanía Contractual del Addon, Pragmatismo P2P y Arquitectura Zero-Reload

El diseño de sistemas distribuidos, sincronización de misiones o herramientas auxiliares en torno a un addon de EsoUI debe respetar las restricciones operativas y el modelo de confianza intrínseco del juego (consistente con ADR-0012):

### 13.1 Soberanía Contractual del Addon (Addon-Driven Data Model)
* **Autoridad Suprema del Esquema:** El addon de Lua es la máxima autoridad del esquema y modelo de datos. Está directamente restringido por las capacidades, eventos y limitaciones de memoria del motor de Zenimax (EsoUI, `LibMapPins`, eventos de retícula, coordenadas cartográficas normalizadas y ciclo de vida de la UI).
* **Subordinación de Sistemas Auxiliares:** Cualquier sistema auxiliar, secundario o periférico (servicios de sincronización, bots comunitarios, visualizadores web, herramientas CLI o scripts externos) debe amoldarse y subordinarse estrictamente al esquema y contratos dictados por el addon, sin forzar abstracciones genéricas o dependencias externas que resulten incompatibles o desalineadas con la ejecución en caliente dentro de ESO.

### 13.2 Pragmatismo P2P y Modelo de Confianza en Rol (Zero Criptofricción)
* **Canal de Transporte Ligero:** La serialización compactada (`LibDeflate` + Base64 alfanumérico URL-safe) debe concebirse exclusivamente como un canal de transporte de datos de bajo tamaño, alta densidad y libre de fricción, optimizado para portapapeles y límites de entrada del motor.
* **Prohibición de Criptoseguridad Inútil en Cliente:** En un cliente Lua público y en actividades colaborativas de rol donde impera la confianza comunitaria y la cooperación lúdica, la criptoseguridad client-side (nonces, firmas HMAC complejas, esquemas anti-falsificación pesados) es conceptualmente ineficaz y añade una sobrecarga de ingeniería desproporcionada.
* **Validación Visual del Máster:** La integridad operativa se sustenta en el principio de confianza interpersonal y en la verificación directa por parte del Game Master (narrador/máster), quien valida visualmente los comprobantes e hitos completados a través de la propia interfaz nativa del addon (ej. contraste de firma determinista o digest Adler32 contra la semilla de la misión sin servicios en la nube).

### 13.3 Arquitectura Zero-Reload In-Game
* **Prioridad Absoluta al Intercambio en Caliente:** Priorizar en todo momento el intercambio directo e interactivo in-game a través de portapapeles o canales de chat (`/rpq quest import` y `/rpq quest completion`) con validación e hidratación inmediata del estado en la UI nativa.
* **Prohibición de Flujos Basados en `/reloadui`:** Queda prohibido diseñar arquitecturas de transporte o integración basadas en archivos en disco (ej. intercambio vía `SavedVariables` externas o directorios compartidos) que obliguen a los jugadores o directores a ejecutar `/reloadui` para sincronizar misiones o completitudes. Toda recarga de interfaz interrumpe la inmersión del rol y degrada críticamente la experiencia de usuario.

---

## 14. Ergonomía de Interacción, Contención de Ruido y Ciclo de Vida Contextual

### 14.1 Cero Ruido en Chat y Compuertas de Logs (Modo Preparación vs Modo Ejecución)
* **Contención Estricta de Telemetría en Chat:** La ventana de chat del jugador es un recurso crítico de comunicación e inmersión; queda prohibida la contaminación con trazas técnicas o mensajes redundantes de depuración durante la experiencia de juego ordinaria.
* **Compuertas de Logs según Contexto Operativo:**
  * Las salidas de telemetría, spikes técnicos, volcados de estado o confirmaciones de edición deben estar confinados exclusivamente al modo de preparación / Game Master o subordinados a banderas explícitas de depuración (`debug = true`).
  * Durante el flujo de juego normal, mantener al mínimo absoluto la salida hacia el chat ordinario del cliente, reservando notificaciones únicamente para errores críticos irrecuperables o feedback indispensable explícitamente solicitado por el usuario.
* **Patrón de Desacoplamiento con Parámetro `silent`:**
  * En módulos de subsistemas, utilidades o spikes técnicos que emiten avisos al chat al ejecutarse manualmente (ej. comandos slash del Master o utilidades como `ActivateAreas(areas, silent)` o `ClearTest(silent)`), sus métodos públicos deben incorporar un parámetro booleano opcional `silent = true`:
    ```lua
    function MyModule:ActivateAreas(areas, silent)
        -- ... ejecución de lógica de áreas ...
        if not silent and Addon.debugMode then
            Addon:Msg("Áreas activadas correctamente para la etapa.")
        end
    end
    ```
  * Al invocar estos métodos desde el ciclo de vida automático del addon (ej. `StartQuest`, `CompleteQuest`, abandono de misión o limpieza de estados), se debe pasar taxativamente `silent = true` para garantizar una experiencia inmersiva limpia y sin residuos de depuración en el chat.

### 14.2 Reactividad y Ciclo de Vida en Controles de Acción Contextuales
* **Visibilidad Subordinada al Estado Activo:** Los controles interactivos de navegación, apertura de mapas o localización (ej. botones `showMapBtn` o accesos directos de cartografía) deben gobernar su visibilidad (`control:SetHidden(...)`) de manera estrictamente reactiva respecto al ciclo de vida y vigencia de la entidad o misión asociada.
* **Ocultamiento Inmediato ante Inactividad o Completitud:** Cuando una misión o etapa transiciona a estado inactivo, completado o descartado, los controles contextuales asociados deben ocultarse de inmediato (`control:SetHidden(true)`) para prevenir acciones inconsistentes o desfasadas con el estado actual del juego.

---

## 15. Dualidad Máster/Jugador en Sistemas P2P y Flujo de Self-Play

En arquitecturas P2P para actividades de rol narrativo, los clientes pueden asumir alternativamente roles de **Game Master** (creador/administrador de la aventura) o de **Jugador** (aventurero ejecutor). Esta coexistencia exige desacoplar estrictamente contratos de datos, controles de UI y flujos de prueba:

### 15.1 Contratos de Datos Asimétricos
* **Registro del Máster (`SavedVariables`):**
  * Almacena las definiciones maestras de misiones creadas o administradas (`savedQuests`), persistiendo la semilla criptográfica secreta (`secretSeed`), borradores editables (`isDraft = true`) y metadatos del autor.
  * Preserva el rol inmutable `role = "MASTER"`, garantizando que la misión exista como registro administrativo independiente de la sesión activa del personaje.
* **Registro del Jugador (`ActiveQuest`):**
  * Consume instancias de misiones hidratadas desde código exportable o importación directa (`isCurrent = true`, `role = "PLAYER"`).
  * Gobierna el seguimiento cuantitativo de objetivos en tiempo de ejecución, el almacenamiento efímero del progreso y la generación del recibo firmado de completitud (`completionCode`) al finalizar.

### 15.2 Segregación de Vistas y Reactividad en la UI (EsoUI)
* **Tagging Semántico en Lista:** En la lista de misiones del diario, cada fila debe prefijarse con un identificador de rol claro y estilizado:
  * Misiones del Máster / Borradores: `|cFFD700[MÁSTER]|r`
  * Misiones en Curso / Jugadas: `|c00FF00[JUGADOR]|r`
* **Paneles de Detalle Asimétricos:**
  * **Vista del Máster:** Expone acciones administrativas (`Exportar Código`, `Probar como Jugador`, `Eliminar`) y la caja interactiva de validación (`validationHeader`, `CT_EDITBOX` y botón `Validar`). Oculta taxativamente los botones de juego ordinario (`Completar Misión`, `Abandonar Misión`).
  * **Vista del Jugador:** Expone seguimiento de objetivos, `Mostrar en mapa`, `Completar Misión`, `Abandonar Misión` y el contenedor con el código de completitud generado tras finalizar. Oculta taxativamente la caja de validación del máster.

### 15.3 Modo de Auto-Prueba Local (Self-Play) y Validación In-Game
* **Prueba en Solitario sin Segundo Cliente:** El Game Master debe poder validar localmente la viabilidad de sus misiones. La acción `SelfTestQuest(quest)` instancia la misión guardada en el motor de juego (`ActiveQuest:StartQuest`) conservando intacto el registro del máster.
* **Validación In-Game y CLI:** Al completar la misión en modo de prueba, el jugador genera un comprobante firmado que el máster puede contrastar inmediatamente contra la semilla secreta de la misión original:
  1. Directamente en la interfaz gráfica mediante la caja de validación (`Journal:ValidateCompletionCode`).
  2. Mediante comando de conveniencia terminal-ready: `/rpq validate <código_completitud>`.

### 15.4 Indexación por Clave Compuesta `(id, role)` y Prevención de Colisiones de Selección
* **Colisión de Identificadores en Modo Dual:** Cuando el máster ejecuta auto-prueba local (`SelfTestQuest`), la misión activa en `ActiveQuest` y la definición persistida en `SavedVariables.savedQuests` comparten idéntico identificador (`id`).
* **Invariante de Búsqueda Multirrol:** Queda prohibido resolver o validar misiones en listas, controladores de selección o refrescos de UI mediante comparaciones directas de clave simple (`q.id == selectedQuest.id`).
* **Patrón Canónico de Indexación:** Toda búsqueda, reasignación o comprobación de selección en la interfaz de usuario debe discriminar obligatoriamente mediante la tupla compuesta `(id, role)` o contrastando `isSaved` frente a `isCurrent`:
  ```lua
  if q.id == self.selectedQuest.id and (self.selectedQuest.role == nil or q.role == self.selectedQuest.role) then
      self.selectedQuest = q
      break
  end
  ```
  Esto previene que la instancia de juego del aventurero enmascare el registro administrativo del máster, garantizando que la caja de validación y las acciones de exportación permanezcan operativas.

---

## 16. Captura Pasiva y Recolección de Entidades en EsoUI (`[E] Take / Interact`)

Los objetivos tradicionales de misiones en MMOs suelen gravitar en torno al combate. Sin embargo, en el rol interactivo son frecuentes las tareas de recolección de fauna ambiental (*critters*), hierbas, minerales o interacción con altares y mecanismos.

### 16.1 Diferenciación Conceptual: Combate vs Interacción Pasiva
* **Objetivos de Eliminación (`KILL`):**
  * Monitorean el pipeline de combate del cliente mediante `EVENT_COMBAT_EVENT`.
  * Requieren filtros de daño letal, cambio de estado de vida o resultados específicos (`ACTION_RESULT_DIED`, `ACTION_RESULT_DIED_XP`).
* **Objetivos de Recolección / Interacción (`COLLECT` e `INTERACT`):**
  * Involucran fauna pasiva que muere o se recoge de un solo golpe/interacción (mariposas, libélulas, antorchas, escarabajos) o nodos recolectables (hierbas alquímicas, vetas, runas, cofres).
  * **Invariante Crítica:** Estas acciones **no** generan eventos convencionales de combate en EsoUI. Monitorearlas a través de `EVENT_COMBAT_EVENT` provocará que el objetivo quede atascado indefinidamente.

### 16.2 Pipeline de Detección e Inspección de Retícula
* **Captura de Contexto de Retícula (`GetGameCameraInteractableActionInfo`):**
  * Al apuntar a una entidad interactuable, consultar la acción del motor antes de la interacción:
    ```lua
    local action, name, interactBlocked, isOwned, additionalInfo = GetGameCameraInteractableActionInfo()
    ```
  * Permite normalizar y asociar nombres en español e inglés (ej. "Tomar", "Take", "Interactuar", "Harvest") sin recurrir a identificadores rígidos.
* **Monitoreo de Entrada en Inventario (`EVENT_LOOT_RECEIVED`):**
  * Para capturas físicas y recolecciones, interceptar la recepción efectiva del ítem:
    ```lua
    local function OnLootReceived(eventCode, receivedBy, itemName, quantity, itemSound, lootType, quest)
        -- Normalizar nombre con zo_strformat(SI_UNIT_NAME, itemName)
        -- Contrastar contra el targetName del objetivo activo y actualizar contadores
    end
    ```
* **Confirmación de Interacción Ambiental (`EVENT_CLIENT_INTERACT_RESULT`):**
  * Para objetos que no depositan ítems en inventario (ej. palancas, libros de atril, estatuas, puertas de cripta), interceptar el resultado de la interacción directa del cliente con el entorno:
    ```lua
    local function OnClientInteractResult(eventCode, result, interactTargetName)
        if result == CLIENT_INTERACT_RESULT_SUCCESS then
            -- Avanzar objetivos de tipo INTERACT
        end
    end
    ```

---

## 17. Exploración Oculta y Narrativa Contextual

Las mecánicas de rol investigativo y deducción geográfica requieren a menudo guiar al aventurero a través de pistas orales o descripciones escritas en lugar de marcadores cartográficos obvios.

### 17.1 Supresión Deliberada de Pines Cartográficos (`hiddenPin` / `noMapMarker`)
* **Preservación del Desafío Narrativo:** Si una zona contiene coordenadas numéricas pero representa un misterio o escondite, dibujar un círculo en el mapa o brújula destruye la experiencia de búsqueda.
* **Filtrado en Gestores de Pines:** Los callbacks registrados en `LibMapPins` y `CustomCompassPins` deben verificar explícitamente las banderas de exploración oculta:
  ```lua
  local function OnMapPinsCallback(pinType)
      for _, area in ipairs(Addon:GetAreas()) do
          if not area.hiddenPin and not area.noMapMarker then
              -- Crear pin en ZO_WorldMap
          end
      end
  end
  ```
  Esto suprime por completo la visibilidad del área en mapas provinciales, submapas urbanos y brújula (`Compass`).

### 17.2 Muestreo Posicional Zonal Periódico
* **Ausencia de Triggers Nativos de Área:** EsoUI carece de un sistema nativo para declarar colisiones geográficas arbitrarias creadas por addons de usuario.
* **Temporizador Periódico de Proximidad (`EVENT_MANAGER:RegisterForUpdate`):**
  * Registrar una rutina periódica con cadencia de bajo impacto (ej. cada 1000 ms a 2000 ms):
    ```lua
    EVENT_MANAGER:RegisterForUpdate("MyAddon_ProximityCheck", 1000, function()
        Addon:CheckProximity()
    end)
    ```
  * En cada iteración:
    1. Validar que el mapa activo coincida con el mapa del área objetivo (`GetMapTileTexture`), aplicando la salvaguarda de mapa abierto y suspensión contextual (§17.4).
    2. Obtener la posición normalizada del jugador con `GetMapPlayerPosition("player")`.
    3. Calcular la distancia euclidiana 2D normalizada:
       $$d = \sqrt{(x_p - x_o)^2 + (y_p - y_o)^2}$$
    4. Evaluar si la distancia es menor o igual al radio de tolerancia del área ($d \le r$).

### 17.3 Detonación Deduplicada de Anuncios Narrativos
* **Prevención de Re-disparos:** Cada área oculta debe mantener un estado local de descubrimiento (`area.discovered = true`). Una vez descubierta, se desactiva el chequeo para dicha área para evitar ráfagas de avisos mientras el jugador camina dentro del perímetro.
* **Anuncio Central en Pantalla (`CENTER_SCREEN_ANNOUNCE`):**
  * Notificar el hallazgo con impacto visual cinematográfico en la interfaz central del jugador:
    ```lua
    if CENTER_SCREEN_ANNOUNCE then
        local params = CENTER_SCREEN_ANNOUNCE:CreateMessageParams(CSA_CATEGORY_LARGE_TEXT, SOUNDS.QUEST_OBJECTIVE_INCREMENT)
        params:SetText(discoveryMessage)
        CENTER_SCREEN_ANNOUNCE:AddMessageWithParams(params)
    end
    ```
* **Preservación del Registro en Chat:** Emitir simultáneamente el texto del hallazgo narrativo en la ventana de chat con prefijo estilizado (`|c00FFFF[Exploración]|r`), garantizando que el jugador pueda releer la pista o descripción incluso después de que desaparezca el texto en pantalla.

---

### 17.4 Salvaguarda Mandatoria de `SetMapToPlayerLocation` y Suspensión Contextual por Discrepancia Cartográfica

En rutinas periódicas de navegación, seguimiento en brújula o muestreo de proximidad, los addons suelen necesitar asegurar que el contexto cartográfico interno de EsoUI apunte a la ubicación real del jugador para obtener coordenadas actualizadas con `GetMapPlayerPosition("player")`. Sin embargo, invocar `SetMapToPlayerLocation()` de manera incondicional introduce graves antipatrones en la experiencia del usuario.

#### 17.4.1 Antipatrón de Bloqueo de `ZO_WorldMap` y Desincronización Zonal
* **Secuestro del Visor Cartográfico:** Si `SetMapToPlayerLocation()` se invoca mientras el jugador tiene abierto el mapa del mundo (`ZO_WorldMap`), el visor es forzado en cada tick de actualización a re-centrarse en la coordenada del personaje. Esto anula por completo la interacción del jugador, bloqueando el zoom-out (impidiendo ver el mapa provincial o global de Tamriel) y el desplazamiento libre (*pan*).
* **Desincronización Textural en Tránsitos de Zona:** Si el personaje cruza fronteras de zona o viaja mediante teleportación y se ejecutan llamadas cartográficas periódicas fuera de contexto, se produce una discrepancia entre las texturas provinciales activas y los marcadores urbanos o de misión, generando parpadeos o asignaciones erróneas de coordenadas.

#### 17.4.2 Salvaguarda Canónica de Mapa Abierto (`IsWorldMapOpen`)
Queda taxativamente prohibido invocar `SetMapToPlayerLocation()` si el mapa mundial está visible en pantalla (`ZO_WorldMap_IsWorldMapShowing()` o `not ZO_WorldMap:IsHidden()`). Todo módulo de muestreo o seguimiento debe encapsular la verificación mediante un helper canónico defensivo:

```lua
local function IsWorldMapOpen()
    if _G.ZO_WorldMap_IsWorldMapShowing and _G.ZO_WorldMap_IsWorldMapShowing() then
        return true
    end
    if _G.ZO_WorldMap and _G.ZO_WorldMap.IsHidden and not _G.ZO_WorldMap:IsHidden() then
        return true
    end
    return false
end
```

* **Regla de Omisión Inmediata:** Si `IsWorldMapOpen()` evalúa como `true`, la rutina de muestreo en segundo plano debe abstenerse estrictamente de llamar a `SetMapToPlayerLocation()`. Si las coordenadas actuales no pueden resolverse limpiamente sin forzar el mapa, la comprobación se omite de forma silente hasta el próximo ciclo.

#### 17.4.3 Refresco Contextual por Proximidad y Suspensión Reactiva (`EVENT_ZONE_CHANGED`)
* **Filtro de Coincidencia de Zona:** Restringir los cómputos de proximidad y reajustes cartográficos exclusivamente a cuando el mapa activo del jugador coincida con el mapa (o submapa) de la misión o punto de interés (`normCurrentMap == normQuestMap`).
* **Suspensión Temporal Fuera de Zona:** Si el jugador se encuentra en una zona distinta (`normCurrentMap ~= normQuestMap`), suspender inmediatamente las comprobaciones periódicas fijando una bandera de estado (`self.isProximitySuspended = true`), evitando ciclos de CPU innecesarios y llamadas cartográficas espurias.
* **Reactivación Reactiva con `EVENT_ZONE_CHANGED`:** Prohibido implementar *polling* continuo para detectar si el jugador regresó a la zona de la misión. La reactivación debe ser exclusivamente reactiva interceptando el evento del motor:
  ```lua
  local function OnZoneChanged(eventCode, zoneName, subZoneName, newSubzone, zoneId, subzoneId)
      if self.isProximitySuspended then
          -- Reevaluar pertenencia de zona
          local currentMap = GetMapTileTexture()
          if currentMap and self.questMap and currentMap == self.questMap then
              self.isProximitySuspended = false
          end
      end
  end

  EVENT_MANAGER:RegisterForEvent(self.name .. "_ZoneWatcher", EVENT_ZONE_CHANGED, OnZoneChanged)
  ```

---

## 18. Regla P0 Anti-Alucinación de Assets y Validación de Contratos Visuales en EsoUI

### 18.1 Verificación Mandatoria de Texturas y Assets (`EsoUI/Art/...`)

El motor de Zenimax (EsoUI) carga sus recursos gráficos desde contenedores binarios internos (`.dat`), direccionados mediante rutas virtuales relativas (por ejemplo, `EsoUI/Art/...` o `/esoui/art/...`).

* **Invariante P0 Anti-Alucinación:** Queda terminantemente prohibido inventar, asumir por analogía o deducir rutas o nombres de archivo de texturas (por ejemplo, inferir `compass_area_pin.dds` basándose en nombres de funciones o constantes).
* **Comprobación Mandatoria Previa:** Antes de incorporar cualquier ruta de textura en código de producción, constantes o arneses de pruebas, el agente **DEBE** verificar su existencia en el catálogo oficial de ZOS mediante:
  1. `eso_search_textures`: Para localizar texturas registradas por coincidencia de subcadena o patrón.
  2. `eso_search_ui_source` / `eso_get_ui_source`: Para inspeccionar controles nativos de ZOS y constatar las rutas exactas de textura asignadas a elementos homólogos (pins, marcos, iconos, barras, botones).
  3. `references/ESOUIDocumentation.txt`: Para constantes y enums relacionados con texturas y estilos.
* **Tolerancia Cero a la Inferencia Generativa:** Si una textura no puede ser verificada en el catálogo canónico mediante el MCP de dominio ni en las referencias oficiales, no debe proponerse ni incorporarse al código bajo ninguna circunstancia.

### 18.2 Protocolo de Circuit Breaker ante Fallos de Contrato Visual (Stop & Audit)

Cuando un componente visual, textura, anclaje o animación falla en tiempo de ejecución en el cliente de EsoUI (manifestándose como un control invisible, textura no renderizada, pin desalineado o error Lua al instanciar el control):

* **Interdicción de Micro-Parches Reactivos:** Queda estrictamente prohibido iniciar secuencias sucesivas de parches a ciegas, cambios especulativos de anclajes o permutación de nombres de archivo basada en prueba y error.
* **Parada Obligatoria y Auditoría de Raíz (Stop & Audit):**
  1. **Detener la Modificación de Código:** Congelar inmediatamente la edición del addon.
  2. **Auditoría del Componente Nativo:** Usar `eso_search_ui_source` para localizar cómo implementa Zenimax controles equivalentes en el código fuente de EsoUI.
  3. **Verificación de Contrato:** Comprobar en el código fuente de ZOS:
     * Contenedor padre (`parent`), tipo de control (`CT_*`) y plantilla XML o virtual usada.
     * Capas gráficas (`drawLayer`, `drawLevel`, `drawTier`).
     * Dimensiones explícitas (`SetDimensions`) y anclajes requeridos (`SetAnchor`).
     * Rutas fidedignas de texturas validadas con `eso_search_textures`.
  4. **Emisión de Diagnóstico Técnico:** Proponer la solución al usuario acompañada de la evidencia del código nativo de ZOS que respalda el cambio, erradicando conjeturas.

