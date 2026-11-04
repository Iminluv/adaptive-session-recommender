"""Session intent scoring and feature aggregation logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pyspark.sql import DataFrame, functions as F


SESSION_WEIGHTS = {
    "view": 1.0,
    "cart": 4.0,
    "remove_from_cart": -3.0,
    "purchase": 5.0,
}


def compute_session_intent(valid_events_df: DataFrame) -> DataFrame:
    """Compute real-time session intent scores by user, session, and category."""
    # Filter for session-relevant events having category, session, and user
    filtered = valid_events_df.filter(
        F.col("user_id").isNotNull()
        & F.col("user_session").isNotNull()
        & F.col("category_code").isNotNull()
        & F.col("event_type").isin(*SESSION_WEIGHTS)
    )

    weight_expr = F.when(F.col("event_type") == "view", F.lit(SESSION_WEIGHTS["view"]))
    weight_expr = weight_expr.when(F.col("event_type") == "cart", F.lit(SESSION_WEIGHTS["cart"]))
    weight_expr = weight_expr.when(F.col("event_type") == "remove_from_cart", F.lit(SESSION_WEIGHTS["remove_from_cart"]))
    weight_expr = weight_expr.when(F.col("event_type") == "purchase", F.lit(SESSION_WEIGHTS["purchase"]))

    weighted = filtered.withColumn("weight", weight_expr)

    # Aggregate by (user_id, user_session, category_code)
    aggregated = (
        weighted.groupBy("user_id", "user_session", "category_code")
        .agg(
            F.sum("weight").alias("raw_score"),
            F.max("event_time").alias("last_event_time"),
            F.count(F.lit(1)).alias("event_count"),
        )
    )

    # Intent score is non-negative; bounded between 0.0 and 1.0 using tanh scaling
    # normalized_score = 2 / (1 + exp(-raw_score / 5)) - 1 if raw_score > 0 else 0
    intent_score_expr = F.when(
        F.col("raw_score") > 0,
        F.round((2.0 / (1.0 + F.exp(-F.col("raw_score") / 5.0))) - 1.0, 4),
    ).otherwise(F.lit(0.0))

    return aggregated.withColumn("intent_score", intent_score_expr)


def write_session_intent_to_cassandra(
    batch_df: DataFrame,
    batch_id: int,
    host: str = "localhost",
    port: int = 9042,
    keyspace: str = "ecommerce",
) -> int:
    """Micro-batch writer upserting session intent records into Cassandra."""
    if batch_df.isEmpty():
        return 0

    try:
        from cassandra.cluster import Cluster
    except ImportError:
        print("cassandra-driver not available, skipping Cassandra upsert")
        return 0

    cluster = Cluster([host], port=port, connect_timeout=5.0)
    session = cluster.connect(keyspace)

    stmt = session.prepare(
        """
        INSERT INTO session_intent (user_id, user_session, category_code, intent_score, last_event_time, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
    )

    rows = batch_df.collect()
    now = datetime.now(timezone.utc)
    count = 0
    for r in rows:
        session.execute(
            stmt,
            (
                str(r["user_id"]),
                str(r["user_session"]),
                str(r["category_code"]),
                float(r["intent_score"]),
                r["last_event_time"],
                now,
            ),
        )
        count += 1

    cluster.shutdown()
    return count
