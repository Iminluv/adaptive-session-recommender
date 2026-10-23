"""Stable validation errors shared by batch, streaming, and API adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    field: str | None = None

