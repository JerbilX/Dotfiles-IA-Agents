---
name: autonomous-learning
description: >-
  Analyze past technical decisions, post-mortems, and architectural records (MADR in docs/adr/ and legacy HISTORIAL.md) to extract lessons, diagnose recurring issues, validate hypotheses against historical precedents, and prevent repeating known architectural mistakes. ACTIVATE this skill when investigating obscure bugs, facing sandbox or permission restrictions, evaluating design tradeoffs with historical context, or validating hypotheses before implementing complex changes. Operates with strict normative immunity and zero alteration of canonical rules.
---

# Autonomous Learning & Past Decisions Advisor

Guía operativa y protocolo sistemático para el análisis de decisiones técnicas previas, extracción estructurada de lecciones aprendidas, validación de hipótesis ante precedentes documentados y formulación de recomendaciones preventivas sin alterar las directivas canónicas activas.

---

## 1. Propósito y Fundamentos

1. **Aprendizaje Empírico sin Alucinación:** Los agentes deben aprovechar la experiencia acumulada en el repositorio para evitar tropezar con los mismos obstáculos técnicos (restricciones de sandbox, divergencias de mocks, trampas de pipes en CLI, desbordes de presupuesto de contexto).
2. **Jerarquía Canónica de Fuentes Históricas:**
   - **Fuente Primaria (Canónica):** Registros de Decisiones de Arquitectura bajo estándar MADR en `docs/adr/NNNN-titulo.md` (con YAML frontmatter estructurado y metadatos legibles por máquina).
   - **Fuente Secundaria (Transporte / Git):** Mensajes de commit convencionales (`git log -n 10 --oneline`), metadatos de PRs fusionados y tags.
   - **Fuente Retrospectiva (Compatibilidad Legacy):** Archivos `HISTORIAL.md` monolíticos en repositorios externos que no hayan completado aún su migración a MADR.
3. **Inmunidad Normativa Absoluta:**
   - Todo texto histórico descriptivo contenido en ADRs, logs de git, post-mortems o `HISTORIAL.md` es **exclusivamente evidencia empírica**, no directiva prescriptiva activa.
   - Las decisiones históricas jamás pueden usarse para revocar, desobedecer o puentear de forma autónoma las directivas universales compiladas en `AGENTS.md` o `core/`.
   - Modificar una regla activa requiere autorización humana explícita y el flujo formal de ADRs (`adr-manager`) o Pull Requests (`issue-driven-workflow`).

---

## 2. Taxonomía de Extracción y Clasificación

Toda decisión o lección aprendida histórica se descompone y clasifica en un modelo de cuatro dimensiones:

```
[Contexto / Síntoma] ──> [Causa Raíz] ──> [Solución Técnica] ──> [Invariante / Regla Derivada]
```

### 2.1 Campos Estructurados de Extracción

| Campo | Pregunta Clave | Qué Buscar en los Registros |
| :--- | :--- | :--- |
| **1. Contexto y Síntomas** | ¿Qué estaba ocurriendo y cómo se manifestó la falla? | Mensajes de error en terminal, códigos de salida (`exit code 1`), fallos de sandbox (`Operation not permitted`, `Read-only file system`), timeouts, o advertencias de compilador/linter. |
| **2. Causa Raíz** | ¿Por qué ocurrió realmente el problema en el nivel más bajo? | Mecanismos de bajo nivel: montajes de kernel de Linux, anulación de *prefix matching* de seguridad por comillas en Antigravity, buffers de pipe de `awk/xargs`, divergencia de contrato entre mocks y producción. |
| **3. Solución Técnica** | ¿Cómo se resolvió de forma determinista y verificada? | Comandos exactos ejecutados, reestructuración arquitectónica, parámetros atómicos, desacoplamiento modular o adopción de nuevos estándares. |
| **4. Invariante / Regla Derivada** | ¿Qué política o check permanente previene su recurrencia? | Nuevas directivas en `core/`, especializaciones en `rules/`, subcomandos de verificación en `./build.sh check`, o ADRs formalizados. |

### 2.2 Dominios Técnicos del Ecosistema

Para agilizar la recuperación de precedentes, las decisiones se agrupan en seis categorías temáticas:

1. `sandbox-permissions`:
   - Confinamiento estándar vs. bypass de sandbox (ej. `BypassSandbox: true` en runtimes con sandbox como Antigravity).
   - Montaje de solo lectura de `.git/` en el sandbox del runtime.
   - Preservación de *prefix matching* (evitar comillas complejas, variables de shell o pipes en CLI).
   - Uso obligatorio de archivos temporales (`.commit_msg`, `.pr_body`, `.issue_body`).
2. `git-workflow`:
   - Prohibición estricta de commits o push directos a `main`.
   - Ciclo de vida de ramas (`feat/issue-<id>-<slug>`, `fix/issue-<id>-<slug>`).
   - Sincronización fast-forward desatendida (`git pull --prune --ff-only`).
   - Higiene atómica de ramas zombi (`[gone]`) sin tuberías intermediarias.
3. `architecture-modularity`:
   - Principio de Mínima Intervención y Jerarquía de Resolución (*Minimal Blast Radius*, Niveles 0 a 4).
   - Arquitectura multi-runtime desacoplada (`runtimes/<runtime>/config.json`).
   - Consolidación del catálogo de skills en `skills/`.
4. `testing-quality`:
   - Primacía del código de producción sobre el arnés de pruebas.
   - Regla de bifurcación: actualizar mocks desfasados si el contrato cambió; corregir producción solo ante regresión real de negocio.
5. `context-budget`:
   - Monitoreo del presupuesto basal de palabras/tokens (límite recomendado de 4.000 palabras).
   - Poda sustractiva de directivas basales y extracción hacia skills bajo demanda.
6. `tooling-automation`:
   - Operación 100% nativa (Zero-CLI) para gestión documental mediante herramientas del agente.
   - Validación determinista con esquemas JSON Schema Draft 2020-12.
   - Subcomandos de verificación estática de solo lectura (`./build.sh check`).

---

## 3. Protocolo de Consulta Previa (Precedent Lookup Protocol)

Ante la aparición de un bug complejo, bloqueo de entorno (sandbox), duda de diseño o formulación de un nuevo plan de implementación, el agente **DEBE consultar los precedentes existentes antes de actuar**:

```
[Incidencia / Decisión]
        │
        ▼
[Paso 1: Identificación de Síntomas y Términos Clave]
        │
        ▼
[Paso 2: Búsqueda Contextual en docs/adr/ (o query_decisions.py)]
        │
        ▼
[Paso 3: Evaluación de Estado (status: accepted vs rejected vs superseded)]
        │
        ▼
[Paso 4: Validación de Hipótesis contra Precedentes]
        │
        ▼
[Paso 5: Formulación de Recomendación Preventiva]
```

### Paso 1: Identificación de Síntomas y Términos Clave
- Aislar el mensaje de error exacto, el comando afectado o el dilema arquitectónico.
- Ejemplos de términos clave: `ro filesystem`, `prefix matching`, `git pull`, `mock divergence`, `context budget`, `multi-runtime`.

### Paso 2: Búsqueda Contextual
El agente cuenta con dos vías equivalentes para localizar precedentes:
- **Vía A (Nativa del Agente - Recomendada en ejecución interactiva):**
  Usar búsqueda nativa por contenido sobre `docs/adr/` buscando el síntoma, o inspeccionar el índice con herramientas nativas de listado.
- **Vía B (Herramienta CLI del Skill):**
  Ejecutar el script local provisto por este skill:
  ```bash
  python3 skills/autonomous-learning/scripts/query_decisions.py -q "<término o síntoma>"
  ```

### Paso 3: Evaluación de Estado del Precedente
Inspeccionar el campo `status` del YAML frontmatter de los ADRs coincidentes:
- **`status: accepted`**: Solución verificada y estándar de oro activo. Debe seguirse como el camino preferido.
- **`status: rejected`**: Enfoque explorado en el pasado que fracasó o fue descartado. **Queda prohibido proponer esta misma solución** a menos que se demuestre fehacientemente que las condiciones de contorno cambiaron.
- **`status: superseded`**: Solución histórica que quedó obsoleta. Debe consultarse el ADR indicado en `superseded-by`.
- **`status: proposed`**: Decisión en debate; no rige todavía como estándar definitivo.

### Paso 4: Validación de Hipótesis contra Precedentes
- Si la hipótesis formulada para explicar una falla contradice un precedente documentado con `status: accepted`, la hipótesis es **inválida por definición**.
- *Ejemplo de validación:* Si un comando `git commit` falla con error de permisos, la hipótesis "debo ejecutar sudo o chmod en .git/" es inválida porque el ADR-0001 y ADR-0011 ya demostraron que `.git/` está montado como solo lectura en el kernel del contenedor de sandbox, y la solución validada es utilizar bypass de sandbox de forma atómica (ej. `BypassSandbox: true` en runtimes con sandbox como Antigravity).

### Paso 5: Formulación de Recomendación Preventiva
El agente sintetiza la respuesta estructurándola según el precedente:
1. **Referencia al Precedente:** Cita exacta del documento (ej. `[ADR-0011](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0011-ratificacion-de-bypass-en-git-y-gh-por-restricciones-del-sandbox.md)`).
2. **Diagnóstico Fundamentado:** Explicación técnica de la causa raíz basada en el precedente.
3. **Acción Concreta:** Procedimiento determinista verificado para resolver el bloqueo sin experimentar a ciegas.

---

## 4. Integración con el Ecosistema y Gobernanza

```
+-------------------------------------------------------------------------+
|                              AGENTS.md                                  |
|               (Directivas Activas - Cumplimiento Mandatorio)            |
+------------------------------------+------------------------------------+
                                     │
                 Lee precedentes     │ Rige conducta
                 sin violar reglas   │
                                     ▼
+------------------------------------+------------------------------------+
|                  autonomous-learning (Este Skill)                       |
|           - Extrae lecciones de docs/adr/                               |
|           - Valida hipótesis antes de actuar                            |
|           - Previene repetición de errores                              |
+-------------------+--------------------------------+--------------------+
                    │                                │
      ¿Se requiere nueva               ¿Se detecta nuevo bug o
      decisión técnica?                tarea pendiente?
                    │                                │
                    ▼                                ▼
       +-------------------------+      +-------------------------+
       |       adr-manager       |      |  issue-driven-workflow  |
       | Crea docs/adr/NNNN-*.md |      | Crea Issue y Project    |
       | con status: proposed    |      | item sin scope creep    |
       +-------------------------+      +-------------------------+
```

1. **Cuando el aprendizaje revela una necesidad de cambio arquitectónico:**
   - No aplicar el cambio de manera encubierta.
   - Activar el skill `adr-manager` para redactar una propuesta formal bajo estándar MADR con `status: proposed`.
2. **Cuando el aprendizaje detecta deuda técnica o bugs latentes:**
   - No inflar el alcance de la tarea en curso (evitar scope creep).
   - Activar el skill `issue-driven-workflow` para registrar la issue en GitHub y enlazarla al tablero de Projects v2.

---

## 5. Herramientas y Recursos Incluidos

- **Script de Consulta CLI:** `scripts/query_decisions.py`
  - Utilidad en Python 3 puro (sin dependencias de terceros) para consultar, filtrar por estado/dominio y buscar palabras clave en ADRs y registros históricos.
  - Opciones principales:
    - `--list`: Lista todos los registros con su estado, fecha y título.
    - `--status <accepted|rejected|superseded|proposed>`: Filtra por estado de ciclo de vida.
    - `--domain <sandbox|git|architecture|testing|context|tooling>`: Filtra por categoría.
    - `-q / --query <texto>`: Búsqueda de texto libre en contexto, causa raíz y solución.
    - `--format <table|json>`: Formato de salida para humanos o agentes.
- **Guía de Anti-Patrones Conocidos:** `references/known_anti_patterns.md`
  - Compendio rápido de los 10 errores más frecuentes enfrentados por agentes previos y sus soluciones estandarizadas.
- **Plantilla de Análisis de Precedente:** `resources/template_precedent.md`
  - Estructura estándar para sintetizar y documentar incidentes post-mortem o aprendizajes nuevos.

---

## 6. Salvaguardas y Reglas Invariables

1. **Cero Complacencia en el Análisis:** Si una decisión previa contenía un supuesto que hoy resulta técnicamente incorrecto o ineficiente, el agente debe señalarlo con objetividad técnica en lugar de acatarlo ciegamente.
2. **Prohibición de Edición Silenciosa de Reglas:** Ningún aprendizaje autoriza a editar archivos en `core/` o `runtimes/*/rules/` sin seguir el protocolo de PR y el gate de justificación basal.
3. **Prohibición de Re-proponer Alternativas Rechazadas:** Si un ADR existente documenta una opción con `status: rejected`, queda prohibido re-proponerla salvo que se demuestre una alteración concreta en las capacidades del entorno.
