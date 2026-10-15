---
status: accepted
date: 2026-10-15
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0004 - Adopción del Estándar MADR y Skill ADR Manager

## Contexto y Planteamiento del Problema
Inicialmente, las decisiones técnicas y metodológicas se registraban de manera ad-hoc en un archivo monolítico en la raíz (`HISTORIAL.md`). Este formato presentaba severas limitaciones: carecía de metadatos estructurados legibles por máquina (YAML frontmatter), propiciaba la ambigüedad sobre qué decisiones estaban vigentes o deprecadas, e inducía al agente a continuar agregando registros informales sin seguir un estándar de la industria.

## Impulsores de la Decisión (Decision Drivers)
* **Estandarización y Trazabilidad:** Adoptar el estándar MADR (Markdown Architectural Decision Records) compatible con `adr-tools` (`docs/adr/NNNN-titulo.md`).
* **Operación Nativa (Zero-CLI):** Gestionar los registros mediante las herramientas de archivos nativas del agente sin dependencias de paquetes CLI externos.
* **Gobernanza Humana:** Todo nuevo ADR debe nacer estrictamente con `status: proposed` y requiere aprobación explícita del usuario antes de convertirse en `accepted`.

## Opciones Consideradas
* **Opción 1:** Mantener el archivo monolítico `HISTORIAL.md`.
* **Opción 2:** Adoptar el estándar MADR mediante el skill `adr-manager`, migrar las decisiones vigentes a registros atómicos en `docs/adr/`, y prohibir formalmente los archivos `HISTORIAL.md` ad-hoc en todos los proyectos.

## Decisión Adoptada
Opción elegida: **"Opción 2"**, porque profesionaliza el registro de decisiones arquitectónicas, garantiza la inmutabilidad histórica, habilita la detección programática de conflictos y unifica la gestión documental del ecosistema.

### Consecuencias
* **Positivas:**
  * Se retira definitivamente el archivo legacy `HISTORIAL.md`.
  * Toda decisión técnica cuenta con ciclo de vida claro (`proposed`, `accepted`, `rejected`, `superseded`).
  * Integración nativa con el skill `adr-manager` habilitado en el entorno.
* **Negativas / Trade-offs:**
  * Requiere crear archivos individuales por cada decisión significativa en lugar de editar un único documento.
