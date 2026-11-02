---
name: eso-addon-development
description: >-
  MANDATORY: You MUST read this skill BEFORE starting any task, lookup, or code change related to Elder Scrolls Online (ESO) addons. It defines the API lookup hierarchy (prioritizing eso-mcp-server tools before local fallback or text search), canonical reference paths, and strict guidelines for Zenimax (EsoUI) addon development. Do NOT skip reading this.
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
       3. *Freno Obligatorio (Stop & Ask):* Prohibido buscar en el host (`find`, `grep`). Detenerse de inmediato y emitir comando terminal-ready (`cd <dotfiles> && ./build.sh all`) u ofrecer andamiaje estático directo con `write_to_file`.
     * Consulta de API: `eso_search_api`, `eso_get_constant`, `eso_get_enum`, `eso_get_function`, `eso_get_event`, `eso_search_strings`, `eso_api_stats`.
     * Inspección de persistencia (solo lectura): `eso_savedvars_inspect`, `eso_savedvars_get_account_wide`, `eso_savedvars_get_character`, `eso_savedvars_query`. Prohibida la mutación vía MCP.
   * **Vía Fallback — Archivos Locales (Auto-actualizables):**
     * Si el MCP no está disponible, consultar en `references/ESOUIDocumentation.txt` (API/constantes C/Lua) y `references/localizegeneratedstrings.lua` (strings a `SI_*`).
     * **Flujo para textos en pantalla:** Buscar string en `localizegeneratedstrings.lua` -> contrastar constante/enum en `ESOUIDocumentation.txt`.
     * **Principio de Suficiencia:** Asumir e implementar de inmediato la constante identificada.
     * **Sincronización JIT:** Ejecutar `scripts/update_esoui_docs.sh` si el manifiesto requiere una versión de API superior a `ESOUIDocumentation.txt`.
4. **Nivel 4 — Circuit Breaker y Freno Obligatorio (Stop & Ask):**
   * Máximo 1 consulta a GitHub (`https://github.com/esoui/esoui`) o endpoints raw.
   * Si no se localiza la API o constante, **detenerse inmediatamente y consultar al usuario** (Stop & Ask). Prohibido inventar signaturas o asumir parámetros.

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
| **Arquitectura Lua** | Aislamiento de namespace, ciclo `EVENT_ADD_ON_LOADED`, persistencia `SavedVariables` e inspección MCP, `ZO_PreHook`/`ZO_PostHook`, recolección de basura, tipado nativo y centralización de constantes/metadatos. | [`references/lua-architecture.md`](references/lua-architecture.md) |
| **Build y Empaquetado** | Comandos slash en README, sincronización de dependencias (`## DependsOn:` vs README), inyección `@BUILD_VERSION@`, prevalencia del motor sobre mocks y estándares de arnés de pruebas (reporter conciso y anti-table-dumps). | [`references/build-and-packaging.md`](references/build-and-packaging.md) |
| **Documentación API** | API oficial de C/Lua, funciones globales, enums, eventos y constantes del motor ZOS. | [`references/ESOUIDocumentation.txt`](references/ESOUIDocumentation.txt) |
| **Strings y Localización** | Mapeo oficial de textos de interfaz/tooltips en inglés a IDs de strings y enums (`SI_*`). | [`references/localizegeneratedstrings.lua`](references/localizegeneratedstrings.lua) |

---

## 4. Protocolo de Mejora Continua (Self-Improvement)

Si durante el desarrollo se identifica una función nativa obsoleta (*deprecated*), una discrepancia crítica entre la documentación y la ejecución real, o un patrón idiomático no cubierto, alertar al usuario al concluir la tarea y proponer la actualización de este skill.
