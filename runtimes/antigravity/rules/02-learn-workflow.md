# Interceptación y Ruteo de Aprendizajes (Runtime: Antigravity)

<!-- rule: id=AGY_LEARN_INTERCEPT level=P0/P2 origin=#322 -->
- **Interceptación de `/learn`:** Prohibido mutar o crear archivos (`write_to_file`, `replace_file_content`) ante `/learn` o pedidos de aprendizaje; canalizar obligatoriamente a propuesta técnica, GitHub Issue, rama efímera y PR.
<!-- rule: id=AGY_LEARN_ROUTING level=P2 origin=#322 -->
- **Ruteo Contextual de Aprendizajes:**
  - **Conducta Global del Agente o Dotfiles:** Si la lección refiere a reglas generales, herramientas o gobernanza de dotfiles, formular el ticket y canalizarlo hacia `JerbilX/Dotfiles-IA-Agents` (`gh issue create -R JerbilX/Dotfiles-IA-Agents`).
  - **Convenciones Locales del Proyecto (con Git y GitHub):** Si refiere a lógica o estándares específicos del repositorio activo, formalizarlo como issue en el repo local vía `gh issue create`.
  - **Workspaces sin Git o sin GitHub:** Presentar la propuesta en el chat de forma estructurada como recomendación o snippet para aplicación manual, sin intentar mutar archivos ni ejecutar comandos `gh` ciegos.
