# Compendio Canónico de Anti-Patrones y Precedentes Verificados

Este documento recopila los principales anti-patrones y trampas técnicas observadas históricamente en el ecosistema de agentes, junto con su causa raíz demostrada y la solución estandarizada ratificada en los ADRs del repositorio.

---

## 1. Intentar Mutaciones Locales de Git dentro del Sandbox Estándar
- **Anti-Patrón:** Ejecutar `git init`, `git add`, `git commit` o `git checkout` con `BypassSandbox: false`.
- **Síntoma:** Error del sistema de archivos: `fatal: Unable to create '.git/index.lock': Read-only file system` o `Permission denied`.
- **Causa Raíz:** El kernel del entorno confinado monta el subdirectorio `.git/` con permisos de solo lectura (`ro`) para proteger la integridad del control de versiones.
- **Solución Canónica:** Invocar todo comando mutador local (`git init`, `add`, `commit`, `branch -d`, `checkout`, `merge`) y comando remoto (`git push`, `git pull`, `gh`) directamente con `BypassSandbox: true` desde el primer intento. Las consultas pasivas (`git status`, `git log`, `git diff`) deben mantenerse en `BypassSandbox: false`.
- **Precedentes de Referencia:**
  - [ADR-0001: Blindaje de Sandbox y Gestión de Permisos de Git](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0001-blindaje-de-sandbox-y-gestion-de-permisos.md)
  - [ADR-0011: Ratificación de Bypass en Git y GitHub CLI por Restricciones del Sandbox](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0011-ratificacion-de-bypass-en-git-y-gh-por-restricciones-del-sandbox.md)

---

## 2. Invocación de Git y GitHub CLI con Argumentos Multilínea o Comillas Complejas
- **Anti-Patrón:** Usar `git commit -m "..."` o `gh pr create --body "..."` con textos largos o caracteres de escape en la terminal.
- **Síntoma:** Pérdida del *prefix matching* de seguridad; el agente dispara modales interactivos continuos de confirmación humana o fallos de parseo.
- **Causa Raíz:** El evaluador de permisos de Antigravity desactiva la coincidencia por prefijo de comando cuando detecta saltos de línea, comillas anidadas o expansiones dinámicas de variables.
- **Solución Canónica:** Redactar el contenido mediante herramientas nativas de archivos en archivos temporales desacoplados (`.commit_msg`, `.pr_body`, `.issue_body`), transferir con flags atómicos (`-F .commit_msg` o `--body-file .pr_body`) y limpiar de inmediato (`rm -f <archivo>`).
- **Precedentes de Referencia:**
  - [ADR-0001: Blindaje de Sandbox y Gestión de Permisos de Git](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0001-blindaje-de-sandbox-y-gestion-de-permisos.md)
  - [ADR-0012: Optimización de Latencia y Eliminación de Fricción Operativa](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0012-optimizacion-de-latencia-y-eliminacion-de-friccion-operativa.md)

---

## 3. Encadenar Operaciones de Git mediante Tuberías o Wrappers CLI (`awk` / `xargs`)
- **Anti-Patrón:** Limpiar ramas zombi mediante tuberías como `git branch -vv | awk '/: gone]/{print $1}' | xargs -r git branch -d`.
- **Síntoma:** Disparo de solicitudes interactivas de permisos o fallos silenciosos en subshells.
- **Causa Raíz:** Encadenar utilidades delegando privilegios de bypass a binarios que no son Git ni GitHub CLI vulnera la regla de confinamiento y anula el *prefix matching*.
- **Solución Canónica:** Procedimiento atómico en dos fases:
  1. *Fase 1 (Inspección pasiva confinada, `BypassSandbox: false`):* `git branch --format "%(refname:short) %(upstream:track)"`.
  2. *Fase 2 (Poda atómica mutadora, `BypassSandbox: true`):* `git branch -d <rama1> <rama2>` invocando directamente el binario de Git solo si existen ramas marcadas como `[gone]`.
- **Precedentes de Referencia:**
  - [ADR-0010: Política Transversal de Limpieza y Ciclo de Vida de Ramas](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0010-politica-transversal-de-limpieza-y-ciclo-de-vida-de-ramas.md)
  - [ADR-0017: Principio de Mínima Intervención y Jerarquía de Resolución](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md)

---

## 4. Auto-Aceptación No Autorizada de Decisiones Arquitectónicas
- **Anti-Patrón:** Crear un ADR y asignarle de inmediato `status: accepted` sin intervención del usuario.
- **Síntoma:** Quiebre de gobernanza arquitectónica; imposición de decisiones no validadas por el Tech Lead / Usuario.
- **Causa Raíz:** Falta de disciplina en la separación de roles; el agente asume erróneamente facultades de aprobación humana.
- **Solución Canónica:** Todo nuevo ADR redactado por el agente nace obligatoriamente con `status: proposed`. La transición a `status: accepted` es prerrogativa exclusiva del usuario mediante confirmación explícita o fusión del Pull Request.
- **Precedentes de Referencia:**
  - [ADR-0004: Adopción del Estándar MADR y Skill ADR Manager](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0004-adopcion-del-estandar-madr-y-skill-adr-manager.md)

---

## 5. Gestión de Tareas en Archivos Locales Huérfanos (`TODO.md`, `backlog.md`, `tasks/`)
- **Anti-Patrón:** Registrar tareas pendientes, planes o deudas técnicas en archivos markdown informales en el workspace.
- **Síntoma:** Desalineación con el tablero central de proyectos, tareas olvidadas e inconsistencia de contexto entre sesiones.
- **Causa Raíz:** Resistencia a interactuar con la API remota de GitHub o hábitos de notas locales desestructuradas.
- **Solución Canónica:** Prohibición absoluta de backlogs locales. Todo requerimiento futuro se formaliza como una GitHub Issue estructurada (`gh issue create --body-file .issue_body`) y se indexa inmediatamente en el tablero de Projects v2 (`gh project item-add 1 --owner JerbilX --url <issue-url>`).
- **Precedentes de Referencia:**
  - [ADR-0005: Protocolo de Desarrollo Guiado por Issues y Flujo de Pull Requests](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0005-protocolo-de-desarrollo-guiado-por-issues-y-flujo-de-pull-requests.md)

---

## 6. Degradación de Código de Producción para Complacer Mocks Desactualizados
- **Anti-Patrón:** Alterar contratos legítimos de producción o introducir bifurcaciones artificiales para que un test double obsoleto pase en verde.
- **Síntoma:** Degradación arquitectónica y acoplamiento tóxico del código productivo al arnés de pruebas.
- **Causa Raíz:** Optimización miope orientada exclusivamente a que el test suite no falle, sin analizar si el fallo proviene del mock o de una regresión real.
- **Solución Canónica:** Primacía absoluta del código de producción sobre los test doubles. Si el contrato de producción cambió legítimamente, se actualiza el mock o fixture. Solo se modifica producción si se violó una regla de negocio legítima.
- **Precedentes de Referencia:**
  - [ADR-0003: Jerarquía de Producción sobre Tests e Inmunidad Normativa](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0003-jerarquia-de-produccion-sobre-tests-e-inmunidad-normativa.md)

---

## 7. Inflación Basal del System Prompt con Directivas Procedimentales
- **Anti-Patrón:** Agregar especificaciones paso a paso o manuales operativos en `core/*.md`.
- **Síntoma:** Saturación de la ventana de contexto (>4.000 palabras), dilución atencional (*lost in the middle*) y encarecimiento de tokens por turno.
- **Causa Raíz:** Confundir directivas invariantes universales (seguridad, anti-alucinación) con procedimientos de ejecución bajo demanda.
- **Solución Canónica:** Extraer procedimientos a `skills/*/SKILL.md` bajo demanda, manteniendo en `core/` únicamente una directiva de enlace (*Trigger Directive*) concisa (~80-130 palabras).
- **Precedentes de Referencia:**
  - [ADR-0008: Telemetría de Presupuesto de Contexto y Subcomando Check](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md)
  - [ADR-0013: Estrategia de Modularización de Directivas Extensas hacia Skills Bajo Demanda](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md)
  - [ADR-0016: Poda Sustractiva de Directivas Core y Consolidación de Invariantes](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md)

---

## 8. Modificación Innecesaria de Directivas en Capas Superiores (Violación de Minimal Blast Radius)
- **Anti-Patrón:** Modificar archivos en `core/` o reglas de runtime para resolver problemas que pueden solucionarse con flags de CLI o scripts locales.
- **Síntoma:** Inestabilidad sistémica y cambios de comportamiento no deseados en todos los runtimes.
- **Causa Raíz:** Falta de análisis de la escala de abstracción antes de implementar cambios.
- **Solución Canónica:** Regla de Mínima Intervención: resolver siempre en el nivel más bajo posible (Nivel 0 CLI -> Nivel 1 Tooling/Scripts -> Nivel 2 Skills -> Nivel 3 Rules de Runtime -> Nivel 4 Core Basal). Todo cambio en Nivel 4 exige justificación técnica de inviabilidad en niveles 0 a 3.
- **Precedentes de Referencia:**
  - [ADR-0017: Principio de Mínima Intervención y Jerarquía de Resolución](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/adr/0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md)
