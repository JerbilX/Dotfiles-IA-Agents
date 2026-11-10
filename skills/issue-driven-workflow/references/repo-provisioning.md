# Referencia: Aprovisionamiento y Ciclo de Vida de Repositorios Remotos

Protocolo determinista para inicializar repositorios locales y aprovisionar repositorios remotos privados en GitHub.

---

## 1. Detección e Inicialización Local Proactiva

- Cuando el agente esté operando en un workspace donde existan archivos de desarrollo y no exista el directorio `.git`, debe proceder autónomamente a inicializar el repositorio local:
  ```bash
  git init
  ```
- Garantizar que la rama principal sea `main`:
  ```bash
  git branch -M main
  ```
- Preparar los archivos para el commit inicial:
  ```bash
  git add .
  ```
- Redactar el mensaje inicial en `.commit_msg` mediante herramientas nativas de archivos y crear el commit inicial:
  ```bash
  git commit -F .commit_msg
  ```
- Limpiar el archivo temporal:
  ```bash
  rm -f .commit_msg
  ```

---

## 2. Gate de Confirmación para Remoto (Origin)

- Prohibido asumir la subida a GitHub o la creación remota sin confirmación previa del usuario.
- Una vez creado el commit local inicial, el agente debe preguntar de forma directa:
  > *"He inicializado el repositorio local y creado el primer commit. ¿Deseas que cree el repositorio privado en GitHub y lo suba a origin ahora?"*

---

## 3. Ejecución Determinista de Creación Remota y Enlace (Tras Confirmación)

Si el usuario **confirma**:
1. Ejecutar de forma autónoma el aprovisionamiento y push mediante:
   ```bash
   gh repo create <nombre-del-directorio> --private --source=. --remote=origin --push
   ```
   *(Crea el repositorio bajo la cuenta del usuario actual).*
2. Inmediatamente después, configurar la eliminación automática de ramas fusionadas en el repositorio remoto:
   ```bash
   gh repo edit --delete-branch-on-merge
   ```
3. Si el entorno cuenta con permisos para Projects (`gh project`), proceder a enlazar el repositorio al tablero central:
   ```bash
   gh project link <project_number> --owner <project_owner> --repo <nombre-del-directorio>
   ```
   *(Donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json`, aplicando `1` y `@me` por defecto).*

### 3.1 Configuración de Auto-Despliegue Post-Merge (ADR-0055)

En repositorios con servicios del sistema o tooling local (ej. unidades systemd, demonios o ejecutables locales) que requieran actualización desatendida en el host tras fusionar un PR:

1. Declarar la clave opcional `deployCommand` en `.repo-config.json`:
   ```json
   {
     "projectNumber": 1,
     "projectOwner": "@me",
     "deployCommand": "./build.sh deploy"
   }
   ```
2. El hook global `post-merge` de Git configurado por los dotfiles ejecutará el comando en el entorno del host (fuera del sandbox del agente) tras cada `gh pr merge` o `git pull` en ramas base (`main`, `master`, `dev`). Si el archivo o la clave no existen, el hook finaliza silenciosamente.

Si el usuario **rechaza**:
- El repositorio permanece exclusivamente bajo control de versiones local hasta nueva orden explícita.

---

## 4. Principio Git/GitHub-First para Interacción y Contexto de Repositorios

El agente interactúa con el ecosistema de repositorios según las necesidades de la tarea bajo las siguientes directivas:

1. **La Fuente Canónica es Siempre Git / GitHub:**
   - Ante cualquier tarea que requiera conocer, descubrir, listar o validar repositorios del usuario u organización actual, consultar los canales de Git y GitHub CLI (`gh repo list`, `gh repo view`, `git remote`).
   - Para listar repositorios del usuario u organización activa:
     ```bash
     gh repo list --limit 30 --json name,description,isPrivate
     ```
     *(Si se requiere una organización o propietario específico, utilizar `gh repo list <owner>`).*

2. **Límites de Workspace y Exploración:**
   - No realizar búsquedas ni exploraciones en el sistema de archivos fuera del workspace activo (listado o búsqueda de archivos en carpetas hermanas o `..`).
   - No inferir ni inspeccionar repositorios locales externos; resolver la interacción mediante APIs o CLI de GitHub.

3. **Desacoplamiento en Fases de Diseño y Arquitectura:**
   - En tareas de arquitectura, diseño, RFCs o ADRs que contemplen integración multi-repo, los contratos y rutas deben diseñarse de forma agnóstica (vía configuración, parámetros o variables como `WORKSPACE_ROOT`), resolviendo la interacción mediante APIs o CLI sin requerir inspección física del host.

---

## 5. Aprovisionamiento de Módulos de Dominio Especializado (`agent-module`) (ADR-0041)

Para optimizar el presupuesto basal de tokens en el prompt inicial de proyectos generales, los skills de dominio especializado y sus servidores MCP asociados están confinados fuera del catálogo global. Su activación se realiza a nivel de workspace con el CLI `agent-module`:

1. **Activación Asistida On-Demand:**
   - **Vía Pedido Explícito:** Si el usuario solicita habilitar un dominio (ej. *"activa el soporte de eso en este proyecto"*), el agente ejecuta en el workspace actual:
     ```bash
     agent-module enable eso
     ```
   - **Vía Detección Proactiva:** Si el agente detecta archivos indicadores de dominio (ej. `## APIVersion:` o archivos `.addon` en ESO) en un repositorio sin el módulo activo, ofrece su activación con un gate directo:
     > *"He detectado que este proyecto es un addon de ESO. ¿Deseas que active el módulo de dominio `eso` para habilitar el skill `eso-addon-development` y el servidor MCP?"*
     Tras confirmación afirmativa, ejecuta `agent-module enable eso`.

2. **Jerarquía Determinista de Invocación y Fallback:**
   Ante la activación de un módulo, seguir estrictamente la siguiente jerarquía de 3 niveles:
   1. **Vía Canónica:** Invocación directa del CLI en `$PATH`:
      ```bash
      agent-module enable <modulo>
      ```
   2. **Vía Fallback:** Si no se encuentra en `$PATH`, invocar la ruta determinista del runtime activo:
      - Antigravity: `python3 ~/.gemini/config/skills/issue-driven-workflow/bin/agent-module enable <modulo>`
      - Claude Code: `python3 ~/.claude/skills/issue-driven-workflow/bin/agent-module enable <modulo>`
   3. **Freno Obligatorio (Stop & Ask):** Prohibido taxativamente ejecutar barridos masivos o búsquedas en el anfitrión (`find /`, `find $HOME`, `grep`). Detenerse de inmediato y emitir comando terminal-ready (`cd <dotfiles> && ./build.sh all`) u ofrecer andamiaje estático directo mediante herramientas nativas de archivos.

3. **Operaciones del Ciclo de Vida:**
   - Consultar módulos disponibles: `agent-module list`.
   - Consultar estado local: `agent-module status`.
   - Desactivar y podar: `agent-module disable <modulo>`.

