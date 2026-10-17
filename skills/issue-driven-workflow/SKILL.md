---
name: issue-driven-workflow
description: >-
  Orchestrate end-to-end task execution driven by GitHub Issues and GitHub Projects v2, canonical backlog task registration, repository provisioning, branch lifecycles, and Pull Request workflows. ACTIVATE this skill whenever creating future issues/tasks, provisioning new GitHub repos, dispatched to implement an issue (e.g. 'implementa la issue #X'), picking tasks from Ready for Dev, managing feature/fix branch lifecycles, opening Pull Requests, or synchronizing cards in GitHub Projects. Operates with strict git hygiene, temporary file safety, and deterministic CLI commands.
---

# Issue-Driven Workflow and Pull Request Management

Guía operativa y protocolo estricto para el registro canónico de backlog, aprovisionamiento de repositorios, ciclo de vida completo de desarrollo orientado por tareas (GitHub Issues), aislamiento en ramas de trabajo, integración con GitHub Projects v2 y apertura estandarizada de Pull Requests.

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

### 1.3 Creación Determinista del Issue y Protección de Prefix Matching
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

### 1.4 Inyección Inmediata y Agnóstica al Tablero Central (Projects v2)
Para garantizar la indexación inmediata y agnóstica en el tablero central (sin depender de automatizaciones de auto-add restringidas en planes GitHub Free):
```bash
gh project item-add 1 --owner JerbilX --url <issue-url>
```
*(Ejecutado con `BypassSandbox: true` obligatorio desde el primer intento).*

### 1.5 Reporte al Usuario
Al completar la creación e indexación, el agente debe reportar al usuario:
- El número de issue asignado (`#<id>`).
- El enlace web directo al issue (`https://github.com/JerbilX/<repo>/issues/<id>`).
- Confirmación de indexación en el tablero de Projects v2.

### 1.6 Control de Alcance y Desvíos (Scope Creep)
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

---

## 3. Despacho y Recepción de Tareas (Fase 1: Bajo Demanda)

El agente opera bajo demanda ante directivas conversacionales del usuario en el chat:

### Vía A: Instrucción Directa (*"implementa la issue #<id>"*)
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

### Vía B: Instrucción de Backlog (*"toma la siguiente tarea lista en Ready for Dev"*)
1. Consultar exclusivamente las tareas en estado `🎯 Ready for Dev` usando el filtrado nativo server-side de `gh` para evitar desbordes de buffer (`<truncated lines>`):
   ```bash
   gh project item-list 1 --owner JerbilX --query 'status:"🎯 Ready for Dev"' --field "Status"
   ```
   *(Ejecutado con `BypassSandbox: true`).*
   - Si se requiere salida JSON compacta para lectura estructurada, utilizar el flag nativo `-q / --jq`:
     ```bash
     gh project item-list 1 --owner JerbilX --query 'status:"🎯 Ready for Dev"' --format json --jq '.items[] | {number: .content.number, title: .content.title, url: .content.url}'
     ```
   - Si no existen tareas en `🎯 Ready for Dev`, consultar opcionalmente tareas activas excluyendo las finalizadas:
     ```bash
     gh project item-list 1 --owner JerbilX --query '-status:Done' --field "Status" --limit 20
     ```
2. Identificar el ticket prioritario a abordar.
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
1. Posicionarse en la rama principal y sincronizar cambios:
   ```bash
   git checkout main
   git pull origin main
   ```
   *(Ejecutados con `BypassSandbox: true` desde el primer intento).*
2. Ejecutar la poda de higiene local para remover ramas ya fusionadas cuyo upstream remoto fue eliminado:
   ```bash
   git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d
   ```
   *(Ejecutado con `BypassSandbox: true` debido a que la eliminación de ramas muta `.git/refs/`).*
3. Crear y cambiar a la rama descriptiva (`git checkout -b feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) con `BypassSandbox: true` desde el primer intento.

### Paso 3: Planificación y Refinamiento
- **Blindaje del Planning Mode:** Toda tarea que implique diagnóstico de errores (bug fixing) o modificaciones arquitectónicas requiere obligatoriamente redactar `implementation_plan.md` con pausa bloqueante (`RequestFeedback: true`).
- **Excepción de Fast-Path Ejecutivo:** Si la solución técnica o cambio ya fue debatido y consensuado explícitamente en el chat y el usuario emitió una orden ejecutiva directa (*"procedé"*, *"avanza"*, *"aplicalo"*), el agente **NO DEBE** pausar con un plan bloqueante; procede de inmediato a la implementación.
- **Registro de ADRs:** Si se toman decisiones arquitectónicas o estructurales, registrar un nuevo ADR con `status: proposed` mediante el skill `adr-manager` (`docs/adr/NNNN-titulo.md`).

### Paso 4: Desarrollo y Verificación
- Aplicar cambios atómicos exclusivamente mediante las APIs nativas de archivos (`write_to_file`, `replace_file_content`, `view_file`, `grep_search`).
- Ejecutar compilaciones locales, linters y suites de prueba del proyecto para validar que no existan regresiones.

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
   gh pr create --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
   ```
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

## 7. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.

---

## 8. Parámetros de Red, Sandbox y Circuit Breaker

- **Exclusividad de Bypass y Mutadores:** `BypassSandbox: true` está reservado estricta y exclusivamente para comandos mutadores locales de Git (`git init`, `git checkout`, `git checkout -b`, `git branch -d/-D`, `git branch -m/-M`, `git add`, `git commit`, `git merge`, etc.) y comandos remotos o de red de Git y GitHub CLI (`git push`, `git fetch`, `git pull`, `gh issue`, `gh pr`, `gh project`, `gh repo`). Las operaciones de solo lectura (`git status`, `git log`, `git diff`, `git branch` de consulta) deben ejecutarse obligatoriamente de forma confinada (`BypassSandbox: false`).
- **Formato Atómico y Protección de Prefix Matching:** Debido a que el evaluador de permisos de runtimes como Antigravity anula el *prefix matching* ante el uso de comillas multilínea o caracteres complejos en argumentos CLI:
  - **PROHIBIDO** usar `git commit -m "..."`; escribir siempre el mensaje en `.commit_msg` con la API nativa de archivos y usar `git commit -F .commit_msg`.
  - **PROHIBIDO** usar `gh issue create --body "..."` o `gh pr create --body "..."` con cuerpos extensos o multilínea en terminal; escribir siempre el contenido en `.issue_body` o `.pr_body` con las herramientas nativas de archivos y utilizar `--body-file .issue_body` o `--body-file .pr_body`.
- **Prohibición de Scripts Intermediarios de Red y CLI:** Queda estrictamente prohibido generar scripts auxiliares (Python, Shell, Node) para ejecutar comandos de `gh` o parsear respuestas de red. Toda operación e inspección debe realizarse de forma directa y atómica utilizando los flags nativos provistos por GitHub CLI (`--query`, `--field`, `-q / --jq`, `--limit`). Si se requiere una consulta agregada compleja no soportada por `item-list`, la degradación elegante consiste en invocar directamente `gh api graphql` de forma nativa o aplicar Stop & Ask, sin violar el confinamiento del sandbox ni crear scripts huérfanos.
- **Circuit Breaker:** Toda consulta de red iterativa en terminal se limita a un máximo de 3 a 5 iteraciones; si la API carece de endpoint batch o experimenta latencia, el agente debe detenerse y reportar.
- **Higiene de Temporales:** Archivos auxiliares como `.commit_msg`, `.pr_body`, `.comment_body` o `.issue_body` deben ser redactados con las herramientas nativas de archivos, removerse inmediatamente tras su uso (`rm -f <archivo>`) y estar contemplados en `.gitignore`.
