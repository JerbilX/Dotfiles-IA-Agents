# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

<!-- rule: id=AGY_GIT_SANDBOX_BYPASS level=P0/P2 origin=legacy -->
- **Ejecución de Git y Bypass:** Git pasivo local (status/diff) confinado (BypassSandbox: false); gh y git mutador/red con BypassSandbox: true; temporales (.commit_msg, .pr_body) en <appDataDir>/brain/<conversation-id>/scratch/ ante restricciones de write_to_file.
<!-- rule: id=AGY_DOTFILES_PROVISIONING level=P2 origin=legacy -->
- **Aprovisionamiento Hermético de Dotfiles:** build, test y check operan en sandbox (BypassSandbox: false); check valida linters, schemas y suite unitaria vía unittest (prohibido invocar pytest o buscar arneses/entornos virtuales externos); link y all son bootstrap exclusivo del usuario en terminal nativa.
<!-- rule: id=AGY_BYPASS_EXCLUSIVITY level=P0/P2 origin=legacy -->
- **Exclusividad de Bypass:** BypassSandbox: true exclusivo para git, gh y CLIs autorizados (agent-audit, agent-module, gh-pr-review, git-prune-gone), atómicos sin &&, |, subshells ($()) ni wrappers (--jq); prohibido gh api/curl a otros repos citados (Stop & Ask); scripts en scratch/ con BypassSandbox: false.
<!-- rule: id=AGY_ATTRIBUTION level=P2 origin=legacy -->
- **Atribución:** En issues y PRs: `Creado por: Antigravity (<modelo de la sesión>)`. En commits (trailer Git): `Generated-by: Antigravity (<modelo de la sesión>)`.
<!-- rule: id=AGY_ARTIFACT_METADATA_SCOPE level=P2 origin=#345 -->
- **Alcance de ArtifactMetadata:** ArtifactMetadata es exclusivo para artefactos en <appDataDir>/brain/<conversation-id>/ (ej. implementation_plan.md, walkthrough.md); en archivos del workspace, repositorio o scratch/, omitir estrictamente ArtifactMetadata.
<!-- rule: id=AGY_NATIVE_FILE_INSPECTION level=P0/P2 origin=#345 -->
- **Inspección Pasiva de Archivos:** Inspección pasiva de archivos exclusivamente con la herramienta nativa view_file; prohibido ejecutar comandos de shell (cat, head, tail, sed) para lectura (bloqueado por Guard P0).
