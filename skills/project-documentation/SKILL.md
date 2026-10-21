---
name: project-documentation
description: >-
  Standardize, structure, and maintain technical project documentation following a pragmatic Diátaxis model. Defines the minimal README.md contract, modular distribution into docs/ (setup, cli/api, architecture), and documentation quality checklists for software repositories. ACTIVATE whenever creating, refactoring, or auditing repository documentation, onboarding guides, or technical references.
---

# Project Documentation and Technical Writing Standard

Guía canónica y operativa para la estructuración, redacción y mantenimiento de documentación técnica en repositorios de software, aplicando el modelo Diátaxis adaptativo y el principio de divulgación progresiva (*Progressive Disclosure*).

---

## 1. Principios Fundamentales

1. **Divulgación Progresiva (*Progressive Disclosure*):**
   El archivo raíz `README.md` es la puerta de entrada ligera, legible y ejecutable para humanos y agentes. No debe saturarse con manuales exhaustivos, árboles completos de archivos ni bitácoras históricas. Los detalles profundos se distribuyen modularmente en `docs/`.
2. **Anti-Rigidez y Adaptabilidad por Tamaño (*Repository Sizing Tiers*):**
   La arquitectura documental debe adaptarse a la escala y naturaleza del proyecto. No se fuerza una fragmentación excesiva en micro-proyectos donde un único archivo es más eficiente, ni se tolera la saturación monolítica en plataformas complejas.
3. **Enfoque Local-First y Navegabilidad Relativa:**
   Toda referencia entre documentos debe resolverse mediante enlaces relativos directos dentro del repositorio (`docs/...`). Se prohíbe depender de wikis externas o servicios en la nube para información esencial del proyecto.
4. **Inmunidad Normativa y Separación de Responsabilidades:**
   La documentación técnica es descriptiva, arquitectónica y operacional. **No define directivas de comportamiento ni órdenes para agentes de IA** (las cuales se reservan exclusivamente a `core/` y `rules/` bajo el estándar `AGENTS.md`).
5. **Erradicación de Backlogs Locales y Bitácoras Informales:**
   Prohibido crear o mantener archivos como `TODO.md`, `backlog.md` o bitácoras `HISTORIAL.md`. La deuda técnica o tareas pendientes se canalizan mediante GitHub Issues e indexación en Projects v2.

---

## 2. Matriz de Adaptabilidad por Repositorio (Sizing Tiers)

Para seleccionar la estructura documental idónea, evalúa la complejidad del repositorio según la siguiente matriz:

| Tier | Perfil del Repositorio | Estructura Documental Mínima | Justificación Técnica |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Scripts simples, micro-utilidades, librerías acotadas (< 500 LOC). | `README.md` único autocontenido ($\le 120$ líneas). | La fragmentación en `docs/` introduce sobre-ingeniería y fricción innecesaria. Un solo documento claro cubre pitch, quickstart y referencia. |
| **Tier 2** | Aplicaciones medianas, servicios backend, herramientas CLI estándar. | `README.md` minimalista + `docs/setup.md` + `docs/cli.md` (o `usage.md`) + `docs/adr/` (si aplica). | Separa el onboarding inmediato del manual operativo y la guía de despliegue, protegiendo el buffer atencional del agente y el lector. |
| **Tier 3** | Plataformas modulares, arquitecturas multi-runtime, infraestructuras complejas (ej. `Dotfiles-IA-Agents`). | `README.md` minimalista + `docs/setup.md` + `docs/cli.md` + `docs/architecture.md` + `docs/adr/`. | Exige modularización estricta: bootstrap aislado, manual de interfaces CLI/API, arquitectura conceptual desacoplada y decisiones MADR. |

---

## 3. Contrato Canónico de `README.md` (Tiers 2 y 3)

En repositorios Tier 2 y Tier 3, el archivo raíz `README.md` debe cumplir estrictamente con los siguientes límites y estructura:

### 3.1 Presupuesto Cuantitativo
- **Líneas:** $\le 70$ líneas.
- **Palabras:** $\le 500$ palabras (umbral estático de advertencia: `MAX_README_WORDS=600`).
- **Tiempo de Lectura:** $< 2$ minutos para humanos; $< 700$ tokens para agentes de IA.

### 3.2 Estructura Obligatoria en 6 Bloques
1. **Header & Badges:** Título oficial del proyecto, badges relevantes de estado (build/CI status, versión, tecnologías soportadas) y un subtítulo de una sola frase que resuma la función central.
2. **Resumen Ejecutivo (*Elevator Pitch*):** Exactamente **un párrafo denso** (3-5 líneas) que responda qué es el proyecto, su propuesta de valor diferencial y su enfoque arquitectónico.
3. **Arquitectura Esencial (Diagrama Conceptual):** Esquema conceptual compacto de alto nivel (diagrama Mermaid o bloque de texto/ASCII sintético de 4 a 6 líneas) mostrando el flujo o desacoplamiento del sistema. **Prohibido incluir árboles ASCII exhaustivos de archivos.**
4. **Puesta en Marcha Determinista (*Quickstart*):** Bloque copiable de 3 a 5 comandos atómicos y verificados para clonar, configurar e iniciar el proyecto inmediatamente en una máquina estándar.
5. **Tabla Sintética de Comandos / Interfaces:** Resumen tabular conciso (1 fila por subcomando o interfaz principal) con descripción en una línea y enlace explícito a la referencia completa en `docs/cli.md` o `docs/usage.md`.
6. **Mapa de Navegación Documental y Convenciones:**
   - Enlaces relativos a los documentos especializados en `docs/`.
   - Máximo 3 viñetas (*bullet points*) con las convenciones operativas esenciales del repositorio (ej. flujo de compilación, gestión de ADRs, ramas/PRs).

---

## 4. Estructura y Contrato Modular de `docs/` (Modelo Diátaxis)

La carpeta `docs/` implementa una división pragmática basada en el estándar Diátaxis:

```
docs/
├── setup.md          # [How-To / Bootstrap] Precondiciones, instalación OS, PATH y troubleshooting
├── cli.md            # [Reference] Manual exhaustivo de CLI/API, subcomandos, variables y códigos
├── architecture.md   # [Explanation] Arquitectura multi-componente, contratos, esquemas y extensibilidad
└── adr/              # [Decisions] Architectural Decision Records bajo estándar MADR (adr-manager)
```

### 4.1 `docs/setup.md` (How-To / Guía de Instalación y Entorno)
- **Propósito:** Conducir al desarrollador u operador desde una máquina vacía hasta un entorno completamente funcional.
- **Secciones Requeridas:**
  1. *Precondiciones del Sistema:* Versiones mínimas de runtime, dependencias del SO y herramientas externas.
  2. *Variables de Entorno y Configuración de Shell:* Exportación de `$PATH`, variables requeridas y persistencia en `.bashrc`/`.zshrc`.
  3. *Flujo de Aprovisionamiento Paso a Paso:* Comandos detallados de bootstrap, clonado, compilación inicial y creación de symlinks o artefactos.
  4. *Resolución de Problemas Frecuentes (*Troubleshooting*):* Diagnóstico de fallos típicos (errores de permisos, dependencias faltantes, symlinks rotos).
  5. *Procedimiento de Limpieza o Desinstalación:* Pasos limpios y reversibles para purgar el entorno.

### 4.2 `docs/cli.md` (o `docs/usage.md`) (Reference / Referencia Técnica de Interfaces)
- **Propósito:** Servir de manual de consulta exhaustivo para usuarios, desarrolladores y agentes que necesitan operar las interfaces del proyecto.
- **Secciones Requeridas:**
  1. *Sintaxis General de Invocación:* Firma de comandos, subcomandos y flags globales.
  2. *Catálogo Exhaustivo de Subcomandos / Módulos:* Cada subcomando documentado con: descripción, sintaxis, flags admitidos, ejemplos prácticos de uso y comportamiento ante fallos.
  3. *Variables de Entorno de Control:* Tabla con variables, valores predeterminados y propósito.
  4. *Códigos de Salida y Manejo de Errores:* Significado de cada código devuelto por los procesos (`0`, `1`, `2`, etc.).

### 4.3 `docs/architecture.md` (Explanation / Arquitectura y Diseño del Sistema)
- **Propósito:** Explicar los fundamentos técnicos, la visión de diseño, el flujo de datos y los contratos que gobiernan el sistema.
- **Secciones Requeridas:**
  1. *Filosofía y Principios de Diseño:* Desacoplamiento, patrones arquitectónicos adoptados y límites del sistema.
  2. *Mapa Modular y Organización de Código:* Árbol estructural de directorios detallado y responsabilidades de cada módulo.
  3. *Esquemas de Datos y Manifiestos:* Especificación de esquemas JSON, contratos de comunicación o modelos de datos.
  4. *Guía de Extensibilidad:* Procedimiento paso a paso para incorporar nuevas extensiones, plugins o módulos sin alterar el núcleo.

### 4.4 `docs/adr/` (Decisions / Decisiones de Arquitectura)
- **Gobernanza Exclusiva:** Monopolio absoluto del skill `adr-manager` bajo el estándar MADR (`NNNN-titulo.md`). `project-documentation` únicamente enlaza e indexa esta carpeta.

---

## 5. Delimitación Estricta de Fronteras

| Skill / Área | Responsabilidad Primaria | Límite con `project-documentation` |
| :--- | :--- | :--- |
| **`project-documentation`** | Arquitectura de información, contrato de `README.md`, redacción de `docs/` y plantillas Diátaxis. | No administra decisiones arquitectónicas individuales ni ejecuta workflows de Git. |
| **`adr-manager`** | Monopolio sobre creación, numeración correlativa, transiciones y archivo de ADRs en `docs/adr/`. | `project-documentation` solo referencia `docs/adr/` en el mapa documental; **prohibido modificar o reemplazar el estándar MADR**. |
| **`issue-driven-workflow`** | Ciclo de vida de tareas, transiciones en GitHub Projects v2, ramas efímeras y Pull Requests. | `project-documentation` define el contenido documental; el flujo de entrega se rige por `issue-driven-workflow`. |
| **`core/` y `rules/`** | Directivas de comportamiento obligatorias e invariantes de ejecución del agente. | La documentación técnica es descriptiva para usuarios y agentes; **no contiene órdenes normativas para el System Prompt**. |

---

## 6. Checklist de Verificación y Calidad Documental

Antes de finalizar cualquier tarea de documentación o abrir un Pull Request, valida los siguientes puntos:

- [ ] **Presupuesto Cuantitativo:** `README.md` tiene $\le 70$ líneas y $\le 500$ palabras (verificado con `wc -l` y `wc -w`).
- [ ] **Quickstart Probado:** Los comandos del Quickstart son atómicos y fueron probados empíricamente en el entorno.
- [ ] **Integridad de Enlaces:** Todos los enlaces relativos hacia `docs/` existen en el sistema de archivos (sin rutas rotas ni referencias a archivos inexistentes).
- [ ] **Cero Contenido Normativo:** No se redactaron órdenes o imperativos hacia agentes en los archivos Markdown de `docs/`.
- [ ] **Separación Diátaxis:** No hay instrucciones de instalación mezcladas en `docs/architecture.md`, ni descripciones conceptuales extensas en `docs/setup.md`.
- [ ] **Validación Estática:** `./build.sh check` ejecuta con 0 errores y 0 advertencias sobre documentación.

---

## 7. Catálogo de Plantillas Operativas (`resources/`)

El skill incluye plantillas listas para su uso en proyectos nuevos o en refactorizaciones dentro de `skills/project-documentation/resources/`:

- [`template-readme-tier1.md`](resources/template-readme-tier1.md): Plantilla para micro-utilidades y proyectos pequeños (Tier 1).
- [`template-readme-tier2-3.md`](resources/template-readme-tier2-3.md): Plantilla de README minimalista para proyectos medianos y grandes (Tier 2 y 3).
- [`template-setup.md`](resources/template-setup.md): Plantilla de How-To para instalación, `$PATH` y bootstrap.
- [`template-cli.md`](resources/template-cli.md): Plantilla de Reference para manuales técnicos de CLI y APIs.
- [`template-architecture.md`](resources/template-architecture.md): Plantilla de Explanation para visión técnica, esquemas y extensibilidad.
