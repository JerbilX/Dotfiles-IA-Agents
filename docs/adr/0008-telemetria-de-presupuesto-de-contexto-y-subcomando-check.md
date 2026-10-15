---
status: proposed
date: 2026-10-15
decision-makers: [Usuario, Antigravity]
consulted: []
informed: []
---

# 0008 - Telemetría de Presupuesto de Contexto y Subcomando de Verificación Estática

## Contexto y Planteamiento del Problema

El archivo compilado `dist/antigravity/AGENTS.md` se inyecta como directivas de sistema (*System Prompt*) al inicializar cualquier sesión de agentes en el entorno. A medida que el número de directivas normativas (`core/`) y reglas de runtime (`rules/`) se expande, surgen dos problemas arquitectónicos:

1. **Riesgo de Context Drift y Saturación Basal:** La concatenación de módulos se realiza sin métricas sobre el tamaño del prompt resultante (líneas, palabras y tokens estimados). Un prompt desmedido degrada la atención del modelo (*lost in the middle*) y reduce la ventana útil disponible para código, herramientas y contexto de conversación.
2. **Carencia de Validación de Integridad de Solo Lectura:** El orquestador `build.sh` disponía de comandos mutantes (`build`, `link`, `skills`) que alteran el disco y purgan symlinks, pero carecía de un mecanismo idempotente y de solo lectura (`check`) adecuado para auditorías estáticas, pre-commit o pipelines de CI/CD.

## Impulsores de la Decisión (Decision Drivers)

* **Visibilidad Preventiva (Budget Drift):** Monitorear en tiempo de compilación el peso del System Prompt emitiendo alertas cuando se supere el presupuesto recomendado sin bloquear ni truncar directivas de forma destructiva.
* **Idempotencia Estricta y Operación de Solo Lectura:** El subcomando `check` no debe crear, mover, borrar ni alterar ningún archivo ni enlace simbólico en el sistema de archivos.
* **Diagnóstico Consolidado vs. Fail-Fast:** En operaciones de auditoría (`check`), es prioritario evaluar todas las dimensiones (esquema, skills en disco, binarios, colisiones y enlaces rotos) y reportar un diagnóstico completo en lugar de abortar en el primer fallo.
* **Zero Dependencias Adicionales:** El cálculo de métricas y la verificación de colisiones deben realizarse con utilidades estándar POSIX (`wc`, Bash built-ins) y el módulo estándar de Python 3 para JSON Schema.
* **Aislamiento de Entorno (Sin Falsos Positivos):** La auditoría de symlinks en directorios compartidos del sistema de usuario (como `~/.local/bin`) debe acotarse a enlaces gobernados por este repositorio para evitar fallos producidos por herramientas de terceros no relacionadas.

## Opciones Consideradas

* **Opción 1: Tokenizador externo pesado (`tiktoken` / Hugging Face).** Proporciona conteo de tokens exacto para modelos específicos, pero requiere empaquetar o instalar dependencias de Python con bindings nativos, violando el principio de ligereza de `build.sh`.
* **Opción 2: Solo conteo de líneas (`wc -l`).** Es nativo pero no refleja la densidad real de texto en tokens (líneas largas con código o tablas distorsionan la métrica).
* **Opción 3: Telemetría mediante heurística determinista POSIX + Subcomando `cmd_check` consolidado.**

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes componentes:

1. **Telemetría de Contexto en `cmd_build`:**
   - Cálculo mediante `wc -l`, `wc -w` y `wc -c` sobre el artefacto compilado.
   - Heurística determinista entera de tokens: $\text{tokens} = \frac{\text{palabras} \times 4 + 2}{3}$ (~1.33 tokens por palabra para español técnico y directivas de código/markdown).
   - Umbral configurable mediante variable de entorno: `MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-4000}"`. Si se sobrepasa, se emite una advertencia en `stderr` recomendando modularización a skills, sin abortar el build.
2. **Subcomando `cmd_check` de Solo Lectura:**
   - Retorna código de salida `0` si todas las pruebas son limpias y `1` si existe al menos un fallo crítico.
   - Ejecuta una matriz de 5 validaciones:
     - **Esquema de configuración:** Valida `config.json` contra `runtime-config.schema.json`.
     - **Skills en disco:** Verifica la presencia de cada directorio de skill habilitado en `AGY_SKILLS_PATH` y su respectivo `SKILL.md`.
     - **Binarios declarados:** Valida que los scripts origen mapeados en `.binaries` existan y tengan permisos de ejecución.
     - **Ausencia de colisiones:**
       - Unicidad de prefijos numéricos `NN-` de forma intra-directorio (`core/` y `rules/` independientes).
       - Unicidad de títulos Markdown de primer nivel (`# `) a través de todas las directivas compiladas.
     - **Integridad de enlaces simbólicos:** Inspecciona enlaces huérfanos o rotos en `~/.gemini/config/AGENTS.md`, `~/.gemini/config/skills/` y enlaces gobernados en `~/.local/bin/`.

### Consecuencias

* **Positivas:**
  - Visibilidad inmediata del consumo de tokens y palabras durante el desarrollo de nuevas directivas.
  - Capacidad de ejecutar auditorías preventivas en CI o pre-commit con `./build.sh check`.
  - Detección temprana de roturas de symlinks y colisiones sintácticas antes de desplegar.
* **Negativas / Trade-offs:**
  - La estimación de tokens es una aproximación heurística (~$\pm 5\%$) y no una tokenización BPE exacta de cada arquitectura de modelo de lenguaje.
