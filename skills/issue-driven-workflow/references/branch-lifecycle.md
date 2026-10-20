# Referencia: Convención de Ramas, Ciclo E2E y Gestión de Pull Requests

Guía procedimental detallada para el ciclo de vida completo de ramas de trabajo, ejecución de tareas guiadas por issues, higiene de Git, apertura de PRs y cierre de tickets.

---

## 1. Convención Canónica de Ramas de Trabajo

Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código del workspace.

### 1.1 Estrategia Híbrida Contextual (Ref: docs/adr/0021-estrategia-de-ramas-troncales-y-promocion-de-entornos.md)
La estructura de ramas troncales responde a la naturaleza del proyecto según su archivo de configuración raíz (`.repo-config.json` o `config.json`):

1. **Categoría A (Predeterminada - Repositorios Compactos / Dotfiles / Tooling / Librerías):**
   - **Troncal única:** `main`.
   - **Ramas efímeras:** Se originan en `main` (`git checkout -b feat/issue-<id>-<slug>`).
   - **Pull Requests:** Apuntan directamente a `main`. Cero ramas troncales intermedias.
2. **Categoría B (Aplicaciones con Ambientes de Despliegue Físicos):**
   - **Troncal de integración continua:** `dev` (desplegada a entorno de staging/dev).
   - **Troncal de producción:** `main` (desplegada a producción).
   - **Ramas efímeras:** Se originan en `dev` (`git checkout -b feat/issue-<id>-<slug> dev`).
   - **Pull Requests:** Apuntan a `dev` (`gh pr create --base dev ...`).
   - **Promoción a Producción:** Se formaliza exclusivamente mediante un *Release Pull Request* de `dev` a `main` con tag de versión SemVer (`vX.Y.Z`).

### 1.2 Detección Declarativa de la Estrategia del Repositorio
Al iniciar el trabajo en un repositorio, el agente inspecciona el archivo de configuración en la raíz (`.repo-config.json` o `config.json`):
```json
{
  "repository_type": "category_a",
  "base_branch": "main"
}
```
En ausencia de archivo de configuración o si no se explicita `repository_type`, se adopta por defecto **Categoría A** (`base_branch: "main"`).

### 1.3 Nomenclatura Canónica de Ramas Efímeras
- **Nomenclatura Obligatoria:**
  - Para nuevas funcionalidades, refactors o tareas generales: `feat/issue-<id>-<slug>`
  - Para corrección de errores o parches: `fix/issue-<id>-<slug>`
- **Creación in-place:**
  ```bash
  git checkout -b <nombre-de-rama>
  ```
  *(Ejecutado con `BypassSandbox: true` desde el primer intento debido al montaje `ro` de `.git/`).*

---

## 2. Ciclo de Vida E2E de la Tarea

Cualquier tarea despachada debe cumplir secuencialmente con las siguientes 7 fases:

```
[1. Ingesta] -> [2. Higiene de Ramas] -> [3. Planificación] -> [4. Desarrollo] -> [5. Commit] -> [6. Push] -> [7. PR & Tablero]
```

### Paso 1: Ingesta Técnica
1. Lectura profunda de los requerimientos, contexto, diagnóstico y criterios de aceptación en `gh issue view <id>` (`BypassSandbox: true`).
2. Transicionar el ticket a `⚙️ In Progress` en el tablero central (Project 1):
   ```bash
   gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "⚙️ In Progress"
   ```
   *(Ejecutado con `BypassSandbox: true`).*

### Paso 2: Aislamiento e Higiene del Workspace
1. Posicionarse en la rama base del repositorio (`main` por defecto, o `dev` en Categoría B) y sincronizar cambios podando referencias remotas obsoletas:
   ```bash
   git checkout <base_branch>
   git pull --prune --ff-only
   ```
   *(Ejecutados con `BypassSandbox: true` desde el primer intento).*
   - **Mecánica de Transporte de Git:** Invocado sin argumentos posicionales de remoto o rama (`origin main`), `git pull --prune --ff-only` procesa el refspec estándar completo (`+refs/heads/*:refs/remotes/origin/*`), poda de forma automática las referencias zombi (`remotes/origin/*`) y avanza la rama base exclusivamente en modo fast-forward sin modales interactivos en Antigravity.
   - **Prohibición Categórica de `git remote prune`:** Queda terminantemente prohibido ejecutar `git remote prune` (ej. `git remote prune origin`). Toda poda de tracking remoto debe canalizarse exclusivamente a través del transporte estándar de sincronización (`git pull --prune --ff-only` o `git fetch --prune origin`).
2. Ejecutar la poda de higiene local en un único paso atómico mediante el CLI determinista de Nivel 1 `git-prune-gone`:
   ```bash
   git-prune-gone
   ```
   *(Ejecutado con `BypassSandbox: true` desde el primer intento debido al montaje `ro` de `.git/`).*
   - **Fallback Determinista:** Si el binario no está disponible en `$PATH`, invocar directamente `skills/issue-driven-workflow/bin/git-prune-gone`.
   - **Mecánica Interna:** Inspecciona las ramas locales mediante formato estructurado (`%(HEAD)|%(refname:short)|%(upstream:track)`), detecta aquellas con tracking zombi `[gone]` y ejecuta la poda segura (`git branch -d`) sin requerir turnos intermedios del LLM ni pipes de shell.
   - **Prohibición Categórica de Pipelines y Wrappers CLI (`awk` / `xargs`):** Queda terminantemente prohibido utilizar tuberías o utilidades intermediarias (ej. `git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d`). Encadenar comandos en pipes rompe el *prefix matching* de seguridad en Antigravity y viola los estándares de entorno.
3. Crear y cambiar a la rama descriptiva (`git checkout -b feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) con `BypassSandbox: true` desde el primer intento.

### Paso 3: Planificación y Refinamiento
- **Blindaje del Planning Mode:** Toda tarea que implique diagnóstico de errores (bug fixing) o modificaciones arquitectónicas requiere obligatoriamente redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
- **Evaluación Obligatoria de Minimal Blast Radius:** Todo plan de implementación debe evaluar y registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Si la propuesta plantea modificar directivas basales (`core/`), debe incorporar obligatoriamente la sección **"Justificación de Elevación Basal"** acreditando la inviabilidad técnica en los niveles 0 a 3.
- **Excepción de Fast-Path Ejecutivo:** Si la solución técnica o cambio ya fue debatido y consensuado explícitamente en el chat y el usuario emitió una orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), el agente **NO DEBE** pausar con un plan bloqueante; procede de inmediato a la implementación.
- **Registro de ADRs:** Si se toman decisiones arquitectónicas o estructurales, registrar un nuevo ADR con `status: proposed` mediante el skill `adr-manager` (`docs/adr/NNNN-titulo.md`).

### Paso 4: Desarrollo y Verificación
- Aplicar cambios atómicos exclusivamente mediante las APIs nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`). Prohibido usar comandos de terminal para I/O (`cat`, `sed`, `awk`, `tee`).
- Ejecutar compilaciones locales, linters y suites de prueba del proyecto para validar que no existan regresiones (`./build.sh check` con `BypassSandbox: false`).
- **Transición de ADRs a Accepted:** Al finalizar el desarrollo y verificar los cambios (o tras la aprobación humana del plan), transicionar todo nuevo ADR asociado a la tarea a `status: accepted` en la rama de trabajo antes del commit. La posterior revisión y fusión (merge) del PR en `main` por parte del usuario constituye el gate definitivo de ratificación.

### Paso 5: Commit Atómico
- Debido a que el evaluador de permisos anula el prefijo con comillas, **queda estrictamente prohibido** usar `git commit -m "..."`.
- Redactar el mensaje convencional en `.commit_msg` con `write_to_file`.
- Ejecutar el commit leyendo el archivo con `BypassSandbox: true` desde el primer intento:
  ```bash
  git commit -F .commit_msg
  ```
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
  ```bash
  rm -f .commit_msg
  ```

### Paso 6: Publicación Remota
- Subir la rama al repositorio remoto (`BypassSandbox: true`):
  ```bash
  git push -u origin <nombre-de-rama>
  ```

### Paso 7: Apertura de Pull Request
- Redactar el cuerpo del PR en `.pr_body` con `write_to_file` y publicarlo mediante GitHub CLI (`BypassSandbox: true`):
  ```bash
  gh pr create --base <base_branch> --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
  ```
  *(Si `<base_branch>` es la rama por defecto del repositorio en GitHub, ej. `main` en Categoría A, el flag `--base` puede omitirse; en Categoría B debe especificarse explícitamente `--base dev`).*
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
  ```bash
  rm -f .pr_body
  ```

---

## 3. Flujo Mandatorio de Pull Requests y Projects v2

- **Prohibición Total de Push/Merge a `main`:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
- **Vinculación Canónica de Cierre (Simple y Múltiple):** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse el PR. Si el Pull Request resuelve conjuntamente una issue de implementación y una issue previa de investigación/auditoría o spike que motivó el cambio, debe listar cada una de forma independiente en líneas contiguas:
  ```markdown
  Closes #<id_implementacion>
  Closes #<id_investigacion>
  ```
- **Sincronización Determinista con el Tablero Central:** Asegurar que el estado del ítem en Project 1 pase a `👀 In Review / PR` mediante el comando directo por nombre de campo:
  ```bash
  gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "👀 In Review / PR"
  ```
  *(Queda prohibido ejecutar consultas exploratorias de `field-list` o `item-list` para resolver IDs cuando el comando directo es determinista).*
- **Gate de Aprobación Humana:** La revisión del diff, aprobación y fusión del PR es responsabilidad exclusiva del PM / Tech Lead en la interfaz de GitHub.

---

## 4. Protocolo Especial: Tareas de Investigación, Auditoría o Spikes (Cierre Autónomo sin PR)

Cuando una tarea despachada tenga por objeto una auditoría forense (`audit(...)`), investigación técnica, diagnóstico o spike exploratorio, y su conclusión técnica determine que **no se requieren cambios de código**:

1. **Prohibición de Delegación Pasiva de Cierre:**
   - Queda **terminantemente prohibido** que el agente finalice la tarea emitiendo una recomendación pasiva de cierre (ej. *"Se recomienda proceder al cierre de la issue #X"*), dejando la tarjeta abierta en el backlog para que el usuario la cierre manualmente.
2. **Publicación Determinista del Informe Técnico:**
   - Redactar el reporte técnico o justificación de resolución en `.issue_comment` mediante la herramienta nativa `write_to_file`.
   - Publicar el comentario en el ticket mediante GitHub CLI (`BypassSandbox: true`):
     ```bash
     gh issue comment <id> --body-file .issue_comment
     ```
   - Limpiar inmediatamente el archivo temporal (`BypassSandbox: false`):
     ```bash
     rm -f .issue_comment
     ```
3. **Cierre Autónomo Inmediato:**
   - Cerrar formalmente la issue de manera autónoma con GitHub CLI (`BypassSandbox: true`):
     ```bash
     gh issue close <id> --comment "Cierre automatizado tras concluir la investigación/auditoría técnica."
     ```
4. **Sincronización con Projects v2:**
   - Sincronizar el tablero a `Done` si GitHub CLI no lo realiza automáticamente:
     ```bash
     gh project item-edit 1 --owner "@me" --url <issue-url> --field "Status" --value "Done"
     ```
5. **Reporte Final al Usuario:**
   - Reportar al usuario la conclusión del análisis, el enlace al issue cerrado y la confirmación del estado de la tarjeta en `Done`.

---

## 5. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.
