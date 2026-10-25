# Referencia: Protocolo de Rollback y Reversión de Emergencia

Protocolo operativo determinista para emergencias, regresiones críticas o roturas tras la fusión de Pull Requests en la rama troncal `<base_branch>` (`main` en Categoría A o `dev` en Categoría B).

---

## 1. Criterios de Activación

- **Rotura de Build o Tests:** El código en `<base_branch>` no compila o falla catastróficamente en `./build.sh check` o suites de prueba locales.
- **Bloqueo Crítico de Operación:** Directivas o scripts generan bucles infinitos, fallos de permisos insalvables o vulneraciones de seguridad.
- **Inconsistencia Arquitectónica:** Fusión accidental de cambios que contradicen decisiones vigentes (`docs/adr/`) sin discusión previa.

---

## 2. Ciclo de Ramas y Git (Reversión Atómica)

Para preservar la prohibición estricta de push directo o reescritura de historia (`git reset --hard`) en `<base_branch>` (resuelta desde `.repo-config.json`, siendo `main` por defecto o `dev` en Categoría B):

1. **Sincronizar `<base_branch>`:**
   ```bash
   git checkout <base_branch>
   git pull --prune --ff-only
   ```
   *(Ejecutados con `BypassSandbox: true` desde el primer intento).*

2. **Crear Rama de Reversión Dedicada:**
   Nomenclatura obligatoria: `fix/revert-pr-<id>-<slug>` (donde `<id>` corresponde al número del PR causante del fallo).
   ```bash
   git checkout -b fix/revert-pr-<id>-<slug>
   ```
   *(Ejecutado con `BypassSandbox: true` desde el primer intento).*

3. **Invocación Atómica y Desatendida de `git revert`:**
   Obtener el SHA del commit integrado en `<base_branch>` (`<commit_sha>`) y determinar su naturaleza inspeccionando sus ancestros directos:
   ```bash
   git rev-list --parents -n 1 <commit_sha>
   ```
   *(Ejecutado con `BypassSandbox: true`).*

   - **Squash Commit (1 padre - Escenario Canónico):** Si la salida contiene 2 identificadores (`<commit_sha> <parent1>`), se trata de un commit de squash (estándar canónico del flujo). Revertir directamente sin especificar línea principal:
     ```bash
     git revert --no-commit <commit_sha>
     ```
     *(Nota: especificar `-m 1` en un squash commit produce el error `fatal: mainline was specified but commit ... is not a merge`).*

   - **Merge Commit Tradicional (2 o más padres):** Si la salida contiene 3 o más identificadores (`<commit_sha> <parent1> <parent2>...`), se trata de un merge commit tradicional. Revertir indicando la línea principal (`-m 1`):
     ```bash
     git revert -m 1 <commit_sha> --no-commit
     ```
     *(Nota: omitir `-m 1` en un merge commit tradicional produce el error `fatal: commit ... is a merge but no -m option was given`).*

   *En ambos casos, el flag `--no-commit` previene que Git abra un editor interactivo en terminal y permite formatear el mensaje de commit de manera determinista y controlada.*

4. **Commit Atómico de Reversión:**
   Redactar el mensaje convencional en `.commit_msg` con la herramienta nativa `write_to_file`:
   ```markdown
   fix(revert): revert PR #<pr_id> - <motivo breve>

   Reverts PR #<pr_id> (<commit_sha>).
   Razón: <diagnóstico técnico conciso de la regresión o anomalía>.
   ```
   Ejecutar el commit leyendo el archivo temporal (`BypassSandbox: true`):
   ```bash
   git commit -F .commit_msg
   ```
   Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
   ```bash
   rm -f .commit_msg
   ```

5. **Publicación Remota:**
   ```bash
   git push -u origin fix/revert-pr-<id>-<slug>
   ```
   *(Ejecutado con `BypassSandbox: true`).*

---

## 3. Gestión de Backlog y Tablero Central (Projects v2)

Una reversión no debe dejar cabos sueltos ni tarjetas en estados inconsistentes:

1. **Apertura del Pull Request de Reversión:**
   Redactar el cuerpo del PR en `.pr_body` con `write_to_file`:
   ```markdown
   ### Diagnóstico de Emergencia
   [Descripción de la anomalía o regresión que motiva la reversión]

   ### Cambios
   - Reversión atómica del commit `<commit_sha>` (squash o merge commit).
   - Restablecimiento del estado estable previo en `<base_branch>`.

   Reverts #<pr_id>
   ```
   Publicar el PR apuntando a la rama troncal donde ocurrió la integración defectuosa (`<base_branch>`) mediante GitHub CLI (`BypassSandbox: true`):
   ```bash
   gh pr create --base <base_branch> --title "fix(revert): revert PR #<pr_id> - <motivo>" --body-file .pr_body
   ```
   *(Donde `<base_branch>` se resuelve desde `.repo-config.json`, siendo `main` en Categoría A o `dev` en Categoría B).*

   Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
   ```bash
   rm -f .pr_body
   ```

2. **Transición Automatizada del PR de Reversión:**
   La publicación del Pull Request activa de forma nativa su inclusión y transición en Projects v2 a `👀 In Review / PR` mediante los Built-in Workflows, sin requerir `gh project item-edit`.

3. **Reapertura de la Issue Original Fallida:**
   Para no perder la trazabilidad de la tarea original que falló, reabrir formalmente su issue:
   ```bash
   gh issue reopen <id>
   ```
   *(Ejecutado con `BypassSandbox: true`).*

4. **Comentario Técnico y Reubicación en Backlog:**
   Redactar un comentario técnico en `.issue_comment` documentando la causa de la reversión y los requerimientos pendientes para su posterior reintento:
   ```bash
   gh issue comment <id> --body-file .issue_comment
   ```
   *(Ejecutado con `BypassSandbox: true`).*
   Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
   ```bash
   rm -f .issue_comment
   ```
   Al reabrirse el issue con `gh issue reopen`, el Built-in Workflow *Item reopened* de Projects v2 transiciona automáticamente la tarjeta a `🎯 Ready for Dev` sin mutaciones manuales de CLI.

---

## 4. Gobierno Arquitectónico (MADR)

Si el Pull Request revertido introdujo un Architectural Decision Record en `docs/adr/` que había transicionado a `status: accepted`:

1. **Deprecación Inmediata:**
   - La historia arquitectónica no se borra ni se reescribe. Queda terminantemente prohibido eliminar el archivo ADR revertido.
   - Modificar exclusivamente el YAML frontmatter del ADR mediante `replace_file_content`:
     ```yaml
     status: deprecated
     ```
   - Añadir una nota explicativa en el cuerpo:
     `> **Nota de Reversión:** Decisión deprecada tras la reversión del PR #<pr_id> debido a <motivo>.`
2. **ADR Compensatorio (si aplica):**
   - Si la reversión exige documentar formalmente una alternativa arquitectónica sustituta o formular lecciones aprendidas de la falla, crear un nuevo registro correlativo (ej. `docs/adr/NNNN-reemplazo-de-estrategia.md`) mediante `adr-manager` con `status: proposed`.

---

## 5. Restauración Local en Sistema Anfitrión (`build.sh rollback`)

Si la falla o regresión afectó el entorno local desplegado en el host (directorios `~/.gemini/config/` o `~/.claude/`):
1. Ejecutar de forma inmediata la restauración atómica del último respaldo funcional:
   ```bash
   ./build.sh rollback [runtime]
   ```
   *(Ejecutado localmente para restaurar `AGENTS.md` y `mcp_config.json` desde su último `.bak.<timestamp>`).*
2. Ejecutar `./build.sh check [runtime]` para validar la estabilidad recuperada del anfitrión.
