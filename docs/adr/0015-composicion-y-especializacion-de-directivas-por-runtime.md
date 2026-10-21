---
status: accepted
date: 2026-10-16
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0015 - Composición y Especialización de Directivas Base por Runtime

## Contexto y Planteamiento del Problema

Históricamente, los estándares de confinamiento de workspace, el uso exclusivo de APIs nativas de archivos, la restricción de comandos de consola y las políticas de ejecución con privilegios elevados se encontraban consolidados en un único archivo: `runtimes/antigravity/rules/01-sandbox.md`.

Aunque la política de aislamiento territorial y el uso de herramientas nativas de manipulación de código constituyen principios universales e invariantes para cualquier agente de software autónomo, la implementación concreta contenía acoplamientos técnicos exclusivos del entorno Antigravity:
1. El parámetro `BypassSandbox: true` y sus reglas de aplicación.
2. Las particularidades del sandbox en Linux (namespaces/bwrap que montan `.git/` en modo solo lectura).
3. Las limitaciones del evaluador de permisos de Antigravity (pérdida de prefix-matching ante comillas y necesidad de commits vía `.commit_msg`).
4. Reglas anti-sugerencias específicas de la interfaz de chat del IDE.

Con la evolución hacia un ecosistema multi-runtime (donde futuros adaptadores para otros entornos como Claude Code, Codex, Cursor o agentes headless deban ser soportados), mantener estos estándares acoplados en una única regla de runtime obligaría a clonar principios universales o a inyectar directivas inaplicables en el System Prompt de otros modelos.

Se requiere establecer un patrón arquitectónico formal que permita definir configuraciones/directivas base en `core/` y especializarlas, adaptarlas o sobrescritas por configuraciones específicas dentro de cada runtime, similar al ciclo de vida en que los ADRs extienden o sustituyen decisiones previas.

## Impulsores de la Decisión (Decision Drivers)

* **Separación de Responsabilidades y Pureza de Capas:** Diferenciar nítidamente entre leyes universales de ingeniería de software para agentes (invariantes en `core/`) y adaptadores técnicos específicos de cada entorno (en `runtimes/<runtime>/`).
* **Cero Duplicación de Texto (DRY):** Evitar que futuros runtimes requieran duplicar normas universales (I/O nativo, higiene, confinamiento), previniendo la deriva de configuración (*configuration drift*).
* **Preservación del Presupuesto de Contexto Basal:** Mantener el System Prompt compilado estrictamente por debajo del umbral de 4.000 palabras fijado en [ADR-0008](0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md).
* **Flexibilidad y Capacidad de Sobrescritura (Superseding):** Habilitar que un runtime pueda no solo especializar (extender) una directiva base, sino también anularla o sustituirla formalmente si su paradigma técnico entra en conflicto directo.
* **Determinismo e Idempotencia en el Pipeline:** El mecanismo de ensamblado en `build.sh` y la validación en `./build.sh check` deben operar de manera predecible, validada por esquemas formales y sin dependencias externas pesadas.

## Opciones Consideradas

* **Opción 1: Sobrescritura Declarativa Completa (File Shadowing / Superseding Total).** Cada directiva base tiene un identificador. Si un runtime define un archivo con el mismo identificador o lo declara en su configuración, la regla base se descarta por completo y se utiliza la del runtime (análogo a un reemplazo completo de ADR).
* **Opción 2: Plantillas con Slots / Preprocesador AST (Template Injection).** La directiva base contiene marcadores o comentarios delimitadores (`<!-- SLOT: runtime_sandbox -->`) donde el compilador inyecta fragmentos provistos por cada runtime.
* **Opción 3: Composición Estratificada Híbrida (Layered Composition + Declarative Superseding).** Capa base universal en `core/` combinada con adaptadores especializados en `rules/`, complementada con capacidades declarativas en `config.json` para omitir (`disabled_core_rules`) o mapear sustituciones (`overrides`) cuando un runtime lo requiera formalmente.

## Decisión Adoptada

Opción elegida: **Opción 3 ("Composición Estratificada Híbrida")**, estructurada en los siguientes pilares:

### 1. Desacoplamiento de Estándares de Entorno (`core/10-environment-standards.md`)
Se extraen de `01-sandbox.md` los principios universales de confinamiento y se trasladan a `core/10-environment-standards.md`:
* **Uso Exclusivo de Herramientas Nativas de Archivos:** Creación con `write_to_file`, edición atómica con `replace_file_content`, inspección con `view_file` y búsqueda con `grep_search`. Prohibición estricta de subshells de mutación (`cat`, `sed`, `awk`, scripts temporales `patch_*.py`).
* **Restricción de Comandos de Consola:** Terminal reservada para runtime, compilación y tests. Invocaciones atómicas y deterministas.
* **Límites Territoriales de Workspace:** Prohibición absoluta de mutar o inspeccionar rutas externas al workspace activo.
* **Higiene de Temporales:** Eliminación inmediata de archivos de intercambio (`.commit_msg`, `.pr_body`, etc.).
* **Gobernanza de Permisos y Degradación:** Confinamiento estándar por defecto; si el runtime impone restricciones de bajo nivel, las adaptaciones y escalaciones se rigen por la directiva de especialización del runtime anfitrión.

### 2. Adaptador de Especialización de Runtime (`runtimes/antigravity/rules/01-sandbox.md`)
El archivo en `rules/` se redefine exclusivamente como el adaptador de runtime para Antigravity (`# Especialización de Sandbox y Ejecución (Runtime: Antigravity)`):
* **Bypass de Sandbox en Git:** Exclusividad de `BypassSandbox: true` para mutadores locales (debido al montaje de solo lectura de `.git/` en Linux namespaces) y comandos remotos/red (`git push`, `gh`).
* **Prefix-Matching y Commits Atómicos:** Prohibición de `git commit -m "..."` por limitaciones del evaluador de permisos; obligación de utilizar `.commit_msg` con `git commit -F .commit_msg`.
* **Aprovisionamiento Hermético:** Ejecución confinada de `./build.sh build` y `./build.sh check`, dejando `./build.sh link` y `./build.sh all` como responsabilidad exclusiva del anfitrión.
* **Blindaje Anti-Sugerencias:** Instrucción imperativa de ignorar sugerencias automáticas del IDE para habilitar bypass en comandos locales comunes.

### 3. Mecanismo de Resolución y Compilación en `build.sh`
El compilador resuelve las directivas aplicando el siguiente algoritmo determinista:
1. **Lectura del Manifiesto de Runtime (`config.json`):**
   - Extrae `disabled_core_rules` (lista de nombres base en `core/` a ignorar).
   - Extrae `overrides` (diccionario de `{ "directiva_core": "directiva_runtime" }`).
2. **Filtrado de `core/`:**
   - Para cada archivo en `core/*.md`, si su nombre coincide con alguna entrada en `disabled_core_rules` o con alguna clave de `overrides`, se omite de la compilación de `core`.
3. **Ensamblado Secuencial:**
   - Se concatenan las directivas activas de `core/`.
   - Se concatenan las directivas especializadas de `runtimes/<runtime>/rules/*.md`.
   - Debido a que la atención secuencial del modelo evalúa primero el contexto universal y luego la especialización contextual, las reglas de runtime refinan legítimamente las normas base sin contradecirlas.

### 4. Contrato de Datos Formal (`runtime-config.schema.json`)
Se actualiza el esquema formal JSON Schema para soportar los campos de gobernanza:
* `disabled_core_rules`: Array opcional de nombres de archivos Markdown en `core/`.
* `overrides`: Objeto opcional de pares clave-valor que mapea directivas de `core/` a sus reemplazos en `rules/`.

### 5. Auditoría Estática en `./build.sh check`
El subcomando `check` valida:
* Que toda regla declarada en `disabled_core_rules` u `overrides` exista físicamente en `core/`.
* Que toda regla sustituta declarada en `overrides` exista físicamente en `rules/`.
* Que no existan colisiones accidentales de títulos H1, permitiéndolas únicamente si corresponden a un override declarado explícitamente.

## Consecuencias

### Positivas
* **Desacoplamiento Limpio:** `core/` se convierte en un conjunto 100% universal de directivas para cualquier agente; `runtimes/` aloja únicamente los adaptadores de su tecnología específica.
* **Cero Inflación de Contexto Basal:** La separación de `01-sandbox.md` (726 palabras) en Base (~300 palabras) + Adaptador (~420 palabras) arroja un saldo neto de ~720 palabras. La ocupación de `dist/antigravity/AGENTS.md` se mantiene estable en ~3.050 palabras (~76% del presupuesto de 4.000 palabras).
* **Extensibilidad Multi-Runtime:** Incorporar un nuevo runtime (e.g. `claude-code`) solo requiere definir su `config.json` y su adaptador específico de permisos/sandbox en `rules/`, reutilizando íntegramente las directivas de `core/`.
* **Gobernanza Declarativa:** Si un futuro runtime prescinde de alguna regla base (ej. flujo de git o disciplina web), puede anularla de forma explícita y auditable en su configuración sin parches manuales.

### Negativas / Trade-offs
* **Fragmentación Documental:** Quien audite las reglas debe comprender que la política de ejecución se compone de la directiva universal (`core/10-environment-standards.md`) más la especialización del runtime (`runtimes/antigravity/rules/01-sandbox.md`). Esto se mitiga con referencias cruzadas explícitas en los encabezados.

## Pros y Contras de las Opciones

#### Opción 1: Sobrescritura Declarativa Completa (File Shadowing)
* **Pro:** Aislamiento absoluto por archivo.
* **Contra:** Duplicación masiva de texto universal en cada runtime que requiera ajustar un parámetro menor. Riesgo severo de desincronización y deuda técnica.

#### Opción 2: Plantillas con Slots (Template Injection)
* **Pro:** Inyección quirúrgica sin dividir archivos.
* **Contra:** Destruye la legibilidad del Markdown crudo. Agrega dependencia de motores de templating o regex complejas en `build.sh`.

#### Opción 3: Composición Estratificada Híbrida (Elegida)
* **Pro:** Mantiene Markdown estándar puro, máxima reutilización DRY, presupuesto de contexto inalterado y soporte formal para reemplazos de archivo completo cuando sea estrictamente necesario.
* **Contra:** Requiere enriquecer la lógica de filtrado de `build.sh` y mantener sincronizado el esquema de validación.
