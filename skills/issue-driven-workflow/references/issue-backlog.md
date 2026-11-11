# Referencia: Gestión Canónica de Backlog y Tareas (GitHub Issues & Projects v2)

Guía operativa exhaustiva para el registro, especificación técnica, jerarquía de resolución, indexación en GitHub Projects v2 y control de alcance de tareas.

---

## 1. Prohibición de Backlogs Locales, Trazabilidad y Niveles de Ceremonia

- **Prohibición de Backlogs Locales:** No crear, sincronizar ni depender de archivos `TODO.md`, `backlog.md`, `NOTES.md` o bitácoras informales en cualquier nivel del proyecto. No volcar prompts, especificaciones de tareas ni planes de ejecución en carpetas o archivos temporales huérfanos (ej. `tasks/`, `prompts/`).
- **Trazabilidad en GitHub Issues:** Todo requerimiento pendiente, mejora, refactor o bug detectado debe formalizarse exclusiva y directamente como una **GitHub Issue** tipificando su perfil de ejecución (`profile:flash-low`, `profile:flash-medium`, `profile:flash-high`, `profile:pro`) e indexada en Projects v2.
- **Niveles de Ceremonia:**
  - **N0** (consultas, exploración, scripts en `scratch/`): sin issue ni rama. Pedidos informales de scripts sin ticket: snippet en el chat o `scratch/`, nunca en el workspace.
  - **N1** (cambio acotado, evidente, sin tocar `core/`, `runtimes/` ni ADR): issue mínima (cuerpo de 1-2 líneas), sin plan bloqueante, sin ADR ni label de perfil.
  - **N2** (funcionalidad nueva, refactor estructural, ambigüedad de diseño, impacto en `core/`, `runtimes/` o creación/modificación de ADR): ciclo completo con especificación exhaustiva, tipificación de perfil y plan formal.


---

## 2. Estructura Canónica del Cuerpo del Issue

El cuerpo del ticket debe ser exhaustivo y autosuficiente para eliminar la necesidad de redactar prompts manuales posteriores. Debe redactarse mediante herramientas nativas de archivos en el archivo temporal `.issue_body` con la siguiente estructura técnica:

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
| **1** | **Tooling / Automatización Local** | Scripts de verificación, tests locales, linters, utilidades o targets de `build.sh`. Impacto local al pipeline de compilación. | Target `./build.sh check`, `gh-pr-review`, `git-prune-gone`, linters. |
| **2** | **Skills bajo Demanda** | Procedimientos detallados, guías operativas o flujos E2E en `skills/*/SKILL.md` y `references/*.md`. Impacto acotado a la activación del skill. | Procedimientos de `issue-driven-workflow`, guías de `adr-manager`. |
| **3** | **Reglas Especializadas de Runtime** | Directivas acotadas al runtime activo en `runtimes/<runtime>/rules/*.md`. Impacto restringido a dicho entorno. | Especialización de sandbox para Antigravity (`rules/01-sandbox.md`). |
| **4** | **Core Basal / System Prompt Universal** | Invariantes duros de gobernanza, seguridad universal y principios irrenunciables en `core/*.md`. Impacto permanente y universal en cada turno. | Prohibición de push directo a `main`, confinamiento de sandbox, zero complacencia. |

- **Regla de Resolución:** Resolver siempre en el nivel de abstracción más bajo posible; no proponer ni ejecutar cambios en un nivel $N+1$ si el requerimiento puede resolverse eficazmente en un nivel menor o igual a $N$.

---

## 4. Matriz Canónica de Ruteo de Modelos y Metadata de Perfiles de Ejecución

Para habilitar la orquestación desatendida (*headless*) mediante herramientas de despacho automático (ej. `agent-cockpit`) y optimizar la asignación de recursos computacionales sin incurrir en sobredimensionamiento ni en subdimensionamiento analítico, toda issue registrada debe tipificarse deterministamente según su nivel de Minimal Blast Radius (MBR), la naturaleza técnica de la tarea y el perfil de modelo/thinking requerido.

### 4.1 Matriz de Correspondencia Técnica (MBR -> Perfil de Modelo)

| Nivel MBR | Naturaleza y Alcance Técnico | Perfil de Ejecución | Label de GitHub Issue | Familia y Modo de Thinking Recomendado |
| :---: | :--- | :--- | :--- | :--- |
| **0** | Tareas triviales, correcciones de formato, typos, documentación menor o sincronización cosmética. | `flash-low` | `profile:flash-low` | Gemini Flash (Thinking: low / mínimo). Máxima velocidad y latencia mínima. |
| **1 - 2** | Reglas markdown, configuraciones de runtime, tooling local con tests, scripts y procedimientos operativos de skills. | `flash-medium` | `profile:flash-medium` | Gemini Flash (Thinking: medium / estándar). Balance analítico óptimo y razonamiento guiado. |
| **3** | Refactors arquitectónicos, manejo de estado o concurrencia, reglas especializadas de runtime, diagnósticos inciertos o con múltiples hipótesis. | `flash-high` | `profile:flash-high` | Gemini Flash (Thinking: high / profundo) o Gemini Pro. Razonamiento intensivo y verificación sistemática. |
| **4** | Directivas basales (`core/`), blindaje de seguridad de runtime, invariantes universales, impacto transversal o cross-repo. | `pro` | `profile:pro` | Gemini Pro (Thinking: high / exhaustivo). Capacidad de frontera para deducción lógica estricta y contención de riesgo basal. |

### 4.2 Contrato de Metadata Estructurada (Machine-Readable)

Los orquestadores desatendidos consumen la metadata de perfiles directamente a través de GitHub API/CLI (`gh issue list --json labels`, `gh issue view --json labels`), evitando invocar modelos adicionales para clasificar la tarea y eliminando la fragilidad de parsing en lenguaje natural:
* **`profile:flash-low`**: Asignado a tareas MBR 0 sin impacto estructural ni lógico.
* **`profile:flash-medium`**: Asignado a tareas MBR 1 y MBR 2 (tooling, skills y configuraciones).
* **`profile:flash-high`**: Asignado a tareas MBR 3 (refactors, concurrencia, diagnósticos complejos).
* **`profile:pro`**: Asignado a tareas MBR 4 (invariantes basales, seguridad de runtime, impacto transversal).

---

## 5. Gate de Justificación de Elevación Basal

Toda propuesta en la especificación de una issue (`.issue_body`) o plan de implementación que plantee modificar directivas en la capa basal (`core/`) debe incluir obligatoriamente el apartado técnico **"Justificación de Elevación Basal"**. Dicha sección debe demostrar fehacientemente por qué la necesidad técnica es inviable o insuficiente de abordar en los niveles 0 a 3. Propuestas de modificación a `core/` sin esta justificación se consideran técnicamente inválidas por definición.

---

## 6. Creación Determinista del Issue y Protección de Prefix Matching

Debido a que el evaluador de permisos del runtime (Antigravity) anula el *prefix matching* cuando se utilizan comillas complejas o cadenas multilínea en la terminal, el cuerpo debe transferirse mediante archivo temporal y el perfil tipificarse vía label:

1. Redactar la especificación técnica en `.issue_body` mediante herramientas nativas de archivos.
2. Crear el issue mediante GitHub CLI especificando su perfil de ejecución:
   ```bash
   gh issue create --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body --label "profile:<perfil>"
   ```
3. Limpiar el archivo temporal en el mismo turno:
   ```bash
   rm -f .issue_body
   ```

---

## 7. Inyección Inmediata y Agnóstica al Tablero Central (Projects v2)

El workflow nativo `Auto-add to project` indexa automáticamente los issues de repositorios que coinciden con su filtro configurado. Para garantizar la indexación inmediata y agnóstica en repositorios fuera de dicho filtro (o como salvaguarda idempotente ante demoras del workflow):
```bash
gh project item-add <project_number> --owner <project_owner> --url <issue-url>
```
*(Donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json`, aplicando `1` y `@me` por defecto cuando no estén declarados).*

---

## 8. Taxonomía Canónica de Estados en Projects v2

El campo `Status` del tablero central (Project 1 `Proyectos-IA-V3`) define 6 estados canónicos, cuya transición está desacoplada de la CLI del agente y gobernada por el ciclo nativo de Git/GitHub y los Built-in Workflows (para la matriz completa de transiciones progresivas y regresivas, ver [`references/state-machine.md`](state-machine.md)):

| Estado | Significado Operativo | Agente Activo | Acciones Permitidas |
| :--- | :--- | :--- | :--- |
| `📥 Backlog` | Tarea registrada desde chats, requerimientos futuros o deuda técnica. Sin priorizar. | No | Consulta y edición de especificación. Prohibido codificar o crear ramas. |
| `🎯 Ready for Dev` | Tarea priorizada por el usuario, con especificación completa y criterios de aceptación. Lista para ser tomada. | No | Seleccionable para despacho vía Vía B (Backlog). |
| `📐 In Planning` | Tarea tomada por una sesión de agente. Fase activa de investigación técnica, exploración de dependencias y redacción de `implementation_plan.md` y/o borrador de ADR. | Sí | Lectura de código, tests locales no mutantes, redacción de plan/ADR. Prohibido mutar código de producción hasta aprobación humana (salvo fast-path). |
| `⚙️ In Progress` | Tarea en desarrollo activo tras aprobación humana del plan de implementación o por orden ejecutiva directa. | Sí | Edición de código de producción mediante I/O nativo, tests locales (`./build.sh check`), commits atómicos. |
| `👀 In Review / PR` | Implementación finalizada y Pull Request abierto en GitHub con vinculación `Closes #<id>`. | En espera / Review | Atención de comentarios de Code Review (`gh-pr-review`) en la rama del PR. |
| `Done` | PR fusionado (merge) en la rama troncal (`<base_branch>`) o tarea investigativa cerrada autónomamente. Cierre automático vía Built-in Workflows. | No | Tarea concluida. No admite mutaciones posteriores. |

---

## 9. Reporte al Usuario

Al completar la creación e indexación, el agente debe reportar al usuario:
- El número de issue asignado (`#<id>`).
- El enlace web directo al issue (`https://github.com/<owner>/<repo>/issues/<id>`).
- Confirmación de indexación en el tablero de Projects v2.

---

## 10. Control de Alcance (Scope Creep) y Tareas Derivadas

- El agente **no debe inflar** el objetivo del ticket original con refactors, mejoras o arreglos colaterales no contemplados en la especificación de la issue.
- Si durante el desarrollo se detecta un bug, deuda técnica o necesidad secundaria, el agente **lo lista al usuario y, con su confirmación, lo registra como una nueva GitHub Issue** (`gh issue create --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body --label "profile:<perfil>"`), indexarla al tablero central (`gh project item-add <project_number> --owner <project_owner> --url <issue-url>`) y continuar enfocado en el ticket asignado sin desviarse.
- **Vinculación Múltiple en Tareas Derivadas:** Si una tarea de investigación, auditoría forense o spike genera una o más issues derivadas de corrección/implementación, cuando se resuelva la causa raíz y se abra el Pull Request respectivo, el cuerpo del PR (`.pr_body`) DEBE declarar explícitamente el cierre de todas las issues vinculadas:
  ```markdown
  Closes #<issue_derivada>
  Closes #<issue_madre_investigacion>
  ```
  Esto garantiza que el merge en GitHub cierre automáticamente ambos tickets sin dejar tareas residuales en el backlog.

---

## 11. Consultas de Tablero y Coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*)

Ante preguntas de consulta, estado o coordinación sobre tareas pendientes en el tablero central:

1. **Comando CLI Simple y Filtrado Contextual por Repositorio:**
   Para prevenir la sobrecarga cognitiva y la dilución de contexto provocada por el volcado de inventarios masivos multi-proyecto, la consulta estándar ante preguntas sobre el board debe invocar el alias prefix-matchable `gh board` pasando únicamente el identificador `<owner>/<repo>`:
   ```bash
   gh board <owner>/<repo>
   ```
   *(Sustituir `<owner>/<repo>` por la identificación del repositorio actual).*

   - **Aprovisionamiento Canónico:** Los aliases `board` y `board-ready` se configuran de forma idempotente mediante `./build.sh link` (ver [`docs/setup.md`](../../../docs/setup.md)).
   - **Fallback sin Alias Configurado:** Si el alias no existe aún en el host, ejecutar la consulta cruda explicitando `--limit 100` para evitar el truncado de 30 ítems:
     ```bash
     gh project item-list <project_number> --owner <project_owner> --limit 100 --query "repo:<owner>/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'
     ```
     *(Donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json` o aplican `1` y `@me` por defecto).*

2. **Priorización Analítica y Recomendación (Top 2 a 3):**
   - **Evaluación Técnica:** El agente debe procesar el listado acotado del repositorio actual y evaluar la relevancia técnica de las tareas:
     - Priorizar fixes o bloqueos inmediatos, tareas en estado `🎯 Ready for Dev` o quick wins de alto impacto técnico frente a ítems de backlog general o de largo plazo.
     - Analizar dependencias lógicas y coherencia secuencial entre tickets para estructurar la progresión del trabajo.
   - **Respuesta Sintética y Asertiva:** En lugar de volcar listas exhaustivas o cortar ciegamente por índice posicional, emitir una respuesta concisa presentando el **Top 2 o 3** de tareas más convenientes para continuar, con una recomendación explícita y justificada de cuál tomar primero y cuál abordar después.
   - **Inventario Exhaustivo Solo Bajo Petición Expresa:** El volcado íntegro del inventario de tareas o la inclusión de ítems pertenecientes a otros repositorios del tablero queda restringido exclusivamente a cuando el usuario lo solicite de manera explícita (ej. *"mostrame todas las tareas del board sin filtrar"* o *"¿qué tareas hay en otros repositorios?"*).

> [!WARNING]
> **Uso de Filtrado Nativo en CLI:** No crear scripts intermediarios o efímeros (Python, Node, Bash, ej. `check_board.py`) para consultar, parsear o envolver llamadas a GitHub Projects. `gh` provee filtrado nativo (`--query`, `--field`, `-q / --jq`, `--limit`). Ejecutar scripts envoltorios con bypass viola la política de confinamiento, rompe el *prefix matching* y dispara solicitudes innecesarias de autorización interactiva.

---

## 12. Manifiesto Canónico de Configuración de Repositorio (`.repo-config.json`)

Para desacoplar el comportamiento del flujo de trabajo y la integración con GitHub Projects v2 de valores cableados o supuestos globales, todo repositorio puede definir en su raíz el archivo `.repo-config.json`. Queda formalmente descartado el uso de nombres genéricos como `config.json` para evitar colisiones con frameworks o herramientas del proyecto.

### 12.1 Contrato y Esquema Formal

```json
{
  "repository_type": "category_a",
  "base_branch": "main",
  "project_number": 1,
  "project_owner": "@me"
}
```

* **`repository_type`** *(string, opcional)*: Estrategia troncal del repositorio. Admite `"category_a"` (Trunk-Based / `main` única) o `"category_b"` (Git-Flow / `dev` -> `main`). Default: `"category_a"` (previa clasificación heurística; ver `branch-lifecycle.md` §1.1.1).
* **`base_branch`** *(string, opcional)*: Rama base de integración y verificación. Default: `"main"` (o `"dev"` en Categoría B).
* **`project_number`** *(integer, opcional)*: Número del tablero en GitHub Projects v2 al que pertenece el repositorio. Default: `1`.
* **`project_owner`** *(string, opcional)*: Identificador del propietario del tablero en GitHub Projects v2 (ej. `"@me"` para el usuario autenticado, o el nombre de una organización/usuario específico). Default: `"@me"`.

### 12.2 Resolución Dinámica con Fallback Determinista

Al consultar o interactuar con GitHub Projects v2 (`gh project item-list`, `gh project item-add`, `gh project link`), el agente debe:
1. Verificar si existe `.repo-config.json` en la raíz del workspace activo mediante herramientas nativas de lectura o inspección de archivos.
2. Extraer `project_number` y `project_owner` declarados.
3. Si el archivo no existe o alguna de las claves está omitida, aplicar de forma automática e inmediata los valores por defecto (`project_number: 1`, `project_owner: "@me"`), garantizando completa compatibilidad hacia atrás y cero intervención manual del usuario.
