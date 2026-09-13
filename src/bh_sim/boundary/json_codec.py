"""Strict, tagged JSON codec for the neutral DW1 contract family.

This is separate from the scientific canonical codec. Unknown fields, types,
versions and mutable/incompatible values fail before command dispatch.
"""

from __future__ import annotations

import json
import math
import types
from dataclasses import fields, is_dataclass
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from . import contracts

_TYPES = {
    name: value
    for name, value in vars(contracts).items()
    if isinstance(value, type) and is_dataclass(value)
}


def _primitive(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$type": type(value).__name__,
            **{field.name: _primitive(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, tuple):
        return [_primitive(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError(f"not an immutable neutral contract value: {type(value).__name__}")


def _decode(value: Any, hint: Any) -> Any:
    origin = get_origin(hint)
    args = get_args(hint)
    if origin in (Union, types.UnionType):
        for member in args:
            try:
                return _decode(value, member)
            except (ValueError, TypeError):
                continue
        raise ValueError("value does not match declared contract alternatives")
    if origin is Literal:
        if value not in args or not any(type(value) is type(item) for item in args):
            raise ValueError("unsupported literal value")
        return value
    if hint is type(None):
        if value is not None:
            raise ValueError("expected null")
        return None
    if hint in (str, int, float, bool):
        if hint is float and type(value) in (int, float):
            try:
                if math.isfinite(value):
                    return float(value)
            except OverflowError as error:
                raise ValueError("scalar is outside the finite float range") from error
        if type(value) is not hint:
            raise ValueError(f"expected {hint.__name__}")
        return value
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError("expected JSON array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(item, args[0]) for item in value)
        if len(value) != len(args):
            raise ValueError("wrong tuple length")
        return tuple(_decode(item, member) for item, member in zip(value, args, strict=True))
    if isinstance(hint, type) and is_dataclass(hint):
        if not isinstance(value, dict) or value.get("$type") != hint.__name__:
            raise ValueError(f"expected tagged {hint.__name__}")
        field_names = {field.name for field in fields(hint)}
        if set(value) != field_names | {"$type"}:
            raise ValueError(f"unknown or missing {hint.__name__} fields")
        hints = get_type_hints(hint)
        return hint(**{name: _decode(value[name], hints[name]) for name in field_names})
    raise ValueError("unsupported contract type")


def boundary_json(value: Any) -> str:
    """Serialize a validated immutable DTO without redefining scientific hashes."""

    primitive = _primitive(value)
    _decode(primitive, type(value))
    return json.dumps(
        primitive, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def boundary_from_json(data: str) -> Any:
    """Decode only registered, fully typed neutral contracts."""

    value = json.loads(data)
    if not isinstance(value, dict) or value.get("$type") not in _TYPES:
        raise ValueError("unknown neutral contract type")
    return _decode(value, _TYPES[value["$type"]])
