# Guía de Configuración: Workflows Nativos de GitHub Projects v2

Guía procedimental paso a paso para configurar los flujos de automatización integrados (*Built-in Workflows*) en GitHub Projects v2 (tablero central `Proyectos-IA-V3`), permitiendo sincronizar el ciclo de vida de issues y Pull Requests sin sobrecarga burocrática en la CLI del agente.

---

## 1. Contexto y Filosofía de Diseño

Bajo el estándar de desarrollo guiado por issues (formalizado en `docs/adr/0030-desacoplamiento-de-maquina-de-estados-y-alineacion-al-ciclo-nativo-git-github.md`), los agentes de IA tienen **prohibido modificar manualmente los estados del tablero** mediante `gh project item-edit`.

En su lugar, el tablero se sincroniza de forma desatendida a través del ciclo de vida nativo de Git/GitHub:
* La vinculación canónica `Closes #<id>` en el cuerpo de un PR transiciona automáticamente la tarjeta a revisión.
* La fusión (*merge*) o el cierre de issues transiciona la tarjeta a finalizado.

Esta arquitectura requiere que el administrador del repositorio configure una única vez los flujos integrados en la interfaz web de GitHub Projects.

---

## 2. Procedimiento de Configuración Paso a Paso

1. Inicia sesión en GitHub y navega al tablero central del proyecto (`Proyectos-IA-V3`).
2. En la esquina superior derecha del tablero, haz clic en el menú de tres puntos (`...`) o en el icono de engranaje para acceder a **Project Settings**.
3. En la barra lateral izquierda, selecciona la pestaña **Workflows**.
4. Habilita y configura los siguientes **6 workflows nativos** según las especificaciones de la tabla inferior:

| Workflow Nativo | Disparador (*Trigger*) | Acción (*Set value*) | Propósito Operativo |
| :--- | :--- | :--- | :--- |
| **`Auto-add to project`** | `When filter matches` (`is:issue,pr is:open` por repo) | Add item to project | Indexación desatendida de issues y PRs en repositorios bajo su filtro (con `item-add` como salvaguarda). |
| **`Pull request linked to issue`** | `When a pull request is linked to an issue` | `Status: 👀 In Review / PR` | Transición automática a revisión al publicar un PR con `Closes #<id>`. |
| **`Pull request merged`** | `When a pull request is merged` | `Status: Done` | Cierre y archivo automático de la tarjeta del PR al fusionarse en la rama base. |
| **`Item closed`** | `When an item is closed` | `Status: Done` | Cierre automático de la tarjeta de la issue al mergear el PR o cerrar spikes sin PR. |
| **`Code changes requested`** | `When review requests changes` | `Status: ⚙️ In Progress` | Retorno automático a progreso si el revisor solicita correcciones en GitHub Web. |
| **`Item reopened`** | `When an item is reopened` | `Status: 🎯 Ready for Dev` | Reactivación de tickets reabiertos para un nuevo ciclo de desarrollo. |

5. Asegúrate de activar el interruptor (**Enable workflow**) en cada una de las 6 automatizaciones.

---

## 3. Verificación de Funcionamiento

Para comprobar que las automatizaciones operan adecuadamente:

1. **Test de Vinculación:** Crea una rama efímera de prueba, sube un commit y abre un Pull Request que incluya `Closes #<id>` en el cuerpo. Verifica en el tablero que la tarjeta de la issue cambie automáticamente de `⚙️ In Progress` a `👀 In Review / PR`.
2. **Test de Cierre:** Fusiona el PR en la interfaz web o mediante `gh pr merge --squash --delete-branch`. Verifica que tanto la issue como el PR transicionen a `Done`.

---

## 4. Documentación Relacionada

* [Guía de Setup y Bootstrap del Repositorio](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/setup.md)
* [Arquitectura y Contratos del Sistema](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/docs/architecture.md)
* [Referencia de Ciclo de Ramas y PRs](file:///home/jerbilx/Proyectos-IA-V3/Dotfiles-IA-Agents/skills/issue-driven-workflow/references/branch-lifecycle.md)
