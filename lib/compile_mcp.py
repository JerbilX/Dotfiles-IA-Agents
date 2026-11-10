#!/usr/bin/env python3
"""
compile_mcp.py - Compilación y validación atómica de configuración MCP por runtime.

Uso: compile_mcp.py <config_file> <mcp_dir> <dist_file> [<schema_file>]

Lee los servidores MCP habilitados en config_file, valida cada definición
contra schema_file (si se provee), expande variables de entorno, elimina claves
de metadatos ($schema, description) y escribe atómicamente el resultado en dist_file.
"""

import json
import os
import sys

# Permitir importación directa de módulos hermanos en lib/
_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

try:
    from validate import validate_file
except ImportError:
    validate_file = None


def expand_val(val):
    """Expande recursivamente variables de entorno en strings, listas y dicts."""
    if isinstance(val, str):
        return os.path.expandvars(val)
    elif isinstance(val, list):
        return [expand_val(x) for x in val]
    elif isinstance(val, dict):
        return {k: expand_val(v) for k, v in val.items()}
    return val


def compile_mcp(config_file: str, mcp_dir: str, dist_file: str, schema_file: str = None) -> int:
    """Valida y compila la configuración MCP para un runtime.

    Retorna la cantidad de servidores MCP compilados.
    Lanza ValueError, FileNotFoundError o RuntimeError ante inconsistencias.
    """
    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except Exception as e:
            raise ValueError(f"Error de sintaxis JSON en {config_file}: {e}")

    enabled_servers = [s for s in config.get("mcp_servers", []) if s and str(s).strip()]
    mcp_servers_dict = {}

    if not enabled_servers:
        output = {"mcpServers": {}}
        _write_atomic(dist_file, output)
        return 0

    for s_name in enabled_servers:
        s_path = os.path.join(mcp_dir, f"{s_name}.json")
        if not os.path.isfile(s_path):
            raise FileNotFoundError(
                f"Error: Módulo de servidor MCP '{s_name}' declarado en {config_file} no existe en {s_path}"
            )

        if schema_file:
            if not os.path.isfile(schema_file):
                raise FileNotFoundError(f"Error: Esquema MCP no encontrado en {schema_file}")
            if validate_file is not None:
                errors = validate_file(s_path, schema_file)
                if errors:
                    err_msg = "\n".join(f"Error de validación: {err}" for err in errors)
                    raise ValueError(err_msg)

        with open(s_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                raise ValueError(f"Error de sintaxis JSON en {s_path}: {e}")

        data.pop("$schema", None)
        data.pop("description", None)

        mcp_servers_dict[s_name] = expand_val(data)

    output = {"mcpServers": mcp_servers_dict}
    _write_atomic(dist_file, output)
    return len(mcp_servers_dict)


def _write_atomic(dest_path: str, data: dict) -> None:
    """Escribe data como JSON de forma atómica en dest_path usando un archivo temporal."""
    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    os.makedirs(dest_dir, exist_ok=True)
    tmp_file = f"{dest_path}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_file, dest_path)


def main():
    if len(sys.argv) < 4:
        sys.stderr.write("Uso: compile_mcp.py <config_file> <mcp_dir> <dist_file> [<schema_file>]\n")
        sys.exit(2)

    config_file = sys.argv[1]
    mcp_dir = sys.argv[2]
    dist_file = sys.argv[3]
    schema_file = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None

    try:
        compile_mcp(config_file, mcp_dir, dist_file, schema_file)
    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error inesperado al compilar MCP: {e}\n")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
