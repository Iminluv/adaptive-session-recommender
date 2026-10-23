#!/usr/bin/env python3
"""Validate a JSONL fixture and print a reproducible summary."""

import json
import sys
from collections import Counter
from pathlib import Path

from adaptive_recommender.common.validation import validate_event


def main(path: str) -> int:
    counts = Counter()
    valid = 0
    invalid = 0
    seen_ids: set[str] = set()
    duplicates = 0
    for line_number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        event, errors = validate_event(payload)
        if event is None:
            invalid += 1
            counts.update(error.code for error in errors)
            continue
        valid += 1
        if event.event_id in seen_ids:
            duplicates += 1
        seen_ids.add(event.event_id)
        counts[event.event_type] += 1
    print(f"fixture={path}")
    print(f"valid={valid} invalid={invalid} duplicate_ids={duplicates}")
    print("counts=" + json.dumps(dict(sorted(counts.items())), sort_keys=True))
    return 0 if valid and invalid else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

