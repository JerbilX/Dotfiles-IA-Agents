---
status: proposed
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0023 - Blindaje de Herramientas Nativas y Confinamiento de Workspace

## Contexto y Planteamiento del Problema

Durante el ciclo de desarrollo en la conversación `ace3c35b-60d4-4be2-a089-92512bf2aafe` sobre el repositorio `JerbilX/Agent-Cockpit` (Issue #1), el agente recibió la directiva ejecutiva `"avanza"` para iniciar el diseño de un entorno web local de orquestación multi-repo. Ante el requerimiento de diseñar un selector de repositorios de la organización, el agente intentó de forma no solicitada inspeccionar el directorio superior del host invocando la herramienta nativa:

```json
{
  "name": "list_dir",
  "args": {
    "DirectoryPath": "/home/jerbilx/Proyectos-IA-V3"
  }
}
```

Dado que el workspace activo estaba estrictamente delimitado a `/home/jerbilx/Proyectos-IA-V3/Agent-Cockpit`, el arnés del runtime Antigravity interceptó la operación como un acceso fuera de los límites de workspace, disparando un diálogo modal interactivo de confirmación de permisos en el IDE que interrumpió la ejecución autónoma por casi dos minutos hasta ser rechazado por el usuario.

El análisis retrospectivo evidenció las siguientes fallas:
1. **Asimetría en la concepción del Sandbox:** Las directivas preexistentes (ADR-0001, `01-sandbox.md`) estaban fuertemente focalizadas en el confinamiento de `run_command` y en restringir el flag `BypassSandbox: true` a Git/GH, pero no advertían que las herramientas nativas de archivos (`list_dir`, `view_file`, `find_by_name`, `grep_search`) están sujetas a la misma frontera de confinamiento en el IDE y provocan alertas interactivas si intentan resolver rutas ascendentes (`../`) o externas.
2. **Reconocimiento físico innecesario:** En fases tempranas de diseño y arquitectura (RFCs/ADRs), el agente incurrió en el antipatrón de sondear el disco local en lugar de mantener el diseño desacoplado y parametrizado mediante variables de entorno (ej. `WORKSPACE_ROOT`).
3. **Falta de protocolo de descubrimiento multi-repo:** No existía una directiva canónica que especificara que el inventario de proyectos de la organización debe consultarse de forma centralizada vía GitHub CLI (`gh repo list`).

## Impulsores de la Decisión (Decision Drivers)

* **Aislamiento Estricto e Inviolabilidad de Workspace:** Garantizar que ninguna operación (sea por terminal o por herramientas nativas de archivo) traspase los límites del workspace activo sin autorización humana expresa.
* **Autonomía y Cero Fricción en IDE:** Prevenir la aparición de modales interactivos de confirmación de permisos en Antigravity causados por lecturas exploratorias indebidas.
* **Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius - ADR-0017):** Abordar el problema de forma integral en sus capas correspondientes (Core Basal, Runtime Antigravity y Skill procedimental).
* **Determinismo en Operaciones Multi-Repo:** Estandarizar la API de GitHub CLI (`gh repo list`) como la única fuente canónica para inventario de repositorios.

## Opciones Consideradas

* **Opción 1: Confiar exclusivamente en el mecanismo reactivo del runtime.**
  * Permitir que el agente intente accesos fuera de workspace y que el runtime de Antigravity intercepte y consulte al usuario.
  * *Descarte:* Degrada gravemente la experiencia de usuario, rompe el flujo autónomo de trabajo e ignora el principio de confinamiento preventivo.
* **Opción 2: Documentar la prohibición únicamente en notas o guías de skill (Nivel 2).**
  * Incluir la advertencia solo en `issue-driven-workflow`.
  * *Descarte:* Insuficiente. El confinamiento de workspace es un invariante de seguridad que aplica a cualquier tarea, no solo al flujo de issues. Dejarlo fuera del Core permite que agentes en otros contextos reincidan en la misma conducta.
* **Opción 3: Blindaje Multinivel Integral (Core Basal + Runtime + Skill + ADR).**
  * **Nivel 4 (Core Basal - `core/10-environment-standards.md`):** Establecer el invariante universal de prohibición de rutas ascendentes (`..`) o externas en herramientas nativas, prohibir el escaneo físico para multi-repo y exigir diseño desacoplado.
  * **Nivel 3 (Runtime Antigravity - `runtimes/antigravity/rules/01-sandbox.md`):** Tipificar explícitamente que invocar herramientas nativas fuera de workspace en Antigravity dispara diálogos modales de permisos y constituye una violación de confinamiento.
  * **Nivel 2 (Skill - `skills/issue-driven-workflow/SKILL.md`):** Incorporar la sección procedimental 2.4 instruyendo el uso exclusivo de `gh repo list` para tareas multi-repo.

### Justificación de Elevación Basal

La intervención en `core/10-environment-standards.md` (Nivel 4) es estrictamente necesaria porque los límites de workspace son un invariante universal del arnés del agente. No existen flags de CLI (Nivel 0) ni scripts de compilación (Nivel 1) capaces de interceptar las llamadas a herramientas nativas generadas internamente por el LLM; por ende, la directiva debe gobernar basalmente el comportamiento del agente en todos los runtimes y proyectos.

## Decisión Adoptada

Opción elegida: **"Opción 3"**, articulada de la siguiente forma:

1. **Invariante Universal en Core Basal (`core/10-environment-standards.md`):**
   * Se prohíbe el uso de rutas relativas ascendentes (`..`) o absolutas fuera del workspace activo en `list_dir`, `view_file`, `find_by_name`, `grep_search`, `write_to_file` y `replace_file_content`.
   * Se prohíbe el escaneo físico de carpetas del host para descubrimiento multi-repo; se delega exclusivamente en `gh repo list <org/owner>`.
   * Se exige que los diseños de arquitectura con integración multi-repo se formulen de forma agnóstica mediante variables de entorno o configuración.

2. **Especialización para Runtime Antigravity (`runtimes/antigravity/rules/01-sandbox.md`):**
   * Se documenta la restricción del IDE respecto a modales interactivos de elevación de privilegios generados por herramientas nativas.
   * Se tipifica que la raíz reportada en `<user_information>` es la frontera dura de ejecución.

3. **Estandarización Procedimental (`skills/issue-driven-workflow/SKILL.md`):**
   * Se formaliza la sección `2.4 Descubrimiento y Consulta Multi-Repo (API Exclusiva)` con el comando determinista:
     ```bash
     gh repo list JerbilX --limit 30 --json name,description,isPrivate
     ```
     ejecutado con `BypassSandbox: true`.

### Consecuencias

* **Positivas:**
  * Se elimina el vector de escape de workspace mediante herramientas nativas de lectura o escritura.
  * Se erradican las interrupciones por modales de confirmación de permisos en el IDE de Antigravity al trabajar en repositorios desacoplados.
  * Se unifica y optimiza el descubrimiento de repositorios de la organización a través de la API estructurada de GitHub.
* **Negativas / Trade-offs:**
  * Cualquier consulta que requiera inventariar proyectos de la organización debe consumir cuota de red de GitHub CLI en lugar de inspecciones instantáneas locales en disco.
