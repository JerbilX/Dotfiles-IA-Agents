# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

<!-- rule: id=AGY_GIT_SANDBOX_BYPASS level=P0/P2 origin=#382 -->
- **Ejecución de Git y Bypass:** Bypass de sandbox automatizado en P0 para gh y git mutador; temporales (.commit_msg, .pr_body) en <appDataDir>/brain/<conversation-id>/scratch/.
<!-- rule: id=AGY_DOTFILES_PROVISIONING level=P2 origin=legacy -->
- **Aprovisionamiento Hermético de Dotfiles:** build, test y check operan en sandbox (BypassSandbox: false); check valida linters, schemas y suite unitaria vía unittest (prohibido invocar pytest o buscar arneses/entornos virtuales externos); link y all son bootstrap exclusivo del usuario en terminal nativa.
<!-- rule: id=AGY_BYPASS_EXCLUSIVITY level=P0/P2 origin=legacy -->
- **Exclusividad de Bypass:** BypassSandbox: true exclusivo para git, gh y CLIs autorizados (agent-module, etc.); prohibidos wrappers (--jq) y repos externos; scratch/ con BypassSandbox: false.
<!-- rule: id=AGY_ATTRIBUTION level=P2 origin=legacy -->
- **Atribución:** En issues y PRs: `Creado por: Antigravity (<modelo de la sesión>)`. En commits (trailer Git): `Generated-by: Antigravity (<modelo de la sesión>)`.
<!-- rule: id=AGY_ARTIFACT_METADATA_SCOPE level=P2 origin=#345 -->
- **Alcance de ArtifactMetadata:** ArtifactMetadata es exclusivo para artefactos en <appDataDir>/brain/<conversation-id>/ (ej. implementation_plan.md, walkthrough.md); en archivos del workspace, repositorio o scratch/, omitir estrictamente ArtifactMetadata.
<!-- rule: id=AGY_NATIVE_FILE_INSPECTION level=P0/P2 origin=#345 -->
- **Inspección Pasiva de Archivos:** Inspección pasiva de archivos exclusivamente con la herramienta nativa view_file; prohibido ejecutar comandos de shell (cat, head, tail, sed) para lectura.
<!-- rule: id=AGY_GIT_INSPECTION_SAFEGUARD level=P2 origin=#398 -->
- **Inspección de Revisiones Git:** Prohibidas tuberías (|) con utilidades de filtrado (sed, head, tail, cat, awk, grep) sobre Git (git show, log, diff). Revisiones históricas: exportar a <appDataDir>/brain/<conversation-id>/scratch/ vía redirección simple (git show <ref>:<path> > <scratch_path>) e inspeccionar con view_file (StartLine/EndLine); logs y diffs: flags nativos (git log -n, git diff -U) sin tuberías.

