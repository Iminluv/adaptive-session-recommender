"""Deterministic identifiers for replayed source records."""

import hashlib


def replay_event_id(source_file: str, row_number: int) -> str:
    """Return the stable ID for one source row, including its source position."""
    if not source_file:
        raise ValueError("source_file must not be empty")
    if row_number < 1:
        raise ValueError("row_number must be positive")
    raw = f"{source_file}:{row_number}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

