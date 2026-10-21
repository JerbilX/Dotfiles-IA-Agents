---
status: accepted
date: 2026-10-15
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
---

# 0007 - Esquema Canónico de Validación y Desacoplamiento de Binarios en Runtimes

## Contexto y Planteamiento del Problema

Tras la adopción de `config.json` como manifiesto operativo de runtime ([ADR 0006](0006-desacoplamiento-de-directivas-y-configuracion-de-runtimes.md)), persistían dos limitaciones de diseño en la gestión de dotfiles:

1. **Acoplamiento de Casos Especiales en `build.sh`:** El script `build.sh` contenía una condición fija que evaluaba si el script era `build_release.sh` y el skill correspondía a `eso-addon*`, forzando el renombrado a `eso-build` al crear el enlace simbólico en `~/.local/bin`. Esto violaba el principio de responsabilidad única (SRP), introduciendo conocimiento específico de un proyecto externo dentro del núcleo orquestador global de Dotfiles.
2. **Ausencia de Validación Formal de Esquema:** El manifiesto `runtimes/antigravity/config.json` declaraba como `$schema` el metaschema general de JSON Schema (`https://json-schema.org/draft/2020-12/schema`), careciendo de un contrato de datos local que garantizara tipos estrictos, claves requeridas (`skills`) y prohibición de propiedades arbitrarias (`additionalProperties: false`).

## Impulsores de la Decisión (Decision Drivers)

* **Principio de Responsabilidad Única (SRP):** El orquestador `build.sh` debe ser agnóstico a los skills concretos y operar como un motor genérico de aprovisionamiento.
* **Declaratividad y Extensibilidad:** Los mapeos, alias y personalizaciones de binarios deben definirse de forma explícita en los manifiestos de configuración (`config.json`), no en la lógica procedural de Bash.
* **Integridad Estructural y Fail-Fast:** Errores de sintaxis o propiedades no soportadas en `config.json` deben abortar la ejecución antes de alterar el sistema de archivos (`~/.gemini/config/skills/` o `~/.local/bin/`).
* **Zero Dependencias Adicionales:** La validación de esquema debe operar nativamente con herramientas disponibles en el entorno (`python3` estándar o `jq`), sin requerir librerías externas como `jsonschema` de PyPI.

## Opciones Consideradas

* **Opción 1: Obligar a los repositorios de skills a renombrar sus scripts.** No soportar alias y asumir que los nombres en `scripts/*.sh` siempre son finales. (Inflexible si dos skills exponen un script con el mismo nombre o si se prefiere un alias corto en el PATH local).
* **Opción 2: Mapeo declarativo en `config.json` sin validación.** Permitir una clave `"binaries"` pero sin verificar tipos ni integridad. (Riesgo de fallos silenciosos o enlaces rotos por typos en la configuración).
* **Opción 3: JSON Schema local dedicado (`runtime-config.schema.json`) + Mapeo declarativo en `config.json` + Validador integrado en `build.sh`.**

## Decisión Adoptada

Opción elegida: **Opción 3**, porque:

1. **Esquema Formal Local:** Se crea `runtimes/schema/runtime-config.schema.json` bajo el estándar JSON Schema Draft 2020-12, definiendo:
   - `skills`: Lista obligatoria de cadenas únicas no vacías.
   - `binaries`: Objeto opcional de pares clave-valor (`string: string`) para alias de ejecutables.
   - `additionalProperties: false`: Bloqueo estricto contra propiedades desconocidas.
2. **Desacoplamiento de Binarios:** `build.sh` consulta dinámicamente si el script base existe en la sección `binaries` de `config.json`. Si existe, aplica el alias; de lo contrario, utiliza el nombre original del script. Se erradica cualquier referencia a `eso-addon` o `eso-build` del código de `build.sh`.
3. **Validación Automática Pre-Flight:** Se incorpora `validate_config()` en `build.sh`, ejecutada de forma obligatoria en `cmd_skills()` antes de alterar enlaces en disco, garantizando fail-fast mediante el módulo estándar `json` de Python 3.

### Consecuencias

* **Positivas:**
  - `build.sh` queda completamente desacoplado de skills particulares y es 100% genérico.
  - La configuración de runtime es auto-documentada y validable por IDEs mediante el `$schema` local.
  - Se previenen errores de aprovisionamiento por configuraciones malformadas o typos.
* **Negativas / Trade-offs:**
  - Introduce una función de validación en Python en `build.sh` (mantenida de forma compacta y dependiente únicamente de la biblioteca estándar).
