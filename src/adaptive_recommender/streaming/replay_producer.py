"""Kafka replay producer preserving historical event time and setting current ingest time."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptive_recommender.common.event_ids import replay_event_id


def build_replayed_event(row: dict[str, Any], source_file: str, row_idx: int) -> dict[str, Any]:
    """Enrich a source event row with deterministic ID and current ingest timestamp."""
    event = dict(row)
    if not event.get("event_id"):
        event["event_id"] = replay_event_id(source_file, row_idx)

    # Ingest time is strictly the processing/arrival time
    event["ingest_time"] = datetime.now(timezone.utc).isoformat()
    if not event.get("event_source"):
        event["event_source"] = "historical_replay"
    return event


def replay_events(
    input_path: Path | str,
    bootstrap_servers: str = "localhost:9092",
    topic: str = "ecommerce.replay",
    rate: float = 10.0,
    dry_run: bool = False,
    manifest_dir: Path | str = "data/generated/manifests",
) -> dict[str, Any]:
    file_path = Path(input_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input fixture file not found: {file_path}")

    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    run_id = started_at.strftime("%Y%m%dT%H%M%S%fZ")

    producer = None
    if not dry_run:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=[s.strip() for s in bootstrap_servers.split(",")],
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
        )

    events_sent = 0
    events_failed = 0
    first_event_id = None
    last_event_id = None
    offsets: list[int] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw_row = json.loads(line)
                event = build_replayed_event(raw_row, file_path.name, idx)
                eid = event["event_id"]
                if first_event_id is None:
                    first_event_id = eid
                last_event_id = eid

                if not dry_run and producer is not None:
                    user_key = str(event.get("user_id") or "")
                    future = producer.send(topic, key=user_key or None, value=event)
                    record_metadata = future.get(timeout=10.0)
                    offsets.append(record_metadata.offset)

                events_sent += 1

                if rate > 0:
                    time.sleep(1.0 / rate)
            except Exception as exc:
                events_failed += 1
                print(f"Warning: failed row {idx}: {exc}", file=sys.stderr)

    if producer:
        producer.flush()
        producer.close()

    elapsed = round(time.monotonic() - started_clock, 3)
    manifest = {
        "run_id": run_id,
        "status": "SUCCESS" if events_sent > 0 else "EMPTY",
        "input_path": str(file_path),
        "topic": topic,
        "bootstrap_servers": bootstrap_servers,
        "rate": rate,
        "dry_run": dry_run,
        "events_sent": events_sent,
        "events_failed": events_failed,
        "first_event_id": first_event_id,
        "last_event_id": last_event_id,
        "min_offset": min(offsets) if offsets else None,
        "max_offset": max(offsets) if offsets else None,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
    }

    manifest_path = Path(manifest_dir) / f"replay-{run_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay historical events to Kafka with rate limiting")
    parser.add_argument("--input", type=Path, default=Path("data/sample/events.jsonl"))
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topic", default="ecommerce.replay")
    parser.add_argument("--rate", type=float, default=10.0, help="Events per second")
    parser.add_argument("--dry-run", action="store_true", help="Format and validate without sending to Kafka")
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/generated/manifests"))
    args = parser.parse_args()

    try:
        manifest = replay_events(
            input_path=args.input,
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
            rate=args.rate,
            dry_run=args.dry_run,
            manifest_dir=args.manifest_dir,
        )
        print(json.dumps(manifest, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
