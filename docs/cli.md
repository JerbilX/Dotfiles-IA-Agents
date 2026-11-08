# Referencia Técnica del Orquestador CLI (`build.sh`)

Manual exhaustivo de subcomandos, variables de entorno, compuertas de auditoría y protocolos de recuperación del script central de automatización `build.sh`.

---

## 1. Sintaxis General de Invocación

```bash
./build.sh <subcomando> [runtime]
```

### Argumentos Generales
- `<subcomando>`: Acción operativa requerida (`build`, `link`, `skills`, `mcp`, `status`, `rollback`, `check`, `reconcile`, `workspace`, `all`).
- `[runtime]`: Parámetro opcional (`antigravity`, `claude` o `all`).
  - **Por defecto (omitido):** Procesa exclusivamente los runtimes con `status: "active"` (`antigravity`), eliminando overhead de I/O y procesamiento de agentes no utilizados en el día a día.
  - **Específico (`<runtime>`):** Procesa bajo demanda (*on-demand*) el entorno indicado (ej. `claude`).
  - **Masivo (`all`):** Procesa la totalidad de los runtimes registrados en `runtimes/` (activos y bajo demanda).

---

## 2. Catálogo Exhaustivo de Subcomandos

### 1. `build`
Concatena en orden determinista los módulos de `core/*.md` con las especializaciones de cada runtime en `runtimes/<runtime>/rules/*.md` para generar `dist/<runtime>/AGENTS.md`. Resuelve macros declarativas (`${WORKSPACE}`, `${HOME}`) en las definiciones modulares de MCP y genera `dist/<runtime>/mcp_config.json`.
```bash
./build.sh build            # Compila runtimes activos (antigravity)
./build.sh build claude      # Compila bajo demanda el runtime Claude Code
./build.sh build all         # Compila la totalidad de runtimes registrados
```

### 2. `link`
Verifica la existencia del directorio destino declarado en `target.config_dir`, genera respaldos con timestamp (`.bak.YYYYMMDD_HHMMSS`) de cualquier archivo preexistente, crea enlaces simbólicos atómicos (`ln -sfn`) hacia las ubicaciones canónicas del host, aprovisiona los skills y sus binarios CLI en `~/.local/bin/` y configura los aliases prefix-matchables de GitHub CLI (`board` y `board-ready`):
```bash
./build.sh link             # Enlaza runtimes activos (antigravity)
./build.sh link claude      # Enlaza ~/.claude/ bajo demanda
./build.sh link all         # Enlaza todos los runtimes registrados
```

### 3. `skills`
Valida `runtimes/<runtime>/config.json` contra `runtimes/schema/runtime-config.schema.json` (*fail-fast*), purga symlinks obsoletos en el destino de skills, aprovisiona los skills habilitados en `target.skills_dir` y expone sus herramientas CLI en `~/.local/bin/` aplicando los alias declarados en `binaries`:
```bash
./build.sh skills             # Expone skills y binarios de todos los runtimes
./build.sh skills antigravity # Expone herramientas para Antigravity
```
> [!TIP]
> Cada vez que se incorpore un skill que provea herramientas CLI (como `agent-audit` o `git-prune-gone`), se debe ejecutar `./build.sh skills` en el anfitrión para garantizar que los enlaces simbólicos se creen en `~/.local/bin/`.

### 4. `mcp`
Subcomando especializado para compilar, respaldar y enlazar exclusivamente la configuración de servidores MCP de uno o todos los runtimes:
```bash
./build.sh mcp
./build.sh mcp antigravity
```

### 5. `status`
Inspecciona el estado de los enlaces simbólicos y respaldos en las rutas destino de cada runtime, reportando validez, tipo y archivo de destino:
```bash
./build.sh status
./build.sh status antigravity
```

### 6. `rollback`
Inspecciona de forma determinista el directorio destino (`target.config_dir`) y revierte atómicamente el estado del runtime al último respaldo disponible (`.bak.<timestamp>`) generado durante el despliegue previo (`link` o `mcp`), tanto para directivas (`AGENTS.md`) como para servidores MCP (`mcp_config.json`). Si no existen respaldos previos, retorna código de salida `1`:
```bash
./build.sh rollback             # Restaura todos los runtimes con respaldos
./build.sh rollback antigravity # Restaura exclusivamente Antigravity
./build.sh rollback claude      # Restaura exclusivamente Claude Code
```

### 7. `check`
Ejecuta una auditoría estática de integridad de **solo lectura** (*read-only*), ideal para validaciones pre-commit y CI/CD:
```bash
./build.sh check            # Audita runtimes activos (antigravity) y valida esquemas de secundarios
./build.sh check claude      # Audita bajo demanda el runtime Claude Code
./build.sh check all         # Audita la totalidad de los runtimes registrados
```
Inspecciona esquemas JSON, sintaxis, presencia de binarios, aliases de GitHub CLI, colisiones de prefijos numéricos o títulos H1, comandos con bypass entrecomillados en skills, integridad de symlinks en el host, presupuesto de contexto (global y modular) e integridad de la documentación técnica.

### 8. `reconcile`
Ejecuta la reconciliación y ratificación determinista de Architecture Decision Records (ADRs) tras la fusión de Pull Requests en la rama troncal (`main`). Identifica ADRs en `status: proposed` que ya forman parte del historial de `main` y actualiza atómicamente su metadato a `status: accepted`:
```bash
./build.sh reconcile
```

### 9. `workspace`
Aprovisiona de forma declarativa e idempotente las skills locales (`.agents/skills/`, `.gemini/skills/`, `.claude/skills/`) y las configuraciones de suite de dominio (como `eso`) hacia un directorio de proyecto destino (o el directorio actual si se omite la ruta):
```bash
./build.sh workspace <modulo> [ruta_destino] [runtime]
./build.sh workspace eso .              # Aprovisiona skills y MCP para Antigravity y Claude en $PWD
./build.sh workspace eso /ruta/a/addon  # Aprovisiona en directorio específico
```
> [!TIP]
> Desde el workspace del proyecto también puedes utilizar directamente la herramienta CLI en `$PATH` (`~/.local/bin/agent-module` expuesta tras `./build.sh all` o `./build.sh skills`):
> - `agent-module list`: Lista los módulos disponibles en dotfiles.
> - `agent-module status [ruta]`: Inspecciona el estado de los módulos en el workspace actual.
> - `agent-module enable <modulo> [ruta] [--runtime all|antigravity|claude]`: Aprovisiona skills y configuraciones MCP.
> - `agent-module disable <modulo> [ruta] [--runtime all|antigravity|claude]`: Poda y revierte la integración local.
> O bien solicitarlo conversacionalmente al agente en el chat (*"activa el soporte de eso en este proyecto"*).


### 10. `all`
Flujo completo por defecto. Ejecuta secuencialmente `build`, `link`, `skills`, `status` y la verificación final `check`:
```bash
./build.sh                  # Flujo completo para runtimes activos (antigravity por defecto)
./build.sh all claude       # Flujo completo bajo demanda para Claude Code
./build.sh all all          # Flujo completo para la totalidad de runtimes registrados
```

---

## 3. Variables de Entorno de Control

| Variable | Tipo | Por Defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `MAX_CONTEXT_WORDS` | `integer` | `2000` | Techo duro de palabras para el prompt global compilado (`dist/<runtime>/AGENTS.md`). Provoca error estático en `check`. |
| `TARGET_CONTEXT_WORDS` | `integer` | `1100` | Banda objetivo (~55% del techo) para el prompt compilado. Superarla emite advertencia en `build` y `check`. |
| `MAX_MODULE_WORDS` | `integer` | `300` | Presupuesto modular por archivo individual en `core/*.md` y `rules/*.md`. |
| `MAX_README_WORDS` | `integer` | `600` | Umbral máximo recomendado de palabras en el `README.md` raíz. |

---

## 4. Auditoría de Presupuesto de Contexto

El subcomando `check` implementa dos controles de auditoría (presupuesto global con techo y banda, y presupuesto modular) para prevenir la degradación atencional por saturación del System Prompt ([ADR-0008](adr/0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md), [ADR-0013](adr/0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md), [ADR-0017](adr/0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md), [ADR-0047](adr/0047-resolucion-desacople-progressive-disclosure-y-compilacion-autosuficiente.md) y [ADR-0048](adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md)):

1. **Presupuesto Global Dual ([ADR-0048](adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md)):**
   - **Techo Duro (`MAX_CONTEXT_WORDS=2000`):** Límite estricto que aborta con error estático (`exit 1`) si el prompt compilado supera este valor.
   - **Banda Objetivo (`TARGET_CONTEXT_WORDS=1100`):** Umbral operativo recomendado (~55% del techo). Superarlo emite una advertencia estática en `build` y `check`, obligando a justificar en el PR por qué la directiva no reside en enforcement mecánico (P0) o skill bajo demanda (P1).
2. **Presupuesto Modular (`MAX_MODULE_WORDS=300`):**
   Audita individualmente cada directiva en `core/*.md` y `rules/*.md`. Si un archivo supera este umbral, emite una advertencia estática instando a evaluar la extracción del procedimiento a un skill bajo demanda (patrón *Trigger Directive + Dedicated Skill*).
3. **Control de Admisión de Reglas Basales ([ADR-0048](adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md)):**
   Audita que cada regla del prompt basal (`core/*.md` y `runtimes/*/rules/*.md`) porte metadatos estructurados en comentario HTML (`<!-- rule: id=<ID> level=<P0|P1|P2|Build|P0/P2|P0/P1|P1/P2> origin=<#ISSUE|legacy> -->`):
   - Aborta con error (`exit 1`) si una regla no tiene ID o nivel válido, si un ID colisiona, si existen metadatos huérfanos, o ante ausencia/fallo de ejecución del validador (`python3`).
   - Aborta con error (`exit 1`) si una regla clasificada con componente `P0` (pura o mixta) supera el techo estático de 100 palabras.
   - Emite una advertencia estática (contabilizada en `CHECK_WARNINGS`) si una regla con componente `P0` supera el límite recomendado de huella residual de 30 palabras ([ADR-0048 §2.2](adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md)), orientando la evacuación hacia hooks mecánicos.
   - El compilador (`build_core.sh`) descarta estos comentarios al generar `dist/`, asegurando cero impacto en el recuento de palabras.

---

## 5. Códigos de Salida (Exit Codes)

| Código | Significado | Causa Común |
| :---: | :--- | :--- |
| `0` | **Éxito (Success)** | Operación completada exitosamente sin infracciones. |
| `1` | **Fallo Operativo / Error de Chequeo** | Errores en `./build.sh check`, esquemas JSON inválidos o ausencia de respaldos para `rollback`. |
