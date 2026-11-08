#!/usr/bin/env python3
"""merge_settings.py - Combina un fragmento de settings de runtime en el settings del host (ADR-0045).

Uso: merge_settings.py <fragmento.json> <destino.json>

Las listas en permissions.allow/deny/ask se unen preservando el orden (primero las
del usuario); los hooks se combinan por evento (ver merge_hooks); el resto de las
claves del usuario no se modifica. Escritura atómica.
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
    merge_hooks(target, fragment.get("hooks", {}))
    return target


def merge_hooks(target, f_hooks):
    """Combina hooks por evento (ADR-0051).

    Los comandos declarados en el fragmento son propiedad del repo: se retiran del destino
    (incluso bajo otro matcher) y se agregan las entradas del fragmento al final. Así el
    merge es idempotente y un cambio de matcher no deja entradas huérfanas. Los hooks
    propios del usuario no se tocan.
    """
    if not f_hooks:
        return
    t_hooks = target.setdefault("hooks", {})
    for event, f_entries in f_hooks.items():
        f_entries = [
            {**entry, "hooks": [{**h, "command": expand(h.get("command", ""))} for h in entry.get("hooks", [])]}
            for entry in f_entries
        ]
        owned = {h["command"] for entry in f_entries for h in entry["hooks"]}
        kept = []
        for entry in t_hooks.get(event, []):
            remaining = [h for h in entry.get("hooks", []) if h.get("command") not in owned]
            if remaining:
                kept.append({**entry, "hooks": remaining})
        t_hooks[event] = kept + f_entries


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
    print(f"  [✓] Permisos y hooks combinados en {target_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
