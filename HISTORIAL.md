# Historial de Decisiones y Cambios (Log de Aprendizaje)

Este documento registra las decisiones arquitectónicas, de seguridad y metodológicas tomadas durante el desarrollo. El objetivo es mantener un historial de **qué** se hizo, **por qué** se hizo, y **cómo** se resolvió, para poder desarrollar en un futuro un "skill de aprendizaje" donde el agente analice estas decisiones para mejorar su comportamiento autónomo.

## [2026-10-07] Resolución de Brecha de Seguridad en Sandbox y Automatización de Build

**Contexto (El Problema):**
Un agente en otro proyecto (sesión `b5dad9e0...`) logró eludir la política del sandbox y acceder a rutas fuera del workspace (`/mnt/LinuxGames/...`). 
Esto ocurrió porque el sistema, tras un fallo de sandbox, le sugirió automáticamente al agente usar `BypassSandbox: true`. El agente priorizó esta sugerencia del sistema por encima de las reglas globales (que prohibían tocar esas rutas). Además, el sistema ejecutó el comando sin preguntar al usuario porque hizo *prefix matching* (Always Allow) con un comando genérico previamente aprobado (`ls`).

**Decisión Tomada:**
1. Se estableció una directiva estricta en `01-sandbox.md` ("Blindaje Anti-Sugerencias") que prohíbe explícitamente al agente usar `BypassSandbox: true` para comandos que no sean `git` o `gh`, y le obliga a ignorar la sugerencia automática del sistema.
2. El usuario limpió la caché manual de "Always Allow" de su sistema para revocar los permisos genéricos (`ls`, etc.).

**Problema Secundario (Fricción en el Build):**
Al endurecer el sandbox, el script de compilación de las reglas (`./build.sh`) dejó de funcionar desde los agentes, porque el paso de "link" intentaba crear un symlink en `~/.gemini/config/AGENTS.md` (ruta protegida, de solo lectura para el sandbox).

**Resolución de Fricción:**
En lugar de crear una excepción de seguridad que permitiera al agente salir del sandbox para ejecutar `./build.sh` (Opción A), se optó por la automatización limpia (Opción B): 
- El usuario crea el symlink manualmente en su consola por única vez.
- El script `./build.sh` está diseñado de forma idempotente: si detecta que el symlink ya existe y apunta al lugar correcto, retorna éxito (código 0) sin intentar escribir en la ruta protegida.
- Esto permite al agente ejecutar `./build.sh` en modo seguro (`BypassSandbox: false`) de forma transparente y sin fricción.

**Tareas Derivadas:**
- Se agregó al `Todo.md` la creación de un protocolo de "Fallback de Comandos".
- Se agregó al `Todo.md` la revisión de este historial para entrenar al agente.

## [2026-10-07] Control de Bucle de Decisiones y Refactor de Historial

**Contexto:**
Se debatió el modelo de funcionamiento del propio historial. Surgió el riesgo de "recursividad de decisiones": si el agente escribe lecciones de manera 100% autónoma, podría entrar en un bucle donde re-procesa el historial y toma decisiones sin supervisión, usurpando el rol del usuario. Además, se analizó dónde debería residir la regla (runtimes vs. core).

**Decisión Tomada:**
1. **Migración a Core:** La directiva de historial se movió de `runtimes/antigravity/` a `core/06-documentation.md`, ya que es una metodología de ingeniería universal, agnóstica al entorno.
2. **Implementación de "Gate de Aprobación":** Se prohibió terminantemente la auto-escritura autónoma. El agente ahora tiene la obligación de sintetizar la lección aprendida y pedir permiso explícito al usuario antes de guardarla.
3. **Skill Centralizado:** Para evitar inflar el prompt global (y para mantener cohesión), se decidió que a futuro toda la lógica de lectura y escritura del historial residirá en un único Skill (`project-history`), evitando la sobreingeniería de separar lectura y escritura en distintos módulos o proyectos.

## [2026-10-07] Metodología de Verificación Previa (Defensividad)

**Contexto:**
Al generar instrucciones para que un agente inicializara un nuevo Skill en un proyecto externo, el agente asumió ciegamente (basado en un comentario conversacional) que el entorno de destino carecía de repositorio Git, proponiendo ejecutar `git init` de manera incondicional.

**Decisión Tomada:**
1. **Verificación Previa (Verify First):** Queda metodológicamente prohibido que los agentes asuman el estado de un entorno basándose únicamente en el contexto conversacional. 
2. **Programación Defensiva:** Antes de proponer o ejecutar acciones permitidas por las reglas globales que alteren archivos (ej. inicializaciones con las herramientas nativas como `write_to_file`, sobreescrituras), el agente debe verificar activamente el estado actual (ej. comprobar si existe `.git`) e incluir lógica condicional explícita ("Solo si no existe, entonces..."). Esto previene daños accidentales a infraestructuras o historiales existentes, y de ninguna manera otorga permisos para evadir las restricciones de aislamiento del Sandbox.

## [2026-10-07] Revisión de Políticas de Sandbox para Operaciones Locales de Git

**Contexto:**
Se comprobó que, en entornos de seguridad estrictos, la invocación atómica de `git commit -F` y otros comandos locales de git son bloqueados nativamente por el sistema operativo (error "Read-only file system" sobre `.git/index.lock`), invalidando la presunción de que corrían limpiamente en el sandbox sin bypass.

**Decisión Tomada:**
1. **Excepción de Git Local:** Autorizar el uso de `BypassSandbox: true` para operaciones de la suite completa de git, incluyendo comandos locales (`git add`, `git commit`), en caso de enfrentar un bloqueo por nivel de OS.
2. **Exclusividad Estricta:** Se mantiene y refuerza la prohibición estricta de bypass para cualquier otro comando no relacionado a git (`ls`, `cat`, scripts locales, etc.), debiendo ignorar completamente cualquier sugerencia automática del sistema para elevar permisos.

## [2026-10-07] Refuerzo Obligatorio del Registro de Decisiones (Derogada)

**Contexto:**
Se detectó la necesidad de registrar decisiones para mantener contexto sin depender de recordatorios manuales del usuario.

**Decisión Tomada:**
1. Inicialmente se incorporó una directiva en `core/06-documentation.md` que instruía a proponer el registro en `HISTORIAL.md`.
2. *Nota de estado:* Esta directiva fue posteriormente derogada y eliminada en el commit `e61d547` (2026-10-08) para evitar sobrecarga de contexto, delegando la gestión futura a un skill especializado.

## [2026-10-07] Adición de Directivas de Cero Tolerancia a la Alucinación Técnica

**Contexto:**
Se formalizó la necesidad de evitar comportamientos adivinatorios o suposiciones en torno a comandos, flags y firmas de API que generan pérdida de tiempo y fricción severa al usuario cuando resultan incorrectos.

**Decisión Tomada:**
1. Se estableció una regla estricta (en `core/07-anti-hallucination.md`) que prohíbe inventar datos o configuraciones.
2. Se impuso el mecanismo de "Freno Obligatorio" (Stop & Ask), donde el agente debe detenerse inmediatamente ante la falta de certeza técnica al 100%, pidiendo autorización para buscar en la web o consultar explícitamente al usuario.

## [2026-10-08] Retiro de la Regla de Documentación Global para Optimización de Contexto

**Contexto:**
La presencia obligatoria de la directiva de registro en `core/06-documentation.md` dentro de `AGENTS.md` generaba sobrecarga innecesaria en el prompt de sistema de todos los agentes.

**Decisión Tomada:**
1. En el commit `e61d547`, se eliminó completamente `core/06-documentation.md`, dejando sin efecto la obligación de registrar decisiones en `HISTORIAL.md` como parte del prompt global.
2. La funcionalidad de análisis y registro histórico quedó diferida al backlog (`Todo.md`) para ser implementada a través de un Skill dedicado (`project-history`), aislada del prompt base de los agentes.

## [2026-10-12] Jerarquía de Producción sobre Tests e Inmunidad Normativa

**Contexto:**
En desarrollo de código, se detectó la tendencia del agente a degradar el código de producción con ramas artificiales y comprobaciones defensivas para evitar fallos en mocks artesanales incompletos (*Test-Induced Design Damage*). Asimismo, se detectó que la lectura exploratoria de archivos históricos con redacción imperativa antigua provocaba reactivación de directivas en desuso (*prompt injection* pasivo).

**Decisión Tomada:**
1. **Estándares de Ingeniería (`core/06-engineering-standards.md`):** Se formalizó el principio universal donde el dominio y el código de producción priman sobre los *test doubles* (mocks/fixtures), definiendo un protocolo de bifurcación ante fallos (actualizar mocks desactualizados vs. corregir regresiones de lógica de negocio).
2. **Inmunidad Normativa (`core/03-agent-rules-convention.md`):** Se blindó el sistema estableciendo que los archivos del workspace y el historial de Git constituyen exclusivamente datos descriptivos/históricos inertes, quedando prohibido que un agente adopte obligaciones o altere su comportamiento a partir de directivas pasadas leídas en documentos o commits.
