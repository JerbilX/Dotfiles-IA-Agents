# Referencia: Gestión Canónica de Backlog y Tareas (GitHub Issues & Projects v2)

Guía operativa exhaustiva para el registro, especificación técnica, jerarquía de resolución, indexación en GitHub Projects v2 y control de alcance de tareas.

---

## 1. Prohibición Estricta de Backlogs Locales y Archivos Huérfanos

- **Queda terminantemente prohibido** crear, sincronizar o depender de archivos `TODO.md`, `backlog.md`, `NOTES.md` o bitácoras informales en cualquier nivel del proyecto.
- **Queda terminantemente prohibido** volcar prompts, especificaciones de tareas o planes de ejecución en carpetas o archivos temporales huérfanos (ej. `tasks/`, `prompts/`).
- Todo requerimiento pendiente, mejora, refactor o bug detectado debe formalizarse exclusiva y directamente como una **GitHub Issue**.

---

## 2. Estructura Canónica del Cuerpo del Issue

El cuerpo del ticket debe ser exhaustivo y autosuficiente para eliminar la necesidad de redactar prompts manuales posteriores. Debe redactarse mediante la API nativa de archivos (`write_to_file`) en el archivo temporal `.issue_body` con la siguiente estructura técnica:

```markdown
### Diagnóstico del Problema
[Descripción concisa del problema, limitación actual o contexto técnico detectado]

### Objetivos y Requerimientos Técnicos
[Especificación técnica detallada de los cambios requeridos y directivas aplicables]

### Criterios de Aceptación
[ ] [Criterio 1 verificable]
[ ] [Criterio 2 verificable]
[ ] [Validación de compilación, tests y chequeos de integridad ejecutados con éxito]
```

---

## 3. Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius)

Al diseñar, planificar o registrar cualquier solución, el agente debe aplicar estrictamente la escala canónica de menor a mayor abstracción:

| Nivel | Capa de Abstracción | Mecanismo y Alcance | Ejemplo |
| :---: | :--- | :--- | :--- |
| **0** | **Configuración / Parámetro CLI / API** | Argumentos nativos, flags o capacidades existentes de la herramienta. Impacto local al comando invocado. | `--query`, `--format json`, `--field`, flags de `gh` o `git`. |
| **1** | **Tooling / Automatización Local** | Scripts de verificación, tests locales, linters, utilidades o targets de `build.sh`. Impacto local al pipeline de compilación. | Target `./build.sh check`, `gh-pr-review`, linters. |
| **2** | **Skills bajo Demanda** | Procedimientos detallados, guías operativas o flujos E2E en `skills/*/SKILL.md` y `references/*.md`. Impacto acotado a la activación del skill. | Procedimientos de `issue-driven-workflow`, guías de `adr-manager`. |
| **3** | **Reglas Especializadas de Runtime** | Directivas acotadas al runtime activo en `runtimes/<runtime>/rules/*.md`. Impacto restringido a dicho entorno. | Especialización de sandbox para Antigravity (`rules/01-sandbox.md`). |
| **4** | **Core Basal / System Prompt Universal** | Invariantes duros de gobernanza, seguridad universal y principios irrenunciables en `core/*.md`. Impacto permanente y universal en cada turno. | Prohibición de push directo a `main`, confinamiento de sandbox, zero complacencia. |

- **Regla Invariante de Resolución:** Queda **terminantemente prohibido** proponer o ejecutar cambios en un nivel $N+1$ si el problema técnico o requerimiento operativo puede resolverse eficazmente en un nivel menor o igual a $N$.

---

## 4. Gate de Justificación de Elevación Basal

Toda propuesta en la especificación de una issue (`.issue_body`) o plan de implementación que plantee modificar directivas en la capa basal (`core/`) debe incluir obligatoriamente el apartado técnico **"Justificación de Elevación Basal"**. Dicha sección debe demostrar fehacientemente por qué la necesidad técnica es inviable o insuficiente de abordar en los niveles 0 a 3. Propuestas de modificación a `core/` sin esta justificación se consideran técnicamente inválidas por definición.

---

## 5. Creación Determinista del Issue y Protección de Prefix Matching

Debido a que el evaluador de permisos del runtime (Antigravity) anula el *prefix matching* cuando se utilizan comillas complejas o cadenas multilínea en la terminal, el cuerpo debe transferirse obligatoriamente mediante archivo temporal:

1. Redactar la especificación técnica en `.issue_body` con `write_to_file`.
2. Crear el issue mediante GitHub CLI (`BypassSandbox: true` obligatorio desde el primer intento por requerir acceso de red):
   ```bash
   gh issue create --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body
   ```
3. Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
   ```bash
   rm -f .issue_body
   ```

---

## 6. Inyección Inmediata y Agnóstica al Tablero Central (Projects v2)

Para garantizar la indexación inmediata y agnóstica en el tablero central (sin depender de automatizaciones de auto-add restringidas en planes GitHub Free):
```bash
gh project item-add 1 --owner "@me" --url <issue-url>
```
*(Ejecutado con `BypassSandbox: true` obligatorio desde el primer intento; `--owner "@me"` resuelve dinámicamente al usuario autenticado).*

---

## 7. Reporte al Usuario

Al completar la creación e indexación, el agente debe reportar al usuario:
- El número de issue asignado (`#<id>`).
- El enlace web directo al issue (`https://github.com/<owner>/<repo>/issues/<id>`).
- Confirmación de indexación en el tablero de Projects v2.

---

## 8. Control de Alcance (Scope Creep) y Tareas Derivadas

- El agente **no debe inflar** el objetivo del ticket original con refactors, mejoras o arreglos colaterales no contemplados en la especificación de la issue.
- Si durante el desarrollo se detecta un bug, deuda técnica o necesidad secundaria, el agente **DEBE registrarla inmediatamente como una nueva GitHub Issue** (`gh issue create --body-file .issue_body`), indexarla al tablero central (`gh project item-add 1 --owner "@me" --url <issue-url>`) y continuar enfocado en el ticket asignado sin desviarse.
- **Vinculación Múltiple en Tareas Derivadas:** Si una tarea de investigación, auditoría forense o spike genera una o más issues derivadas de corrección/implementación, cuando se resuelva la causa raíz y se abra el Pull Request respectivo, el cuerpo del PR (`.pr_body`) DEBE declarar explícitamente el cierre de todas las issues vinculadas:
  ```markdown
  Closes #<issue_derivada>
  Closes #<issue_madre_investigacion>
  ```
  Esto garantiza que el merge en GitHub cierre automáticamente ambos tickets sin dejar tareas residuales en el backlog.

---

## 9. Consultas de Tablero y Coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*)

Ante preguntas de consulta, estado o coordinación sobre tareas pendientes en el tablero central (Project 1 `Proyectos-IA-V3`):

1. **Comando CLI Simple y Filtrado Contextual por Repositorio:**
   Para prevenir la sobrecarga cognitiva y la dilución de contexto provocada por el volcado de inventarios masivos multi-proyecto, la consulta estándar ante preguntas sobre el board debe filtrar los ítems activos exclusivamente para el repositorio donde está posicionado el agente:
   ```bash
   gh project item-list 1 --owner "@me" --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'
   ```
   *(Ejecutado con `BypassSandbox: true` obligatorio; sustituir `<owner>/<repo>` por la identificación del repositorio actual).*

2. **Priorización Analítica y Recomendación (Top 2 a 3):**
   - **Evaluación Técnica:** El agente debe procesar el listado acotado del repositorio actual y evaluar la relevancia técnica de las tareas:
     - Priorizar fixes o bloqueos inmediatos, tareas en estado `🎯 Ready for Dev` o quick wins de alto impacto técnico frente a ítems de backlog general o de largo plazo.
     - Analizar dependencias lógicas y coherencia secuencial entre tickets para estructurar la progresión del trabajo.
   - **Respuesta Sintética y Asertiva:** En lugar de volcar listas exhaustivas o cortar ciegamente por índice posicional, emitir una respuesta concisa presentando el **Top 2 o 3** de tareas más convenientes para continuar, con una recomendación explícita y justificada de cuál tomar primero y cuál abordar después.
   - **Inventario Exhaustivo Solo Bajo Petición Expresa:** El volcado íntegro del inventario de tareas o la inclusión de ítems pertenecientes a otros repositorios del tablero queda restringido exclusivamente a cuando el usuario lo solicite de manera explícita (ej. *"mostrame todas las tareas del board sin filtrar"* o *"¿qué tareas hay en otros repositorios?"*).

> [!CAUTION]
> **Prohibición de Scripts Envoltorios Ad-hoc:** Queda terminantemente prohibido crear scripts intermediarios o efímeros (Python, Node, Bash, ej. `check_board.py`) para consultar, parsear o envolver llamadas a GitHub Projects. `gh` provee filtrado nativo (`--query`, `--field`, `-q / --jq`, `--limit`). Ejecutar scripts envoltorios con `BypassSandbox: true` viola la política de confinamiento de Antigravity (que reserva el bypass exclusivamente para la suite de `git` y `gh`), rompe el *prefix matching* y dispara solicitudes innecesarias de autorización interactiva.
