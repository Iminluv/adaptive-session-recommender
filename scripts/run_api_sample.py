"""Verify serving API endpoints against local generated batch artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app


def run_sample_verification(data_dir: Path | str = "data/generated") -> dict:
    data_path = Path(data_dir)
    app = create_app()
    client = TestClient(app)

    # 1. Health
    health_resp = client.get("/health")
    health_data = health_resp.json()
    if health_resp.status_code != 200:
        raise RuntimeError(f"Health check failed: {health_data}")

    # 2. Products
    products_resp = client.get("/products?limit=5")
    products_data = products_resp.json()
    if products_resp.status_code != 200:
        raise RuntimeError(f"Products endpoint failed: {products_data}")

    # 3. Known user recommendations (ALS candidates from October batch)
    known_resp = client.get("/recommendations/user-1?limit=3")
    known_data = known_resp.json()
    if known_resp.status_code != 200 or known_data.get("fallback") is not False:
        raise RuntimeError(f"Known user recommendation failed: {known_data}")

    # 4. Unknown user recommendations (Popularity fallback)
    unknown_resp = client.get("/recommendations/anonymous-guest?limit=3")
    unknown_data = unknown_resp.json()
    if unknown_resp.status_code != 200 or unknown_data.get("fallback") is not True:
        raise RuntimeError(f"Unknown user fallback failed: {unknown_data}")

    # 5. Ingest event
    now = datetime.now(timezone.utc).isoformat()
    event_payload = {
        "schema_version": 1,
        "event_id": "api-sample-probe-1",
        "event_time": now,
        "ingest_time": now,
        "event_type": "view",
        "product_id": 1001,
        "category_id": 2053013555631882655,
        "category_code": "electronics.smartphone",
        "brand": "samsung",
        "price": 499.0,
        "user_id": "user-1",
        "user_session": "sample-session",
        "event_source": "api_sample",
    }
    event_resp = client.post("/events", json=event_payload)
    event_data = event_resp.json()
    if event_resp.status_code != 202:
        raise RuntimeError(f"Event ingestion probe failed: {event_data}")

    summary = {
        "status": "PASSED",
        "health": health_data,
        "products_count": products_data["count"],
        "known_user": {
            "user_id": known_data["user_id"],
            "fallback": known_data["fallback"],
            "top_product": known_data["recommendations"][0]["product_id"] if known_data["recommendations"] else None,
            "top_score": known_data["recommendations"][0]["score"] if known_data["recommendations"] else None,
            "reason": known_data["recommendations"][0]["reason"] if known_data["recommendations"] else None,
        },
        "unknown_user": {
            "user_id": unknown_data["user_id"],
            "fallback": unknown_data["fallback"],
            "top_product": unknown_data["recommendations"][0]["product_id"] if unknown_data["recommendations"] else None,
            "reason": unknown_data["recommendations"][0]["reason"] if unknown_data["recommendations"] else None,
        },
        "event_probe": {
            "status": event_data["status"],
            "event_id": event_data["event_id"],
        },
    }
    return summary


def main() -> int:
    try:
        result = run_sample_verification()
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
