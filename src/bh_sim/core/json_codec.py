"""Deterministic JSON codec for immutable v1alpha contracts."""

from __future__ import annotations

import hashlib
import json
import types
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from bh_sim.core import contracts as contracts_module
from bh_sim.core import ids as ids_module
from bh_sim.core import quantity as quantity_module

_CONTRACT_TYPES = {
    value.__name__: value
    for module in (contracts_module, ids_module, quantity_module)
    for value in vars(module).values()
    if isinstance(value, type) and is_dataclass(value)
}


def _to_primitive(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$type": type(value).__name__,
            **{item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)},
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_to_primitive(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported contract value: {type(value).__name__}")


def _decode_with_hint(value: Any, hint: Any = Any) -> Any:
    if isinstance(value, dict) and "$type" in value:
        type_name = value["$type"]
        try:
            contract_type = _CONTRACT_TYPES[type_name]
        except KeyError as error:
            raise ValueError(f"unknown contract type: {type_name!r}") from error
        hints = get_type_hints(contract_type)
        expected = {item.name for item in fields(contract_type)}
        actual = set(value) - {"$type"}
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(f"invalid {type_name} fields; missing={missing}, extra={extra}")
        return contract_type(
            **{name: _decode_with_hint(value[name], hints.get(name, Any)) for name in expected}
        )

    if hint is Any:
        if isinstance(value, list):
            return tuple(_decode_with_hint(item) for item in value)
        return value

    origin = get_origin(hint)
    arguments = get_args(hint)
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError("expected a JSON array for tuple field")
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(_decode_with_hint(item, arguments[0]) for item in value)
        if len(value) != len(arguments):
            raise ValueError("fixed tuple has the wrong number of elements")
        return tuple(
            _decode_with_hint(item, item_hint)
            for item, item_hint in zip(value, arguments, strict=True)
        )
    if origin in (Union, types.UnionType):
        if value is None and type(None) in arguments:
            return None
        # Tagged dataclasses identify themselves. Remaining primitive unions are
        # decoded against the first compatible member.
        for member in arguments:
            if member is type(None):
                continue
            try:
                return _decode_with_hint(value, member)
            except (TypeError, ValueError):
                continue
        raise ValueError(f"value does not match union {hint!r}")
    if isinstance(hint, type) and issubclass(hint, Enum):
        return hint(value)
    if hint in (str, int, float, bool):
        if hint is float and isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if not isinstance(value, hint):
            raise ValueError(f"expected {hint.__name__}, received {type(value).__name__}")
        return value
    if value is None:
        return None
    return value


def canonical_json(value: Any) -> str:
    """Serialize a contract deterministically for interchange and hashing."""

    return json.dumps(
        _to_primitive(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def contract_from_json(data: str) -> Any:
    """Load and validate one registered contract object."""

    parsed = json.loads(data)
    if not isinstance(parsed, dict) or "$type" not in parsed:
        raise ValueError("contract JSON must contain a tagged object at its root")
    return _decode_with_hint(parsed)


def contract_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_contract(path: str | Path, value: Any) -> None:
    """Write canonical JSON to an explicitly selected path."""

    Path(path).write_text(canonical_json(value) + "\n", encoding="utf-8")


def read_contract(path: str | Path) -> Any:
    return contract_from_json(Path(path).read_text(encoding="utf-8"))
