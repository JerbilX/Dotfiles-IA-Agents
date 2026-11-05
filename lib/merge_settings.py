#!/usr/bin/env python3
"""merge_settings.py - Combina un fragmento de settings de runtime en el settings del host (ADR-0045).

Uso: merge_settings.py <fragmento.json> <destino.json>

Las listas en permissions.allow/deny/ask se unen preservando el orden (primero las
del usuario); el resto de las claves del usuario no se modifica. Escritura atómica.
"""

import json
import os
import sys

PERMISSION_LISTS = ("allow", "deny", "ask")
# ${DOTFILES_ROOT} se expande a la ruta absoluta del repo. En reglas de permisos de
# Claude Code, `//` inicia una ruta absoluta: "Read(/${DOTFILES_ROOT}/x)" -> "Read(//home/.../x)".
DOTFILES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def expand(entry):
    return entry.replace("${DOTFILES_ROOT}", DOTFILES_ROOT)


def load_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge(target, fragment):
    t_perms = target.setdefault("permissions", {})
    f_perms = fragment.get("permissions", {})
    for key in PERMISSION_LISTS:
        if key not in f_perms:
            continue
        current = t_perms.setdefault(key, [])
        for entry in map(expand, f_perms[key]):
            if entry not in current:
                current.append(entry)
    return target


def main(argv):
    if len(argv) != 3:
        print("Uso: merge_settings.py <fragmento.json> <destino.json>", file=sys.stderr)
        return 2
    fragment_path, target_path = argv[1], argv[2]
    fragment = load_json(fragment_path)
    try:
        target = load_json(target_path)
    except json.JSONDecodeError as exc:
        print(f"Error: {target_path} no es JSON válido ({exc}); no se modifica.", file=sys.stderr)
        return 1
    before = json.dumps(target, sort_keys=True)
    merged = merge(target, fragment)
    if json.dumps(merged, sort_keys=True) == before:
        print(f"  [=] Sin cambios en {target_path}")
        return 0
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    tmp_path = f"{target_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, target_path)
    print(f"  [✓] Permisos combinados en {target_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
