"""Spark Structured Streaming job validating Kafka events and aggregating session intent."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyspark.sql import SparkSession, functions as F, types as T

from adaptive_recommender.batch.run_sample import EVENT_SCHEMA, EVENT_TYPES
from adaptive_recommender.streaming.session_intent import (
    compute_session_intent,
    write_session_intent_to_cassandra,
)


def run_stream_pipeline(
    bootstrap_servers: str = "localhost:9092",
    input_topics: str = "ecommerce.replay,ecommerce.live",
    dlq_topic: str = "ecommerce.dlq",
    cassandra_host: str = "localhost",
    cassandra_port: int = 9042,
    checkpoint_dir: Path | str = "data/checkpoints/session_intent",
    watermark: str = "10 minutes",
    once: bool = True,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    run_id = started_at.strftime("%Y%m%dT%H%M%S%fZ")

    spark = (
        SparkSession.builder.appName("adaptive-recommender-stream-events")
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    # Read from Kafka stream
    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", input_topics)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # Parse JSON value
    parsed = kafka_df.select(
        F.from_json(F.col("value").cast("string"), EVENT_SCHEMA).alias("data"),
        F.col("timestamp").alias("kafka_timestamp"),
    ).select("data.*", "kafka_timestamp")

    # Classify data quality
    valid_condition = F.coalesce(
        (
            F.col("schema_version").eqNullSafe(1)
            & F.col("event_id").isNotNull()
            & (F.length(F.trim(F.col("event_id"))) > 0)
            & F.col("event_time").isNotNull()
            & F.col("ingest_time").isNotNull()
            & F.col("event_type").isin(*EVENT_TYPES)
            & (F.col("product_id") > 0)
            & (F.col("price").isNull() | (F.col("price") >= 0))
            & (F.col("event_time") <= F.col("ingest_time"))
        ),
        F.lit(False),
    )

    classified = parsed.withColumn(
        "quality_error",
        F.when(F.col("schema_version").isNull() | (F.col("schema_version") != 1), "invalid_schema_version")
        .when(F.col("event_id").isNull() | (F.length(F.trim(F.col("event_id"))) == 0), "missing_event_id")
        .when(F.col("event_time").isNull(), "missing_event_time")
        .when(F.col("ingest_time").isNull(), "missing_ingest_time")
        .when(F.col("event_type").isNull() | ~F.col("event_type").isin(*EVENT_TYPES), "invalid_event_type")
        .when(F.col("product_id").isNull() | (F.col("product_id") <= 0), "invalid_product_id")
        .when(F.col("price").isNotNull() & (F.col("price") < 0), "negative_price")
        .when(F.col("event_time") > F.col("ingest_time"), "event_time_after_ingest_time"),
    )

    valid_events = (
        classified.filter(valid_condition)
        .withWatermark("event_time", watermark)
        .dropDuplicates(["event_id", "event_time"])
    )

    invalid_events = classified.filter(~valid_condition)

    # Process and write valid session intent
    session_intents = compute_session_intent(valid_events)

    processed_counts = {"valid": 0, "invalid": 0, "intents_written": 0}

    def process_microbatch(batch_df: DataFrame, batch_id: int) -> None:
        count = write_session_intent_to_cassandra(
            batch_df=batch_df,
            batch_id=batch_id,
            host=cassandra_host,
            port=cassandra_port,
        )
        processed_counts["intents_written"] += count

    query_builder = (
        session_intents.writeStream.outputMode("update")
        .foreachBatch(process_microbatch)
        .option("checkpointLocation", str(Path(checkpoint_dir) / "intent"))
    )

    # Also route invalid events to DLQ
    def process_dlq_microbatch(dlq_batch_df: DataFrame, batch_id: int) -> None:
        if dlq_batch_df.isEmpty():
            return
        try:
            from kafka import KafkaProducer

            producer = KafkaProducer(
                bootstrap_servers=[s.strip() for s in bootstrap_servers.split(",")],
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            for row in dlq_batch_df.collect():
                row_dict = row.asDict()
                producer.send(dlq_topic, key=str(row_dict.get("event_id") or ""), value=row_dict)
                processed_counts["invalid"] += 1
            producer.flush()
            producer.close()
        except Exception as exc:
            print(f"Warning: DLQ producer error: {exc}", file=sys.stderr)

    dlq_query_builder = (
        invalid_events.writeStream.foreachBatch(process_dlq_microbatch)
        .option("checkpointLocation", str(Path(checkpoint_dir) / "dlq"))
    )

    if once:
        query = query_builder.trigger(availableNow=True).start()
        dlq_query = dlq_query_builder.trigger(availableNow=True).start()
        query.awaitTermination()
        dlq_query.awaitTermination()
    else:
        query = query_builder.start()
        dlq_query = dlq_query_builder.start()
        if timeout_seconds:
            query.awaitTermination(timeout_seconds)
            dlq_query.awaitTermination(timeout_seconds)
            query.stop()
            dlq_query.stop()
        else:
            query.awaitTermination()
            dlq_query.awaitTermination()

    elapsed = round(time.monotonic() - started_clock, 3)
    spark.stop()

    manifest = {
        "run_id": run_id,
        "status": "COMPLETED",
        "input_topics": input_topics,
        "dlq_topic": dlq_topic,
        "watermark": watermark,
        "intents_written": processed_counts["intents_written"],
        "dlq_events_routed": processed_counts["invalid"],
        "elapsed_seconds": elapsed,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = Path("data/generated/manifests") / f"streaming-{run_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PySpark Structured Streaming for session intent")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topics", default="ecommerce.replay,ecommerce.live")
    parser.add_argument("--dlq-topic", default="ecommerce.dlq")
    parser.add_argument("--cassandra-host", default="localhost")
    parser.add_argument("--cassandra-port", type=int, default=9042)
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("data/checkpoints/session_intent"))
    parser.add_argument("--watermark", default="10 minutes")
    parser.add_argument("--continuous", action="store_true", help="Run continuously instead of availableNow")
    parser.add_argument("--timeout", type=int, default=None, help="Timeout in seconds for continuous mode")
    args = parser.parse_args()

    try:
        manifest = run_stream_pipeline(
            bootstrap_servers=args.bootstrap_servers,
            input_topics=args.topics,
            dlq_topic=args.dlq_topic,
            cassandra_host=args.cassandra_host,
            cassandra_port=args.cassandra_port,
            checkpoint_dir=args.checkpoint_dir,
            watermark=args.watermark,
            once=not args.continuous,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(manifest, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
