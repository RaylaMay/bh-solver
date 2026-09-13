"""Unit-model descriptors and factories."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from bh_sim.core import (
    MaterialReference,
    Port,
    StableId,
    UnitDefinition,
    UnitOperation,
)

from .properties import PropertyRegistry


@dataclass(frozen=True)
class ModelDescriptor:
    model_id: str
    ports: tuple[Port, ...]
    required_parameters: tuple[str, ...] = ()
    optional_parameters: tuple[str, ...] = ()
    required_metadata: tuple[str, ...] = ()


ModelFactory = Callable[[UnitDefinition, "EvaluationServices"], UnitOperation]


@dataclass(frozen=True)
class EvaluationServices:
    properties: PropertyRegistry
    materials: Mapping[StableId, MaterialReference]


class ModelCatalog:
    def __init__(self) -> None:
        self._descriptors: dict[str, ModelDescriptor] = {}
        self._factories: dict[str, ModelFactory] = {}

    def register(self, descriptor: ModelDescriptor, factory: ModelFactory) -> None:
        if descriptor.model_id in self._descriptors:
            raise ValueError(f"duplicate unit model: {descriptor.model_id}")
        self._descriptors[descriptor.model_id] = descriptor
        self._factories[descriptor.model_id] = factory

    def descriptor(self, model_id: str) -> ModelDescriptor:
        try:
            return self._descriptors[model_id]
        except KeyError as error:
            raise KeyError(f"unknown unit model: {model_id}") from error

    def build(self, definition: UnitDefinition, services: EvaluationServices) -> UnitOperation:
        try:
            factory = self._factories[definition.model_id]
        except KeyError as error:
            raise KeyError(f"unknown unit model: {definition.model_id}") from error
        return factory(definition, services)

    @property
    def model_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._descriptors))


def reference_model_catalog() -> ModelCatalog:
    from .models import register_reference_models

    catalog = ModelCatalog()
    register_reference_models(catalog)
    return catalog
