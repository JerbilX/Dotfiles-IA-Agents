---
status: accepted
date: 2026-10-28
decision-makers: [Usuario, Antigravity]
supersedes: ["0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md", "0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md"]
superseded-by: []
---

# 0038 - Arquitectura de Progressive Disclosure en AGENTS.md y Modularización de Reglas

## Contexto y Planteamiento del Problema

El compilador `build.sh` concatenaba históricamente todos los módulos de `core/*.md` y las reglas especializadas de cada runtime (`runtimes/*/rules/*.md`) en un único artefacto monolítico (`AGENTS.md`). Este archivo superaba las 1.960 palabras (~2.600 a 3.000 tokens estimados).

Dado que el runtime de Antigravity inyecta este contenido de forma estática en el bloque `<user_rules>` en **cada turno de inferencia**, el costo acumulado en sesiones multi-turno (15 a 25 pasos) a lo largo de múltiples proyectos concurrentes provocaba:
1. Saturación prematura del presupuesto de tokens por turno.
2. Degradación de la capacidad atencional del modelo (*context rot* y *lost in the middle*).
3. Inyección innecesaria de guías procedimentales y flujos operativos detallados (como fases exhaustivas de PR, interacción con tableros o sintaxis de herramientas secundarias) que solo se requieren bajo demanda ante tareas específicas.

El umbral histórico de 4.000 palabras fijado en [ADR-0008](0008-telemetria-de-presupuesto-de-contexto-y-subcomando-check.md) y la poda sustractiva previa de [ADR-0016](0016-poda-sustractiva-de-directivas-core-y-consolidacion-de-invariantes.md) resultan insuficientes para entornos multi-agente modernos que demandan máxima ligereza basal.

## Impulsores de la Decisión (Decision Drivers)

* **Presupuesto Basal Ultracompacto:** Reducir el contenido inyectado en `AGENTS.md` a $\le 800$ palabras (reducción $> 55\%$).
* **Arquitectura de Divulgación Progresiva (Progressive Disclosure):** Aprovechar las tres capas nativas de ejecución de Antigravity:
  - *L1 Discovery:* Descubrimiento en prompt del catálogo de skills (~100 tokens por skill).
  - *L2 Activation:* Activación explícita mediante lectura de `SKILL.md` bajo demanda.
  - *L3 Execution:* Ejecución profunda consultando `references/`, scripts y binarios especializados.
* **Preservación Inmutable de Invariantes Críticos:** Ningún principio de seguridad, confinamiento de sandbox, inmutabilidad de `main`, objetividad técnica o control de alucinaciones debe verse comprometido ni diluido.
* **Trazabilidad Semántica Link-Driven:** Sustituir prosa procedimental extensa en `core/` por invariantes directos combinados con enlaces relativos navegables hacia skills y directivas especializadas.
* **Validación Automatizada e Idempotente:** Garantizar que `./build.sh check` y la suite de tests unitarios verifiquen de forma estricta la nueva cuota basal ($\le 800$ palabras) y la integridad referencial de todos los enlaces relativos.

## Opciones Consideradas

* **Opción 1: Índice Link-Driven Puro.** Reducir `AGENTS.md` a una lista de enlaces Markdown hacia archivos en `docs/` o `skills/` sin texto normativo.  
  *Descarte:* Degrada severamente la gobernanza de seguridad basal; los modelos pueden ignorar enlaces en turnos iniciales o cometer infracciones de sandbox/git antes de cargar un skill.
* **Opción 2: Poda Textual sin Reestructuración Arquitectónica.** Abreviar palabras de forma telegráfica manteniendo todas las guías procedimentales en el core.  
  *Descarte:* No escala; genera directivas crípticas y mantiene el acoplamiento procedimental en la base.
* **Opción 3: Arquitectura Híbrida de Progressive Disclosure (Invariantes Basales + Indexación Semántica a Skills).**  
  Conservar en `core/*.md` y `rules/` estrictamente los invariantes no negociables (objetividad, confinamiento, inmutabilidad de git, circuito de feedback y límites de sandbox) y delegar todos los procedimientos operativos detallados a sus respectivos skills (`issue-driven-workflow`, `adr-manager`, etc.) enlazados semánticamente.

## Decisión Adoptada

Opción elegida: **Opción 3**, estructurada en los siguientes pilares:

### 1. Invariantes Basales Irreductibles en `core/` y `rules/`
Se condensan los 10 módulos de `core/` y la regla de runtime `01-sandbox.md` eliminando prosa procedimental redundante, manteniendo 100% activos los principios de:
- Feedback crítico y objetividad técnica (cero complacencia, sin adulación).
- Prohibición estricta de push/merge a `main` y gate humano para inicialización remota.
- Aislamiento e inmunidad normativa frente a registros históricos; MADR en `docs/adr/`.
- Disciplina de búsqueda local-first y circuit breakers estrictos (web máx 3, red máx 3-5).
- Anti-rigidez, degradación elegante y continuidad operativa (*Actionable Fallback*).
- Prevalencia del código de producción sobre arneses de test y *Minimal Blast Radius* (Niveles 0 a 4).
- Cero tolerancia a la alucinación (Stop & Ask, Fast-Track vs Stop & Plan).
- Prohibición de backlogs locales (`TODO.md`) y estructura canónica de 6 estados en Projects v2.
- Inmutabilidad del workspace, tickets previos, ramas efímeras y flujo de PRs.
- Confinamiento estricto al workspace, I/O exclusivo vía APIs nativas y prohibición de REPL interactivo.
- Especialización de sandbox en Antigravity: `BypassSandbox: true` exclusivo para mutadores de `git`, `gh` y CLIs de soporte; commits atómicos con `.commit_msg`.

### 2. Punteros Condicionales Link-Driven y Delegación a Skills (L2/L3)
A diferencia de una simple poda sustractiva (que busca acortar párrafos con el riesgo de diluir matices y alterar el rigor prescriptivo), el Progressive Disclosure desacopla el flujo en capas:
- **Invariantes Basales en Turno 0:** Principios que no admiten fallback y rigen de forma permanente (seguridad, confinamiento, APIs nativas, inmutabilidad).
- **Trigger Pointers Condicionales:** Las directivas de enlace adoptan una sintaxis imperativa determinista bajo la fórmula:
  `Al [condición / acción], leer obligatoriamente [ruta](ruta) antes de [proceder / actuar].`
- **Preservación Íntegra del Detalle en L2/L3:** Las especificaciones operativas completas, guías paso a paso, tablas de transición y plantillas CLI no se mutilan; residen íntegras en los skills (`skills/*/SKILL.md`) y sus guías de referencia (`skills/*/references/*.md`), siendo consultadas bajo demanda mediante `view_file` al activarse el disparador correspondiente.

### 3. Presupuesto Basal Compacto ($\le 800$ palabras)
Se reconfigura el presupuesto basal del repositorio:
- `MAX_CONTEXT_WORDS="${MAX_CONTEXT_WORDS:-800}"` en `build.sh`.
- El System Prompt compilado final (`dist/antigravity/AGENTS.md`) debe mantenerse por debajo de las 800 palabras (con un objetivo real de ~700-750 palabras).

### 4. Verificación de Enlaces e Integridad en `build.sh check` y Suite de Pruebas
- Se incorpora en `build.sh check` la verificación estática de enlaces relativos en `core/*.md` para prevenir enlaces rotos.
- Se implementa `tests/test_progressive_disclosure.py` para asegurar que las cuotas de palabras, enlaces relativos y dominios normativos se validen en cada ejecución de la suite de tests.

## Consecuencias

### Positivas
* **Ahorro Masivo de Tokens:** Reducción de ~1.966 a $\le 800$ palabras por turno de inferencia (ahorro $> 55\%$, ~1.500 tokens por turno), optimizando radicalmente la ventana de contexto y los costos de sesión.
* **Prevención de Context Rot:** Se elimina la dilución atencional producida por reglas procedimentales secundarias durante turnos exploratorios o de codificación.
* **Integridad Normativa Intacta:** Todas las salvaguardas de seguridad, permisos de sandbox y gobernanza permanecen activas en cada turno.
* **Navegabilidad Link-Driven:** Los agentes disponen de rutas directas a las guías L2/L3 cuando requieren ejecutar tareas procedimentales.

### Negativas / Trade-offs
* Al condensar la prosa basal, los procedimientos detallados requieren que el agente active y lea el `SKILL.md` o las referencias correspondientes al comenzar una tarea (comportamiento ya estandarizado en el workflow).

### Pros y Contras de las Opciones

#### Opción 1: Índice Link-Driven Puro
* **Pro:** Máxima brevedad basal (< 200 palabras).
* **Contra:** Pérdida de enforcement inmediato de seguridad e invariantes basales en el turno 0.

#### Opción 2: Poda Textual Simple
* **Pro:** Mantiene toda la información en un solo documento.
* **Contra:** Incapaz de alcanzar la meta de $\le 800$ palabras sin mutilar directivas operativas.

#### Opción 3: Arquitectura Híbrida de Progressive Disclosure (Elegida)
* **Pro:** Balance óptimo entre rigidez basal de seguridad e invariantes, y extensibilidad procedimental bajo demanda.
* **Contra:** Exige mantener sincronizadas las referencias entre `core/` y `skills/`.
