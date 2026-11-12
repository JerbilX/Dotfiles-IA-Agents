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
* **Comportamiento Fiel del Mock:**
  * Al invocar `SetText(text)`, el mock debe aplicar el límite de caracteres si `maxInputChars` fue definido (truncar con `string.sub(text, 1, max)`).
  * Al disparar eventos registrados con `SetHandler("OnTextChanged", callback)`, el harness debe proveer `(control, isUserInteraction)` de forma determinista para verificar que los callbacks ignoran mutaciones programáticas.

### 9.3 Patrón Canónico de Copiado In-Place y Antipatrón de Modales Secundarios
* **Copiado In-Place Asistido (`TakeFocus` + `SelectAll`):** Dado que EsoUI carece de una API nativa para escribir directamente al portapapeles del sistema operativo, el patrón canónico para exportar cadenas de texto, serializaciones compactadas o códigos de misiones consiste en:
  1. Utilizar un control `CT_EDITBOX` interactivo o de solo lectura que contenga la información a transferir.
  2. Al interactuar con el control o pulsar el disparador de copiado, activar el campo e invocar secuencialmente:
     ```lua
     editBox:TakeFocus()
     editBox:SelectAll()
     ```
  3. Acompañar el elemento con una indicación visual estática e intuitiva (ej. `[Ctrl+C para copiar]`) para guiar inmediatamente la acción del usuario.
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

### 14.2 Reactividad y Ciclo de Vida en Controles de Acción Contextuales
* **Visibilidad Subordinada al Estado Activo:** Los controles interactivos de navegación, apertura de mapas o localización (ej. botones `showMapBtn` o accesos directos de cartografía) deben gobernar su visibilidad (`control:SetHidden(...)`) de manera estrictamente reactiva respecto al ciclo de vida y vigencia de la entidad o misión asociada.
* **Ocultamiento Inmediato ante Inactividad o Completitud:** Cuando una misión o etapa transiciona a estado inactivo, completado o descartado, los controles contextuales asociados deben ocultarse de inmediato (`control:SetHidden(true)`) para prevenir acciones inconsistentes o desfasadas con el estado actual del juego.




