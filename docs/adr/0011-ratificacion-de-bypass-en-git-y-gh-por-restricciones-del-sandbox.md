---
status: accepted
date: 2026-10-16
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0011 - Ratificación de Bypass en Git y GitHub CLI por Restricciones de Kernel y Sandbox

## Contexto y Planteamiento del Problema

En el [Issue #23](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/23), se cuestionó si autorizar `BypassSandbox: true` para operaciones de Git es la mejor práctica de arquitectura, o si deberían adoptarse alternativas como enlaces simbólicos (symlinks), un skill especializado o un servidor MCP (Model Context Protocol) para preservar sandboxes inquebrantables.

Para resolver la inquietud con rigor técnico, se ejecutaron pruebas empíricas directamente en el entorno confinado de Antigravity (`BypassSandbox: false`):
1. **Inspección de metadatos:** Operaciones de solo lectura como `git status` y `git branch` funcionan de manera determinista dentro del sandbox estándar (código de salida 0).
2. **Mutación de estado local:** Cualquier comando que intente modificar el repositorio local (`git checkout -b`, `git add`, `git commit`) falla inmediatamente a nivel de kernel/sistema operativo con `Read-only file system` (`EROFS`) al intentar crear lockfiles (`.git/refs/heads/*.lock`, `.git/index.lock`).
3. **Comandos remotos:** Cualquier comando que requiera salida a internet (`git push`, `git fetch`, `git pull`, `gh issue`, `gh pr`, `gh project`) es bloqueado por política de red (`403 not allowed by policy`).

El análisis de seguridad del runtime reveló que el motor de Antigravity en Linux (vía namespaces y bwrap/Landlock) monta deliberadamente `.git/` como solo lectura para impedir que procesos confinados inyecten scripts maliciosos en `.git/hooks/` o manipulen `.git/config`, vectores que comprometerían el host cuando el usuario ejecute Git en su terminal nativa.

## Impulsores de la Decisión (Decision Drivers)

* **Seguridad y Menor Privilegio:** Evitar la elevación innecesaria de privilegios y mitigar el riesgo de fuga fuera del workspace.
* **Viabilidad Operativa:** Garantizar que el flujo de trabajo guiado por issues (`core/09-issue-driven-workflow.md`), la gestión de ramas y el aprovisionamiento de Pull Requests funcionen de forma fluida y autónoma.
* **Ergonomía e Integración:** Mantener compatibilidad total con GitHub CLI (`gh`), incluyendo el tablero central de GitHub Projects v2 (`gh project`), autenticación mediante keyring del sistema y bajo consumo de tokens de contexto.
* **Portabilidad de Dotfiles:** No introducir dependencias pesadas de daemons o servidores MCP que requieran gestión de credenciales estáticas (PATs).

## Opciones Consideradas

* **Opción 1: Encapsular operaciones en un Skill o mediante Symlinks.** Descartada por inviabilidad técnica. Un Skill opera en la capa cognitiva y los symlinks respetan las fronteras del filesystem; ninguno puede sortear el aislamiento de red o el montaje `ro` de `.git/` impuesto por los namespaces del sandbox.
* **Opción 2: Reemplazar Git y GitHub CLI por servidores MCP.** Configurar servidores MCP para Git local y GitHub API en el host. Permite un sandbox de terminal inquebrantable a través de RPC tipado, pero pierde el soporte nativo de `gh project` v2, exige Personal Access Tokens (PAT) con mantenimiento manual y consume tokens de contexto en cada turno de la sesión.
* **Opción 3: Ratificar el uso acotado de `BypassSandbox: true` para la suite de `git` y `gh`.** Mantener la arquitectura establecida en [ADR 0001](0001-blindaje-de-sandbox-y-gestion-de-permisos.md), prohibiendo terminantemente el bypass para utilidades locales o de compilación (`build.sh`), y autorizándolo de forma atómica y prefijable únicamente para `git` y `gh`.

## Decisión Adoptada

Opción elegida: **"Opción 3"**, porque:
1. El montaje `ro` de `.git/` en el sandbox estándar de Antigravity hace que la elevación de permisos sea una condición técnica necesaria para cualquier mutación de control de versiones.
2. `BypassSandbox: true` es el mecanismo oficial provisto por Antigravity para comandos de red y acceso controlado al entorno de desarrollo.
3. El blindaje adoptado en [ADR 0001](0001-blindaje-de-sandbox-y-gestion-de-permisos.md) y [`01-sandbox.md`](../../runtimes/antigravity/rules/01-sandbox.md) mitiga el riesgo al confinar la autorización exclusivamente a comandos atómicos de `git` y `gh`, ignorando sugerencias automáticas para cualquier otro binario.
4. **Categorización Determinista Proactiva (Actualización Issue #38):** Se abandona el modelo reactivo ("reintentar tras fallo") por una prescripción determinista desde el primer intento:
   - **Solo Lectura (`BypassSandbox: false` obligatorio):** Inspección pasiva (`git status`, `git log`, `git diff`, `git branch` de consulta) 100% confinada en el sandbox.
   - **Mutadores Locales y Comandos de Red (`BypassSandbox: true` obligatorio desde el primer intento):** Mutación local (`git init`, `git checkout`, `git checkout -b`, `git branch -d/-D`, `git branch -m/-M`, `git add`, `git commit`, `git merge`) y operaciones remotas (`git push`, `git fetch`, `git pull`, `gh ...`), eliminando turnos fallidos y latencia innecesaria.

### Consecuencias

* **Positivas:**
  * Se mantiene la operatividad plena del flujo guiado por issues y Pull Requests sin fricciones ni bloqueos.
  * Se eliminan los errores fatales predecibles (`fatal: Unable to create '.../.git/index.lock': Read-only file system`) y la latencia recurrente (~5s) en cambios de rama y commits.
  * Compatibilidad completa con GitHub Projects v2 y credenciales heredadas de la sesión de Linux sin requerir tokens adicionales.
  * Cero sobrecarga de tokens en el presupuesto de contexto (no requiere registrar herramientas MCP adicionales para Git).
* **Negativas / Trade-offs:**
  * Se requiere la autorización de `BypassSandbox: true` por parte del usuario (o via prefix-matching) para operaciones de mutación de Git (`checkout -b`, `add`, `commit`, `push`) y GitHub CLI (`gh`).
  * No se alcanza el estado de sandbox 100% inquebrantable en la terminal para el control de versiones.

### Pros y Contras de las Opciones

#### Opción 2: Migración a MCP (Git + GitHub)
* **Pro:** Aislamiento total de la terminal; invocación exclusivamente mediante contratos RPC fuertemente tipados.
* **Contra:** Desconexión con GitHub Projects v2 (`gh project`), gestión de PATs estáticos, alta sobrecarga de tokens de catálogo y mayor complejidad de aprovisionamiento en dotfiles.

#### Opción 3: Ratificación de Bypass Acotado
* **Pro:** Máxima ergonomía, integración nativa con CLI, compatibilidad 100% probada con el flujo de trabajo del repositorio.
* **Contra:** Demanda excepciones controladas de sandbox para la suite de Git y GitHub CLI.
