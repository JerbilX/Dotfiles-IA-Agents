---
status: proposed
date: 2026-10-17
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0019 - Skill de Aprendizaje Autónomo Basado en Decisiones Pasadas

## Contexto y Planteamiento del Problema

Durante el desarrollo autónomo en el repositorio, los agentes de IA se enfrentan recurrentemente a desafíos de entorno y diseño: restricciones del kernel de sandbox (sistemas de archivos de solo lectura en `.git/`), desalineación de *test doubles* frente al código productivo, trampas de anulación de *prefix matching* de seguridad en la terminal, o sobrecarga de presupuesto de contexto en el System Prompt.

Históricamente, estos incidentes y sus resoluciones se registraban de manera informal en `HISTORIAL.md`. En la [Issue #8](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/8) se planteó la creación de un skill de aprendizaje que analizara dicho registro histórico como fuente de datos para mejorar el comportamiento autónomo del agente y no repetir errores arquitectónicos.

Sin embargo, mediante [ADR-0004](0004-adopcion-del-estandar-madr-y-skill-adr-manager.md) y la directiva basal [`core/03-agent-rules-convention.md`](../../core/03-agent-rules-convention.md), el archivo `HISTORIAL.md` fue formalmente erradicado y reemplazado por el estándar abierto **MADR (Markdown Architectural Decision Records)** en `docs/adr/`, complementado por el skill `adr-manager`.

Se requería entonces conciliar la visión de aprendizaje autónomo de la Issue #8 con el estándar MADR vigente, proveyendo un mecanismo sistemático para que los agentes extraigan precedentes estructurados, contrasten hipótesis antes de actuar y prevengan regresiones sin vulnerar las reglas canónicas ni modificar directivas de forma encubierta.

## Impulsores de la Decisión (Decision Drivers)

* **Prevención Empírica de Errores Recurrentes:** Habilitar a los agentes para consultar lecciones previas y soluciones ya verificadas antes de formular hipótesis a ciegas o experimentar en el entorno.
* **Alineación con el Estándar MADR:** Utilizar como fuente de verdad canónica los registros formales en `docs/adr/NNNN-*.md` (con YAML frontmatter estructurado), preservando compatibilidad retrospectiva con `HISTORIAL.md` para repositorios externos que no hayan completado su migración.
* **Inmunidad Normativa Absoluta:** Garantizar que el conocimiento histórico opere como evidencia empírica descriptiva, sin capacidad de puentear o mutar directivas activas de `AGENTS.md` o `core/`.
* **Mínima Intervención (Minimal Blast Radius):** Resolver la necesidad exclusivamente en Nivel 2 (Skill bajo demanda `skills/autonomous-learning/`) y Nivel 1 (Herramienta local `query_decisions.py`), sin saturar el System Prompt basal en Nivel 4 (`core/`).
* **Operación Híbrida (Zero-CLI + Asistida):** Permitir la consulta 100% nativa con las herramientas de archivos del modelo (`grep_search`, `view_file`) y complementar con un script CLI en Python estándar (sin dependencias externas) para consultas complejas o estructuradas.

## Opciones Consideradas

* **Opción 1: Reintroducir `HISTORIAL.md` como log paralelo de fallos.** Mantener bitácoras informales junto a los ADRs. (Descartada por violar la regla basal `core/03`, generar duplicidad de mantenimiento y promover formatos desestructurados).
* **Opción 2: Sobrecargar `adr-manager` con responsabilidades de diagnóstico y aprendizaje.** Añadir heurísticas de consulta y taxonomía de incidentes dentro del skill de gestión de ADRs. (Descartada por violar el principio de responsabilidad única: `adr-manager` es un gestor de ciclo de vida documental y gobierno de decisiones, no un motor de inferencia de precedentes técnicos).
* **Opción 3: Desarrollar el Skill Dedicado `autonomous-learning` basado en MADR.** Crear un skill bajo demanda con taxonomía de extracción en cuatro campos (*Contexto/Síntoma*, *Causa Raíz*, *Solución Técnica*, *Invariante Derivado*), protocolo de consulta previa (*Precedent Lookup*), compendio de anti-patrones conocidos y script de consulta CLI sin dependencias.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes pilares técnicos:

1. **Catálogo Canónico (`skills/autonomous-learning/`):**
   - `SKILL.md`: Guía metodológica completa para consulta de precedentes, contraste de hipótesis, respeto al estado de los ADRs (`accepted` vs `rejected` vs `superseded`) y salvaguardas de gobernanza.
   - `references/known_anti_patterns.md`: Compendio de los 8 anti-patrones más críticos documentados en los ADRs y sus soluciones canónicas.
   - `resources/template_precedent.md`: Plantilla estructurada para documentar nuevos post-mortems.
2. **Herramienta Local de Consulta (`scripts/query_decisions.py`):**
   - Script CLI en Python 3 puro (sin dependencias de terceros).
   - Capacidad de filtrado por estado (`--status`), dominio técnico (`--domain`), consulta de texto libre (`-q`) y salida en tabla o JSON legible por máquina.
   - Soporte nativo para `docs/adr/` y fallback automático si existe `HISTORIAL.md`.
3. **Integración Multi-Runtime:**
   - Registro del skill en `runtimes/antigravity/config.json` y `runtimes/claude/config.json`.
   - Verificación estática con `./build.sh check` y aprovisionamiento con `./build.sh skills`.
4. **Articulación con `adr-manager` e `issue-driven-workflow`:**
   - Si el aprendizaje sugiere un cambio arquitectónico, se formaliza mediante `adr-manager` (`status: proposed`).
   - Si detecta un bug o deuda secundaria, se registra como GitHub Issue en Projects v2 mediante `issue-driven-workflow` para evitar *scope creep*.

## Consecuencias

### Positivas
* **Eliminación de la Alucinación de Hipótesis:** Los agentes consultan primero la base de conocimiento empírica antes de formular supuestos infundados sobre fallos del entorno.
* **Respeto a Alternativas Rechazadas:** Se evita re-proponer soluciones que ya fueron formalmente descartadas en ADRs previos con `status: rejected`.
* **Zero Overhead Basal:** Al confinarse a un skill bajo demanda (Nivel 2), el presupuesto de contexto basal de los runtimes se mantiene protegido (~1.464 palabras en Antigravity, 36% del límite).
* **Compatibilidad Retrospectiva:** Funciona de manera transparente tanto en repositorios modernos basados en MADR como en repositorios antiguos con `HISTORIAL.md`.

### Negativas / Trade-offs
* **Disciplina Operativa Requerida:** Exige que los agentes incorporen proactivamente la consulta de precedentes ante incidencias antes de proceder a la edición de archivos.
