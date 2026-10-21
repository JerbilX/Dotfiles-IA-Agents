# Guía de Instalación, Configuración y Bootstrap (Setup)

Guía procedimental paso a paso para configurar el entorno de directivas, skills, binarios y servidores MCP en una máquina nueva, o para restaurar la configuración tras un formateo o reinstalación del sistema.

---

## 1. Precondiciones del Sistema

Antes de iniciar el aprovisionamiento, asegúrate de contar con las siguientes utilidades mínimas instaladas y configuradas en tu sistema anfitrión (Linux / macOS):

| Herramienta | Versión Mínima | Propósito en el Repositorio |
| :--- | :--- | :--- |
| **Bash** | 4.0+ | Intérprete para `build.sh` y utilidades POSIX (`ln`, `mkdir`, `date`, `wc`). |
| **Python 3** | 3.10+ | Validación de esquemas JSON (`jsonschema` o módulo estándar `json`). Alternativamente `jq`. |
| **Git** | 2.30+ | Control de versiones, ramas efímeras y clonado. |
| **GitHub CLI (`gh`)** | 2.20+ | Autenticación remota, gestión de issues, PRs y Projects v2. |

---

## 2. Configuración de Shell y Persistencia de `$PATH`

El orquestador del proyecto expone las herramientas de línea de comandos de los skills habilitados (como `agent-audit`, `gh-pr-review`, `git-prune-gone`, `eso-build`) dentro del directorio estándar de usuario `~/.local/bin/`.

Para asegurar que estos ejecutables estén siempre disponibles en cualquier sesión de terminal:

```bash
# 1. Asegurar la presencia de ~/.local/bin en tu shell rc (~/.bashrc o ~/.zshrc)
echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> ~/.bashrc

# 2. Recargar la configuración en la sesión activa
source ~/.bashrc
```

Si utilizas Zsh:
```bash
echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

---

## 3. Clonado del Repositorio

El repositorio es 100% autocontenido y aloja directivas basales, configuraciones de runtimes, catálogo canónico de skills y registros de decisiones (ADR):

```bash
mkdir -p ~/Proyectos-IA-V3 && cd ~/Proyectos-IA-V3
git clone https://github.com/JerbilX/Dotfiles-IA-Agents.git
cd Dotfiles-IA-Agents
```

---

## 4. Aprovisionamiento Automático E2E

Para ejecutar el aprovisionamiento completo de directivas, enlaces simbólicos, servidores MCP y herramientas CLI, ejecuta el orquestador principal:

```bash
./build.sh
```

### Mecánica Interna del Aprovisionamiento (`./build.sh all`):
1. **Compilación Determinista:** Concatena las directivas de `core/*.md` con las especializaciones de cada runtime en `runtimes/<runtime>/rules/*.md` para generar `dist/<runtime>/AGENTS.md`. Resuelve macros dinámicas (`${WORKSPACE}`, `${HOME}`) en `dist/<runtime>/mcp_config.json`.
2. **Respaldos Atómicos Pre-Despliegue:** Antes de sobreescribir o enlazar cualquier archivo existente en el host (ej. `~/.gemini/config/AGENTS.md` o `~/.claude/CLAUDE.md`), genera una copia de respaldo con timestamp (`.bak.YYYYMMDD_HHMMSS`).
3. **Enlaces Simbólicos Canónicos:** Crea enlaces atómicos `ln -sfn` hacia las rutas destino declaradas en `target.config_dir` y `target.skills_dir`.
4. **Exposición de Binarios de Skills:** Enlaza los scripts ejecutables y binarios declarados en `~/.local/bin/` aplicando los alias configurados en cada runtime.
5. **Auditoría Estática:** Ejecuta automáticamente la suite de verificación (`check`) reportando el estado final de integridad.

---

## 5. Verificación de Salud del Entorno

En cualquier momento puedes auditar la integridad de la configuración sin modificar ningún archivo ni enlace:

```bash
./build.sh check
```

Una salida saludable debe reportar:
```text
==> [check] Verificación completada: 0 error(es), 0 advertencia(s).
```

---

## 6. Resolución de Problemas Frecuentes (Troubleshooting)

### Error: Binarios o herramientas no encontradas (`command not found`)
- **Causa:** `~/.local/bin` no está presente en la variable de entorno `$PATH` de la subshell activa.
- **Diagnóstico:** Ejecuta `echo $PATH` y verifica si contiene `${HOME}/.local/bin`.
- **Solución:** Revisa la sección 2 de esta guía y recarga tu perfil de shell.

### Advertencia: Symlinks rotos o directorios destino inexistentes
- **Causa:** Se modificaron o eliminaron manualmente archivos en el home del usuario (`~/.gemini/` o `~/.claude/`).
- **Solución:** Ejecuta `./build.sh link` para reconstruir los symlinks atómicos con respaldo seguro.

### Advertencia: Falta de respaldos para Rollback
- **Causa:** Se ejecutó `check` antes de haber corrido `link` o `all` en esa máquina.
- **Solución:** Corre `./build.sh link` una vez para generar el primer respaldo preventivo.

---

## 7. Desinstalación y Purga Limpia

Si necesitas revertir el aprovisionamiento o remover los enlaces simbólicos del host:

```bash
# Revertir directivas y configuración MCP al respaldo previo
./build.sh rollback

# Remover enlaces de binarios en ~/.local/bin creados por el repositorio
rm -f ~/.local/bin/agent-audit ~/.local/bin/gh-pr-review ~/.local/bin/git-prune-gone ~/.local/bin/eso-build
```
