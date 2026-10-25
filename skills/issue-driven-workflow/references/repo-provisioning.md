# Referencia: Aprovisionamiento y Ciclo de Vida de Repositorios Remotos

Protocolo determinista para inicializar repositorios locales y aprovisionar repositorios remotos privados en GitHub.

---

## 1. Detección e Inicialización Local Proactiva

- Cuando el agente esté operando en un workspace donde existan archivos de desarrollo y no exista el directorio `.git`, debe proceder autónomamente a inicializar el repositorio local:
  ```bash
  git init
  ```
  *(Ejecutado con `BypassSandbox: true` desde el primer intento por mutación de `.git/`).*
- Garantizar que la rama principal sea `main`:
  ```bash
  git branch -M main
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Preparar los archivos para el commit inicial:
  ```bash
  git add .
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Redactar el mensaje inicial en `.commit_msg` con `write_to_file` y crear el commit inicial:
  ```bash
  git commit -F .commit_msg
  ```
  *(Ejecutado con `BypassSandbox: true`).*
- Limpiar inmediatamente el archivo temporal (`BypassSandbox: false` obligatorio, confinado en sandbox estándar):
  ```bash
  rm -f .commit_msg
  ```

---

## 2. Gate de Confirmación Obligatorio para Remoto (Origin)

- El agente tiene **estrictamente prohibido** asumir la subida a GitHub sin confirmación previa del usuario.
- Una vez creado el commit local inicial, el agente debe preguntar de forma directa:
  > *"He inicializado el repositorio local y creado el primer commit. ¿Deseas que cree el repositorio privado en GitHub y lo suba a origin ahora?"*

---

## 3. Ejecución Determinista de Creación Remota y Enlace (Tras Confirmación)

Si el usuario **confirma**:
1. Ejecutar de forma autónoma el aprovisionamiento y push mediante:
   ```bash
   gh repo create <nombre-del-directorio> --private --source=. --remote=origin --push
   ```
   *(Ejecutado con `BypassSandbox: true`; crea el repositorio bajo la cuenta del usuario actual sin delegar comandos ni requerir intervención manual).*
2. Inmediatamente después, configurar la eliminación automática de ramas fusionadas en el repositorio remoto:
   ```bash
   gh repo edit --delete-branch-on-merge
   ```
   *(Ejecutado con `BypassSandbox: true` sobre el repositorio actual).*
3. Si el entorno cuenta con permisos para Projects (`gh project`), proceder a enlazar el repositorio al tablero central:
   ```bash
   gh project link <project_number> --owner <project_owner> --repo <nombre-del-directorio>
   ```
   *(Donde `<project_number>` y `<project_owner>` se resuelven desde `.repo-config.json`, aplicando `1` y `@me` por defecto).*

Si el usuario **rechaza**:
- El repositorio permanece exclusivamente bajo control de versiones local hasta nueva orden explícita.

---

## 4. Principio Git/GitHub-First para Interacción y Contexto de Repositorios

El agente interactúa con el ecosistema de repositorios según las necesidades de la tarea bajo las siguientes directivas:

1. **La Fuente Canónica es Siempre Git / GitHub:**
   - Ante cualquier tarea que requiera conocer, descubrir, listar o validar repositorios del usuario u organización actual, el agente debe consultar forzosamente los canales de Git y GitHub CLI (`gh repo list`, `gh repo view`, `git remote`).
   - Para listar repositorios del usuario u organización activa:
     ```bash
     gh repo list --limit 30 --json name,description,isPrivate
     ```
     *(Ejecutado con `BypassSandbox: true` por requerir acceso de red. Si se requiere una organización o propietario específico, utilizar `gh repo list <owner>`).*

2. **Prohibición de Reconocimiento Físico en Disco:**
   - La interacción con repositorios nunca debe inducir salidas del workspace ni exploraciones en el sistema de archivos del host (`list_dir`, `find_by_name`, `ls` en carpetas hermanas o `..`).
   - El agente no debe inferir ni inspeccionar si un repositorio está clonado localmente a menos que opere dentro del workspace activo correspondiente.

3. **Desacoplamiento en Fases de Diseño y Arquitectura:**
   - En tareas de arquitectura, diseño, RFCs o ADRs que contemplen integración multi-repo, los contratos y rutas deben diseñarse de forma agnóstica (vía configuración, parámetros o variables como `WORKSPACE_ROOT`), resolviendo la interacción mediante APIs o CLI sin requerir inspección física del host.
