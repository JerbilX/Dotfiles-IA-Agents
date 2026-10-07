# Ciclo de Vida y Gestión de Repositorios Git / GitHub

- **Detección e Inicialización Local Proactiva:**
  - Cuando el agente esté operando en un workspace donde existan archivos de desarrollo y no exista el directorio `.git`, debe proceder a inicializar el repositorio local con `git init`.
  - Crear el commit inicial respetando estrictamente las políticas de sandbox: escribir el mensaje en `.commit_msg` con la API nativa de archivos y ejecutar `git commit -F .commit_msg`.
  - Garantizar que la rama principal sea `main` (`git branch -M main`).

- **Gate de Confirmación Obligatorio para Remoto (Origin):**
  - El agente tiene **estrictamente prohibido** asumir la subida a GitHub sin confirmación previa del usuario.
  - Una vez creado el commit local, el agente debe preguntar de forma directa:
    > *"He inicializado el repositorio local y creado el primer commit. ¿Deseas que cree el repositorio privado en GitHub y lo suba a origin ahora?"*

- **Ejecución de Creación Remota:**
  - Si el usuario **confirma**: El agente debe ejecutar de forma autónoma el aprovisionamiento y push mediante:
    `gh repo create JerbilX/<nombre-del-directorio> --private --source=. --remote=origin --push`
    *(Sin delegar comandos de consola ni pedirle al usuario que los ejecute manualmente).*
  - Si el usuario **rechaza**: El repositorio permanece exclusivamente bajo control de versiones local hasta nueva orden explícita.
