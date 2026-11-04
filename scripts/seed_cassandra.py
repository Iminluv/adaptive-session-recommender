"""Seed Cassandra tables with Gold ALS candidates and product statistics."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


def seed_cassandra(data_dir: Path | str = "data/generated", host: str = "localhost", port: int = 9042) -> dict:
    data_path = Path(data_dir)
    candidates_path = data_path / "gold" / "als_candidates"
    product_stats_path = data_path / "gold" / "product_stats"

    if not candidates_path.exists() or not product_stats_path.exists():
        raise FileNotFoundError(f"Gold artifacts missing in {data_path}. Run `make batch-sample` first.")

    try:
        from cassandra.cluster import Cluster
        from cassandra.query import BatchStatement
    except ImportError:
        raise RuntimeError("cassandra-driver is not installed. Run `pip install -e .`")

    try:
        cluster = Cluster([host], port=port, connect_timeout=5.0)
        session = cluster.connect()
    except Exception as exc:
        raise ConnectionError(f"Could not connect to Cassandra at {host}:{port}: {exc}") from exc

    # Ensure keyspace and schema tables exist
    init_cql_path = Path(__file__).resolve().parent.parent / "deploy" / "cassandra" / "init.cql"
    if init_cql_path.exists():
        cql_commands = [cmd.strip() for cmd in init_cql_path.read_text().split(";") if cmd.strip()]
        for cmd in cql_commands:
            session.execute(cmd)
    else:
        session.execute(
            """
            CREATE KEYSPACE IF NOT EXISTS ecommerce
              WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
            """
        )
    session.set_keyspace("ecommerce")

    # Read data
    candidates_table = pq.read_table(str(candidates_path))
    products_table = pq.read_table(str(product_stats_path))

    now = datetime.now(timezone.utc)

    # 1. Seed recommendation candidates
    c_stmt = session.prepare(
        """
        INSERT INTO recommendation_candidates (user_id, rank, product_id, als_score, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
    )
    c_count = 0
    for r in candidates_table.to_pylist():
        session.execute(
            c_stmt,
            (
                str(r["user_id"]),
                int(r["rank"]),
                int(r["product_id"]),
                float(r["als_score"]),
                now,
            ),
        )
        c_count += 1

    # 2. Seed product stats
    p_stmt = session.prepare(
        """
        INSERT INTO product_stats (product_id, category_code, brand, event_count, unique_users, average_price, popularity_score, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )
    raw_products = products_table.to_pylist()
    max_events = max((int(r.get("event_count", 0)) for r in raw_products), default=1)
    max_events = max(max_events, 1)

    p_count = 0
    for r in raw_products:
        pid = int(r["product_id"])
        ev_count = int(r.get("event_count", 0))
        pop_score = round(ev_count / max_events, 4)
        avg_price = float(r["average_price"]) if r.get("average_price") is not None else None
        session.execute(
            p_stmt,
            (
                pid,
                r.get("category_code"),
                r.get("brand"),
                ev_count,
                int(r.get("unique_users", 0)),
                avg_price,
                pop_score,
                now,
            ),
        )
        p_count += 1

    cluster.shutdown()
    return {
        "status": "SUCCESS",
        "candidates_seeded": c_count,
        "products_seeded": p_count,
        "keyspace": "ecommerce",
        "host": host,
        "port": port,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Cassandra with generated Gold artifacts")
    parser.add_argument("--data-dir", default="data/generated", type=Path)
    parser.add_argument("--host", default="localhost", type=str)
    parser.add_argument("--port", default=9042, type=int)
    args = parser.parse_args()

    try:
        res = seed_cassandra(args.data_dir, args.host, args.port)
        import json
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
