---
status: accepted
date: 2026-11-06
decision-makers: [JerbilX, Antigravity]
consulted: []
informed: []
references:
  - docs/adr/0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md
  - docs/adr/0013-estrategia-de-modularizacion-de-directivas-extensas-a-skills.md
  - docs/adr/0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md
  - docs/adr/0043-hard-circuit-breaker-y-lifecycle-hooks.md
  - docs/adr/0047-resolucion-desacople-progressive-disclosure-y-compilacion-autosuficiente.md
---

# Niveles de Enforcement, Criterio de Admisión de Reglas Basales y Presupuesto Techo / Objetivo

## Contexto y Problemática

El registro histórico de Git sobre el directorio `core/` muestra alrededor de 25 commits de la forma `fix(core): blindar...`. Casi cada falla observada o desvío de comportamiento de los agentes de IA se corrigió agregando texto normativo al prompt basal compilado (`core/00-router.md` y `core/01-objectivity.md`).

Los sucesivos intentos de achicar el prompt mediante reformulaciones sintácticas, cambio de idioma o condensación de reglas (ADR-0013, ADR-0016, ADR-0038 reduciendo a 800 palabras con pérdida de directivas críticas, y ADR-0047 fijando el límite en 1350 palabras) atacaron únicamente el síntoma. Como consecuencia:
1. **Crecimiento inflacionario recurrente:** Cualquier nuevo incidente vuelve a añadir prohibiciones en lenguaje natural al prompt basal.
2. **Cumplimiento probabilístico:** Como se evidenció en ADR-0043, las instrucciones en texto tienen adhesión no determinista por parte de los LLM, especialmente cuando compiten decenas de directivas simultáneas. Sin embargo, múltiples reglas detectables de manera puramente mecánica (prohibición de REPL en terminal como `bash -c` o `python3 -c`, exfiltración con `find /`, o I/O con `cat`/`sed`) siguen delegadas exclusivamente al texto del prompt.
3. **Costo cognitivo y atencional:** El peso no radica en el consumo de tokens (~1.700 tokens frente a ventanas de contexto de 200k+), sino en la **densidad de prohibiciones simultáneas** que degradan la capacidad de razonamiento y atención del agente en sus tareas principales.
4. **Acoplamiento de vocabulario:** El núcleo basal utiliza nombres específicos de herramientas (ej. herramientas de Antigravity), obligando a runtimes como Claude Code a gastar palabras adicionales en traducir o reinterpretar las equivalencias.

Se requiere una arquitectura estructural que desacople los mecanismos de cumplimiento, establezca compuertas de admisión estrictas y defina un presupuesto dual (techo duro y banda objetivo) que prevenga el crecimiento del prompt basal y habilite su reducción progresiva.

---

## Decisión de Arquitectura

Se aprueba formalmente el modelo de **tres niveles de enforcement**, el **criterio de admisión restrictivo al prompt basal**, el **formato de registro de reglas**, el **presupuesto dual (techo y banda objetivo)** y el **ciclo de mejora continua basado en datos**, complementando las bases establecidas en ADR-0008, ADR-0013, ADR-0017 y ADR-0047.

```
       ▲
       │  [P2: Prompt Basal]         AGENTS.md compilado (criterio, heurística, tabla de ruteo)
       │  ─────────────────────────
Nivel  │  [P1: Carga Bajo Demanda]   Skills especializadas (procedimientos y flujos E2E)
       │  ─────────────────────────
       │  [P0: Entorno / Hooks]      PreToolUse hooks, guards, permisos (enforcement mecánico)
       ▼
```

### 1. Niveles de Enforcement

Cada regla, directiva o salvaguarda debe residir en el **nivel más bajo** con capacidad técnica para hacerla cumplir:

| Nivel | Mecanismo | Alcance y Contenido | Ejemplo |
| :---: | :--- | :--- | :--- |
| **P0** | **Entorno y Hooks Deterministas**<br>(`PreToolUse` hooks, `permissions.deny`, interceptores de sandbox) | Patrones detectables mecánicamente de forma determinista mediante inspección de comandos, herramientas, argumentos o secuencias. | Bloqueo de `bash -c`, `python3 -c`, `find /`, `find $HOME`, uso de `cat`/`tee` para I/O, circuit breaker de lecturas pasivas consecutivas. |
| **P1** | **Carga Bajo Demanda**<br>(Skills en `skills/`) | Procedimientos, flujos de trabajo extensos, convenciones de Git/PRs, taxonomías y reglas aplicables solo a un tipo de tarea específica. | Ciclo E2E de ramas y PRs (`issue-driven-workflow`), ciclo de vida de ADRs (`adr-manager`), taxonomía Diátaxis (`project-documentation`), auditoría de sesiones (`conversation-audit`). |
| **P2** | **Prompt Basal Universal**<br>(`AGENTS.md` compilado desde `core/` y `rules/`) | Criterio de juicio técnico, heurísticas no verificables mecánicamente, lineamientos de conducta crítica y la tabla canónica de activación obligatoria de skills. | Minimal Blast Radius, prevalencia de código de producción, consistencia lógica / Stop & Ask, objetividad y feedback crítico, ruteo de skills. |

---

### 2. Criterio de Admisión al Prompt Basal

1. **Condición Necesaria de Admisión:** Una regla o directiva se admite en el prompt basal (`core/`) **única y exclusivamente** si:
   - No puede ser implementada ni verificada mecánicamente en **P0**.
   - No puede resolverse mediante invocación bajo demanda en **P1**.
2. **Huella Residual Mínima de P0 en P2:** Toda regla cubierta o interceptada por P0 no debe duplicar su lógica en el texto basal. Deja en P2, como máximo, una sola línea que instruya al agente sobre **cómo actuar ante el bloqueo** (ej. ante denegación de circuit breaker: detenerse y sintetizar; ante bloqueo de REPL: crear script en `scratch/`).
3. **Jerarquía de Mitigación de Incidentes:** Ante cualquier fallo operativo o incidente de agente, la solución técnica debe evaluarse en orden estricto:
   $$\text{P0 (Mecánico)} \longrightarrow \text{P1 (Skill)} \longrightarrow \text{P2 (Prompt Basal)}$$
   Queda terminantemente prohibido añadir texto a `core/` si la infracción puede detectarse en P0 o modularizarse en P1.

---

### 3. Registro y Metadatos de Reglas

Para auditar y gobernar las directivas sin sobrecargar el contexto del modelo:
- Cada regla presente en `core/` y `rules/` contará con una metadata estructurada (ID estable, nivel asignado e issue de origen).
- La metadata se gestionará en encabezados o ficheros de control que no aportan palabras al prompt final compilado distribuido a los agentes.
- `./build.sh check` auditará el cumplimiento del criterio de admisión, asegurando que ninguna regla mecanizable permanezca indebidamente en P2 sin plan de migración.

---

### 4. Presupuesto de Contexto: Techo Duro y Banda Objetivo

Se sustituye el umbral estático único de 1350 palabras por un **sistema de control de compuerta dual**:

| Parámetro | Variable | Límite | Comportamiento en `build.sh check` | Propósito |
| :--- | :--- | :---: | :---: | :--- |
| **Techo Duro** | `MAX_CONTEXT_WORDS` | **2000 palabras** | **Error Estático (`CHECK_ERRORS + 1`, exit code 1)** | Límite infranqueable que previene desbordamientos masivos. Permite margen controlado durante transiciones. |
| **Banda Objetivo** | `TARGET_CONTEXT_WORDS` | **1100 palabras**<br>(~55% del techo) | **Advertencia Estática (`CHECK_WARNINGS + 1`)** | Zona operativa saludable. Superar la banda exige justificar explícitamente en el PR por qué la regla no puede ir a P0 o P1. |

#### Mitigación de Riesgos
- *Riesgo identificado:* Un techo de 2000 palabras holgado respecto al estado actual (~1250 palabras) corre el riesgo de convertirse en el objetivo de facto si los desarrolladores añaden texto sin fricción.
- *Mitigación:* Se implementa advertencia visible en `build` y `check` al superar la banda objetivo de 1100 palabras, complementada por la obligatoriedad de justificación en Pull Requests y el control de admisión gobernado por `./build.sh check`.

---

### 5. Ciclo de Mejora Continua sin Componentes Nuevos

Se descarta expresamente la creación de skills adicionales o servidores MCP para gestionar mejoras del prompt:
- Una nueva skill crearía otro procedimiento dependiente de activación probabilística.
- Un servidor MCP introduciría dependencias de proceso en tiempo de ejecución sin añadir control real.

El ciclo de vida y optimización continua se cierra reutilizando el tooling existente:
1. **`agent-audit`:** Mide la frecuencia de violaciones por ID de regla a partir de las transcripciones de las sesiones.
2. **`./build.sh check`:** Audita la admisión de directivas y el presupuesto estático.
3. **Reglas de Transición Dinámica:**
   - **Promoción a P0:** Toda regla en P2 que registre violaciones recurrentes y cuyo patrón sea mecanizable, se migra a un hook en P0 (eliminando su texto extenso del prompt basal).
   - **Degradación o Retiro de P2:** Toda regla en P2 que no registre violaciones tras un período prolongado ($N$ sesiones de auditoría limpia) se traslada a su respectiva skill (P1) o se elimina del catálogo basal.

---

## Consecuencias y Efectos

### Positivas
- **Contención definitiva del prompt basal:** Se frenan los 25 ciclos históricos de parches textuales acumulativos.
- **Enforcement robusto y determinista:** Las prohibiciones mecánicas (REPL, comandos peligrosos, lecturas masivas) se garantizan mediante código (hooks), reduciendo la tasa de fallo de los agentes a 0% en dichos vectores.
- **Menor carga cognitiva:** La reducción progresiva hacia la banda objetivo de 1100 palabras maximiza la atención del LLM para el código y la lógica de negocio.
- **Compatibilidad multi-runtime:** Desacopla la lógica basal de las peculiaridades de interfaz de herramientas de cada runtime.

### Negativas / Deuda Mitigada
- Requiere la implementación de hooks en Claude Code (Issue #287) y guardias adicionales (Issue #283) para poder evacuar reglas basales en la fase posterior (Issue #284).
- Los prompts compilados actuales (~1271 palabras en Antigravity y ~1235 palabras en Claude) superan la banda objetivo de 1100 palabras, generando advertencias en `build` y `check` de forma esperada hasta que se ejecute la evacuación de reglas (Issue #284).
