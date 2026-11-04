"""Unit tests for the Kafka replay producer."""

import json
import tempfile
import unittest
from pathlib import Path

from adaptive_recommender.streaming.replay_producer import (
    build_replayed_event,
    replay_events,
)


class ReplayProducerTests(unittest.TestCase):
    def test_build_replayed_event_generates_deterministic_id(self) -> None:
        raw = {
            "schema_version": 1,
            "event_time": "2019-11-01T00:00:00Z",
            "event_type": "view",
            "product_id": 1001,
        }
        res1 = build_replayed_event(raw, "source.jsonl", 1)
        res2 = build_replayed_event(raw, "source.jsonl", 1)
        self.assertEqual(res1["event_id"], res2["event_id"])
        self.assertEqual(res1["event_time"], "2019-11-01T00:00:00Z")
        self.assertIn("ingest_time", res1)
        self.assertEqual(res1["event_source"], "historical_replay")

    def test_build_replayed_event_preserves_existing_id(self) -> None:
        raw = {
            "schema_version": 1,
            "event_id": "my-fixed-id-99",
            "event_time": "2019-11-01T00:00:00Z",
            "event_type": "view",
            "product_id": 1001,
        }
        res = build_replayed_event(raw, "source.jsonl", 5)
        self.assertEqual(res["event_id"], "my-fixed-id-99")

    def test_replay_dry_run_produces_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fixture_file = tmp_path / "sample.jsonl"
            fixture_file.write_text(
                json.dumps({"schema_version": 1, "event_time": "2019-11-01T00:00:00Z", "event_type": "view", "product_id": 1001}) + "\n"
                + json.dumps({"schema_version": 1, "event_time": "2019-11-01T00:00:01Z", "event_type": "cart", "product_id": 1002}) + "\n"
            )
            manifest_dir = tmp_path / "manifests"

            manifest = replay_events(
                input_path=fixture_file,
                dry_run=True,
                rate=0,
                manifest_dir=manifest_dir,
            )

            self.assertEqual(manifest["status"], "SUCCESS")
            self.assertEqual(manifest["events_sent"], 2)
            self.assertEqual(manifest["events_failed"], 0)
            self.assertTrue(list(manifest_dir.glob("replay-*.json")))


if __name__ == "__main__":
    unittest.main()
