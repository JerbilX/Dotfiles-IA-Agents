---
status: accepted
date: 2026-10-16
decision-makers: [Usuario, Antigravity]
supersedes: []
superseded-by: []
---

# 0014 - Consolidación del Catálogo de Skills en Dotfiles y Deprecación de AGY-Skills

## Contexto y Planteamiento del Problema

Históricamente, los skills para agentes de IA se alojaban en un repositorio hermano independiente (`JerbilX/AGY-Skills`), mientras que las directivas y reglas residían en `Dotfiles-IA-Agents`. Esta dispersión generaba tres problemas arquitectónicos y operativos:

1. **Pérdida de Atomicidad:** Cualquier cambio coordinado entre directivas (ej. disparadores en `core/`) y procedimientos detallados (en `SKILL.md`) requería gestionar ramas, commits y Pull Requests sincronizados en dos repositorios distintos.
2. **Deuda Técnica de Nomenclatura y Acoplamiento:** El nombre `AGY-Skills` ataba las herramientas al runtime específico de Antigravity, cuando los skills siguen la convención abierta y agnóstica de agentes (`SKILL.md`).
3. **Fricción con Políticas de Sandbox:** Las reglas de aislamiento de workspace prohíben a los agentes interactuar o realizar modificaciones en rutas externas al workspace activo, impidiendo mantener y evolucionar los skills dentro del flujo de trabajo habitual sin intervenciones manuales.

En [ADR-0013](0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md) se formalizó el directorio raíz `skills/` en `Dotfiles-IA-Agents` y se introdujo un mecanismo de resolución transicional en `build.sh` (`resolve_skill_dir` con fallback a `AGY_SKILLS_PATH`) mientras se migraba el catálogo completo ([Issue #35](https://github.com/JerbilX/Dotfiles-IA-Agents/issues/35)).

## Impulsores de la Decisión (Decision Drivers)

* **Autonomía y Autosuficiencia del Repositorio:** El repositorio debe poder clonarse, auditarse (`./build.sh check`) y aprovisionarse (`./build.sh`) de manera autocontenida sin requerir clones de repositorios hermanos ni variables de entorno adicionales.
* **Aislamiento Estricto del Workspace:** Permitir que los agentes mantengan, prueben y versionen sus propios skills dentro de los límites seguros de su sandbox.
* **Simplicidad y Determinismo en `build.sh`:** Eliminar lógica bifurcada de resolución de rutas y puntos de falla por rutas inexistentes fuera del repositorio.
* **Higiene del Ecosistema de GitHub:** Evitar repositorios zombis o desactualizados archivando formalmente `JerbilX/AGY-Skills`.

## Opciones Consideradas

* **Opción 1: Mantener catálogo híbrido permanente.** Resolver primero en `skills/` local y luego en `AGY_SKILLS_PATH` de forma indefinida. (Descartada por mantener deuda técnica, dualidad de mantenimiento y riesgo de desincronización).
* **Opción 2: Usar Git Submodules o Git Subtree.** Integrar `AGY-Skills` como submódulo dentro de `skills/`. (Descartada por complejidad operacional excesiva en CI/CD, sincronizaciones de sub-ramas y fricción en agentes de IA).
* **Opción 3: Consolidación total en `skills/` y archivado formal de `AGY-Skills`.** Migrar todos los skills existentes (`adr-manager`, `eso-addon-development`) a `Dotfiles-IA-Agents/skills/`, simplificar `build.sh` para operar 100% de forma local, y marcar como deprecado y archivado el repositorio `JerbilX/AGY-Skills`.

## Decisión Adoptada

Opción elegida: **Opción 3**, ejecutada según los siguientes acuerdos técnicos:

1. **Migración Completa de Skills:**
   - Se incorporan de forma nativa a `skills/`:
     - `skills/adr-manager/` (incluyendo su especificación `SKILL.md` y plantilla `resources/template.md`).
     - `skills/eso-addon-development/` (incluyendo `SKILL.md`, referencias documentales y scripts ejecutables en `scripts/`).
2. **Refactorización de `build.sh`:**
   - Se elimina la variable `AGY_SKILLS_PATH` y su fallback en `resolve_skill_dir()`.
   - Se define `SKILLS_DIR="${SCRIPT_DIR}/skills"` como fuente única de verdad para el aprovisionamiento y verificación estática.
   - Se actualizan las auditorías de symlinks en `check` para validar únicamente rutas pertenecientes a `${SCRIPT_DIR}`.
3. **Actualización de Documentación:**
   - Se actualiza `README.md` simplificando el proceso de bootstrap (un único `git clone`) y reflejando el árbol consolidado de `skills/`.
4. **Deprecación y Archivado del Repositorio Remoto:**
   - Se actualiza la metadata de `JerbilX/AGY-Skills` en GitHub para indicar su deprecación formal.
   - Se archiva el repositorio en GitHub (`gh repo archive JerbilX/AGY-Skills --yes`) para prevenir modificaciones posteriores.

## Consecuencias

### Positivas
* **Repositorio Autocontenido:** Un único repositorio aloja directivas, esquemas de runtime, servidores MCP y catálogo completo de skills.
* **Atomicidad Garantizada:** Modificaciones a directivas normativas y a sus skills correspondientes se canalizan en el mismo Pull Request.
* **Compatibilidad de Sandbox:** Los agentes operan 100% confinados en su workspace, sin violar políticas de acceso fuera de raíz.
* **Limpieza de Código:** `build.sh` se vuelve más simple, predecible y rápido al eliminar resoluciones condicionales complejas.

### Negativas / Trade-offs
* **Reaprovisionamiento de Entorno Local:** Requiere ejecutar `./build.sh skills` (o `./build.sh all`) en entornos locales existentes para que los symlinks en `~/.gemini/config/skills/` y `~/.local/bin/` apunten al nuevo directorio `Dotfiles-IA-Agents/skills/`.
