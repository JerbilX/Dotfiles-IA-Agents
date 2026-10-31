---
status: accepted
date: 2026-10-31
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
supersedes: []
superseded-by: []
---

# 0042 - Arquitectura Modular de build.sh, Helpers JSON, Validadores y Symlinks

## Contexto y Planteamiento del Problema

El script `build.sh` ha crecido hasta superar las 2.200 líneas (~83 KB), asumiendo responsabilidades de orquestación, resolución de rutas, parseo JSON, validación de esquemas, compilación de directivas, linking y backups de symlinks, auditoría estática y ejecución de tests.

Esta concentración genera múltiples fricciones identificadas en la Issue #194:
1. **Duplicación de extracción JSON:** Comprobaciones repetitivas de `jq` vs `python3` a lo largo del script.
2. **Validadores de esquema embebidos y divergentes:** Heredocs extensos con `python3 -c` que validan manualmente reglas de esquema en `validate_config` y `validate_mcp_server`, mientras que el fallback en `jq` valida solo un subconjunto disímil, produciendo divergencia de comportamiento según los paquetes instalados en el sistema anfitrión.
3. **Duplicación de operaciones de symlinks y backup:** `link_runtime` y `link_runtime_mcp` duplican la rutina de detección, creación de sufijo temporal `.bak.<timestamp>`, backup y creación del enlace simbólico.
4. **Monolitismo:** Dificulta el mantenimiento y la extensibilidad de los subsistemas individuales (build, link, check, validate).

## Impulsores de la Decisión (Decision Drivers)

* **Principio de Responsabilidad Única y Modularidad:** Dividir el monolito en submódulos por dominio (`lib/*.sh`) manteniendo `build.sh` como punto de entrada y orquestador determinista.
* **Cero Dependencias Externas (Standard Library First):** Mantener el validador agnóstico (`lib/validate.py`) utilizando exclusivamente la biblioteca estándar de Python (`json`, `re`, `sys`, `os`), sin requerir librerías de terceros (como `jsonschema` o `check-jsonschema`) que requieran pip o violen el confinamiento del sandbox.
* **Paridad de Comportamiento:** Garantizar que la validación de esquemas y las consultas JSON arrojen resultados consistentes independientemente de la presencia de `jq` o `python3`.
* **Atomicidad y Byte-Identidad:** Asegurar que los artefactos generados en `dist/` permanezcan byte-idénticos tras la refactorización.

## Opciones Consideradas

* **Opción 1:** Mantener `build.sh` monolítico y solo extraer funciones a nivel superior dentro del mismo archivo.
* **Opción 2:** Descomponer en `lib/*.sh` por dominio funcional y extraer validadores a `lib/validate.py` basado en la biblioteca estándar de Python.
* **Opción 3:** Reescribir `build.sh` íntegramente en Python o introducir dependencias como `check-jsonschema`.

## Decisión Adoptada

Se elige la **Opción 2**:
1. **Extracción modular de Shell (`lib/*.sh`):**
   - `lib/common.sh`: Constantes base, helper `json_get`, helper `safe_symlink`, resolución y caché de configuración.
   - `lib/validate.sh`: Funciones puente de validación (`validate_config`, `validate_mcp_server`, etc.).
   - `lib/build_core.sh`: Lógica de compilación y empaquetado de directivas y configuración MCP.
   - `lib/link.sh`: Aprovisionamiento de enlaces simbólicos, skills, aliases de GitHub y rollback.
   - `lib/check.sh`: Suite de comprobaciones estáticas, pureza y auditoría.
2. **Validador agnóstico (`lib/validate.py`):**
   - Script standalone testeable que valida archivos de configuración contra sus esquemas canónicos (`runtimes/schema/*.schema.json`) usando la biblioteca estándar de Python.
3. **Helpers canónicos centralizados:**
   - `json_get <file> <expr>`: Abstrae la consulta de propiedades JSON priorizando `jq` y con fallback a `python3`.
   - `safe_symlink <src> <dst> [label]`: Gestiona backups `.bak.<timestamp>` y creación atómica de enlaces con `ln -sfn`.

## Consecuencias y Mitigaciones

* **Positivas:**
  - Reducción drástica del tamaño y complejidad del punto de entrada `build.sh`.
  - Unificación de la lógica de validación de esquemas en un componente testeable directamente con `unittest`.
  - Reutilización consistente del ciclo de backup y symlink.
* **Mitigaciones:**
  - Los scripts en `lib/*.sh` son sourced desde `build.sh` con `set -euo pipefail` activo, previniendo regresiones de variables no definidas o rutas relativas rotas mediante el anclaje a `SCRIPT_DIR`.
  - Pruebas unitarias de regresión en `tests/` que validan el comportamiento con y sin `jq`.
