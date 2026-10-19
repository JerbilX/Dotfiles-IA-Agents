---
status: accepted
date: 2026-10-19
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0021 - Estrategia de Ramas Troncales y Promoción de Entornos

## Contexto y Planteamiento del Problema
En el flujo de trabajo guiado por issues y Pull Requests formalizado en ADR-0005 y ADR-0010, se estableció el aislamiento de tareas en ramas efímeras (`feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`) integradas directamente a la rama principal (`main`).

A medida que el ecosistema de proyectos se diversifica (abarcando dotfiles, tooling, librerías y aplicaciones con despliegues a entornos en la nube), surge la necesidad (planteada en Issue #64) de evaluar la introducción de ramas troncales intermedias de larga duración (como `dev` para desarrollo continuo y `test`/staging para pruebas integradas) antes de consolidar cambios en `main`.

Se requiere determinar la viabilidad técnica de este esquema, su impacto en flujos asistidos por agentes de IA, su ámbito de aplicación (universal vs por tipo de proyecto) y el mecanismo idóneo para su gobierno operativo (Skill vs servidor MCP).

## Impulsores de la Decisión (Decision Drivers)
* **Estabilidad y Confiabilidad en Producción:** Asegurar que el código integrado a `main` esté probado y validado.
* **Prevención de Divergencia y Merge Hell:** Evitar la acumulación de ramas troncales desincronizadas que obliguen a cherry-picks o fusiones conflictivas.
* **Eficiencia de Contexto para Agentes de IA:** Mantener un espacio de estados determinista y predecible que minimice la sobrecarga cognitiva en los prompts de los agentes.
* **Principio de Mínima Intervención (Minimal Blast Radius):** Resolver las necesidades en el nivel de abstracción más bajo posible, evitando sobreingeniería estructural o dependencias innecesarias de runtime.
* **Flexibilidad Arquitectónica según el Tipo de Proyecto:** Distinguir entre proyectos livianos/estáticos (dotfiles, CLI, librerías) y sistemas con infraestructura y ambientes de despliegue físico (web apps, microservicios).

## Opciones Consideradas
* **Opción 1: Gitflow Clásico Universal (`dev` -> `test` -> `main`).**
  * Imponer a todos los repositorios del ecosistema tres ramas troncales de vida infinita, donde las ramas de desarrollo parten de `dev`, se promueven en lote a `test` para pruebas y finalmente pasan a `main`.
  * *Descarte:* Genera severo riesgo de *merge hell* y desfasaje de commits; imposibilita la integración continua (CI) atómica; satura el contexto de los agentes de IA con burocracia de sincronización; e introduce una sobrecarga operativa inútil en repositorios de configuración, tooling y dotfiles.
* **Opción 2: Trunk-Based Development Estricto y Universal (`main` exclusiva).**
  * Mantener `main` como única rama troncal permanente para absolutamente todos los repositorios sin excepción, canalizando todo cambio vía ramas efímeras de issue con validación local previa (Shift-Left).
  * *Evaluación:* Altamente eficiente y estándar para repositorios de dotfiles y librerías, pero insuficiente para proyectos complejos de software que poseen infraestructura real desplegada en la nube conectada a ramas específicas para QA/staging.
* **Opción 3: Modelo Híbrido Contextual con Detección en Configuración de Repositorio (Categoría A vs Categoría B).**
  * Clasificar los repositorios en dos categorías claras:
    * **Categoría A (Compactos / Tooling / Dotfiles / Librerías):** Trunk-Based puro con rama troncal única `main` y ramas efímeras de issue.
    * **Categoría B (Aplicaciones con Despliegues y Ambientes Físicos):** Troncal de integración continua (`dev`) conectada a staging/dev server + troncal de producción (`main`). Las ramas efímeras parten de `dev` y los PRs apuntan a `dev`. La promoción de `dev` a `main` se formaliza vía Release PRs o Tags.
  * La estrategia se define declarativamente por repositorio en su archivo de configuración raíz (`.repo-config.json` o `config.json`).
  * Descarte de servidor MCP: La gobernanza de ramas se delega íntegramente al skill `issue-driven-workflow`, descartando servidores MCP por violar el Minimal Blast Radius.

## Decisión Adoptada
Opción elegida: **"Opción 3"**, estructurando la estrategia bajo las siguientes directivas:

1. **Clasificación Contextual por Repositorio:**
   * **Categoría A (Predeterminada - Trunk-Based Puro):**
     * Aplica a: `Dotfiles-IA-Agents`, utilidades CLI, automatizaciones, scripts y librerías.
     * Rama troncal: Únicamente `main`.
     * Ramas efímeras: `feat/issue-<id>-<slug>` o `fix/issue-<id>-<slug>`.
     * Pruebas: Shift-Left estricto en la rama efímera (linters, pruebas unitarias, `./build.sh check`) antes del commit y PR directo a `main`.
   * **Categoría B (Ambientes de Despliegue Físicos):**
     * Aplica a: Aplicaciones web, servicios backend y sistemas con entornos de infraestructura activos (Dev/QA/Staging vs Producción).
     * Rama troncal de integración: `dev` (recibe el desarrollo continuo y alimenta el ambiente de pruebas).
     * Rama troncal de producción: `main` (código estable desplegado a producción).
     * Ramas efímeras: Se originan desde `dev` y abren PRs hacia `dev`.
     * Promoción a Producción: Se realiza en bloque mediante un **Release Pull Request** (ej. de `dev` a `main` con etiqueta de versión SemVer `vX.Y.Z`). Queda prohibido el cherry-pick aislado o push manual entre ramas troncales.

2. **Detección Declarativa en Configuración de Repositorio:**
   * El agente o herramienta consulta el archivo de configuración del proyecto en la raíz del repositorio (`.repo-config.json` o `config.json`):
     ```json
     {
       "repository_type": "category_a",
       "base_branch": "main"
     }
     ```
   * En ausencia de archivo de configuración o si no se explicita `repository_type`, el sistema asume por defecto **Categoría A** (`base_branch: "main"`), preservando la compatibilidad hacia atrás con todos los repositorios existentes.

3. **Resolución sobre Servidores MCP vs. Skills:**
   * Se determina que no se requiere el desarrollo de un servidor MCP para la gestión de ramas o ciclo de vida de repositorios.
   * La gestión de Git/GitHub es una necesidad de flujo procedural que queda cubierta eficazmente mediante la CLI nativa (`gh` y `git`) y las directivas del skill `issue-driven-workflow` (Nivel 2 de abstracción), evitando dependencias innecesarias de procesos externos.

### Consecuencias
* **Positivas:**
  * Evita la burocracia de ramas innecesarias en repositorios livianos como `Dotfiles-IA-Agents`.
  * Habilita un flujo seguro y ordenado para aplicaciones que cuentan con entornos reales de despliegue en la nube.
  * Mantiene la linealidad del historial y previene el desfasaje descontrolado de commits.
  * Centraliza la gobernanza operativa en el skill `issue-driven-workflow` sin dependencias de servidores MCP.
* **Negativas / Trade-offs:**
  * Los repositorios de Categoría B requieren gestionar el paso formal de promoción (`dev` -> `main`) mediante un Release PR cuando se estabiliza una versión.

### Pros y Contras de las Opciones
#### Opción 1: Gitflow Clásico Universal
* **Pro:** Familiaridad histórica en equipos grandes de desarrollo de software tradicional.
* **Contra:** Merge hell garantizado, inviable para dotfiles, altamente propenso a errores en flujos de agentes autónomos.

#### Opción 2: Trunk-Based Estricto y Universal
* **Pro:** Máxima simplicidad, cero divergencia, mínimo consumo de contexto.
* **Contra:** No contempla las restricciones operativas de proyectos con servidores físicos de staging que requieren validar builds integrados antes de producción.

#### Opción 3: Modelo Híbrido Contextual (Elegida)
* **Pro:** Combina la ligereza de Trunk-Based para dotfiles con la robustez de ramas de integración (`dev`) para proyectos con infraestructura real. Configuración declarativa simple.
* **Contra:** Exige que el skill reconozca la configuración del repositorio para saber qué rama base tomar.
