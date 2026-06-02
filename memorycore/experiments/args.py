from __future__ import annotations

from typing import Any


def parse_overrides(argv: list[str]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for item in argv:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        config[key.replace("-", "_")] = coerce_value(value)
    return config


def coerce_value(value: str) -> object:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    for caster in (int, float):
        try:
            return caster(value)
        except ValueError:
            pass
    return value

