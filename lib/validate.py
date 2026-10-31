#!/usr/bin/env python3
"""
Stand-alone JSON schema validator for Dotfiles-IA-Agents.
Validates configurations against canonical JSON schemas using only Python's standard library.
"""

import json
import os
import re
import sys


def validate_pattern(pattern_str: str, value: str) -> bool:
    try:
        return bool(re.search(pattern_str, value))
    except Exception:
        return True


def validate_value_against_schema(val, schema, path="root") -> list[str]:
    errors = []
    if not isinstance(schema, dict):
        return errors

    # Check type
    schema_type = schema.get("type")
    if schema_type:
        type_map = {
            "object": dict,
            "array": list,
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "null": type(None),
        }
        expected_py_type = type_map.get(schema_type)
        if expected_py_type and not isinstance(val, expected_py_type):
            errors.append(f"'{path}' debe ser de tipo '{schema_type}'.")
            return errors  # No deeper validation if type mismatch

    # String constraints
    if isinstance(val, str):
        pat = schema.get("pattern")
        if pat and not validate_pattern(pat, val):
            errors.append(f"'{path}' no cumple con el patrón requerido: {pat}")
        enum_vals = schema.get("enum")
        if enum_vals is not None and val not in enum_vals:
            enum_str = ", ".join(f"'{x}'" for x in enum_vals)
            errors.append(f"'{path}' debe ser uno de: [{enum_str}].")
        if not val.strip():
            # Check if non-empty is required in properties where empty strings are forbidden
            pass

    # Array constraints
    if isinstance(val, list):
        item_schema = schema.get("items")
        unique_items = schema.get("uniqueItems", False)
        if unique_items:
            try:
                if len(val) != len(set(val)):
                    errors.append(f"'{path}' contiene elementos duplicados.")
            except TypeError:
                pass
        if item_schema:
            for idx, item in enumerate(val):
                sub_errors = validate_value_against_schema(item, item_schema, f"{path}[{idx}]")
                errors.extend(sub_errors)
                if isinstance(item, str) and not item.strip():
                    errors.append(f"Cada elemento de '{path}' debe ser una cadena no vacía.")

    # Object constraints
    if isinstance(val, dict):
        # required properties
        for req in schema.get("required", []):
            if req not in val:
                errors.append(f"Falta la propiedad requerida '{req}'.")

        allowed_props = set(schema.get("properties", {}).keys())
        add_props = schema.get("additionalProperties", True)
        if add_props is False:
            extra = set(val.keys()) - allowed_props
            if extra:
                errors.append(f"Propiedades no permitidas encontradas: {sorted(list(extra))}")
        elif isinstance(add_props, dict):
            for k, v in val.items():
                if k not in allowed_props:
                    sub_errors = validate_value_against_schema(v, add_props, f"{path}.{k}")
                    errors.extend(sub_errors)
                if not isinstance(k, str) or not k.strip():
                    errors.append(f"Claves de '{path}' deben ser cadenas no vacías.")
                if isinstance(v, str) and not v.strip():
                    errors.append(f"Valores de '{path}' deben ser cadenas no vacías.")

        for prop_name, prop_schema in schema.get("properties", {}).items():
            if prop_name in val:
                sub_val = val[prop_name]
                sub_errors = validate_value_against_schema(sub_val, prop_schema, f"{path}.{prop_name}")
                errors.extend(sub_errors)
                if isinstance(sub_val, str) and not sub_val.strip() and prop_name in schema.get("required", []):
                    errors.append(f"La propiedad '{path}.{prop_name}' no puede estar vacía.")

    # oneOf handling
    if "oneOf" in schema:
        valid_matches = 0
        for branch in schema["oneOf"]:
            branch_errs = []
            for req in branch.get("required", []):
                if req not in val:
                    branch_errs.append(f"Missing {req}")
            if "not" in branch and "required" in branch["not"]:
                for not_req in branch["not"]["required"]:
                    if not_req in val:
                        branch_errs.append(f"Forbidden {not_req}")
            if not branch_errs:
                valid_matches += 1
        if valid_matches != 1:
            errors.append(f"'{path}' no cumple exactamente con una de las ramas de 'oneOf'.")

    return errors


def validate_file(json_path: str, schema_path: str) -> list[str]:
    if not os.path.isfile(json_path):
        return [f"Archivo JSON no encontrado: {json_path}"]
    if not os.path.isfile(schema_path):
        return [f"Archivo de esquema no encontrado: {schema_path}"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Error de sintaxis JSON en {json_path}: {e}"]

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        return [f"Error de sintaxis JSON en esquema {schema_path}: {e}"]

    errors = validate_value_against_schema(data, schema, path=os.path.basename(json_path))
    return errors


def main():
    if len(sys.argv) < 3:
        print("Uso: validate.py <archivo.json> <esquema.json>", file=sys.stderr)
        sys.exit(2)

    json_path = sys.argv[1]
    schema_path = sys.argv[2]

    errors = validate_file(json_path, schema_path)
    if errors:
        for err in errors:
            print(f"Error de validación: {err}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
