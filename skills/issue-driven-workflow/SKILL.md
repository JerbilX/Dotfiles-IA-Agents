---
name: issue-driven-workflow
description: >-
  Orchestrate end-to-end task execution driven by GitHub Issues and GitHub Projects v2. ACTIVATE this skill whenever dispatched to implement an issue (e.g. 'implementa la issue #X'), pick tasks from Ready for Dev, manage feature/fix branch lifecycles, open Pull Requests, or synchronize cards in GitHub Projects. Operates with strict git hygiene and deterministic CLI commands.
---

# Issue-Driven Workflow and Pull Request Management

Guía operativa y protocolo estricto para el ciclo de vida completo de desarrollo orientado por tareas (GitHub Issues), aislamiento en ramas de trabajo, integración con GitHub Projects v2 y apertura estandarizada de Pull Requests.

---

## 1. Despacho y Recepción de Tareas (Fase 1: Bajo Demanda)

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
1. Consultar los ítems del tablero central:
   ```bash
   gh project item-list 1 --owner JerbilX --format json
   ```
   *(Ejecutado con `BypassSandbox: true`).*
2. Identificar el primer ticket cuyo estado sea `🎯 Ready for Dev`.
3. Transicionar dicho ítem a `⚙️ In Progress` mediante el comando determinista directo.
4. Proceder con la ingesta técnica de la tarea.

---

## 2. Convención Canónica de Ramas de Trabajo

Todo desarrollo debe aislarse en una rama dedicada creada antes de modificar cualquier archivo de código del workspace.

- **Nomenclatura Obligatoria:**
  - Para nuevas funcionalidades o tareas generales: `feat/issue-<id>-<slug>`
  - Para corrección de errores o parches: `fix/issue-<id>-<slug>`
- **Creación in-place (Fase 1):**
  ```bash
  git checkout -b <nombre-de-rama>
  ```
  *(Si el entorno restringe escrituras en `.git/`, autorizar `BypassSandbox: true`).*

---

## 3. Ciclo de Vida E2E de la Tarea

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
2. Ejecutar la poda de higiene local para remover ramas ya fusionadas cuyo upstream remoto fue eliminado:
   ```bash
   git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d
   ```
3. Crear y cambiar a la rama descriptiva (`git checkout -b feat/issue-<id>-<slug>`).

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
- Ejecutar el commit leyendo el archivo:
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
- Redactar el cuerpo del PR y publicarlo mediante GitHub CLI (`BypassSandbox: true`):
   ```bash
   gh pr create --title "<tipo>(<alcance>): <descripción>" --body-file .pr_body
   ```
- Limpiar inmediatamente el archivo temporal `.pr_body`.

---

## 4. Flujo Mandatorio de Pull Requests y Projects v2

- **Prohibición Total de Push/Merge a `main`:** Queda terminantemente prohibido que el agente comitee o pushee cambios productivos directamente a la rama `main`, o que ejecute `git merge` hacia `main` por su cuenta.
- **Vinculación Canónica de Cierre:** El cuerpo del Pull Request debe incluir obligatoriamente la directiva `Closes #<id>` o `Fixes #<id>` para asegurar el cierre automático de la issue al fusionarse el PR.
- **Sincronización Determinista con el Tablero Central:** Asegurar que el estado del ítem en Project 1 pase a `👀 In Review / PR` mediante el comando directo por nombre de campo:
  ```bash
  gh project item-edit 1 --owner JerbilX --url <issue-url> --field "Status" --value "👀 In Review / PR"
  ```
  *(Queda prohibido ejecutar consultas exploratorias de `field-list` o `item-list` para resolver IDs cuando el comando directo es determinista).*
- **Gate de Aprobación Humana:** La revisión del diff, aprobación y fusión del PR es responsabilidad exclusiva del PM / Tech Lead en la interfaz de GitHub.

---

## 5. Protocolo Operativo de Salida y Reporte Estandarizado

Al completar la publicación del PR, el agente **DEBE emitir un reporte final estructurado** que incluya obligatoriamente:
1. Resumen técnico conciso de los cambios realizados.
2. Verificaciones y pruebas ejecutadas exitosamente.
3. Enlace web directo al Pull Request creado en GitHub.
4. Confirmación del estado de la tarjeta en el tablero de Projects v2 (`👀 In Review / PR`).
5. Indicación explícita para que el usuario revise el diff y apruebe/fusione el PR.

---

## 6. Parámetros de Red, Sandbox y Circuit Breaker

- **Exclusividad de Bypass:** `BypassSandbox: true` está reservado estricta y exclusivamente para comandos de Git y GitHub CLI (`git push`, `git fetch`, `git pull`, `gh issue`, `gh pr`, `gh project`, `gh repo`).
- **Circuit Breaker:** Toda consulta de red iterativa en terminal se limita a un máximo de 3 a 5 iteraciones; si la API carece de endpoint batch o experimenta latencia, el agente debe detenerse y reportar.
- **Higiene de Temporales:** Archivos auxiliares como `.commit_msg`, `.pr_body`, `.comment_body` o `.issue_body` deben removerse inmediatamente tras su uso y estar contemplados en `.gitignore`.
