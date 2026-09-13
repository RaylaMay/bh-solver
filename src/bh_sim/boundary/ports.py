"""Interaction-side command port; peers exchange only immutable neutral values."""

from typing import Protocol

from .contracts import CommandOutcome, CommandRequest


class CommandGateway(Protocol):
    """Available commands and synchronous dispatch; no concrete service ownership."""

    @property
    def command_names(self) -> tuple[str, ...]: ...

    def dispatch(self, request: CommandRequest) -> CommandOutcome: ...
