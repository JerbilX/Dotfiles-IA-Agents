# Especialización de Sandbox y Ejecución (Runtime: Antigravity)

<!-- rule: id=AGY_GIT_SANDBOX_BYPASS level=P0/P2 origin=legacy -->
- **Ejecución de Git y Bypass de Sandbox:** Git pasivo local (status/log/diff) en sandbox (BypassSandbox: false); todo gh y git mutador/red exigen proactivamente BypassSandbox: true; commits atómicos vía .commit_msg.
<!-- rule: id=AGY_DOTFILES_PROVISIONING level=P2 origin=legacy -->
- **Aprovisionamiento Hermético de Dotfiles:** build y check operan en sandbox (BypassSandbox: false); link y all son bootstrap exclusivo del usuario en terminal nativa.
<!-- rule: id=AGY_BYPASS_EXCLUSIVITY level=P0/P2 origin=legacy -->
- **Exclusividad de Bypass:** BypassSandbox: true exclusivo para git, gh y CLIs autorizados (agent-audit, agent-module, gh-pr-review, git-prune-gone), atómicos sin &&, | ni wrappers (--jq); scripts en scratch/ con BypassSandbox: false.
<!-- rule: id=AGY_ATTRIBUTION level=P2 origin=legacy -->
- **Atribución:** En issues y PRs: `Creado por: Antigravity (<modelo de la sesión>)`. En commits (trailer Git): `Generated-by: Antigravity (<modelo de la sesión>)`.
