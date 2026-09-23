"""Temporary data and external-boundary controls; no fake BH application services."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path

import pytest
from harness import Client


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Client]:
    original = socket.socket.connect

    def local_only(sock, address):
        if isinstance(address, tuple):
            assert address[0] in {"127.0.0.1", "::1", "localhost"}, (
                "Acceptance must not contact a live provider"
            )
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)
    result = Client(tmp_path / "project")
    yield result
    result.close()
