"""A stdlib checker for the JSON Schema subset ``schema.json`` uses (ST-053; decision-log
2026-10-07). Supported keywords: type, enum, required, properties, additionalProperties
(false), items, minItems, uniqueItems, minimum, maximum, minLength, pattern; annotations
($schema, $id, title, description) are ignored. Any other keyword is refused at load time, so
the schema can never silently say more than this checker enforces.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from functools import cache
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.json")
ANNOTATIONS = frozenset({"$schema", "$id", "title", "description"})
KEYWORDS = frozenset(
    {"type", "enum", "required", "properties", "additionalProperties", "items", "minItems",
     "uniqueItems", "minimum", "maximum", "minLength", "pattern"}
)  # fmt: skip
_TYPES: dict[str, Any] = {
    "object": dict, "array": list, "string": str, "integer": int, "boolean": bool,
}  # fmt: skip


class UnsupportedSchema(ValueError):
    """``schema.json`` uses a keyword this checker does not enforce."""


def unsupported_keywords(schema: Mapping[str, Any], at: str = "") -> list[str]:
    found = [f"{at or '/'}{k}" for k in schema if k not in KEYWORDS | ANNOTATIONS]
    for name, sub in schema.get("properties", {}).items():
        found += unsupported_keywords(sub, f"{at}/properties/{name}/")
    if isinstance(schema.get("items"), Mapping):
        found += unsupported_keywords(schema["items"], f"{at}/items/")
    return found


@cache
def drill_schema() -> Mapping[str, Any]:
    schema: Mapping[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if bad := unsupported_keywords(schema):
        raise UnsupportedSchema(f"unsupported schema keywords: {', '.join(bad)}")
    return schema


def _is_type(value: object, name: str) -> bool:
    if name == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[name])


def errors(value: object, schema: Mapping[str, Any], path: str = "") -> Iterator[str]:
    """Yield ``"<path>: <message>"`` for each violation; the path is ``a.b[0]`` style."""
    where = path or "(document)"
    if "type" in schema and not _is_type(value, schema["type"]):
        yield f"{where}: must be {schema['type']}"
        return
    if "enum" in schema and value not in schema["enum"]:
        yield f"{where}: must be one of {', '.join(map(str, schema['enum']))}"
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                yield f"{path + '.' if path else ''}{name}: required"
        for name, item in value.items():
            sub = f"{path}.{name}" if path else name
            if name in props:
                yield from errors(item, props[name], sub)
            elif schema.get("additionalProperties") is False:
                yield f"{sub}: unknown field"
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            yield f"{where}: needs at least {schema['minItems']} item(s)"
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) < len(
            value
        ):
            yield f"{where}: items must be unique"
        if isinstance(schema.get("items"), Mapping):
            for i, item in enumerate(value):
                yield from errors(item, schema["items"], f"{path}[{i}]")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            yield f"{where}: must be >= {schema['minimum']}"
        if "maximum" in schema and value > schema["maximum"]:
            yield f"{where}: must be <= {schema['maximum']}"
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            yield f"{where}: must not be empty"
        if "pattern" in schema and not re.search(schema["pattern"], value):
            yield f"{where}: does not match {schema['pattern']}"
