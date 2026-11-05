---
status: accepted
date: 2026-10-28
decision-makers: [Usuario, Antigravity]
supersedes: ["0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md", "0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md"]
superseded-by: ["0047-resolucion-desacople-progressive-disclosure-y-compilacion-autosuficiente.md"]
---

# 0038 - Arquitectura de Progressive Disclosure en AGENTS.md y Modularización de Reglas

## Contexto y Planteamiento del Problema

El compilador `build.sh` concatenaba históricamente todos los módulos de `core/*.md` y las reglas especializadas de cada runtime (`runtimes/*/rules/*.md`) en un único artefacto monolítico (`AGENTS.md`). Este archivo superaba las 1.960 palabras (~2.600 a 3.000 tokens estimados).

Dado que el runtime de Antigravity inyecta este contenido de forma estática en el bloque `<user_rules>` en **cada turno de inferencia**, el costo acumulado en sesiones multi-turno (15 a 25 pasos) a lo largo de múltiples proyectos concurrentes provocaba:
1. Saturación prematura del presupuesto de tokens por turno.
2. Degradación de la capacidad atencional del modelo (*context rot* y *lost in the middle*).
3. Inyección innecesaria de guías procedimentales y flujos operativos detallados (como fases exhaustivas de PR, interacción con tableros o sintaxis de herramientas secundarias) que solo se requieren bajo demanda ante tareas específicas.

Intentar resolver este sobrecosto mediante poda o acortamiento textual de los archivos en `core/` introduce riesgos inaceptables de regresión normativa, pérdida de precisión prescriptiva y ambigüedad. Se requiere una arquitectura de **Progressive Disclosure pura** que mantenga la separación modular ya implementada en `core/` sin alterar el contenido de las directivas operativas.

## Impulsores de la Decisión (Decision Drivers)

* **Presupuesto Basal Ultracompacto:** Reducir el contenido inyectado en `AGENTS.md` a $\le 800$ palabras (reducción $> 55\%$).
* **Arquitectura de Divulgación Progresiva (Progressive Disclosure):** Aprovechar las tres capas de ejecución:
  - *Capa 1 (Basal / Turno 0):* Inyectada en `AGENTS.md`, con invariantes irreductibles y el router de directivas.
  - *Capa 2 (Modular / Bajo Demanda):* Archivos en `core/*.md` y `skills/*/SKILL.md`, consultados mediante `view_file` al activarse su disparador.
  - *Capa 3 (Ejecución):* Referencias profundas en `skills/*/references/*.md`, binarios y scripts.
* **Integridad Absoluta de Directivas:** Preservar al 100% el texto canónico de los módulos de ingeniería, git, backlog, PRs y entorno en `core/`, sin recortes ni mutilaciones.
* **Trazabilidad Semántica Link-Driven:** Sintaxis determinista de disparadores en el router (`If [context], read [core/XX-....md](core/XX-....md) first.`).
* **Soporte Multi-Workspace:** Garantizar que el directorio modular `core/` sea accesible tanto en el repositorio anfitrión como en workspaces secundarios enlazados.
* **Validación Automatizada e Idempotente:** `./build.sh check` y la suite de tests unitarios verifican la cuota basal ($\le 800$ palabras), la cuota modular ($\le 300$ palabras), la integridad de enlaces relativos y la indexación exhaustiva de módulos.

## Opciones Consideradas

* **Opción 1: Índice Link-Driven Puro sin Invariantes.** Reducir `AGENTS.md` a enlaces sin texto normativo.  
  *Descarte:* Degrada la gobernanza de seguridad basal; el modelo puede cometer infracciones de sandbox o complacencia en el Turno 0 antes de consultar enlaces.
* **Opción 2: Poda Textual de Módulos (Compresión).** Abreviar párrafos dentro de `core/*.md` para que la concatenación quepa bajo 800 palabras.  
  *Descarte:* Antipatrón destructivo; incrementa el riesgo de ambigüedad y despoja a las reglas de sus precisiones técnicas esenciales.
* **Opción 3: Arquitectura de Progressive Disclosure con Enrutador Basal y Preservación Íntegra de `core/`.**  
  Mantener los 10 módulos de `core/` en su estado canónico completo e implementar `core/00-router.md` junto con `core/01-objectivity.md` como la Capa Basal compilada en `AGENTS.md`. `build.sh` compila exclusivamente la base normativa y enlaza hacia `core/` bajo demanda.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes pilares:

### 1. Desacoplamiento Basal vs Modular en `core/`
- **Capa Basal (Turno 0 en `AGENTS.md`):**
  - `core/00-router.md`: Define los invariantes universales de confinamiento estricto a workspace, uso exclusivo de APIs nativas de I/O, e inmutabilidad de `main`, junto con el router condicional hacia todos los módulos.
  - `core/01-objectivity.md`: Invariantes permanentes de feedback crítico y objetividad técnica (cero complacencia, cuestionar y proponer, cero adulación o disculpas).
  - Reglas de runtime (`runtimes/*/rules/*.md`): Especializaciones duras (ej. bypass de sandbox obligatorio en mutadores `git` y `gh` para Antigravity).
- **Capa Modular (Bajo Demanda en `core/`):**
  - `core/02-git-lifecycle.md` a `core/10-environment-standards.md` permanecen íntegros en disco sin ninguna alteración textual.

### 2. Disparadores Condicionales Deterministas
El router `core/00-router.md` indexa cada módulo modular con la sintaxis estándar:
`If [condición / tarea], read [core/XX-....md](core/XX-....md) first.`
Los agentes leen el archivo correspondiente con `view_file` al iniciar una tarea que active la condición.

### 3. Pipeline de Compilación y Enlace en `build.sh`
- `compile_runtime_build()`: Compila exclusivamente `CORE_BASAL_RULES=("00-router.md" "01-objectivity.md")` y las reglas del runtime en `dist/<runtime>/AGENTS.md`.
- `link_runtime()`: Crea symlink `${target_dir}/core -> ${CORE_DIR}` para asegurar la resolución de enlaces relativos en cualquier workspace del sistema anfitrión.
- `check_core_rules()`: Verifica que ningún módulo supere `MAX_MODULE_WORDS=300`, que todos los enlaces relativos resuelvan, y que todo módulo `02`..`10` esté indexado en `00-router.md`.

### 4. Presupuesto de Contexto y Telemetría
- `MAX_CONTEXT_WORDS=800` en `build.sh`.
- Resultado compilado real: ~709 palabras en Antigravity (88% del presupuesto) y ~410 palabras en Claude (51% del presupuesto).

## Consecuencias

### Positivas
* **Ahorro Masivo de Tokens:** Reducción de ~1.966 a 709 palabras en Antigravity (~1.500 tokens ahorrados por turno), mitigando aceleradamente el *context rot*.
* **Preservación Normativa al 100%:** Las directivas de ingeniería, backlog, workflow de issues y estándares de entorno conservan todo su rigor prescriptivo original.
* **Integridad Referencial Garantizada:** La auditoría estática (`build.sh check`) y la suite unitaria aseguran que no existan módulos huérfanos ni enlaces rotos.
* **Compatibilidad Multi-Workspace:** Symlink automático de `core/` en el anfitrión asegura funcionamiento transparente entre múltiples repositorios.

### Negativas / Trade-offs
* Tareas operativas especializadas requieren un turno de lectura (`view_file [core/XX-....md]`) previo a la ejecución si el agente no tiene la directiva en contexto. Esto se mitiga con la inyección basal de los invariantes críticos que impiden violaciones de seguridad o sandbox.
