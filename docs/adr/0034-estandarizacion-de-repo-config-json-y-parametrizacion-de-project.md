---
status: accepted
date: 2026-10-25
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0034 - Estandarización de .repo-config.json y Parametrización de Project en GitHub

## Contexto y Planteamiento del Problema

En la evolución del skill `issue-driven-workflow` y sus herramientas asociadas (ADR-0021, ADR-0026, ADR-0032), persistían dos limitaciones de diseño en la configuración por repositorio (identificadas en Issue #146):

1. **Ambigüedad y Riesgo de Colisión de `config.json`:** Tanto `git-prune-gone` como las referencias del skill admitían alternativamente `.repo-config.json` o `config.json` para determinar la estrategia troncal y la rama base (`base_branch`). El nombre `config.json` es genérico en el ecosistema de software y propenso a colisionar con configuraciones de librerías, linters, orquestadores o frameworks presentes en repositorios de usuario.
2. **Hardcode de Número de Proyecto y Propietario en Projects v2:** Las directivas y consultas de tablero (`gh project item-list` y `gh project item-add`) asumían de forma rígida `1` como número de proyecto y `@me` como propietario. En organizaciones de GitHub o cuentas con múltiples proyectos donde el tablero no sea el número 1 o el dueño difiera del usuario autenticado, las consultas fallaban o requerían intervención interactiva manual.

## Opciones Evaluadas

* **Opción 1: Mantener fallback a `config.json` y flags CLI manuales para Projects v2.**
  * *Evaluación:* No resuelve la fragilidad por colisión en repositorios ajenos y perpetúa la intervención manual en entornos multi-cuenta u organizaciones.
* **Opción 2: Variable de entorno en runtime para proyectos.**
  * *Evaluación:* Depende del host del usuario o del manifiesto del runtime, perdiendo portabilidad y configuración por repositorio.
* **Opción 3: Formalización canónica de `.repo-config.json` con fallback declarativo por defecto.**
  * *Evaluación:* Elimina colisiones descartando `config.json`, unifica en un solo contrato de datos la estrategia de ramas y la vinculación a Projects v2, y preserva 100% de compatibilidad hacia atrás mediante valores por defecto (`category_a`, `main`, `1`, `@me`).

## Decisión Adoptada

Opción elegida: **"Opción 3"**, estructurando la estandarización bajo las siguientes directivas:

1. **Eliminación Total de `config.json`:**
   * `git-prune-gone` busca exclusivamente `.repo-config.json` en la raíz del repositorio. Se suprime definitivamente la comprobación de `config.json`.
   * Toda la documentación de `issue-driven-workflow` (`references/*.md`) y contratos de rollback/poda estandarizan exclusivamente `.repo-config.json`.

2. **Esquema Formal de `.repo-config.json`:**
   El archivo de configuración de repositorio formaliza las siguientes propiedades opcionales:
   ```json
   {
     "repository_type": "category_a",
     "base_branch": "main",
     "project_number": 1,
     "project_owner": "@me"
   }
   ```
   * `repository_type` (string, opcional): `"category_a"` (Trunk-Based / `main`) o `"category_b"` (Git-Flow / `dev` -> `main`). Default: `"category_a"`.
   * `base_branch` (string, opcional): Rama base contra la cual integrar o verificar. Default: `"main"` (o `"dev"` si `repository_type` es `category_b`).
   * `project_number` (integer, opcional): Número del tablero central de GitHub Projects v2. Default: `1`.
   * `project_owner` (string, opcional): Propietario del tablero (`"@me"`, usuario o nombre de organización). Default: `"@me"`.

3. **Resolución de Parámetros de Projects v2 en el Skill:**
   * Al ejecutar consultas (`gh board`, `gh board-ready`, o llamadas crudas a `gh project item-list`) e indexaciones (`gh project item-add`), los valores `<project_number>` y `<project_owner>` se resuelven dinámicamente desde `.repo-config.json`.
   * Si el archivo no existe o los campos están omitidos, se aplican los defaults `1` y `@me`.

4. **Minimal Blast Radius:**
   * Cambios acotados a Nivel 1 (CLI `git-prune-gone` y tests en `tests/test_git_prune_gone.py`) y Nivel 2 (skill `issue-driven-workflow` y referencias). Capa basal (`core/`) permanece inalterada.

## Consecuencias y Estado

* **Positivas:**
  * Cero ambigüedades ni colisiones con archivos `config.json` de frameworks de terceros.
  * Soporte nativo y declarativo para organizaciones y proyectos no-estándar en Projects v2.
  * Compatibilidad hacia atrás total con repositorios que no declaren `.repo-config.json`.
* **Negativas / Mitigaciones:**
  * Repositorios existentes que dependían informalmente de `config.json` para declarar `base_branch` deberán renombrarlo a `.repo-config.json`.
