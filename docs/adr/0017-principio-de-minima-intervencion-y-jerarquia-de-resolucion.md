---
status: accepted
date: 2026-10-17
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0017 - Principio de Mínima Intervención y Jerarquía de Resolución (Minimal Blast Radius)

## Contexto y Planteamiento del Problema

Durante el análisis operativo y auditoría de sesiones recientes (ej. análisis inicial de la issue #53 en la conversación `eb5757d2-767a-42a1-8e96-0cfc3db348b6`), se identificó una tendencia recurrente de los agentes hacia la sobre-ingeniería normativa y la elevación prematura del radio de impacto (*blast radius*). Ante requerimientos de comportamiento por defecto o preferencias operativas solubles mediante parámetros CLI nativos o guías procedimentales en skills, el agente propuso de inmediato modificar directivas de la capa `core/` (`AGENTS.md`).

Esta conducta acarrea tres fallas críticas de arquitectura:
1. **Inflación del presupuesto basal de tokens:** Modificar `core/` incrementa el costo permanente de tokens en cada turno de todas las conversaciones futuras, atentando directamente contra los principios de poda y economía atencional formalizados en [ADR-0013](0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md) y [ADR-0016](0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md).
2. **Violación de la separación de responsabilidades:** La capa `core/` debe reservarse exclusivamente para invariantes universales de gobernanza y seguridad de ejecución, no para directivas de formateo, preferencias procedimentales ni parámetros de herramientas.
3. **Carencia de un mecanismo preventivo formal:** Los agentes carecían de una jerarquía canónica explícita y de un gate de validación que impidiera escalar a niveles superiores de abstracción cuando existe una solución de menor orden.

## Impulsores de la Decisión (Decision Drivers)

* **Minimal Blast Radius:** Toda solución debe resolverse en el nivel de menor abstracción y menor alcance de impacto posible.
* **Presupuesto Basal de Contexto y Eficiencia Atencional:** Proteger el presupuesto basal de tokens (< 4.000 palabras) evitando dilución atencional (*lost in the middle*) y sesgos aditivos.
* **Separación de Responsabilidades:** Preservar la capa `core/` para invariantes universales de gobernanza y seguridad, delegando la operativa a skills bajo demanda y capacidades nativas.
* **Verificabilidad y Prevención:** Establecer un gate determinista en la creación de issues y en el Planning Mode que frene propuestas con elevación injustificada de impacto.

## Opciones Consideradas

* **Opción 1: Instrucciones Ad-hoc o Correcciones Reactivas en Conversación.** Confiar en que el usuario señale en cada conversación cuándo una propuesta es sobre-dimensionada. No previene la repetición del patrón ni establece un estándar verificable.
* **Opción 2: Prohibición Absoluta de Modificación de `core/`.** Bloquear por completo cualquier cambio en la capa basal. Imposibilita la evolución legítima de invariantes universales de seguridad o gobernanza.
* **Opción 3: Jerarquía Canónica de Resolución de 5 Niveles (0 a 4) con Gate de Justificación Basal e Invariante Compacto.** Formalizar una escala ordenada de resolución, una regla invariante de no-elevación ($N+1$ prohibido si se resuelve en $\le N$), un gate obligatorio en la planificación y un invariante ultra-denso en la capa core.

## Decisión Adoptada

Se adopta la **Opción 3**. Se implementa el marco estructural del Principio de Mínima Intervención y Jerarquía de Resolución Canónica:

### 1. Escala Canónica de Resolución (Niveles 0 a 4)

| Nivel | Capa de Abstracción | Mecanismo y Alcance | Ejemplo |
| :---: | :--- | :--- | :--- |
| **0** | **Configuración / Parámetro CLI / API** | Argumentos nativos, flags o capacidades existentes de la herramienta. Impacto local al comando invocado. | `--query`, `--format json`, `--field`, flags de `gh` o `git`. |
| **1** | **Tooling / Automatización Local** | Scripts de verificación, tests locales, linters o targets de `build.sh`. Impacto local al pipeline de compilación. | Target `./build.sh check`, validadores de esquemas, linters. |
| **2** | **Skills bajo Demanda** | Procedimientos detallados, guías operativas o flujos E2E en `skills/*/SKILL.md`. Impacto acotado a la activación del skill. | Procedimientos de `issue-driven-workflow`, guías de `adr-manager`. |
| **3** | **Reglas Especializadas de Runtime** | Directivas acotadas al runtime activo en `runtimes/<runtime>/rules/*.md`. Impacto restringido a dicho entorno. | Especialización de sandbox para Antigravity (`rules/01-sandbox.md`). |
| **4** | **Core Basal / System Prompt Universal** | Invariantes duros de gobernanza, seguridad universal y principios irrenunciables en `core/*.md`. Impacto permanente y universal en cada turno. | Prohibición de push directo a `main`, confinamiento de sandbox, zero complacencia. |

### 2. Regla Invariante de Resolución
Queda **terminantemente prohibido** proponer o ejecutar cambios en un nivel $N+1$ si el problema técnico o requerimiento operativo puede resolverse eficazmente en un nivel menor o igual a $N$.

### 3. Gate de Justificación de Elevación Basal
Toda propuesta en un `implementation_plan.md` o en la especificación de una issue (`.issue_body`) que plantee modificar directivas en la capa basal (`core/`) debe incluir obligatoriamente el apartado técnico **"Justificación de Elevación Basal"**. Dicha sección debe demostrar fehacientemente por qué la necesidad técnica es inviable de abordar en los niveles 0 a 3. Propuestas que omitan esta justificación se considerarán técnicamente inválidas por definición.

### 4. Invariante Ultra-Compacto en Core
Se formaliza en `core/06-engineering-standards.md` una regla de máxima densidad informativa (máximo 2 líneas, ~40 palabras) que establece la prohibición de escalación injustificada, asegurando que el agente mantenga activo el freno normativo basal sin inflar el presupuesto de tokens.

## Consecuencias

### Positivas
* **Contención del Blast Radius:** Las soluciones se canalizan al menor nivel de impacto necesario, eliminando la sobre-ingeniería normativa.
* **Protección del Presupuesto Basal:** Se evita la degradación progresiva de la ventana de contexto y se preserva la capacidad atencional en el System Prompt.
* **Separación Robusta de Capas:** El core se mantiene puramente como guardián de invariantes y gobernanza, mientras que los skills absorben los flujos procedimentales.
* **Freno Preventivo Determinado:** El gate de justificación basal obliga al agente a evaluar y justificar alternativas de menor orden antes de proponer cambios en `core/`.

### Negativas / Trade-offs
* Exige al agente evaluar conscientemente la escala de niveles en cada planificación, incrementando levemente la rigurosidad analítica previa a la implementación.
