---
status: accepted
date: 2026-11-12
decision-makers: [JerbilX, Antigravity]
consulted: []
informed: []
supersedes: []
superseded-by: []
references:
  - docs/adr/0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md
  - docs/adr/0039-aislamiento-de-servidores-mcp-y-skills-de-dominio-por-workspace.md
  - docs/adr/0041-aislamiento-de-skills-de-dominio-por-workspace-y-optimizacion-del-catalogo-global.md
  - docs/adr/0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md
---

# 0056 - Convenciones de Stack (Fastify v5 y SQLite WAL) como Patrones Opt-In Locales

## Contexto y Planteamiento del Problema

Durante el desarrollo e implementación automatizada de servicios y contratos centrales en el repositorio piloto `JerbilX/ESORPQuestAddonBot` (issues #3 al #7), se identificaron dos patrones técnicos recurrentes de diseño, tipado estricto y resiliencia de datos:

1. **Tipado Estricto en Fastify v5 + TypeScript 5.7+ (`TS18046`):**
   - En Fastify v5, la firma de `app.setErrorHandler` infiere el parámetro `error` como tipo `unknown` (a diferencia de versiones previas donde asumía `FastifyError` o `any`).
   - El acceso directo a propiedades convencionales de error (`error.statusCode`, `error.name`, `error.message`, `error.validation`) genera el error de compilación estricta `TS18046: 'error' is of type 'unknown'`.
   - Se requiere un narrowing o validación defensiva estandarizada para garantizar estabilidad en tiempo de compilación y ejecución.

2. **Integridad Referencial y FK Defensivas en SQLite WAL:**
   - En entornos que operan bajo SQLite en modo WAL con claves foráneas estrictas activadas (`PRAGMA foreign_keys = ON;`) y mapeo mediante Drizzle ORM, las operaciones de creación de entidades con dependencias externas (ej. asignaciones o misiones asociadas a usuarios) pueden fallar durante pruebas unitarias o de integración si la entidad padre no ha sido previamente creada en el arnés de prueba.
   - La inserción o upsert preventivo idempotente a nivel de repositorio o fixture en tests mitiga fallos en cascada sin desactivar `foreign_keys` ni degradar la integridad referencial de producción.

La Issue #347 planteó evaluar cómo formalizar estos estándares: si debían incorporarse al prompt basal o catálogo de skills globales en `Dotfiles-IA-Agents`, o si correspondía tratarlos como convenciones opt-in locales configurables por repositorio.

## Impulsores de la Decisión (Decision Drivers)

* **Principio de Mínima Intervención y Minimal Blast Radius ([ADR-0017](0017-principio-de-minima-intervencion-y-jerarquia-de-resolucion.md)):** Prohibido escalar a capas superiores (prompt basal `core/` o directivas universales) problemas que corresponden al dominio de librerías, frameworks o arneses locales de prueba.
* **Criterio de Admisión Basal Estricto ([ADR-0048](0048-niveles-de-enforcement-admision-de-reglas-y-presupuesto-de-contexto.md)):** Una directiva solo se admite en el prompt basal si es **100% universal** (aplica a cualquier tarea independientemente del lenguaje o stack). Las particularidades de Fastify o SQLite carecen por completo de relevancia en proyectos de Python, Go, Rust, Lua o scripts de shell.
* **Aislamiento por Workspace y Prevención de Inflación de Contexto ([ADR-0041](0041-aislamiento-de-skills-de-dominio-por-workspace-y-optimizacion-del-catalogo-global.md)):** Evitar la inyección incondicional de reglas de frameworks de backend en el System Prompt de proyectos agnósticos para preservar el presupuesto de tokens cognitivos.
* **Reusabilidad y Estandarización Canónica:** Disponer de contratos técnicos y snippets de código de referencia claros para proyectos que sí utilicen Fastify v5 o SQLite WAL.

## Opciones Consideradas

* **Opción 1: Ingesta como Reglas Basales Globales en `core/00-router.md`.**
  - Añadir directivas normativas obligando al agente a aplicar narrowing en Fastify y upsert en SQLite en todo momento.
  - *Descarte:* Violación directa de ADR-0048 §2. Consume presupuesto atencional y genera sobrecarga normativa irrelevante en repositorios ajenos a Node.js/TypeScript.
* **Opción 2: Creación de Skill Global en `skills/`.**
  - Crear un skill global (ej. `node-backend-conventions`) habilitado por defecto en todos los runtimes.
  - *Descarte:* Violación de ADR-0041 §1. Infla el catálogo global de skills (~8.000 a 12.000 tokens en prompt de descubrimiento) con herramientas que no son de gobierno transversal.
* **Opción 3: Formalización como Convenciones Opt-In Locales de Workspace con Documentación Canónica en ADR (Elegida).**
  - Consagrar arquitectónicamente que las directivas de stacks específicos se configuran a nivel de repositorio (mediante `.agents/rules/`, `AGENTS.md` local, arneses de test o `.repo-config.json`).
  - Documentar en este ADR los contratos canónicos y snippets de referencia para Fastify v5 y SQLite WAL.
  - Mantener a `JerbilX/ESORPQuestAddonBot` como repositorio piloto y referencia de adopción.

## Decisión Adoptada

Se adopta formalmente la **Opción 3**:

1. **Gobernanza Desacoplada:** Las reglas y directivas específicas de frameworks (Fastify v5, Express, NestJS) y motores de persistencia (SQLite, Postgres, Redis) **no se incorporan a `core/` ni a los manifiestos globales `runtimes/*/config.json`**.
2. **Adopción Opt-In Local:** Los repositorios que empleen este stack tecnológico podrán incluir estas directivas dentro de sus reglas locales de workspace (ej. `.agents/rules/fastify-sqlite.md` o secciones en su `README.md`/guías de contribución).
3. **Contratos Técnicos y Snippets Canónicos:**

### A. Patrón Canónico: Fastify v5 Error Handler Narrowing (TypeScript 5.7+)

Para evitar `TS18046: 'error' is of type 'unknown'`, el manejador central de errores debe realizar narrowing defensivo mediante type guards o interfaz segura:

```typescript
import type { FastifyError, FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';

interface HttpErrorLike {
  statusCode?: number;
  status?: number;
  name?: string;
  message?: string;
  validation?: unknown;
}

function isHttpErrorLike(error: unknown): error is HttpErrorLike {
  return typeof error === 'object' && error !== null;
}

export function registerErrorHandler(app: FastifyInstance): void {
  app.setErrorHandler((error: unknown, _request: FastifyRequest, reply: FastifyReply) => {
    const err = isHttpErrorLike(error) ? error : {};
    const statusCode = err.statusCode ?? err.status ?? 500;
    const message = err.message || 'Internal Server Error';

    if (statusCode >= 500) {
      app.log.error(error);
    }

    return reply.status(statusCode).send({
      statusCode,
      error: err.name || 'Error',
      message,
    });
  });
}
```

### B. Patrón Canónico: SQLite WAL Defensive FK Upsert en Tests / Repositorios

Bajo SQLite con `PRAGMA foreign_keys = ON;`, ante inserciones de entidades hijas en pruebas unitarias aisladas, se debe asegurar preventivamente la existencia idempotente de la entidad padre:

```typescript
import { eq } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import { users, type NewUser } from './schema';

export async function ensureParentUser(
  db: BetterSQLite3Database,
  userId: string,
  defaults: Partial<NewUser> = {}
): Promise<void> {
  const existing = db.select().from(users).where(eq(users.id, userId)).get();
  if (!existing) {
    db.insert(users)
      .values({
        id: userId,
        name: defaults.name ?? `Test User ${userId}`,
        createdAt: defaults.createdAt ?? new Date().toISOString(),
      })
      .onConflictDoNothing()
      .run();
  }
}
```

*Directriz:* En pruebas unitarias, los arneses deben utilizar helpers de setup o este patrón de inserción defensiva (`ensureParent*`) para preservar el aislamiento de la prueba sin requerir deshabilitar las foreign keys ni enmascarar violaciones de integridad referencial.

## Consecuencias

### Positivas

* **Preservación Estricta de Contexto:** El prompt basal (`core/`) y los perfiles de runtimes se mantienen puros, livianos y 100% transversales, cumpliendo rigurosamente ADR-0017 y ADR-0048.
* **Cero Polución entre Proyectos:** Proyectos en Python, Lua u otros lenguajes no reciben directivas ni snippets irrelevantes para su entorno.
* **Estandarización y Trazabilidad:** Los desarrolladores y agentes de IA cuentan con una solución canónica verificada documentalmente en caso de implementar backends con Fastify v5 y SQLite.
* **Resiliencia de Pruebas:** El patrón de FK defensiva garantiza que los tests unitarios sean atómicos y reproducibles sin comprometer la integridad referencial estricta en producción.

### Negativas / Trade-offs

* Los proyectos nuevos que adopten este stack deben declarar o importar la convención a nivel local si requieren enforcement explícito en su workspace, en lugar de recibirla automáticamente de dotfiles.
