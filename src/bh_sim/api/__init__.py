"""HTTP adapter whose schema imports do not construct an application."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import create_app

__all__ = ["create_app"]


def __getattr__(name: str) -> Any:
    """Retain the factory import without eager composition."""

    if name != "create_app":
        raise AttributeError(name)
    return import_module(".app", __name__).create_app
