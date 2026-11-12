---
name: eso-addon-development
description: >-
  MANDATORY: You MUST read this skill BEFORE starting any task, lookup, or code change related to Elder Scrolls Online (ESO) addons. It defines the API lookup hierarchy (prioritizing eso-mcp-server tools before local fallback, and reserving web search as last-resort contingency), canonical reference paths, and strict guidelines for Zenimax (EsoUI) addon development. Do NOT skip reading this.
---

# Elder Scrolls Online (ESO) Addon Engineering

Orquestador canónico para desarrollo de addons en Lua bajo el motor de interfaz de Zenimax (EsoUI). Aplica Divulgación Progresiva (Progressive Disclosure) con directivas procedimentales en `references/`.

---

## 1. Política de Información y Consulta de API

Protocolo jerárquico de 4 niveles para resolver dudas de API y constantes:

1. **Nivel 1 — Contexto Local:**
   * El código del proyecto es la referencia arquitectónica interna.
   * Mocks locales en `tests/` son emulaciones artesanales subordinadas a la API oficial (`references/ESOUIDocumentation.txt`), no la fuente de verdad.
2. **Nivel 2 — Conocimiento del Modelo:**
   * Proceder con APIs y constantes conocidas de ZOS y Lua.
   * Validar ejecutando pruebas locales (`luajit tests/...`), sin inspección remota previa.
3. **Nivel 3 — Referencias Canónicas de EsoUI (MCP y Archivos Locales):**
   * **Vía Preferente — Servidor MCP (`eso-mcp-server`):**
     * **Aislamiento por Workspace y Aprovisionamiento (ADR-0041):** Activado localmente en el repositorio del addon (`.agents/plugins/eso-addon-suite/mcp_config.json` en Antigravity y `.mcp.json` en Claude Code). No reside en el catálogo global.
     * **Jerarquía Determinista de Invocación de `agent-module`:**
       1. *Vía Canónica:* `agent-module enable eso`
       2. *Vía Fallback:* `python3 ~/.gemini/config/skills/issue-driven-workflow/bin/agent-module enable eso` (en Claude Code: `python3 ~/.claude/skills/issue-driven-workflow/bin/agent-module enable eso`)
       3. *Freno Obligatorio (Stop & Ask):* Prohibido buscar en el host (`find`, `grep`). Detenerse de inmediato y emitir comando terminal-ready (`cd <dotfiles> && ./build.sh all`) u ofrecer andamiaje estático directo mediante herramientas nativas de archivos.
     * **Blindaje Anti-Reconocimiento MCP:** Si `eso-mcp-server` no está activo en el entorno (herramientas no disponibles en la sesión), queda taxativamente prohibido inspeccionar el host (`~/.gemini/antigravity/mcp/...`, `~/.claude/...` o rutas internas afines) vía terminal (`ls`, `find`) o APIs de lectura para buscar esquemas o scripts. En su lugar, saltar directamente a la Vía Fallback — Archivos Locales (`references/ESOUIDocumentation.txt` y `references/localizegeneratedstrings.lua`).
     * **Límite y Circuit Breaker MCP:** Rige el límite MCP definido en el Nivel 4 (Límites por Etapa).
     * **Búsqueda Guiada por Hipótesis:** Prohibida la navegación exploratoria ciega. Exige formular una hipótesis técnica previa antes de invocar herramientas de exploración profunda (`eso_search_ui_source`, `eso_get_ui_modules`).
     * **Lectura de Código UI por Rango:** Firma `eso_get_ui_source(file_path, symbol?, start_line?, end_line?, max_lines=200)`. Los nombres canónicos son `start_line`/`end_line`. Las herramientas rechazan parámetros desconocidos con `Unknown parameter(s): ... Valid parameters: ...`: corregir el nombre según esa lista y reintentar, sin reformular la consulta.
     * **Salida MCP No Paginable:** Las salidas grandes se persisten (ej. `.system_generated/steps/<n>/output.txt`) como JSON de pocas líneas, con el código en una sola cadena. Paginar ese archivo por líneas (mediante lectura con delimitación de rango) no acota el contenido. Pedir rangos chicos al MCP (`start_line`/`end_line`, `max_lines`) en lugar de releer el archivo.
     * Consulta de API: `eso_search_api`, `eso_get_constant`, `eso_get_enum`, `eso_get_function`, `eso_get_event`, `eso_search_strings`, `eso_api_stats`.
     * Inspección de persistencia (solo lectura): `eso_savedvars_inspect`, `eso_savedvars_get_account_wide`, `eso_savedvars_get_character`, `eso_savedvars_query`. Prohibida la mutación vía MCP.
   * **Vía Fallback — Archivos Locales (Auto-actualizables):**
     * Si el MCP no está disponible, o tras agotar su límite sin localizar el símbolo, consultar en `references/ESOUIDocumentation.txt` (API/constantes C/Lua) y `references/localizegeneratedstrings.lua` (strings a `SI_*`).
     * **Flujo para textos en pantalla:** Buscar string en `localizegeneratedstrings.lua` -> contrastar constante/enum en `ESOUIDocumentation.txt`.
     * **Principio de Suficiencia:** Asumir e implementar de inmediato la constante identificada.
     * **Sincronización JIT:** Ejecutar `scripts/update_esoui_docs.sh` si el manifiesto requiere una versión de API superior a `ESOUIDocumentation.txt`.
   * **Vía Contingencia — Búsqueda Web:**
     * Prohibido realizar búsquedas web o consultas externas de forma prematura. Reservado exclusivamente ante vacíos documentales confirmados tras consultar sin éxito el MCP y las referencias locales (solo las referencias locales si el MCP no está disponible en el entorno).
4. **Nivel 4 — Circuit Breaker y Freno Obligatorio (Stop & Ask):**
   * **Límites por Etapa (fuente única del circuit breaker):**
     * **MCP:** Máximo 3 consultas a herramientas de `eso-mcp-server`, guiadas por hipótesis técnica. Prohibido reiniciar el contador mediante acciones intermedias automáticas (mutación de código local o ejecución de pruebas); el límite solo se reinicia tras un gate humano (confirmación explícita del usuario vía Stop & Ask).
     * **Referencias Locales:** Al alcanzar 3 lecturas pasivas en `references/ESOUIDocumentation.txt` o `references/localizegeneratedstrings.lua` sin formular mutaciones o pruebas, es mandatorio formular y declarar explícitamente una hipótesis técnica verificable antes de proceder con lecturas adicionales. La etapa queda agotada cuando la hipótesis no se sostiene o no hay avance.
     * **Web:** Máximo 1 búsqueda web acotada o consulta externa (endpoints raw o repositorio oficial de EsoUI), solo ante vacío documental confirmado.
   * **Flujo Ordenado de Inspección y Fallback:** Cada etapa opera dentro de su límite y, si no localiza la API o constante, cede a la siguiente.
     * **Con Servidor MCP Disponible:** MCP -> Referencias Locales -> Web -> Stop & Ask.
     * **Si el MCP No Está Disponible:** Referencias Locales -> Web -> Stop & Ask.
     * **Stop & Ask:** Si no se localiza la API o constante tras agotar el flujo, **detenerse inmediatamente y consultar al usuario**. Prohibido inventar signaturas, asumir parámetros o reiniciar bucles de inspección ciega.

---

## 2. Criterio de Proporcionalidad y Flujo Incremental

* **Tareas Incrementales:** Filtros, opciones en LibAddonMenu, eventos conocidos o ajustes menores son rutinarios: proceder directo a código y tests. Reservar `implementation_plan.md` para refactors mayores o petición expresa.
* **Abstracción Tipada:** Clasificar ítems con tipos del motor (`ItemType`, `SpecializedItemType`), evitando listas quemadas de `itemId`.
* **Librerías Externas:** Consultar la documentación propia de `LibAddonMenu-2.0` o `LibCharacterKnowledge`.

---

## 3. Matriz de Ruteo y Referencias Especializadas

Procedimientos detallados y normativas de ingeniería en `references/`:

| Dominio | Contenido | Referencia Especializada |
| :--- | :--- | :--- |
| **Arquitectura Lua** | Aislamiento de namespace, ciclo `EVENT_ADD_ON_LOADED`, persistencia `SavedVariables` e inspección MCP, `ZO_PreHook`/`ZO_PostHook`, recolección de basura, tipado nativo, constantes, anclaje de escenas/diario (`ZO_QuestJournal` vs `ZO_SharedRightPanelBackground`), `CT_EDITBOX`, ciclo de borrador y convención de texturas de mapa en DLCs multi-zona. | [`references/lua-architecture.md`](references/lua-architecture.md) |
| **Build y Empaquetado** | Comandos slash en README, sincronización de dependencias (`## DependsOn:` vs README), inyección `@BUILD_VERSION@`, prevalencia del motor sobre mocks, estándares de arnés de pruebas, paridad de orden de carga con el manifiesto, flujo de desarrollo in-game vía symlinks y paridad multi-addon. | [`references/build-and-packaging.md`](references/build-and-packaging.md) |
| **Documentación API** | API oficial de C/Lua, funciones globales, enums, eventos y constantes del motor ZOS. | [`references/ESOUIDocumentation.txt`](references/ESOUIDocumentation.txt) |
| **Strings y Localización** | Mapeo oficial de textos de interfaz/tooltips en inglés a IDs de strings y enums (`SI_*`). | [`references/localizegeneratedstrings.lua`](references/localizegeneratedstrings.lua) |

---

## 4. Protocolo de Mejora Continua (Self-Improvement)

Si durante el desarrollo se identifica una función nativa obsoleta (*deprecated*), una discrepancia crítica entre la documentación y la ejecución real, o un patrón idiomático no cubierto, alertar al usuario al concluir la tarea y proponer la actualización de este skill.
