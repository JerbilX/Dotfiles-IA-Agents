---
status: accepted
date: 2026-11-10
decision-makers: [JerbilX, Antigravity]
supersedes: []
superseded-by: []
---

# 0055 - Estandarización de Hook Post-Merge Global para Auto-Despliegue

## Contexto y Planteamiento del Problema

Durante el ciclo de desarrollo en repositorios con servicios locales o tooling de sistema (ej. `JerbilX/ESOChatLogSvc`), tras la fusión remota y cierre de un Pull Request (`gh pr merge`) o sincronización (`git pull`), el entorno local requiere ejecutar un paso de despliegue (`./build.sh deploy`, `install.py --upgrade`, reinicio de unidades `systemd --user`, etc.) para actualizar los binarios o servicios activos en el sistema operativo del host.

Debido al confinamiento estricto de sandbox de los agentes de IA (`BypassSandbox: false`, ADR-0001, ADR-0011), los agentes no tienen acceso a sockets de usuario (`systemctl --user`, D-Bus) ni a rutas fuera del workspace activo. Consecuentemente, el agente no puede ni debe ejecutar comandos de despliegue del host durante sus turnos interactivos.

La solución desacoplada consiste en delegar la ejecución del despliegue en un hook nativo de Git (`post-merge`), el cual se ejecuta en el entorno del host fuera del sandbox de forma desatendida. Sin embargo, configurar hooks manualmente en `.git/hooks/` o `.githooks/` en cada repositorio no escala y se pierde en entornos vírgenes o clones nuevos si no se automatiza globalmente desde `Dotfiles-IA-Agents`.

## Impulsores de la Decisión (Decision Drivers)

* **Confinamiento de Sandbox:** El agente no debe mutar el host ni requiere privilegios elevados; la ejecución del despliegue debe ocurrir exclusivamente en el host nativo.
* **Cero Falsos Positivos:** El mecanismo no debe disparar despliegues accidentales ni fallar en repositorios generales que contengan `build.sh` u otros scripts pero no contemplen despliegue.
* **Respeto a Configuraciones Locales:** Repositorios con hooks locales existentes (`.githooks/` o `.git/hooks/`) no deben ser anulados o rotos por la configuración global.
* **Desatendido y Silencioso:** Ejecución no intrusiva tras `gh pr merge` o `git pull` en ramas base (`main`, `master`, `dev`), con salida clara y sin alterar el código de salida de Git.

## Opciones Consideradas

* **Opción 1: Plantilla Global de Git (`init.templateDir`).** Configurar una plantilla con un hook `post-merge` genérico que Git copia a `.git/hooks/` en cada `git init` o `git clone`.
* **Opción 2: Hook Global (`core.hooksPath`) con Detección Heurística (`./build.sh deploy`).** Configurar `core.hooksPath` global a `~/.config/git/hooks/` y ejecutar `./build.sh deploy` en cualquier repo que contenga `build.sh`.
* **Opción 3: Hook Global (`core.hooksPath`) con Contrato Opt-In vía `.repo-config.json` y Delegación Local.** Configurar `core.hooksPath` global apuntando a `~/.config/git/hooks/post-merge`, el cual:
  1. Verifica si la rama activa es una rama de integración base (`main`, `master`, `dev`).
  2. Delega a hooks locales existentes (`.githooks/post-merge` o `.git/hooks/post-merge.local`).
  3. Lee `.repo-config.json` en la raíz del repo y, si declara explícitamente `deployCommand`, ejecuta dicho comando.

## Decisión Adoptada

Opción elegida: **"Opción 3: Hook Global (`core.hooksPath`) con Contrato Opt-In vía `.repo-config.json` y Delegación Local"**, porque:
1. **Garantiza cero falsos positivos:** La clave `deployCommand` en `.repo-config.json` (ADR-0034) establece un contrato explícito y agnóstico de lenguaje/herramienta (soporta `./build.sh deploy`, `python3 install.py --upgrade`, etc.) sin asumir que todo `build.sh` admite despliegue.
2. **Centralización y mantenibilidad:** Se gestiona mediante symlink desde `Dotfiles-IA-Agents` (`core/git/hooks/post-merge` -> `~/.config/git/hooks/post-merge`), actualizándose en todos los repos del host inmediatamente sin requerir re-inicializar plantillas.
3. **Encadenamiento limpio:** No eclipsa los hooks locales de repositorios que ya utilizan hooks propios (como el propio `Dotfiles-IA-Agents`), ejecutándolos en cadena.

### Consecuencias

* **Positivas:**
  * Auto-despliegue 100% desatendido tras `gh pr merge` y `git pull` en el host fuera del sandbox.
  * Extensible a cualquier repositorio administrado añadiendo `"deployCommand": "..."` en `.repo-config.json`.
  * Preserva la integridad de repositorios sin auto-despliegue (overhead despreciable ~1ms, salida limpia).
* **Negativas / Trade-offs:**
  * Si un repositorio define un `core.hooksPath` local en `.git/config` (como hace `Dotfiles-IA-Agents` con `.githooks`), la configuración local de Git tiene precedencia sobre la global. En dichos repositorios con `core.hooksPath` local, el hook del repositorio debe incluir la llamada correspondiente o el repositorio debe depender de su propio hook.

### Pros y Contras de las Opciones

#### Opción 1: `init.templateDir`
* **Pro:** Estándar nativo de Git; no sobreescribe `core.hooksPath`.
* **Contra:** Inerte en repositorios ya clonados; los cambios futuros al hook no se propagan a repositorios existentes sin `git init` manual.

#### Opción 2: Hook Global con Detección Heurística
* **Pro:** Aplica automáticamente a todos los repositorios.
* **Contra:** Alto riesgo de falsos positivos en proyectos que posean `build.sh` sin target `deploy`, arrojando errores o mensajes de uso innecesarios en cada `git pull`.

#### Opción 3: Hook Global con Contrato Opt-In vía `.repo-config.json`
* **Pro:** Preciso, desacoplado de la tecnología del proyecto, centralizado y compatible con repositorios existentes y nuevos.
* **Contra:** Requiere que el repositorio administrado declare `.repo-config.json` con la propiedad `deployCommand`.
