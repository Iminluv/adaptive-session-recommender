"""Contract validation with stable reason codes."""

from typing import Any

from .errors import ValidationError
from .schemas import EVENT_TYPES, Event


REQUIRED_FIELDS = ("schema_version", "event_id", "event_time", "ingest_time", "event_type", "product_id", "event_source")


def validate_event(payload: dict[str, Any]) -> tuple[Event | None, tuple[ValidationError, ...]]:
    errors: list[ValidationError] = []
    for field in REQUIRED_FIELDS:
        if field not in payload or payload[field] in (None, ""):
            errors.append(ValidationError("missing_required_field", f"Missing required field: {field}", field))
    if errors:
        return None, tuple(errors)

    try:
        event = Event.from_dict(payload)
    except (TypeError, ValueError, KeyError) as exc:
        return None, (ValidationError("invalid_field_type", str(exc)),)

    if event.schema_version != 1:
        errors.append(ValidationError("unsupported_schema_version", "schema_version must be 1", "schema_version"))
    if event.event_type not in EVENT_TYPES:
        errors.append(ValidationError("invalid_event_type", f"Unsupported event_type: {event.event_type}", "event_type"))
    if event.product_id <= 0:
        errors.append(ValidationError("invalid_product_id", "product_id must be positive", "product_id"))
    if event.price is not None and event.price < 0:
        errors.append(ValidationError("negative_price", "price must be non-negative", "price"))
    if event.event_time > event.ingest_time:
        errors.append(ValidationError("event_time_after_ingest_time", "event_time cannot be after ingest_time", "event_time"))
    return (event if not errors else None), tuple(errors)

