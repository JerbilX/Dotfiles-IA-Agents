---
status: accepted
date: 2026-11-12
decision-makers: [JerbilX, Claude Code]
supersedes: []
superseded-by: []
references:
  - docs/adr/0009-estandarizacion-y-gestion-modular-de-servidores-mcp.md
  - docs/adr/0045-operacion-multi-runtime-e-issues-cruzadas.md
  - docs/adr/0053-integracion-global-del-servidor-mcp-leantoken.md
---

# 0057 - Despliegue MCP de Claude Code por Fusión en `~/.claude.json`

## Contexto y Planteamiento del Problema

ADR-0053 habilitó `leantoken` en el perfil global de `antigravity` y `claude`. El despliegue reutilizaba el symlink `~/.claude/mcp_config.json -> dist/claude/mcp_config.json`, pero Claude Code no lee ese archivo: los servidores MCP de alcance usuario se registran en la clave `mcpServers` de `~/.claude.json`. El resultado era `mcpServers: {}` en el host, ausencia de herramientas `mcp__leantoken__*` y un falso positivo en `./build.sh check`, que solo validaba el manifiesto fuente (#375).

`~/.claude.json` no puede enlazarse: Claude Code lo reescribe con estado propio (proyectos, contadores, credenciales de sesión).

## Impulsores de la Decisión (Decision Drivers)

* Cumplir el contrato de ADR-0053 en Claude Code sin tocar `core/` ni reglas de runtime (MBR 1).
* Preservar claves y servidores MCP del usuario no gestionados por el repo.
* Idempotencia, respaldo `.bak` para `rollback` y verificación efectiva en `check`.
* Sin dependencia de binarios externos en `link` ni en la suite de tests.

## Opciones Consideradas

* **Opción 1:** `claude mcp add-json --scope user` por servidor.
* **Opción 2:** Fusión determinista de `dist/<r>/mcp_config.json` en `mcpServers` del JSON del host mediante `lib/merge_mcp.py`, declarada por `target.mcp_merge_file` (Elegida).

## Decisión Adoptada

Opción elegida: **Opción 2**, porque es testeable sobre un `HOME` temporal, no depende de que el binario `claude` esté instalado ni de su CLI, y sigue el patrón existente de `lib/merge_settings.py` (ADR-0045).

* `target.mcp_merge_file` (schema de runtime) activa el modo fusión; `claude` declara `${HOME}/.claude.json`. Los runtimes sin la clave conservan el symlink.
* El catálogo `runtimes/<r>/mcp/*.json` define los servidores gestionados: se agregan o actualizan los habilitados y se retiran solo los gestionados deshabilitados.
* Si hay cambios, se respalda el destino en `<archivo>.bak.<timestamp>` y se escribe de forma atómica preservando sus permisos. `rollback` y `check` buscan los respaldos junto al archivo destino.
* `link` retira el symlink heredado `~/.claude/mcp_config.json`; `check` advierte por cada servidor habilitado no registrado.

### Consecuencias

* **Positivas:** `leantoken` disponible en Claude Code; `check` refleja el estado efectivo; futuros MCP globales de `claude` heredan el mecanismo.
* **Negativas / Trade-offs:** `rollback` restaura `~/.claude.json` completo, revirtiendo también el estado que Claude Code haya escrito después del respaldo. La escritura puede competir con una sesión de Claude Code activa; se mitiga con reemplazo atómico, y se recomienda ejecutar `link` sin sesiones abiertas.
