---
name: issue-driven-workflow
description: >-
  Orchestrate end-to-end task execution driven by GitHub Issues and GitHub Projects v2, canonical backlog task registration, repository provisioning, branch lifecycles, and Pull Request workflows. ACTIVATE this skill whenever creating future issues/tasks, provisioning new GitHub repos, dispatched to implement an issue (e.g. 'implementa la issue #X'), querying the board or coordinating next tasks (e.g. '¿qué hay en el board?'), picking tasks from Ready for Dev, managing feature/fix branch lifecycles, opening Pull Requests, attending and resolving Code Review comments on Pull Requests, or synchronizing cards in GitHub Projects. Operates with strict git hygiene, temporary file safety, and deterministic CLI commands.
---

# Issue-Driven Workflow and Pull Request Management

Guía operativa y protocolo estricto para el registro canónico de backlog, aprovisionamiento de repositorios, ciclo de vida completo de desarrollo orientado por tareas (GitHub Issues), aislamiento en ramas de trabajo, integración con GitHub Projects v2, apertura estandarizada de Pull Requests y ciclo de resolución autónoma de Code Review.

---

## 1. Registro Canónico de Backlog y Tareas Futuras

Cuando el usuario solicite registrar una tarea, mejora, refactor o deuda técnica futura, o cuando durante el desarrollo se identifique un bug o necesidad secundaria fuera del alcance de la tarea activa:

### 1.1 Prohibición Estricta de Backlogs Locales y Archivos Huérfanos
- **Queda terminantemente prohibido** crear, sincronizar o depender de archivos `TODO.md`, `backlog.md`, `NOTES.md` o bitácoras informales en cualquier nivel del proyecto.
- **Queda terminantemente prohibido** volcar prompts, especificaciones de tareas o planes de ejecución en carpetas o archivos temporales huérfanos (ej. `tasks/`, `prompts/`).
- Todo requerimiento pendiente debe formalizarse exclusiva y directamente como una **GitHub Issue**.

### 1.2 Estructura Canónica del Cuerpo del Issue
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

### 1.3 Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius)
Al diseñar, planificar o registrar cualquier solución, el agente debe aplicar estrictamente la escala canónica de menor a mayor abstracción:

| Nivel | Capa de Abstracción | Mecanismo y Alcance | Ejemplo |
| :---: | :--- | :--- | :--- |
| **0** | **Configuración / Parámetro CLI / API** | Argumentos nativos, flags o capacidades existentes de la herramienta. Impacto local al comando invocado. | `--query`, `--format json`, `--field`, flags de `gh` o `git`. |
| **1** | **Tooling / Automatización Local** | Scripts de verificación, tests locales, linters o targets de `build.sh`. Impacto local al pipeline de compilación. | Target `./build.sh check`, validadores de esquemas, linters. |
| **2** | **Skills bajo Demanda** | Procedimientos detallados, guías operativas o flujos E2E en `skills/*/SKILL.md`. Impacto acotado a la activación del skill. | Procedimientos de `issue-driven-workflow`, guías de `adr-manager`. |
| **3** | **Reglas Especializadas de Runtime** | Directivas acotadas al runtime activo en `runtimes/<runtime>/rules/*.md`. Impacto restringido a dicho entorno. | Especialización de sandbox para Antigravity (`rules/01-sandbox.md`). |
| **4** | **Core Basal / System Prompt Universal** | Invariantes duros de gobernanza, seguridad universal y principios irrenunciables en `core/*.md`. Impacto permanente y universal en cada turno. | Prohibición de push directo a `main`, confinamiento de sandbox, zero complacencia. |

- **Regla Invariante de Resolución:** Queda **terminantemente prohibido** proponer o ejecutar cambios en un nivel $N+1$ si el problema técnico o requerimiento operativo puede resolverse eficazmente en un nivel menor o igual a $N$.

### 1.4 Gate de Justificación de Elevación Basal
Toda propuesta en la especificación de una issue (`.issue_body`) o plan de implementación que plantee modificar directivas en la capa basal (`core/`) debe incluir obligatoriamente el apartado técnico **"Justificación de Elevación Basal"**. Dicha sección debe demostrar fehacientemente por qué la necesidad técnica es inviable o insuficiente de abordar en los niveles 0 a 3. Propuestas de modificación a `core/` sin esta justificación se consideran técnicamente inválidas por definición.

### 1.5 Creación Determinista del Issue y Protección de Prefix Matching
Debido a que el evaluador de permisos del runtime (Antigravity) anula el *prefix matching* cuando se utilizan comillas complejas o cadenas multilínea en la terminal, el cuerpo debe transferirse obligatoriamente mediante archivo temporal:

1. Redactar la especificación técnica en `.issue_body` con `write_to_file`.
2. Crear el issue mediante GitHub CLI (`BypassSandbox: true` obligatorio desde el primer intento por requerir acceso de red):
   ```bash
   gh issue create --title "<tipo>(<alcance>): <descripción>" --body-file .issue_body
   ```
3. Limpiar inmediatamente el archivo temporal:
   ```bash
   rm -f .issue_body
   ```

### 1.6 Inyección Inmediata y Agnóstica al Tablero Central (Projects v2)
Para garantizar la indexación inmediata y agnóstica en el tablero central (sin depender de automatizaciones de auto-add restringidas en planes GitHub Free):
```bash
gh project item-add 1 --owner JerbilX --url <issue-url>
```
*(Ejecutado con `BypassSandbox: true` obligatorio desde el primer intento).*

### 1.7 Reporte al Usuario
Al completar la creación e indexación, el agente debe reportar al usuario:
- El número de issue asignado (`#<id>`).
- El enlace web directo al issue (`https://github.com/JerbilX/<repo>/issues/<id>`).
- Confirmación de indexación en el tablero de Projects v2.

### 1.8 Control de Alcance y Desvíos (Scope Creep)
- El agente **no debe inflar** el objetivo del ticket original con refactors, mejoras o arreglos colaterales no contemplados en la especificación de la issue.
- Si durante el desarrollo se detecta un bug, deuda técnica o necesidad secundaria, el agente **DEBE registrarla inmediatamente como una nueva GitHub Issue** (`gh issue create --body-file .issue_body`), indexarla al tablero central (`gh project item-add 1 --owner JerbilX --url <issue-url>`) y continuar enfocado en el ticket asignado sin desviarse.


---

## 2. Aprovisionamiento y Ciclo de Vida de Repositorios Remotos

Protocolo determinista para inicializar repositorios locales y aprovisionar repositorios remotos privados en GitHub.

### 2.1 Detección e Inicialización Local Proactiva
- Cuando el agente esté operando en un workspace donde existan archivos de desarrollo y no exista el directorio `.git`, debe proceder autónomamente a inicializar el repositorio local:
  ```bash
  git init
  ```
  *(Ejecutado con `BypassSandbox: true` desde el primer intento por mutación de `.git/`).*
- Garantizar que la rama principal sea `main`:
  ```bash
  git branch -M main
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Preparar los archivos para el commit inicial (`git add .`).
- Redactar el mensaje inicial en `.commit_msg` con `write_to_file` y crear el commit inicial:
  ```bash
  git commit -F .commit_msg
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Limpiar inmediatamente el archivo temporal: `rm -f .commit_msg`.

### 2.2 Gate de Confirmación Obligatorio para Remoto (Origin)
- El agente tiene **estrictamente prohibido** asumir la subida a GitHub sin confirmación previa del usuario.
- Una vez creado el commit local inicial, el agente debe preguntar de forma directa:
  > *"He inicializado el repositorio local y creado el primer commit. ¿Deseas que cree el repositorio privado en GitHub y lo suba a origin ahora?"*

### 2.3 Ejecución Determinista de Creación Remota y Enlace (Tras Confirmación)
Si el usuario **confirma**:
1. Ejecutar de forma autónoma el aprovisionamiento y push mediante:
   ```bash
   gh repo create JerbilX/<nombre-del-directorio> --private --source=. --remote=origin --push
   ```
   *(Ejecutado con `BypassSandbox: true`; sin delegar comandos de consola ni pedirle al usuario que los ejecute manualmente).*
2. Inmediatamente después, configurar la eliminación automática de ramas fusionadas en el repositorio remoto:
   ```bash
   gh repo edit JerbilX/<nombre-del-directorio> --delete-branch-on-merge
   ```
   *(Ejecutado con `BypassSandbox: true`).*
3. Si el entorno cuenta con permisos para Projects (`gh project`), proceder a enlazar el repositorio al tablero central:
   ```bash
   gh project link 1 --owner JerbilX --repo JerbilX/<nombre-del-directorio>
   ```
   *(Ejecutado con `BypassSandbox: true`).*

Si el usuario **rechaza**:
- El repositorio permanece exclusivamente bajo control de versiones local hasta nueva orden explícita.

### 2.4 Principio Git/GitHub-First para Interacción y Contexto de Repositorios

El skill gobierna cómo el agente interactúa con el ecosistema de repositorios según las necesidades de la tarea:

1. **La Fuente Canónica es Siempre Git / GitHub:**
   - Ante cualquier tarea que requiera conocer, descubrir, listar o validar repositorios de la organización (`JerbilX/*`), el agente debe consultar forzosamente los canales de Git y GitHub CLI (`gh repo list`, `gh repo view`, `git remote`).
   - Para listar repositorios de la organización:
     ```bash
     gh repo list JerbilX --limit 30 --json name,description,isPrivate
     ```
     *(Ejecutado con `BypassSandbox: true` por requerir acceso de red).*

2. **Prohibición de Reconocimiento Físico en Disco:**
   - La interacción con repositorios nunca debe inducir salidas del workspace ni exploraciones en el sistema de archivos del host (`list_dir`, `find_by_name`, `ls` en carpetas hermanas o `..`).
   - El agente no debe inferir ni inspeccionar si un repositorio está clonado localmente a menos que opere dentro del workspace activo correspondiente.

3. **Desacoplamiento en Fases de Diseño y Arquitectura:**
   - En tareas de arquitectura, diseño, RFCs o ADRs que contemplen integración multi-repo, los contratos y rutas deben diseñarse de forma agnóstica (vía configuración, parámetros o variables como `WORKSPACE_ROOT`), resolviendo la interacción mediante APIs o CLI sin requerir inspección física del host.

---

## 3. Despacho y Recepción de Tareas (Fase 1: Bajo Demanda)

El agente opera bajo demanda ante directivas conversacionales del usuario en el chat:

> [!IMPORTANT]
> **Comportamiento Ante Consultas de Coordinación:** Preguntas meta-conversacionales o de coordinación en el chat (ej. *"¿con qué seguimos?"*, *"¿qué hay en el board?"*, *"¿cerramos este hilo e iniciamos uno nuevo?"*) son exclusivamente de consulta o planificación. Queda estrictamente prohibido ejecutar mutaciones, sincronizaciones preparatorias o cambios de rama en Git en la terminal hasta que el usuario emita una directiva explícita de despacho o implementación.

### 3.1 Consultas de Tablero y Coordinación (*"¿qué hay en el board?"*, *"¿con qué seguimos?"*)

Ante preguntas de consulta, estado o coordinación sobre las tareas pendientes en el tablero central (Project 1 `Proyectos-IA-V3`):

1. **Comando CLI Simple y Filtrado Contextual por Repositorio:**
   Para prevenir la sobrecarga cognitiva y la dilución de contexto provocada por el volcado de inventarios masivos multi-proyecto, la consulta estándar ante preguntas sobre el board debe filtrar los ítems activos exclusivamente para el repositorio donde está posicionado el agente:
   ```bash
   gh project item-list 1 --owner JerbilX --query "repo:JerbilX/<repo> -status:Done" --format json --jq '.items[] | {number: .content.number, title: .content.title, status: .status}'
   ```
   *(Ejecutado con `BypassSandbox: true` obligatorio desde el primer intento por requerir acceso de red; sustituir `<repo>` por el nombre del repositorio actual, ej. `Dotfiles-IA-Agents`).*

2. **Priorización Analítica y Recomendación (Top 2 a 3):**
   - **Evaluación Técnica:** El agente debe procesar el listado acotado del repositorio actual y evaluar la relevancia técnica de las tareas:
     - Priorizar fixes o bloqueos inmediatos, tareas en estado `🎯 Ready for Dev` o quick wins de alto impacto técnico frente a ítems de backlog general o de largo plazo.
     - Analizar dependencias lógicas y coherencia secuencial entre tickets para estructurar la progresión del trabajo.
   - **Respuesta Sintética y Asertiva:** En lugar de volcar listas exhaustivas o cortar ciegamente por índice posicional, emitir una respuesta concisa presentando el **Top 2 o 3** de tareas más convenientes para continuar, con una recomendación explícita y justificada de cuál tomar primero y cuál abordar después.
   - **Inventario Exhaustivo Solo Bajo Petición Expresa:** El volcado íntegro del inventario de tareas o la inclusión de ítems pertenecientes a otros repositorios del tablero queda restringido exclusivamente a cuando el usuario lo solicite de manera explícita (ej. *"mostrame todas las tareas del board sin filtrar"* o *"¿qué tareas hay en otros repositorios?"*).

### 3.2 Despacho de Tareas: Vía A - Instrucción Directa (*"implementa la issue #<id>"*)
1. Consultar el contexto técnico completo de la issue:
   ```bash
   gh issue view <id>
   ```
   *(Ejecutado con `BypassSandbox: true`).*
2. Transicionar el estado del ticket en el tablero central (Project 1) a `⚙️ In Progress`:
   ```bash
   gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "⚙️ In Progress"
   ```
   *(Ejecutado con `BypassSandbox: true`).*

### 3.3 Despacho de Tareas: Vía B - Instrucción de Backlog (*"toma la siguiente tarea lista en Ready for Dev"*)
1. Consultar exclusivamente las tareas en estado `🎯 Ready for Dev` acotadas al repositorio actual usando el filtrado nativo server-side de `gh` para evitar desbordes de buffer (`<truncated lines>`):
   ```bash
   gh project item-list 1 --owner JerbilX --query 'repo:JerbilX/<repo> status:"🎯 Ready for Dev"' --field "Status"
   ```
   *(Ejecutado con `BypassSandbox: true`).*
   - Si se requiere salida JSON compacta para lectura estructurada, utilizar el flag nativo `-q / --jq`:
     ```bash
     gh project item-list 1 --owner JerbilX --query 'repo:JerbilX/<repo> status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'
     ```
   - Si no existen tareas en `🎯 Ready for Dev`, consultar opcionalmente tareas activas excluyendo las finalizadas:
     ```bash
     gh project item-list 1 --owner JerbilX --query 'repo:JerbilX/<repo> -status:Done' --field "Status" --limit 20
     ```
2. Identificar el ticket prioritario a abordar aplicando el criterio de priorización analítica (Top 2-3).
3. Transicionar dicho ítem a `⚙️ In Progress` mediante el comando determinista directo:
   ```bash
   gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "⚙️ In Progress"
   ```
   *(Ejecutado con `BypassSandbox: true`).*
4. Proceder con la ingesta técnica de la tarea (`gh issue view <id>`).

> [!CAUTION]
> **Prohibición de Scripts Envoltorios Ad-hoc:** Queda terminantemente prohibido crear scripts intermediarios o efímeros (Python, Node, Bash, ej. `check_board.py`) para consultar, parsear o envolver llamadas a GitHub Projects. `gh` provee filtrado nativo (`--query`, `--field`, `-q / --jq`, `--limit`). Ejecutar scripts envoltorios con `BypassSandbox: true` viola la política de confinamiento de Antigravity (que reserva el bypass exclusivamente para la suite de `git` y `gh`), rompe el *prefix matching* y dispara solicitudes innecesarias de autorización interactiva.

---

## 4. Convención Canónica de Ramas de Trabajo

Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código del workspace.

### 4.1 Estrategia Híbrida Contextual (Ref: docs/adr/0021-estrategia-de-ramas-troncales-y-promocion-de-entornos.md)
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

### 4.2 Detección Declarativa de la Estrategia del Repositorio
Al iniciar el trabajo en un repositorio, el agente inspecciona el archivo de configuración en la raíz (`.repo-config.json` o `config.json`):
```json
{
  "repository_type": "category_a",
  "base_branch": "main"
}
```
En ausencia de archivo de configuración o si no se explicita `repository_type`, se adopta por defecto **Categoría A** (`base_branch: "main"`).

### 4.3 Nomenclatura Canónica de Ramas Efímeras
- **Nomenclatura Obligatoria:**
  - Para nuevas funcionalidades o tareas generales: `feat/issue-<id>-<slug>`
  - Para corrección de errores o parches: `fix/issue-<id>-<slug>`
- **Creación in-place (Fase 1):**
  ```bash
  git checkout -b <nombre-de-rama>
  ```
  *(Ejecutado con `BypassSandbox: true` desde el primer intento debido al montaje `ro` de `.git/`).*

---

## 5. Ciclo de Vida E2E de la Tarea

Cualquier tarea despachada debe cumplir secuencialmente con las siguientes 7 fases:

```
[1. Ingesta] -> [2. Higiene de Ramas] -> [3. Planificación] -> [4. Desarrollo] -> [5. Commit] -> [6. Push] -> [7. PR & Tablero]
```

### Paso 1: Ingesta Técnica
- Lectura profunda de los requerimientos, contexto, diagnóstico y criterios de aceptación en `gh issue view <id>`.

### Paso 2: Aislamiento e Higiene del Workspace
1. Posicionarse en la rama base del repositorio (`main` por defecto, o `dev` en Categoría B) y sincronizar cambios podando referencias remotas obsoletas:
   ```bash
   git checkout <base_branch>
   git pull --prune --ff-only
   ```
   *(Ejecutados con `BypassSandbox: true` desde el primer intento).*
   - **Mecánica de Transporte de Git:** Invocado sin argumentos posicionales de remoto o rama (`origin main`), `git pull --prune --ff-only` procesa el refspec estándar completo (`+refs/heads/*:refs/remotes/origin/*`), poda de forma automática las referencias zombi (`remotes/origin/*`) y avanza la rama base exclusivamente en modo fast-forward. Esto erradica la invocación de `git merge`, garantizando una ejecución 100% desatendida y sin modales interactivos de confirmación en Antigravity, cumpliendo estrictamente con la prohibición de merge hacia ramas troncales de `core/09-issue-driven-workflow.md`.
   - **Prohibición Categórica de `git remote prune`:** Queda terminantemente prohibido ejecutar `git remote prune` (ej. `git remote prune origin`). Toda poda de tracking remoto debe canalizarse exclusivamente a través del transporte estándar de sincronización (`git pull --prune --ff-only` o `git fetch --prune origin`).
2. Ejecutar la poda de higiene local en dos fases atómicas para remover ramas ya fusionadas cuyo upstream remoto fue eliminado:
   - **Fase 1: Inspección Pasiva Confinada (`BypassSandbox: false` obligatorio):**
     Consultar el estado de tracking de las ramas locales mediante una llamada nativa de lectura:
     ```bash
     git branch --format "%(refname:short) %(upstream:track)"
     ```
     El modelo/agente inspecciona la salida en su propio contexto para identificar qué ramas presentan el estado `[gone]`.
   - **Fase 2: Poda Atómica Mutadora (`BypassSandbox: true` obligatorio desde el primer intento):**
     Si existen ramas con upstream marcado como `[gone]`, invocar directamente la poda atómica con el binario de Git sin envoltorios ni tuberías:
     ```bash
     git branch -d <rama1> <rama2>
     ```
     Si no existen ramas con estado `[gone]`, no se emite ninguna llamada mutadora.
   - **Prohibición Categórica de Pipelines y Wrappers CLI (`awk` / `xargs`):** Queda terminantemente prohibido utilizar tuberías o utilidades intermediarias (ej. `git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d`). Encadenar comandos en pipes rompe el *prefix matching* de seguridad en Antigravity, viola los estándares de entorno (`core/10-environment-standards.md`), vulnera el confinamiento de sandbox al delegar privilegios de bypass a binarios no autorizados (`runtimes/antigravity/rules/01-sandbox.md`) y dispara modales interactivos de confirmación de permisos.
3. Crear y cambiar a la rama descriptiva (`git checkout -b feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) con `BypassSandbox: true` desde el primer intento.

### Paso 3: Planificación y Refinamiento
- **Blindaje del Planning Mode:** Toda tarea que implique diagnóstico de errores (bug fixing) o modificaciones arquitectónicas requiere obligatoriamente redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
- **Evaluación Obligatoria de Minimal Blast Radius:** Todo plan de implementación debe evaluar y registrar explícitamente el nivel de intervención más bajo posible (Nivel 0 a 4). Si la propuesta plantea modificar directivas basales (`core/`), debe incorporar obligatoriamente la sección **"Justificación de Elevación Basal"** acreditando la inviabilidad técnica en los niveles 0 a 3.
- **Excepción de Fast-Path Ejecutivo:** Si la solución técnica o cambio ya fue debatido y consensuado explícitamente en el chat y el usuario emitió una orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), el agente **NO DEBE** pausar con un plan bloqueante; procede de inmediato a la implementación.
- **Registro de ADRs:** Si se toman decisiones arquitectónicas o estructurales, registrar un nuevo ADR con `status: proposed` mediante el skill `adr-manager` (`docs/adr/NNNN-titulo.md`).

### Paso 4: Desarrollo y Verificación
- Aplicar cambios atómicos exclusivamente mediante las APIs nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`).
- Ejecutar compilaciones locales, linters y suites de prueba del proyecto para validar que no existan regresiones.
- **Transición de ADRs a Accepted:** Al finalizar el desarrollo y verificar los cambios (o tras la aprobación humana del plan), transicionar todo nuevo ADR asociado a la tarea a `status: accepted` en la rama de trabajo antes del commit. La posterior revisión y fusión (merge) del PR en `main` por parte del usuario constituye el gate definitivo de ratificación, asegurando que `main` no reciba ADRs en `proposed` ni se generen PRs redundantes.

### Paso 5: Commit Atómico
- Debido a que el evaluador de permisos anula el prefijo con comillas, **queda estrictamente prohibido** usar `git commit -m "..."`.
- Redactar el mensaje convencional en `.commit_msg` con `write_to_file`.
- Ejecutar el commit leyendo el archivo con `BypassSandbox: true` desde el primer intento:
   ```bash
   git commit -F .commit_msg
   ```
- Limpiar inmediatamente el archivo temporal: `rm -f .commit_msg`.

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
- Limpiar inmediatamente el archivo temporal: `rm -f .pr_body`.

---

## 6. Flujo Mandatorio de Pull Requests y Projects v2

- **Prohibición Total de Push/Merge a `main`:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
- **Vinculación Canónica de Cierre:** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse el PR.
- **Sincronización Determinista con el Tablero Central:** Asegurar que el estado del ítem en Project 1 pase a `👀 In Review / PR` mediante el comando directo por nombre de campo:
  ```bash
  gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "👀 In Review / PR"
  ```
  *(Queda prohibido ejecutar consultas exploratorias de `field-list` o `item-list` para resolver IDs cuando el comando directo es determinista).*
- **Gate de Aprobación Humana:** La revisión del diff, aprobación y fusión del PR es responsabilidad exclusiva del PM / Tech Lead en la interfaz de GitHub.

---

## 7. Sub-protocolo de Feedback Loop y Resolución Autónoma de Code Review

Protocolo operativo determinista para atender observaciones, revisiones humanas y comentarios inline dejados en el diff de Pull Requests en GitHub.

### 7.1 Criterios de Activación y Ámbito
- **Trigger Conversacional:** El agente activa este sub-protocolo cuando el usuario solicite atender, corregir o resolver observaciones de Code Review en un Pull Request activo (ej. *"resolvé los comentarios del PR #<id>"*, *"atendé el review del PR #<id>"*, *"revisá el feedback dejado en el diff de #<id>"*).
- **Aislamiento en Rama Activa:** Todas las correcciones solicitadas en la revisión de código deben realizarse estrictamente sobre la rama activa del Pull Request. Queda **terminantemente prohibido** crear ramas secundarias o abrir nuevos issues para abordar observaciones del code review del PR activo.

### 7.2 Fase 1: Contexto y Sincronización de Rama
1. **Posicionamiento en la Rama del PR:**
   - Si el workspace ya se encuentra en la rama asociada al PR, sincronizar con el remoto para incorporar posibles commits o sugerencias aplicadas desde la web:
     ```bash
     git pull --ff-only
     ```
   - Si el workspace se encuentra en otra rama o se atiende el PR en una nueva sesión, posicionarse deterministamente en la rama del PR:
     ```bash
     gh pr checkout <pr_id>
     ```
     *(Ejecutados con `BypassSandbox: true` obligatorio desde el primer intento).*

### 7.3 Fase 2: Ingesta Determinista de Feedback de Review
1. **Inspección de Reseñas Generales y Veredicto:**
   Consultar los comentarios globales y el estado de aprobación del Pull Request:
   ```bash
   gh pr view <pr_id> --comments
   ```
   *(Ejecutado con `BypassSandbox: true`).*

2. **Consulta Determinista de Comentarios Inline en el Diff:**
   Para obtener los comentarios específicos línea por línea dejados en el diff del Pull Request, consultar directamente el endpoint nativo de la API de GitHub mediante GitHub CLI:
   ```bash
   gh api repos/:owner/:repo/pulls/<pr_id>/comments --jq '.[] | {id: .id, path: .path, line: (.line // .original_line), diff_hunk: .diff_hunk, body: .body}'
   ```
   *(Ejecutado con `BypassSandbox: true` obligatorio desde el primer intento por requerir acceso de red; los marcadores `:owner` y `:repo` son autocompletados automáticamente por GitHub CLI según el contexto del repositorio).*

3. **Prohibición Categórica de Scripts Envoltorios o Tuberías:**
   Queda estrictamente prohibido crear scripts temporales (Python, Bash, Node, ej. `fetch_comments.py`) o encadenar tuberías con utilidades de terminal (`awk`, `sed`, `jq` externo). Todo el parseo y filtrado debe realizarse mediante los flags nativos de GitHub CLI (`--jq`) para preservar el *prefix matching* de seguridad de Antigravity.

### 7.4 Fase 3: Flujo Atómico de Resolución
1. **Mapeo y Análisis Técnico:**
   - Inspeccionar el archivo afectado (`path`) y las líneas señaladas (`line` / `diff_hunk`) mediante la herramienta nativa `view_file`.
   - Contrastar la observación del revisor con el diseño del sistema y los invariantes del proyecto, identificando la solución con el menor radio de impacto posible (*Minimal Blast Radius*).
2. **Aplicación de Parches:**
   - Aplicar las correcciones solicitadas exclusivamente a través de las herramientas nativas de edición (`replace_file_content` o `write_to_file`). Prohibido usar comandos CLI de streaming (`sed`, `cat >`, `echo >>`) o scripts efímeros de parcheo.
3. **Verificación Estática y Local (Shift-Left):**
   - Ejecutar la suite de pruebas del proyecto y linters locales:
     ```bash
     ./build.sh check
     ```
     *(Ejecutado con `BypassSandbox: false` confinado).*
   - Validar que no existan errores (0 errores) y que el presupuesto de contexto se mantenga dentro de los umbrales definidos.
4. **Commit Atómico de Corrección:**
   - Redactar el mensaje en el archivo temporal `.commit_msg` mediante `write_to_file` siguiendo el estándar convencional:
     `fix(<alcance>): atender feedback de code review en PR #<id>`
   - Ejecutar el commit leyendo el archivo con `BypassSandbox: true`:
     ```bash
     git commit -F .commit_msg
     rm -f .commit_msg
     ```
5. **Publicación Remota:**
   - Subir los commits a la rama del Pull Request:
     ```bash
     git push
     ```
     *(Ejecutado con `BypassSandbox: true`).*

### 7.5 Fase 4: Trazabilidad y Cierre del Ciclo de Feedback
1. **Respuesta Opcional a Comentarios Inline Específicos:**
   Si se requiere dejar constancia explícita sobre un hilo de comentario puntual en el diff:
   ```bash
   gh api repos/:owner/:repo/pulls/<pr_id>/comments/<comment_id>/replies -f body="Resuelto en commit <short_sha>: <descripción concisa>"
   ```
   *(Ejecutado con `BypassSandbox: true`).*
2. **Comentario Consolidado en el Pull Request:**
   Para notificar formalmente al revisor humano que las observaciones fueron atendidas:
   - Redactar el resumen en `.pr_comment` mediante `write_to_file`.
   - Publicar el comentario en el PR:
     ```bash
     gh pr comment <pr_id> --body-file .pr_comment
     rm -f .pr_comment
     ```
     *(Ejecutado con `BypassSandbox: true`).*
3. **Preservación del Estado en Projects v2:**
   - La tarjeta de la tarea permanece en `👀 In Review / PR` en el tablero central (Project 1) a la espera de la re-inspección, aprobación y fusión (merge) definitiva por parte del usuario.

---

## 8. Protocolo de Rollback y Reversión de Emergencia

Cuando tras la fusión (merge) de un Pull Request en `main` se detecten anomalías críticas, roturas de compilación, fallos de sandbox o regresiones funcionales severas que comprometan la estabilidad del entorno, debe activarse de inmediato el protocolo de reversión estandarizado.

### 8.1 Criterios de Activación
- **Rotura de Build o Tests:** El código en `main` no compila o falla catastróficamente en `./build.sh check` o suites de prueba locales.
- **Bloqueo Crítico de Operación:** Directivas o scripts generan bucles infinitos, fallos de permisos insalvables o vulneraciones de seguridad.
- **Inconsistencia Arquitectónica:** Fusión accidental de cambios que contradicen decisiones vigentes (`docs/adr/`) sin discusión previa.

### 8.2 Ciclo de Ramas y Git (Reversión Atómica)
Para preservar la prohibición estricta de push directo o reescritura de historia (`git reset --hard`) en `main`:

1. **Sincronizar `main`:**
   ```bash
   git checkout main
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
   Obtener el SHA del commit de merge (`<merge_commit_sha>`) y revertirlo indicando la línea principal (`-m 1`):
   ```bash
   git revert -m 1 <merge_commit_sha> --no-commit
   ```
   *(Ejecutado con `BypassSandbox: true`). El flag `--no-commit` previene que Git abra un editor interactivo en terminal y permite formatear el mensaje de commit de manera determinista y controlada.*

4. **Commit Atómico de Reversión:**
   Redactar el mensaje convencional en `.commit_msg` con la herramienta nativa `write_to_file`:
   ```markdown
   fix(revert): revert PR #<pr_id> - <motivo breve>

   Reverts PR #<pr_id> (<merge_commit_sha>).
   Razón: <diagnóstico técnico conciso de la regresión o anomalía>.
   ```
   Ejecutar el commit leyendo el archivo temporal:
   ```bash
   git commit -F .commit_msg
   rm -f .commit_msg
   ```
   *(Commit ejecutado con `BypassSandbox: true`).*

5. **Publicación Remota:**
   ```bash
   git push -u origin fix/revert-pr-<id>-<slug>
   ```
   *(Ejecutado con `BypassSandbox: true`).*

### 8.3 Gestión de Backlog y Tablero Central (Projects v2)
Una reversión no debe dejar cabos sueltos ni tarjetas en estados inconsistentes:

1. **Apertura del Pull Request de Reversión:**
   Redactar el cuerpo del PR en `.pr_body` con `write_to_file`:
   ```markdown
   ### Diagnóstico de Emergencia
   [Descripción de la anomalía o regresión que motiva la reversión]

   ### Cambios
   - Reversión atómica del merge commit `<merge_commit_sha>`.
   - Restablecimiento del estado estable previo en `main`.

   Reverts #<pr_id>
   ```
   Publicar el PR mediante GitHub CLI:
   ```bash
   gh pr create --title "fix(revert): revert PR #<pr_id> - <motivo>" --body-file .pr_body
   rm -f .pr_body
   ```
   *(Ejecutado con `BypassSandbox: true`).*

2. **Indexación y Transición del PR de Reversión:**
   Asegurar que la tarjeta del PR de reversión ingrese en el tablero central (Project 1) en estado `👀 In Review / PR`:
   ```bash
   gh project item-edit 1 --owner JerbilX --url <revert-pr-url> --field "Status" --value "👀 In Review / PR"
   ```
   *(Ejecutado con `BypassSandbox: true`).*

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
   rm -f .issue_comment
   ```
   Transicionar deterministamente la tarjeta de la issue reabierta en Project 1 al estado `🎯 Ready for Dev`:
   ```bash
   gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "🎯 Ready for Dev"
   ```
   *(Ejecutado con `BypassSandbox: true`).*

### 8.4 Gobierno Arquitectónico (MADR)
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

### 8.5 Restauración Local en Sistema Anfitrión (`build.sh rollback`)
Si la falla o regresión afectó el entorno local desplegado en el host (directorios `~/.gemini/config/` o `~/.claude/`):
1. Ejecutar de forma inmediata la restauración atómica del último respaldo funcional:
   ```bash
   ./build.sh rollback [runtime]
   ```
   *(Ejecutado localmente para restaurar `AGENTS.md` y `mcp_config.json` desde su último `.bak.<timestamp>`).*
2. Ejecutar `./build.sh check [runtime]` para validar la estabilidad recuperada del anfitrión.

---

## 9. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.

---

## 10. Parámetros de Red, Sandbox y Circuit Breaker

- **Exclusividad de Bypass y Mutadores:** `BypassSandbox: true` está reservado estricta y exclusivamente para comandos mutadores locales de Git (`git init`, `git checkout`, `git checkout -b`, `git branch -d/-D`, `git branch -m/-M`, `git add`, `git commit`, `git merge`, etc.) y comandos remotos o de red de Git y GitHub CLI (`git push`, `git fetch`, `git pull`, `gh issue`, `gh pr`, `gh project`, `gh repo`). Las operaciones de solo lectura (`git status`, `git log`, `git diff`, `git branch` de consulta) deben ejecutarse obligatoriamente de forma confinada (`BypassSandbox: false`).
- **Formato Atómico y Protección de Prefix Matching:** Debido a que el evaluador de permisos de runtimes como Antigravity anula el *prefix matching* ante el uso de comillas multilínea o caracteres complejos en argumentos CLI:
  - **PROHIBIDO** usar `git commit -m "..."`; escribir siempre el mensaje en `.commit_msg` con la API nativa de archivos y usar `git commit -F .commit_msg`.
  - **PROHIBIDO** usar `gh issue create --body "..."` o `gh pr create --body "..."` con cuerpos extensos o multilínea en terminal; escribir siempre el contenido en `.issue_body` o `.pr_body` con las herramientas nativas de archivos y utilizar `--body-file .issue_body` o `--body-file .pr_body`.
  - **PROHIBIDO** encadenar comandos de Git mediante tuberías (`|`) o utilidades intermediarias/envoltorios (`awk`, `xargs`, `sed`, `grep`, `env`). Toda operación de Git debe invocarse de forma atómica y directa para preservar el *prefix matching* y evitar la delegación indebida de privilegios de `BypassSandbox: true` a utilidades de terminal.
- **Prohibición de Scripts Intermediarios de Red y CLI:** Queda estrictamente prohibido generar scripts auxiliares (Python, Shell, Node) para ejecutar comandos de `gh` o parsear respuestas de red. Toda operación e inspección debe realizarse de forma directa y atómica utilizando los flags nativos provistos por GitHub CLI (`--query`, `--field`, `-q / --jq`, `--limit`). Si se requiere una consulta agregada compleja no soportada por `item-list`, la degradación elegante consiste en invocar directamente `gh api graphql` de forma nativa o aplicar Stop & Ask, sin violar el confinamiento del sandbox ni crear scripts huérfanos.
- **Prohibición Categórica de `git remote prune`:** Prohibido invocar `git remote prune <remote>`. La poda de referencias remotas obsoletas debe gestionarse exclusivamente mediante el comando estándar de transporte (ej. `git pull --prune --ff-only` o `git fetch --prune <remote>`). Invocaciones aisladas a `git remote prune` violan la política desatendida y disparan alertas interactivas de confirmación de permisos en Antigravity.
- **Circuit Breaker:** Toda consulta de red iterativa en terminal se limita a un máximo de 3 a 5 iteraciones; si la API carece de endpoint batch o experimenta latencia, el agente debe detenerse y reportar.
- **Higiene de Temporales:** Archivos auxiliares como `.commit_msg`, `.pr_body`, `.comment_body` o `.issue_body` deben ser redactados con las herramientas nativas de archivos, removerse inmediatamente tras su uso (`rm -f <archivo>`) y estar contemplados en `.gitignore`.
