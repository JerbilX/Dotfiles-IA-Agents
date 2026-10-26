---
status: accepted
date: 2026-10-25
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0036 - Modularización del Skill eso-addon-development y Adopción de Progressive Disclosure

## Contexto y Planteamiento del Problema

El skill canónico `eso-addon-development` (`skills/eso-addon-development/SKILL.md`) rige el desarrollo de addons en Lua para Elder Scrolls Online bajo el motor de interfaz de Zenimax (EsoUI). Con un tamaño de 14.05 KB y aproximadamente 1.800 palabras, se convirtió en el archivo individual más pesado del catálogo de skills tras la modularización de `issue-driven-workflow` (ADR-0025).

El documento original concentraba de forma monolítica tres dominios diferenciados:
1. La política de información y jerarquía de consulta de API (contexto local -> modelo -> MCP `eso-mcp-server` / fallback local -> circuit breaker Stop & Ask).
2. Los diez principios arquitectónicos de desarrollo en Lua y ciclo de vida de EsoUI.
3. Los protocolos de build, empaquetado, sincronización de dependencias y prevalencia del motor sobre mocks de prueba.

Esta estructura monolítica satura innecesariamente la ventana de contexto del LLM cada vez que el skill se activa para consultas puntuales (como verificar un evento o consultar una constante), diluyendo la atención y aumentando el riesgo de dispersión técnica.

## Impulsores de la Decisión (Decision Drivers)

* **Preservación del Presupuesto de Contexto:** Reducir la sobrecarga basal del skill a <= 600 palabras, mitigando el efecto *Lost in the Middle*.
* **Patrón de Divulgación Progresiva (Progressive Disclosure):** Mantener un orquestador basal compacto con matriz de ruteo clara y diferir el detalle procedimental y técnico a referencias especializadas en `references/`.
* **Principio de Mínima Intervención y Jerarquía de Resolución (ADR-0017):** Resolver la modularización en Nivel 2 (Skills bajo demanda) sin alterar reglas basales (`core/`) ni configuraciones de runtime (Nivel 3).
* **Integridad Funcional y Cero Regresiones:** Preservar intactos los scripts (`build_release.sh`, `update_esoui_docs.sh`), los archivos canónicos de API (`ESOUIDocumentation.txt`, `localizegeneratedstrings.lua`) y asegurar validación sin errores en `./build.sh check`.

## Opciones Consideradas

* **Opción 1: Mantener el Documento Monolítico con Poda Textual Leve.**
  * Reducir palabras mediante reescritura superficial en un único archivo.
  * *Descarte:* Inviable para alcanzar la meta de <= 600 palabras sin mutilar especificaciones técnicas esenciales como los ejemplos de hooking, SavedVariables o inyección en build.
* **Opción 2: Fragmentar en Múltiples Skills Independientes.**
  * Dividir en skills separados: `eso-api-lookup`, `eso-lua-architecture` y `eso-build-packaging`.
  * *Descarte:* Fragmenta artificialmente un único dominio cohesivo (desarrollo de addons para ESO), dispersa el catálogo de skills e introduce fricción en la activación del agente.
* **Opción 3: Orquestador Basal Compacto con Referencias Especializadas (Progressive Disclosure).**
  * Mantener `skills/eso-addon-development/SKILL.md` como orquestador basal (<= 600 palabras) con la política de consulta de API, criterio de proporcionalidad y una matriz de ruteo explícita.
  * Modularizar los principios arquitectónicos de runtime en `references/lua-architecture.md`.
  * Modularizar las directivas de build, empaquetado, manifiesto y mocks en `references/build-and-packaging.md`.
  * Mantener los archivos de datos de API existentes en `references/` (`ESOUIDocumentation.txt` y `localizegeneratedstrings.lua`).

## Decisión Adoptada

Se adopta la **Opción 3**, estructurada de la siguiente manera:

1. **Orquestador Basal (`skills/eso-addon-development/SKILL.md`):**
   * Condensado a <= 600 palabras.
   * Preserva la política de consulta jerárquica de 4 niveles (Contexto Local -> Modelo -> MCP/Archivos Locales -> Circuit Breaker Stop & Ask).
   * Conserva el criterio de proporcionalidad (flujo ágil para tareas incrementales vs plan formal para refactors mayores).
   * Incorpora una matriz de ruteo hacia las guías especializadas en `references/`.
2. **Guía de Arquitectura Lua (`skills/eso-addon-development/references/lua-architecture.md`):**
   * Aísla los principios de diseño de runtime: aislamiento de namespace, ciclo de vida (`EVENT_ADD_ON_LOADED`), persistencia de `SavedVariables` e inspección con herramientas MCP, hooking no destructivo (`ZO_PreHook`/`ZO_PostHook`), recolección de basura y tipado nativo vs hardcoding de IDs.
3. **Guía de Build y Empaquetado (`skills/eso-addon-development/references/build-and-packaging.md`):**
   * Aísla las directivas de empaquetado y sincronización: registro de comandos slash en `README.md`, sincronización de manifiesto vs `README.md` con detección de asimetrías, SSoT para metadatos e inyección en build-time vía `scripts/build_release.sh`, y prevalencia del motor oficial sobre mocks de prueba (anti-test-induced damage).

### Consecuencias

* **Positivas:**
  * Reducción de más del 65% en el volumen del archivo principal del skill, liberando ventana de contexto.
  * Carga bajo demanda: el agente consulta únicamente los principios de arquitectura Lua o las directivas de build cuando la tarea específica lo requiere.
  * Preservación de la totalidad de las directivas técnicas, ejemplos de código y contratos de seguridad preexistentes.
  * Validación limpia en `./build.sh check` sin afectación a esquemas ni colisiones.
* **Negativas / Trade-offs:**
  * El agente debe realizar una lectura adicional (`view_file`) en `references/` cuando requiera directivas procedimentales profundas de arquitectura o build.

### Pros y Contras de las Opciones

#### Opción 1: Mantener Monolito
* **Pro:** Todo el contenido en un solo archivo.
* **Contra:** Sobrecarga innecesaria de contexto (~1.800 palabras por invocación) y riesgo de *Lost in the Middle*.

#### Opción 2: Fragmentar en Micro-Skills
* **Pro:** Desacoplamiento total en carpetas independientes.
* **Contra:** Fragmentación del dominio ESO, proliferación de skills en el catálogo y sobrecarga de ruteo.

#### Opción 3: Progressive Disclosure (Elegida)
* **Pro:** Balance óptimo entre compacidad basal, cohesión de dominio y acceso detallado bajo demanda.
* **Contra:** Requiere consulta secundaria en `references/` para el detalle exhaustivo.
