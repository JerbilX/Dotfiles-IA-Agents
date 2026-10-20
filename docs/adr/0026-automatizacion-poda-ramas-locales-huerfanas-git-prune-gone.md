---
status: accepted
date: 2026-10-20
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0026 - Automatización de Poda de Ramas Locales Huérfanas con git-prune-gone

## Contexto y Planteamiento del Problema

En el flujo de desarrollo guiado por tareas e higiene de Git (formalizado en ADR-0010 y detallado en `skills/issue-driven-workflow/references/branch-lifecycle.md`), tras la fusión de un Pull Request y la sincronización con `git pull --prune --ff-only`, las ramas locales cuyo tracking remoto fue eliminado quedan en estado huérfano (`[gone]`).

Para mantener el árbol local limpio y sin violar los estándares de entorno (prohibición de tuberías `awk | xargs` que rompen el *prefix matching* de seguridad en Antigravity), el protocolo exigía un procedimiento en dos turnos:
1. Inspección pasiva confinada (`git branch --format "%(refname:short) %(upstream:track)"`).
2. Procesamiento cognitivo por parte del LLM en contexto para listar las ramas `[gone]` e invocar de forma mutadora `git branch -d <rama1> <rama2>`.

Esta fricción operativa consumía turnos innecesarios de LLM, introducía latencia acumulativa en el inicio de cada tarea y dependía de la atención del modelo para detectar y podar las ramas zombi.

## Impulsores de la Decisión (Decision Drivers)

* **Reducción de Latencia y Eficiencia Operativa:** Ejecutar la higiene de ramas locales en un único paso atómico al inicio de cada ciclo E2E sin consumir turnos redundantes del LLM.
* **Principio de Mínima Intervención (Minimal Blast Radius - ADR-0017):** Resolver el problema en el nivel más bajo posible (Nivel 1: Tooling determinista) en lugar de inflar directivas o prompts en Nivel 2.
* **Robustez de Sandbox y Prefix Matching:** Preservar la compatibilidad de permisos sin utilizar tuberías (`|`), scripts temporales de parcheo ni subshells.
* **Compatibilidad Multi-Runtime y Cero Dependencias:** Operar de forma idéntica en Antigravity y Claude Code utilizando exclusivamente la biblioteca estándar de Python 3.
* **Salvaguarda de Integridad (Anti-Data Loss):** Evitar la eliminación accidental de código no integrado mediante el uso por defecto de poda segura (`git branch -d`) y omitir con advertencia la rama actualmente activa si estuviera marcada como `[gone]`.

## Opciones Consideradas

* **Opción 1: Mantener el Flujo en Dos Turnos (Status Quo).**
  * *Descarte:* Ineficiente. Consume llamadas de API adicionales y latencia innecesaria en cada tarea despachada.
* **Opción 2: Permitir Pipelines de Terminal (`git branch -vv | awk ... | xargs git branch -d`).**
  * *Descarte:* Inviable. Rompe el *prefix matching* de permisos en sandbox, dispara confirmaciones interactivas al evaluar binarios no autorizados y vulnera los estándares de entorno.
* **Opción 3: CLI Determinista de Nivel 1 (`git-prune-gone`) en Python 3 Estándar.**
  * *Ventaja:* Encapsula la lógica de inspección y eliminación segura en un comando atómico ejecutable en un único paso, con soporte de flags (`--dry-run`, `--json`, `-f`) y formato estructurado.

## Decisión Adoptada

Se adopta la **Opción 3**:

1. **Nivel 1 (Tooling Determinista - `git-prune-gone`):**
   * Creación del ejecutable `skills/issue-driven-workflow/bin/git-prune-gone` en Python 3 estándar.
   * Inspección estructurada mediante `git branch --format="%(HEAD)|%(refname:short)|%(upstream:track)"`.
   * Poda segura mediante llamada atómica a `git branch -d`, con reporte claro de ramas eliminadas o confirmación de árbol limpio.
2. **Nivel 2 (Skills y Protocolos E2E):**
   * Actualización de `skills/issue-driven-workflow/SKILL.md` (Regla de Oro 4 y Fase 2 del Ciclo E2E) y `references/branch-lifecycle.md` para invocar directamente `git-prune-gone`.
3. **Nivel 3 (Configuración y Reglas de Runtime):**
   * Registro del binario en `binaries` de `runtimes/antigravity/config.json` y `runtimes/claude/config.json` para su exposición en `~/.local/bin/git-prune-gone`.
   * Autorización expresa de `git-prune-gone` en `runtimes/antigravity/rules/01-sandbox.md` para ejecución desatendida con `BypassSandbox: true` (requerido por la mutación de `.git/`).

### Consecuencias

* **Positivas:**
  * Eliminación de 1 turno redundante del agente en la Fase 2 de cada tarea guiada por issues.
  * Poda consistente, atómica y segura sin riesgo de romper el sandbox.
  * Soporte nativo para inspección desatendida (`--dry-run`) e interoperabilidad estructurada (`--json`).
* **Negativas / Trade-offs:**
  * Requiere mantener el binario en `skills/issue-driven-workflow/bin/` y asegurar permisos de ejecución (`+x`).

### Pros y Contras de las Opciones

#### Opción 1: Status Quo (Dos Turnos)
* **Pro:** Sin nuevo código ni binarios.
* **Contra:** Latencia recurrente y consumo innecesario de turnos de LLM en cada tarea.

#### Opción 2: Pipelines de Shell
* **Pro:** Una sola línea de bash.
* **Contra:** Destruye el *prefix matching*, bloquea la ejecución autónoma en Antigravity y viola estándares de seguridad.

#### Opción 3: CLI Determinista `git-prune-gone`
* **Pro:** Cumple el Minimal Blast Radius (Nivel 1), seguro, testeable, independiente de librerías externas y compatible multi-runtime.
* **Contra:** Añade un archivo ejecutable al repositorio.
