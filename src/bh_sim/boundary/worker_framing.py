"""Length-prefixed binary stream framing for worker IPC.

Messages are serialized using the strict boundary JSON codec and framed with a
4-byte big-endian length prefix. Frames exceeding MAX_FRAME_SIZE are rejected
to prevent unbounded memory allocation.
"""

from __future__ import annotations

import struct
from typing import BinaryIO

from .json_codec import boundary_from_json, boundary_json

MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10 MB


class FramingError(ValueError):
    """Base error for framing protocol violations."""


class FrameSizeError(FramingError):
    """Raised when a message exceeds the maximum permitted frame size."""


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    """Read exactly count bytes from stream, raising FramingError on partial read."""
    data = bytearray()
    while len(data) < count:
        chunk = stream.read(count - len(data))
        if not chunk:
            if not data:
                return b""
            raise FramingError(f"Unexpected EOF: read {len(data)} of {count} expected bytes")
        data.extend(chunk)
    return bytes(data)


def write_frame(stream: BinaryIO, message: object) -> None:
    """Serialize and write a length-prefixed frame to the binary stream."""
    encoded = boundary_json(message).encode("utf-8")
    if len(encoded) > MAX_FRAME_SIZE:
        raise FrameSizeError(
            f"Message payload size {len(encoded)} bytes exceeds limit {MAX_FRAME_SIZE} bytes"
        )
    header = struct.pack("!I", len(encoded))
    stream.write(header + encoded)
    stream.flush()


def read_frame(stream: BinaryIO) -> object | None:
    """Read and deserialize a length-prefixed frame. Returns None on clean EOF."""
    header = _read_exact(stream, 4)
    if not header:
        return None
    if len(header) < 4:
        raise FramingError("Incomplete frame length header")
    length = struct.unpack("!I", header)[0]
    if length > MAX_FRAME_SIZE:
        raise FrameSizeError(
            f"Incoming frame size {length} bytes exceeds maximum permitted {MAX_FRAME_SIZE} bytes"
        )
    body = _read_exact(stream, length)
    if len(body) < length:
        raise FramingError(f"Incomplete frame body: expected {length} bytes, got {len(body)}")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FramingError("Frame body is not valid UTF-8 text") from error
    return boundary_from_json(text)
