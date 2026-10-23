"""Canonical event contract for every project boundary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


EVENT_TYPES = frozenset({"view", "cart", "remove_from_cart", "purchase"})


@dataclass(frozen=True)
class Event:
    schema_version: int
    event_id: str
    event_time: datetime
    ingest_time: datetime
    event_type: str
    product_id: int
    category_id: int | None
    category_code: str | None
    brand: str | None
    price: float | None
    user_id: str | None
    user_session: str | None
    event_source: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Event":
        """Build an Event without hiding validation errors."""
        return cls(
            schema_version=int(payload["schema_version"]),
            event_id=str(payload["event_id"]),
            event_time=_parse_datetime(payload["event_time"]),
            ingest_time=_parse_datetime(payload["ingest_time"]),
            event_type=str(payload["event_type"]),
            product_id=int(payload["product_id"]),
            category_id=_optional_int(payload.get("category_id")),
            category_code=_optional_str(payload.get("category_code")),
            brand=_optional_str(payload.get("brand")),
            price=_optional_float(payload.get("price")),
            user_id=_optional_str(payload.get("user_id")),
            user_session=_optional_str(payload.get("user_session")),
            event_source=str(payload["event_source"]),
        )


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)

