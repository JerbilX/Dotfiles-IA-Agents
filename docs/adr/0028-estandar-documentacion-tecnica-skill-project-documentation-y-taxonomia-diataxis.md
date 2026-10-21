---
status: proposed
date: 2026-10-21
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0028 - Estándar de Documentación Técnica, Skill `project-documentation` y Taxonomía Diátaxis

## Contexto y Planteamiento del Problema

El ecosistema de proyectos (`Proyectos-IA-V3`) carecía de un estándar canónico formalizado para gobernar la arquitectura de información, los contratos de archivo raíz y el ciclo de vida de la documentación técnica. Como consecuencia directa:

1. **Sobrecarga y Saturación de Archivo Raíz:** El archivo `README.md` de `Dotfiles-IA-Agents` acumuló 224 líneas, 1.831 palabras y ~15,8 KB, consumiendo ~2.450 tokens por lectura. Conviven en un único documento responsabilidades dispares (árboles de directorios exhaustivos, guías de instalación/bootstrap, referencia de 8 subcomandos de `build.sh`, schemas JSON y convenciones normativas).
2. **Dilución Atencional (*Lost in the Middle*):** La saturación del buffer de contexto con manuales extensos incrementa el riesgo de pérdida de directivas críticas durante sesiones complejas de desarrollo agéntico.
3. **Deuda Técnica por Desincronización de Árboles ASCII:** El mantenimiento manual de árboles de archivos detallados en el `README.md` diverge rápidamente frente a la incorporación continua de nuevos ADRs o módulos.
4. **Ausencia de Taxonomía Adaptativa:** No existía un criterio estructurado para distinguir cuándo un micro-proyecto se beneficia de un único `README.md` autocontenido frente a plataformas complejas que requieren modularización profunda en `docs/`.

Tras la conclusión del Spike técnico (#115), se requiere definir un estándar documental integral y un skill especializado que proporcione guías, contratos y plantillas operativas reutilizables.

## Impulsores de la Decisión (Decision Drivers)

* **Divulgación Progresiva (*Progressive Disclosure*):** Preservar la ventana de contexto de modelos de IA y el tiempo de lectura humana manteniendo el `README.md` como una puerta de entrada ligera y ejecutable ($\le 70$ líneas, $\le 500$ palabras).
* **Adaptabilidad y Anti-Rigidez (*Repository Sizing Tiers*):** Evitar tanto la saturación monolítica en proyectos grandes como la sobre-ingeniería innecesaria en proyectos pequeños (< 500 LOC).
* **Taxonomía Formal (Diátaxis Pragmático):** Estructurar la documentación profunda en categorías funcionales claras: How-To (`setup.md`), Reference (`cli.md`), Explanation (`architecture.md`) y Decisions (`adr/`).
* **Principio de Mínima Intervención (Minimal Blast Radius - ADR-0017):** Operar estrictamente en Nivel 1 (tooling estático en `build.sh check`) y Nivel 2 (skill bajo demanda `project-documentation`), con cero alteraciones en la capa basal (`core/`) ni reglas de runtime (`rules/`).
* **Delimitación Estricta de Fronteras:** Preservar la autonomía de `adr-manager` sobre `docs/adr/` y de `issue-driven-workflow` sobre el ciclo de vida de Git/GitHub.

## Opciones Consideradas

* **Opción 1:** Mantener el `README.md` monolítico actual y redactar directivas imperativas de documentación en `core/`.
* **Opción 2:** Modularizar manualmente el `README.md` en `Dotfiles-IA-Agents` sin crear un skill formal ni verificación automatizada en `build.sh`.
* **Opción 3:** Implementar el skill canónico `project-documentation` (Nivel 2) con matriz Diátaxis adaptativa por Tiers, plantillas en `resources/`, verificación estática en `build.sh check` (Nivel 1) y dogfooding empírico en `Dotfiles-IA-Agents` (Tier 3).

## Decisión Adoptada

Opción elegida: **"Opción 3"**, porque institucionaliza la arquitectura de información para todo el ecosistema de proyectos, provee plantillas operativas listas para consumo por agentes humanos y sintéticos, previene la sobrecarga atencional y añade salvaguardas estáticas en el tooling local.

### 1. Matriz de Adaptabilidad por Repositorio (Sizing Tiers)
* **Tier 1 (Micro-proyectos, scripts < 500 LOC):** `README.md` único autocontenido ($\le 120$ líneas). Sin fragmentación en `docs/`.
* **Tier 2 (Aplicaciones medianas, microservicios, CLI estándar):** `README.md` minimalista + `docs/setup.md` + `docs/cli.md` (o `usage.md`) + `docs/adr/`.
* **Tier 3 (Plataformas modulares, multi-runtime, infraestructuras complejas):** `README.md` minimalista + `docs/setup.md` + `docs/cli.md` + `docs/architecture.md` + `docs/adr/`.

### 2. Contrato Canónico de `README.md` Minimalista
* **Presupuesto Máximo:** $\le 70$ líneas y $\le 500$ palabras (alerta estática en `MAX_README_WORDS=600`).
* **6 Bloques Obligatorios:** Header & Badges, Resumen Ejecutivo (1 párrafo), Arquitectura Esencial (diagrama conceptual $\le 6$ líneas), Quickstart Determinista (3-5 comandos), Tabla Sintética de Interfaces/Subcomandos y Mapa de Navegación Documental con 3 convenciones clave.

### 3. Tooling Estático de Nivel 1 en `build.sh check`
* Validación de presencia de `README.md` en la raíz (`CHECK_ERRORS`).
* Validación de presupuesto de palabras (`MAX_README_WORDS=600`, emite advertencia si se excede).
* Inspección de enlaces locales relativos en Markdown hacia `docs/` para garantizar la ausencia de rutas rotas (`CHECK_ERRORS`).

### 4. Delimitación Estricta de Fronteras
* `adr-manager` retiene el monopolio sobre `docs/adr/`. `project-documentation` únicamente enlaza e indexa.
* La documentación técnica es descriptiva y operacional; no define directivas de comportamiento ni órdenes para agentes (reservadas a `core/` y `rules/`).
* Prohibición absoluta de bitácoras informales (`HISTORIAL.md`, `TODO.md`, `backlog.md`).

## Consecuencias

### Positivas
* **Optimización Atencional:** El `README.md` de `Dotfiles-IA-Agents` se reduce en más del 70% en líneas y volumen de palabras (~395 palabras), liberando ~1.700 tokens por consulta.
* **Separación de Responsabilidades:** Bootstrap, manual CLI y arquitectura quedan desacoplados en documentos especializados con responsabilidades atómicas.
* **Reutilización y Consistencia:** Cualquier proyecto nuevo o existente en `Proyectos-IA-V3` puede estructurar su documentación de forma homogénea activando el skill `project-documentation`.
* **Protección Estática Continua:** `./build.sh check` previene regresiones por crecimiento desmedido del archivo raíz o enlaces rotos en pre-commit y CI/CD.

### Negativas / Trade-offs
* Mantenimiento de múltiples archivos Markdown en `docs/` en lugar de un único archivo centralizado en repositorios Tier 2 y Tier 3.
* Requisito de validar que los enlaces relativos se mantengan vigentes ante reorganizaciones de carpetas (mitigado por la verificación automática en `build.sh check`).
