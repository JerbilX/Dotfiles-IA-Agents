---
status: accepted
date: 2026-10-23
decision-makers: [Usuario, Agente]
supersedes: []
superseded-by: []
---

# 0032 - Compatibilidad de git-prune-gone y Rollback con Squash Merge

## Contexto y Planteamiento del Problema

El flujo canónico de desarrollo gobernado por `issue-driven-workflow` (formalizado en ADR-0005 y ADR-0031) prescribe el cierre de Pull Requests mediante squash merge (`gh pr merge <id> --squash --delete-branch`). Sin embargo, dos procedimientos basales del flujo asumían erróneamente un historial con merge commits tradicionales:

1. **`git-prune-gone` (Nivel 1):** Dependía exclusivamente de `git branch -d` para la poda segura de ramas huérfanas (`[gone]`). Al realizarse un squash merge, los commits individuales de la rama efímera no forman parte de la ascendencia directa de `HEAD` en `main`, provocando el error `error: the branch '<rama>' is not fully merged` y salida con código 1. El flag `--force` (`-D`) forzaba la eliminación sin discriminar ramas efectivamente integradas de ramas con trabajo no publicado o pendiente.
2. **Protocolo de Rollback (`references/rollback.md`):** Prescribía `git revert -m 1 <merge_commit_sha> --no-commit`. Al ser un commit de squash, tiene un único padre, fallando inmediatamente con `fatal: mainline was specified but commit ... is not a merge`.

## Impulsores de la Decisión (Decision Drivers)

* **Minimal Blast Radius (ADR-0017):** Resolver el problema estrictamente en Niveles 1 (tooling determinista) y 2 (documentación procedimental de skills), sin alterar directivas basales (`core/`).
* **Salvaguarda de Integridad y Prevención de Pérdida de Datos (Anti-Data Loss):** Garantizar que `git-prune-gone` nunca elimine una rama con cambios no integrados a menos que se invoque explícitamente con `--force`, distinguiendo rigurosamente entre ramas mergeadas tradicionalmente, ramas integradas vía squash y ramas no integradas.
* **Determinismo y Rendimiento:** Utilizar capacidades nativas de Git para la verificación de árboles sin introducir dependencias externas ni scripts temporales.
* **Resiliencia Operativa en Emergencias:** Proveer un criterio determinista para la detección del tipo de commit en reversiones de emergencia (`git rev-list --parents`).

## Opciones Consideradas

* **Opción 1: Requerir `--force` indiscriminado en `git-prune-gone` y documentarlo en el skill.**
  * *Descarte:* Inaceptable. Destruye la red de seguridad del flujo, permitiendo el borrado accidental de trabajo local huérfano no integrado.
* **Opción 2: Detección de parches mediante `git cherry` sobre commit sintético.**
  * *Descarte:* Limitada. Si la rama troncal sufrió commits adicionales que tocaron las mismas regiones de archivo o resolvieron conflictos durante el squash, los patch-ids discrepan y `git cherry` arroja falsos negativos (clasifica como no integrado contenido que sí fue mergeado).
* **Opción 3: Verificación de equivalencia de árbol con `git merge-tree --write-tree` y discriminación de commits en rollback.**
  * *Selección:* Óptima. `git merge-tree --write-tree <base> <branch>` simula la integración en memoria: si el árbol resultante coincide exactamente con el árbol de la rama base (`<base>^{tree}`), se verifica de forma matemática e irrefutable que el 100% de los cambios de la rama están presentes en la base. Si no coincide o hay conflictos, se clasifica como `unmerged`. En rollback, se utiliza la cuenta de padres (`git rev-list --parents -n 1 <sha>`) para bifurcar entre `git revert --no-commit` y `git revert -m 1 --no-commit`.

## Decisión Adoptada

Se adopta la **Opción 3**:

1. **Evolución de `git-prune-gone` (Nivel 1):**
   * Incorporar soporte para el flag `--base <rama>` con resolución automática (parámetro CLI -> `base_branch` de `.repo-config.json` o `config.json` -> `"main"`).
   * Clasificar cada rama candidata `[gone]` en:
     * `merged`: Si `git merge-base --is-ancestor <branch> <base>` es exitoso (poda con `git branch -d`).
     * `squash-merged`: Si `git merge-tree --write-tree <base> <branch>` produce un árbol idéntico a `<base>^{tree}` (poda segura verificada con `git branch -D`).
     * `unmerged`: Si no cumple ninguna de las anteriores. Estas ramas se omiten y se reportan en `failed` / `unmerged` con código de salida 1, requiriendo `--force` para su borrado.
   * Reflejar la clasificación en `--dry-run` y `--json`.
2. **Actualización del Protocolo de Rollback (`references/rollback.md` - Nivel 2):**
   * Inspeccionar los padres del commit mediante `git rev-list --parents -n 1 <commit_sha>`.
   * Si posee 1 padre (squash commit): `git revert --no-commit <commit_sha>`.
   * Si posee 2 o más padres (merge commit): `git revert -m 1 --no-commit <commit_sha>`.
3. **Actualización de Documentación de Skill (`SKILL.md` y `references/branch-lifecycle.md` - Nivel 2):**
   * Documentar la clasificación tripartita de `git-prune-gone`, la salvaguarda anti-pérdida de datos y los flags disponibles.
4. **Verificación Automatizada en `./build.sh check`:**
   * Agregar ejecución de tests unitarios reproducibles en `tests/` para verificar los escenarios de squash, tradicional y ramas no integradas.

### Consecuencias

* **Positivas:**
  * Eliminación definitiva del fallo recurrente de `git-prune-gone` tras squash merges.
  * Protección robusta contra pérdida accidental de ramas no integradas.
  * Protocolo de reversión de emergencia determinista y tolerante a squash commits y merge commits.
  * Cobertura mediante tests unitarios integrados en `./build.sh check`.
* **Negativas / Trade-offs:**
  * La invocación de `git merge-tree` requiere Git >= 2.38 (el entorno dispone de Git 2.55).
