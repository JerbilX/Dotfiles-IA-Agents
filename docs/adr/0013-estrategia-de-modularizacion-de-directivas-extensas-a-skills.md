---
status: proposed
date: 2026-10-16
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0013 - Estrategia de Modularización de Directivas Extensas hacia Skills Bajo Demanda

## Contexto y Planteamiento del Problema

A medida que el archivo compilado `dist/antigravity/AGENTS.md` incorpora directivas normativas en `core/` y reglas de runtime en `rules/`, el tamaño del System Prompt basal alcanzó 3.434 palabras (~4.579 tokens estimados, 85% del límite recomendado de 4.000 palabras fijado en [ADR-0008](0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md)).

Saturar la ventana basal con directivas altamente procedimentales (como el protocolo E2E de desarrollo guiado por issues, con 640 palabras) degrada la capacidad atencional del modelo (*lost in the middle*) y reduce el presupuesto de contexto útil disponible para análisis de código, ejecución de herramientas y razonamiento.

Por otra parte, la dispersión inicial de los skills en un repositorio hermano externo (`AGY-Skills`) introducía problemas de gobernanza: pérdida de atomicidad en Pull Requests, deuda de nomenclatura acoplada a una herramienta específica, y restricciones de aislamiento del workspace que impedían a los agentes mantener sus propios skills sin violar políticas de sandbox.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación del Presupuesto de Contexto Basal:** Mantener el System Prompt basal dentro de un margen seguro (<75% del umbral de 4.000 palabras) para maximizar la ventana útil de trabajo.
* **Criterios Objetivos de Desacoplamiento:** Establecer reglas cuantitativas y cualitativas precisas para identificar qué directivas deben permanecer en el núcleo basal y cuáles deben extraerse a skills bajo demanda.
* **Preservación de Invariantes Normativos (Gobernanza):** Garantizar que las prohibiciones críticas (push/merge a `main`, gate de revisión humana) sigan activas e inquebrantables en el System Prompt basal mediante directivas de enlace (*Trigger Directives*).
* **Consolidación y Atomicidad del Ecosistema:** Habilitar la coexistencia y versionado unificado de directivas y skills dentro del repositorio de Dotfiles (`skills/`), eliminando la fricción de sincronización multi-repositorio.

## Opciones Consideradas

* **Opción 1: Compresión agresiva o truncamiento de directivas en `core/`.** Resumir las directivas procedimentales omitiendo detalles de comandos y pasos. (Descartada por diluir la fuerza normativa y generar ambigüedad en la ejecución de tareas).
* **Opción 2: Extraer flujos a scripts bash opacos sin soporte de skill.** Crear scripts de automatización CLI para tareas E2E sin exponer conocimiento al agente. (Descartada porque elimina la adaptabilidad contextual del modelo ante incidencias en el desarrollo).
* **Opción 3: Patrón "Trigger Directive + Dedicated Skill" con Catálogo Canónico en Dotfiles.**

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes pilares:

### 1. Criterios Objetivos de Extracción
Una directiva es candidata prioritaria a extracción como skill cuando cumple:
* **Criterio Cuantitativo:** Extensión superior a **500 palabras** en un único módulo, o consumo mayor al **15% del presupuesto de contexto basal** (600 palabras sobre 4.000).
* **Criterio Cualitativo:** Naturaleza procedimental y especializada (aplicable únicamente bajo demanda ante tareas específicas como despacho de tickets, gestión de PRs o ciclos de release), en contraposición a reglas basales universales (objetividad, anti-alucinación, seguridad de sandbox) que rigen en cada turno.

### 2. Patrón "Trigger Directive + Dedicated Skill"
* **En `core/` (Trigger Directive, ~80–130 palabras):**
  - Mantiene los invariantes absolutos no negociables (ej. prohibición total de commits/push a `main`, gate humano de aprobación).
  - Define el trigger imperativo de activación: ante la recepción de una orden de trabajo (ej. *"implementa la issue #X"*), el agente **DEBE activar y consultar obligatoriamente el skill correspondiente** antes de iniciar.
  - Conserva marcadores canónicos esenciales (nomenclatura de ramas, directiva de vinculación `Closes #<id>`).
* **En `skills/` (`SKILL.md` bajo demanda):**
  - Encapsula la especificación operativa completa, ciclos de vida E2E, comandos CLI deterministas, transiciones de estado en tableros y plantillas de reporte de salida.

### 3. Migración Primaria (`core/09-issue-driven-workflow.md` a `issue-driven-workflow`)
* Se extrae el procedimiento E2E hacia `skills/issue-driven-workflow/SKILL.md`.
* Se sustituye `core/09` por la directiva liviana de enlace, logrando una reducción de ~500 palabras en el System Prompt basal.

### 4. Consolidación de Skills en Dotfiles
* Se adopta el directorio raíz `skills/` en `Dotfiles-IA-Agents` como la ubicación canónica de skills para agentes.
* El orquestador `build.sh` prioriza `${SCRIPT_DIR}/skills/${skill_name}`, manteniendo resolución de retrocompatibilidad con `AGY_SKILLS_PATH` mientras se completa la migración definitiva de skills remotos ([Issue #35](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/35)).

## Consecuencias

### Positivas
* **Reducción Inmediata de Presupuesto:** Liberación de ~500 palabras (~660 tokens) en el System Prompt basal, bajando la ocupación del 85% a ~73% de la ventana recomendada.
* **Integridad Normativa Intacta:** El agente mantiene en memoria basal las restricciones de seguridad y gobernanza, y carga los procedimientos exhaustivos solo cuando los necesita.
* **Versionado Atómico:** Cambios en directivas y skills correspondientes pueden fusionarse en un único Pull Request dentro del mismo repositorio.
* **Alineación con Estándares Abiertos:** El catálogo en `skills/` es compatible con el estándar general de skills de agentes de IA.

### Negativas / Trade-offs
* **Latencia en Primer Turno de Tarea:** Al recibir una instrucción de tarea, el agente debe realizar una lectura local de `SKILL.md` (mitigado por ser lectura de archivo local instantánea en disco).
