import unittest
from datetime import datetime, timezone

from adaptive_recommender.common.event_ids import replay_event_id
from adaptive_recommender.common.validation import validate_event


def valid_payload() -> dict:
    return {
        "schema_version": 1,
        "event_id": "event-1",
        "event_time": "2019-10-01T10:00:00Z",
        "ingest_time": "2019-10-01T10:00:01Z",
        "event_type": "view",
        "product_id": 1001,
        "category_id": 10,
        "category_code": "electronics.smartphone",
        "brand": "demo",
        "price": 499.0,
        "user_id": "user-1",
        "user_session": "session-1",
        "event_source": "test",
    }


class ContractTests(unittest.TestCase):
    def test_valid_event_is_parsed_with_timezone(self):
        event, errors = validate_event(valid_payload())
        self.assertEqual(errors, ())
        self.assertIsNotNone(event)
        self.assertEqual(event.event_time.tzinfo, timezone.utc)

    def test_missing_required_field_is_rejected(self):
        payload = valid_payload()
        del payload["event_id"]
        event, errors = validate_event(payload)
        self.assertIsNone(event)
        self.assertEqual(errors[0].code, "missing_required_field")

    def test_invalid_type_is_rejected(self):
        payload = valid_payload()
        payload["product_id"] = "not-an-id"
        event, errors = validate_event(payload)
        self.assertIsNone(event)
        self.assertEqual(errors[0].code, "invalid_field_type")

    def test_negative_price_is_rejected(self):
        payload = valid_payload()
        payload["price"] = -1
        event, errors = validate_event(payload)
        self.assertIsNone(event)
        self.assertEqual(errors[0].code, "negative_price")

    def test_future_event_time_is_rejected(self):
        payload = valid_payload()
        payload["event_time"] = "2019-10-01T10:00:02Z"
        event, errors = validate_event(payload)
        self.assertIsNone(event)
        self.assertEqual(errors[0].code, "event_time_after_ingest_time")

    def test_replay_id_is_deterministic(self):
        first = replay_event_id("october.csv", 42)
        second = replay_event_id("october.csv", 42)
        self.assertEqual(first, second)
        self.assertNotEqual(first, replay_event_id("october.csv", 43))


if __name__ == "__main__":
    unittest.main()

