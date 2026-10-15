---
status: accepted
date: 2026-10-07
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0001 - Blindaje de Sandbox y Gestión de Permisos de Git

## Contexto y Planteamiento del Problema
En sesiones iniciales de desarrollo con agentes de IA, se detectó una vulnerabilidad de aislamiento donde un agente eludió el sandbox para acceder a rutas externas al workspace (`/mnt/...`). Esto ocurrió porque el sistema, ante un fallo de sandbox, sugirió automáticamente elevar permisos con `BypassSandbox: true`, lo cual el agente acató por encima de las directivas de seguridad. Asimismo, se detectó fricción técnica al compilar directivas mediante `./build.sh` y al ejecutar comandos locales de git debido a bloqueos a nivel de sistema operativo (`.git/index.lock` en modo de solo lectura).

## Impulsores de la Decisión (Decision Drivers)
* **Aislamiento Estricto:** Evitar fugas de contexto o alteraciones no autorizadas fuera del workspace del proyecto.
* **Idempotencia y Fluidez:** Permitir la compilación local de directivas sin requerir elevación manual continua.
* **Determinismo Operativo:** Prohibir que los agentes adopten sugerencias automáticas del entorno que contradigan directivas de seguridad.

## Opciones Consideradas
* **Opción 1:** Permitir bypass indiscriminado ante cualquier sugerencia del sistema.
* **Opción 2:** Blindar el sandbox prohibiendo el bypass en utilidades de sistema, otorgar excepción controlada exclusivamente para la suite de git (`index.lock` y operaciones remotas), y diseñar `./build.sh` de forma idempotente para ejecución sin privilegios.

## Decisión Adoptada
Opción elegida: **"Opción 2"**, porque garantiza la seguridad del sistema operativo impidiendo accesos arbitrarios fuera del workspace, a la vez que desbloquea la operatividad esencial de control de versiones y compilación de directivas.

### Consecuencias
* **Positivas:**
  * Se elimina el riesgo de fuga o contaminación hacia particiones y rutas del sistema operativo.
  * El agente ignora obligatoriamente sugerencias automáticas de elevación para utilidades de consola (`ls`, `cat`, etc.).
  * El build y la gestión de git operan de manera determinista y predecible.
* **Negativas / Trade-offs:**
  * Requiere autorización explícita de `BypassSandbox: true` para operaciones de git que interactúen con `.git/` bloqueado o con servicios de red remotos.
