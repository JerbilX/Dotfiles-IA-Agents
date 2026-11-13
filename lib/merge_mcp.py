#!/usr/bin/env python3
"""merge_mcp.py - Fusiona los servidores MCP compilados en la clave mcpServers de un JSON del host.

Uso: merge_mcp.py <dist_mcp_config.json> <destino.json> [servidor_gestionado ...]

Ref: docs/adr/0057-despliegue-mcp-de-claude-por-fusion-en-claude-json.md

Los servidores de dist/ se escriben (alta o actualización). Los servidores gestionados
(catálogo runtimes/<r>/mcp/*.json) ausentes de dist/ se retiran del destino; el resto
de servidores y claves del usuario no se modifica. Si hay cambios, respalda el destino
en <destino>.bak.<timestamp> y escribe de forma atómica preservando sus permisos.
"""

import json
import os
import shutil
import sys
import time


def load_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge(target, servers, managed):
    t_servers = target.setdefault("mcpServers", {})
    for name in managed:
        if name not in servers:
            t_servers.pop(name, None)
    t_servers.update(servers)
    return target


def main(argv):
    if len(argv) < 3:
        print("Uso: merge_mcp.py <dist_mcp_config.json> <destino.json> [servidor_gestionado ...]", file=sys.stderr)
        return 2
    dist_path, target_path, managed = argv[1], argv[2], argv[3:]
    servers = load_json(dist_path).get("mcpServers", {})
    try:
        target = load_json(target_path)
    except json.JSONDecodeError as exc:
        print(f"Error: {target_path} no es JSON válido ({exc}); no se modifica.", file=sys.stderr)
        return 1
    before = json.dumps(target, sort_keys=True)
    merged = merge(target, servers, managed)
    if json.dumps(merged, sort_keys=True) == before:
        print(f"  [=] Sin cambios en {target_path}")
        return 0
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    mode = 0o600
    if os.path.isfile(target_path):
        mode = os.stat(target_path).st_mode & 0o777
        backup = f"{target_path}.bak.{time.strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(target_path, backup)
        print(f"  [✓] Respaldo previo en {backup}")
    tmp_path = f"{target_path}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp_path, mode)
    os.replace(tmp_path, target_path)
    print(f"  [✓] Servidores MCP combinados en {target_path}: {', '.join(sorted(servers)) or '(ninguno)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
