# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

<!-- rule: id=AGY_SANDBOX_POLICY level=P0/P2 origin=#407 -->
- **Política y Exclusividad de Sandbox:** Inspección pasiva en sandbox (BypassSandbox: false); BypassSandbox: true exclusivo para git mutadores/red, gh y CLIs autorizados (agent-audit, agent-module, gh-pr-review, git-prune-gone) de forma atómica (sin &&, | ni wrappers (--jq)); scripts en scratch/ con BypassSandbox: false y commits atómicos vía .commit_msg.
<!-- rule: id=AGY_DOTFILES_PROVISIONING level=P2 origin=legacy -->
- **Aprovisionamiento Hermético de Dotfiles:** build y check operan en sandbox (BypassSandbox: false); link y all son bootstrap exclusivo del usuario en terminal nativa.
<!-- rule: id=AGY_ATTRIBUTION level=P2 origin=legacy -->
- **Atribución:** En issues y PRs: `Creado por: Antigravity (<modelo de la sesión>)`. En commits (trailer Git): `Generated-by: Antigravity (<modelo de la sesión>)`.
