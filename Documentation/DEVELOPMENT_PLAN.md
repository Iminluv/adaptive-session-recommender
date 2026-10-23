# Development Plan

## Adaptive Session-Aware Product Recommendation System

**Project type:** IT4043E Big Data Storage and Processing milestone project  
**Team:** 3 university students  
**Delivery window:** 4 weeks  
**Planning baseline:** 2026-10-22  
**Architecture:** Lambda Architecture  
**Primary language:** Python / PySpark  
**Primary evidence:** reproducible pipeline, benchmark results, recovery evidence, and live demo

## Executive decision

Build one complete Lambda-style system around the fixed project context:

```text
October REES46 data
  -> HDFS Bronze
  -> Spark batch cleaning and feature generation
  -> Silver Parquet + Gold aggregates
  -> Spark MLlib ALS candidates
  -> Cassandra serving tables

November replay + live web events
  -> Kafka
  -> Spark Structured Streaming
  -> validation, deduplication, watermark, stateful session intent
  -> Cassandra session state
  -> FastAPI normalization and re-ranking
  -> React/Vite demo
```

The four-week constraint makes a full production platform unrealistic. The plan therefore has a strict cut line:

- **Must pass:** one end-to-end sample path, October batch path, November replay path, live event path, adaptive re-ranking, cold-start fallback, HDFS, Parquet, Kafka, Spark Structured Streaming, Cassandra, FastAPI, React/Vite, recommendation evaluation, Spark optimization evidence, distributed-system benchmark evidence, reproducibility documentation.
- **Course evidence:** windows, pivot/unpivot, advanced aggregations, at least one custom aggregation, broadcast and sort-merge join comparison, partition pruning, caching or persistence, AQE/skew discussion, watermarking, state, checkpoint/restart evidence, and deployment on Kubernetes or a cloud-equivalent environment.
- **Cut first if blocked:** rich UI, full 20,000 events/s stress test, eight-executor scaling, hybrid replay/live polish, Grafana dashboards beyond the core panels, advanced ML tuning, GraphFrames.

This preserves the course focus on Big Data Storage and Processing instead of spending the final week on frontend polish.

## Requirements basis

The course page states that the milestone must implement Lambda or Kappa Architecture and an end-to-end ingestion → processing → storage → visualization pipeline. It lists Spark, HDFS or equivalent distributed storage, Kafka/RabbitMQ or equivalent message queue, NoSQL, and Kubernetes or cloud deployment as the technology requirements. It also calls for Spark work covering complex aggregations, advanced transformations, joins, optimization, Structured Streaming, watermarking, state management, and exactly-once discussion. The report must cover problem definition, architecture/design, implementation details, deployment/monitoring, and lessons learned.

Source: [IT4043E - Big data storage and processing](https://datalab.vn/teaching/it4043e-big-data-storage-and-processing), accessed 2026-10-22.

The source requirement is interpreted conservatively: exactly-once is treated as a design and recovery claim to test, not a default guarantee for Kafka plus Cassandra.

## Fixed project decisions carried into the plan

| Decision | Plan treatment |
|---|---|
| October is train/history | All batch profiles, implicit feedback, ALS training, and optimization baselines use October only. |
| November is test/replay | November events remain chronological held-out data and replay input. |
| Historical replay is simulated streaming | Reports distinguish replay from actual live browser events. |
| Live event semantics are fixed | `view` means product open, `cart` means explicit add, `remove_from_cart` means explicit removal, `purchase` means successful checkout. |
| Original `product_id` is preserved | It remains the join key across source data, ALS, catalog, events, serving, and recommendations. |
| ALS is offline | No per-click retraining. Live behavior updates session state and re-ranking only. |
| Score components are normalized | Raw ALS, intent, popularity, and brand scores are never added blindly. |
| Cold start is required | Known users, new users with clicks, and completely new users each have a fallback. |
| Event time is preserved | Replay keeps the original `event_time` and adds runtime `ingest_time`. |
| Eventual consistency is acceptable | The report states the expected update delay instead of claiming transactional consistency. |
| Exactly-once is not assumed | Use `event_id`, deduplication, deterministic/upsert-friendly keys, checkpointing, and restart tests. |
| Compose first, Kubernetes last | Local development is Docker Compose. Kubernetes is a late smoke deployment and evidence item. |

## Team operating model

Names are placeholders until the team assigns people.

| Member | Primary ownership | Secondary ownership | Weekly expectation |
|---|---|---|---:|
| Member 1 | Data profiling, HDFS, Spark batch, ALS, recommendation evaluation | Report data/method sections | 12–15 h |
| Member 2 | Kafka, Spark Structured Streaming, state, watermark, Cassandra, infrastructure | Distributed benchmarks and recovery | 12–15 h |
| Member 3 | FastAPI, React/Vite demo, serving integration, monitoring, final demo | Re-ranking evaluation and report integration | 12–15 h |

All three members jointly own interface reviews, integration gates, benchmark interpretation, and the final report. No feature is considered complete until a second member can run it from the documented command.

### Collaboration rules

1. Work against the repository structure in `PROJECT_CONTEXT_V2.md`.
2. Every interface change updates schema/config/docs/tests in the same task.
3. Use one shared `.env.example`, one canonical event schema, and one sample dataset.
4. Merge only after a local sample test and a second-member review.
5. Keep a daily `decision-log.md` entry for changed assumptions, failed experiments, and evidence.
6. Do not fabricate benchmark numbers. If a run is unavailable, report the limitation and the reason.

## Four-week schedule

### Week 1: data evidence and batch baseline

**Goal:** prove that the dataset is usable, create a sample mode, and finish the first offline recommendation path.

**Exit gate G1:** October sample → Spark cleaning → implicit feedback → ALS → Top-N candidates → a callable recommendation response.

- Day 1: confirm roles, obtain dataset, inspect schemas, freeze canonical event schema.
- Day 2: measure row/event/null/cardinality/skew statistics and October/November overlap.
- Day 3: create `data/sample/`, HDFS Bronze loader, validation rules, and Silver Parquet layout.
- Day 4: build windows, pivot/unpivot, custom aggregation, user/product/category aggregates, and implicit feedback.
- Day 5: train ALS, generate Top-50/Top-100 candidates, expose a minimal static serving response, and record G1 evidence.

### Week 2: streaming and vertical slice

**Goal:** connect replay, Kafka, Structured Streaming, state, Cassandra, and the minimum serving path.

**Exit gate G2:** a known user can trigger an event that flows through Kafka and Spark Streaming into session state and a recommendation response.

- Day 6: start Compose services, create Kafka topics, implement deterministic event IDs and replay producer.
- Day 7: parse/validate events, route invalid events to DLQ, deduplicate, preserve timestamps, and add checkpoint paths.
- Day 8: implement event-time windows, watermark candidates, stateful session features, and Cassandra sink tables.
- Day 9: implement FastAPI product/event/recommendation endpoints and the catalog-backed UI shell.
- Day 10: integrate one browser click and one cart action end to end; capture logs, screenshots, and latency timestamps.

### Week 3: adaptation, evaluation, and benchmarks

**Goal:** turn the baseline into an adaptive system and generate credible course evidence.

**Exit gate G3:** recommendation quality and distributed-system benchmark runs are reproducible on sample data, with selected full-data runs where hardware permits.

- Day 11: implement session intent weighting, time decay, score normalization, re-ranking, and cold-start branches.
- Day 12: implement temporal recommendation evaluation: Popularity vs ALS vs ALS + Session-Aware Re-ranking.
- Day 13: implement Time-to-Adapt and Purchase HitRate@10 when the held-out data supports it.
- Day 14: run CSV vs Parquet/partition pruning, broadcast vs sort-merge, cache/persistence, and AQE/skew comparisons.
- Day 15: run input-rate vs P95/P99 latency, Kafka lag, and 1/2/4 executor scaling. Record limits instead of extending the run indefinitely.

### Week 4: reliability, deployment, and report

**Goal:** make the system reproducible, explainable, and defensible in a presentation.

**Exit gate G4:** a clean-machine or clean-environment rehearsal can reproduce the sample pipeline, the demo works, evidence is stored, and the report matches the implementation.

- Day 16: add core Prometheus metrics and a small Grafana dashboard; harden Compose startup and health checks.
- Day 17: execute kill/restart from checkpoint, verify duplicate/loss behavior, and document recovery results.
- Day 18: deploy the minimum Compose stack to Kubernetes or approved cloud-equivalent infrastructure; capture the deployment path and limitations.
- Day 19: run the reproduction script, close test gaps, finalize architecture and benchmark diagrams, and freeze the demo dataset/config.
- Day 20: final report edit, demo rehearsal, presentation rehearsal, archive evidence, and final acceptance review.

## Architecture and data contracts

### Lambda layers

| Layer | Inputs | Processing | Outputs | Evidence |
|---|---|---|---|---|
| Batch layer | October CSV | PySpark validation, Bronze/Silver/Gold, aggregates, implicit feedback, ALS | Parquet, ALS candidates, profile/stat tables | Spark UI, explain plans, counts, candidate rows |
| Speed layer | November replay and live events | Kafka, Structured Streaming, deduplication, watermark, stateful session features, intent | Session state, stream metrics, DLQ, checkpoint | Kafka offsets/lag, state metrics, late-event counts, restart run |
| Serving layer | ALS candidates, session intent, catalog, popularity | FastAPI lookup, normalization, re-ranking, fallbacks | Top-K recommendations and demo UI | API contract tests, latency timestamps, screenshots |

### Canonical event schema

```json
{
  "event_id": "uuid-or-deterministic-id",
  "event_time": "original-or-live-event-time",
  "ingest_time": "runtime-ingestion-time",
  "event_type": "view|cart|remove_from_cart|purchase",
  "product_id": 1004856,
  "category_id": 2053013555631882655,
  "category_code": "electronics.smartphone",
  "brand": "samsung",
  "price": 499.0,
  "user_id": "520088904",
  "user_session": "session-id",
  "event_source": "historical_replay|live_demo"
}
```

Required invariants:

- `event_time`, `user_id`, and `product_id` are non-null.
- `price >= 0`.
- `event_type` is one of the four allowed values.
- `event_id` is stable across retries.
- Invalid records go to `ecommerce.dlq`, not silent deletion.
- October events are not used to create features for earlier November timestamps.

### Storage layout

```text
/data/bronze/ecommerce/
/data/silver/events/year=2019/month=10/day=DD/
/data/gold/user_profiles/
/data/gold/product_stats/
/data/gold/category_stats/
/data/gold/implicit_feedback/
/data/gold/als_candidates/
```

Do not partition by `user_id` or `product_id` because of high cardinality. Keep Cassandra tables aligned with access patterns:

- `recommendation_candidates(user_id, rank, product_id, als_score, updated_at)`
- `session_intent(user_id, user_session, category_code, intent_score, updated_at)`
- `product_stats(product_id, category_code, brand, popularity_score, trend_score, updated_at)`
- optional `live_recommendations(user_id, rank, product_id, final_score, updated_at)`

## Work breakdown

Effort is estimated team time. A task can be parallelized, but its dependency must be satisfied before integration.

| ID | Week | Workstream | Task | Owner | Effort | Depends on | Deliverable / acceptance evidence | Priority |
|---|---:|---|---|---|---:|---|---|---|
| P0-01 | 1 | Planning | Confirm member roles, available hardware, dataset location, and Kubernetes/cloud access | All | 2 h | None | Decision log entry and assigned owners | P0 |
| P0-02 | 1 | Data | Acquire October/November data and record file sizes/checksums | M1 | 2 h | P0-01 | `docs/dataset.md` source and acquisition record | P0 |
| P0-03 | 1 | Data | Inspect schemas, event types, nulls, cardinalities, and row counts | M1 | 4 h | P0-02 | Profiling output for both months | P0 |
| P0-04 | 1 | Data | Measure Oct/Nov overlap and identify cold-start severity | M1 | 3 h | P0-03 | User/product/category/brand overlap table | P0 |
| P0-05 | 1 | Data | Inspect skew and select sample rows covering all event types | M1 | 3 h | P0-03 | Sample selection notes and skew summary | P0 |
| P0-06 | 1 | Architecture | Freeze canonical event schema, config keys, and timestamp contract | All | 2 h | P0-03 | Schema file, `.env.example`, review sign-off | P0 |
| W1-01 | 1 | Batch | Scaffold repository, test layout, run commands, and configuration loader | M3 | 3 h | P0-06 | Reproducible sample command | P0 |
| W1-02 | 1 | Batch | Create `data/sample/` and DEV/FULL data mode | M1 | 4 h | P0-05 | Sample data with documented provenance | P0 |
| W1-03 | 1 | Storage | Load October sample/full input to HDFS Bronze | M1 | 4 h | W1-02 | HDFS path exists and can be read | P0 |
| W1-04 | 1 | Batch | Build Spark schema validation and invalid-record report | M1 | 5 h | W1-03 | Null/type/range validation report | P0 |
| W1-05 | 1 | Batch | Build Silver Parquet with date partitions and derived date fields | M1 | 5 h | W1-04 | Partitioned Parquet and row-count reconciliation | P0 |
| W1-06 | 1 | Batch | Implement windows, pivot/unpivot, custom aggregation, and multi-stage transforms | M1 | 7 h | W1-05 | Spark job plus explainable sample outputs | P0 |
| W1-07 | 1 | Batch | Build user/product/category statistics and join examples | M1 | 5 h | W1-05 | Gold tables and join plan evidence | P0 |
| W1-08 | 1 | ML | Create weighted implicit feedback and train initial MLlib ALS | M1 | 6 h | W1-07 | ALS model and metrics on sample data | P0 |
| W1-09 | 1 | ML | Generate Top-50/Top-100 candidates and baseline response | M1/M3 | 5 h | W1-08 | Candidate table and API/fixture response | P0 |
| W1-10 | 1 | Infrastructure | Start Docker Compose services and health checks | M2 | 5 h | P0-06 | Compose startup log and health checks | P0 |
| W1-11 | 1 | Integration | Record G1 demo and fix the first vertical-slice defects | All | 5 h | W1-09, W1-10 | G1 checklist passed | P0 |
| W2-01 | 2 | Streaming | Create Kafka topics, producer config, and deterministic replay event IDs | M2 | 5 h | P0-06 | `ecommerce.replay`, `ecommerce.live`, `ecommerce.dlq` | P0 |
| W2-02 | 2 | Streaming | Implement November replay producer with configurable rate | M2 | 6 h | W2-01 | Replays preserve event time and expose ingest time | P0 |
| W2-03 | 2 | Streaming | Parse and validate stream records; route invalid events to DLQ | M2 | 6 h | W2-02 | DLQ count and valid-count metrics | P0 |
| W2-04 | 2 | Streaming | Add event-time windows, watermark candidates, checkpoint, and deduplication | M2 | 8 h | W2-03 | State query and late-event evidence | P0 |
| W2-05 | 2 | Streaming | Implement session feature aggregation and Cassandra state sink | M2 | 8 h | W2-04 | Session state rows and restart-safe upsert key | P0 |
| W2-06 | 2 | Serving | Implement Cassandra candidate/product/session repositories | M3 | 5 h | W1-09, W2-05 | Repository tests and seed/read script | P0 |
| W2-07 | 2 | Serving | Implement FastAPI `/products`, `/events`, `/recommendations/{user_id}`, `/health` | M3 | 6 h | W2-06 | OpenAPI or endpoint contract tests | P0 |
| W2-08 | 2 | Frontend | Build catalog, product detail, cart, and recommendation shell | M3 | 8 h | W2-07 | UI can load dataset-backed products | P0 |
| W2-09 | 2 | Frontend | Generate event semantics for open, add, remove, and successful checkout | M3 | 5 h | W2-08 | Browser actions emit canonical events | P0 |
| W2-10 | 2 | Integration | Complete G2 replay/live → Kafka → Spark → Cassandra → API path | All | 8 h | W2-05, W2-07, W2-09 | One known-user demo with timestamps | P0 |
| W3-01 | 3 | ML | Implement weighted session intent and time decay | M2 | 5 h | W2-05 | Intent scores respond to recent events | P0 |
| W3-02 | 3 | Serving | Normalize ALS, intent, popularity, and brand scores | M3 | 4 h | W3-01 | Normalization unit tests and bounded scores | P0 |
| W3-03 | 3 | Serving | Implement weighted re-ranking with configurable parameters | M3 | 5 h | W3-02 | Top-K changes after a dominant session category | P0 |
| W3-04 | 3 | Serving | Implement known-user, new-user, and global-popularity cold-start paths | M3 | 5 h | W3-03 | API never fails for unknown user | P0 |
| W3-05 | 3 | Evaluation | Implement temporal Popularity vs ALS vs adaptive evaluation | M1 | 7 h | W1-08, W3-03 | NDCG@10, HitRate@10 tables | P0 |
| W3-06 | 3 | Evaluation | Implement Time-to-Adapt and Purchase HitRate@10 where data supports it | M1 | 5 h | W3-05 | Adaptation result table and limitations | P1 |
| W3-07 | 3 | Benchmark | Compare CSV, Parquet, and partition pruning | M1 | 5 h | W1-05 | Runtime/bytes-read comparison | P0 |
| W3-08 | 3 | Benchmark | Compare broadcast vs sort-merge, caching, and AQE/skew handling | M1/M2 | 8 h | W1-07 | Explain plans and measured comparison | P0 |
| W3-09 | 3 | Benchmark | Run replay throughput, Kafka lag, and P50/P95/P99 streaming latency | M2 | 7 h | W2-02, W2-04 | Rate/lag/latency table and saturation point | P0 |
| W3-10 | 3 | Benchmark | Run 1/2/4 executor scaling with fixed workload | M2 | 5 h | W3-09 | Speedup/efficiency table | P1 |
| W3-11 | 3 | Documentation | Draft architecture, data, benchmark, and reproducibility docs | All | 6 h | W3-05, W3-09 | Docs match implementation and evidence paths | P0 |
| W3-12 | 3 | Integration | Record G3 demo and freeze benchmark configurations | All | 4 h | W3-03, W3-09 | G3 checklist and config snapshot | P0 |
| W4-01 | 4 | Monitoring | Add Prometheus metrics and core Grafana panels | M3 | 6 h | W3-09 | Input rate, processing rate, lag, latency panels | P1 |
| W4-02 | 4 | Reliability | Execute kill/restart from checkpoint and inspect duplicate/loss behavior | M2 | 6 h | W2-04, W2-05 | Recovery report with measured results | P0 |
| W4-03 | 4 | Deployment | Harden Compose startup, health checks, and one-command sample run | M2/M3 | 5 h | W4-01 | Clean-environment run succeeds | P0 |
| W4-04 | 4 | Deployment | Deploy minimum stack to Kubernetes or approved cloud equivalent | M2 | 8 h | W4-03 | Deployment manifest/runbook and smoke evidence | P0 |
| W4-05 | 4 | QA | Run unit, integration, schema, API, and UI smoke tests | All | 6 h | W4-02, W4-03 | Test report and known limitations | P0 |
| W4-06 | 4 | Reproducibility | Execute full reproduction rehearsal from sample data | All | 6 h | W4-05 | Reproduction log with elapsed times | P0 |
| W4-07 | 4 | Report | Finalize problem, architecture, implementation, lessons learned, limitations | All | 8 h | W4-06 | Report draft tied to evidence | P0 |
| W4-08 | 4 | Demo | Freeze demo persona/data, script, screenshots, and fallback recording | M3 | 5 h | W4-06 | 8–10 minute demo script and backup | P0 |
| W4-09 | 4 | Presentation | Rehearse technical questions and benchmark explanation | All | 4 h | W4-07, W4-08 | Timed rehearsal and Q&A notes | P0 |
| W4-10 | 4 | Acceptance | Run G4 checklist and archive code, config, results, and docs | All | 4 h | W4-07, W4-08, W4-09 | Final acceptance record | P0 |

## Course requirement traceability

| Course requirement | Implementation response | Evidence to save | Planned week |
|---|---|---|---:|
| Lambda or Kappa architecture | Lambda: October batch + November/live speed layer + serving layer | Architecture diagram and data-flow explanation | 1–4 |
| End-to-end pipeline | HDFS → Spark → Kafka/Streaming → Cassandra → FastAPI → React | G2/G4 run logs and screenshots | 2–4 |
| Spark | PySpark batch and Structured Streaming | Source code, Spark UI, explain plans | 1–4 |
| Distributed storage | HDFS Bronze and partitioned Parquet Silver | HDFS paths, row counts, file layout | 1 |
| Message queue | Kafka replay/live/DLQ topics | Topic config, offsets, lag | 2–3 |
| NoSQL | Cassandra serving/state tables | Table definitions, read/write tests | 2 |
| Kubernetes or cloud | Minimum smoke deployment | Manifest/runbook, service health output | 4 |
| Complex aggregation | Windows, pivots, custom aggregation | Sample output and code reference | 1 |
| Advanced transformations | Multi-stage Spark transforms and native functions | Explain plan and transformation tests | 1 |
| Joins | Broadcast and sort-merge comparison | Runtime and shuffle evidence | 1, 3 |
| Optimization | Partition pruning, cache/persistence, AQE/skew | Benchmark table | 3 |
| Streaming | Structured Streaming, output modes, checkpoint | Streaming query progress | 2–4 |
| Watermark/late data | 2/5/10-minute comparison where feasible | Accepted/dropped late-event counts | 2–3 |
| State management | Session features and Cassandra state | State query and recovery report | 2, 4 |
| Exactly-once discussion | Idempotent keys, deduplication, restart measurement | Explicit claim/limitation in report | 2, 4 |
| Report | Problem, architecture, implementation, lessons learned | Final report and diagrams | 4 |

## Evaluation and benchmark plan

### Recommendation quality

Use the November chronological test split. Compare:

1. global/category popularity baseline;
2. October ALS;
3. October ALS plus session-aware re-ranking.

Primary metrics:

- NDCG@10;
- HitRate@10;
- Time-to-Adapt;
- Purchase HitRate@10 if purchase sequences are sufficient.

The primary claim is not that the recommender is state of the art. The claim is that session-aware re-ranking adapts more quickly than static ALS while the system preserves a reproducible distributed pipeline.

### Distributed and Spark evidence

| Experiment | Controlled factor | Metrics | Minimum result |
|---|---|---|---|
| Storage | CSV vs Parquet vs date-partitioned Parquet | runtime, bytes read, scan size | Explain why partitioning helps or does not help on the tested filter |
| Join | broadcast vs sort-merge | runtime, shuffle read/write, max task duration | Explain when each plan is appropriate |
| Cache | no cache vs cache/persist | repeated-query runtime, memory | Cache only reused data |
| Skew/AQE | default vs AQE/skew handling | max/median task duration, spill | Record whether skew is material |
| Streaming load | 1k, 2.5k, 5k, 10k events/s, higher only if stable | input/processing rate, Kafka lag, P50/P95/P99 | Identify sustainable rate and saturation behavior |
| Scaling | 1, 2, 4 executors, 8 only if available | throughput, P95, CPU/memory, speedup/efficiency | Explain diminishing returns |
| Watermark | 2, 5, 10 minutes if time permits | late accepted/dropped, state size, latency | State the selected default and trade-off |
| Recovery | kill and restart from checkpoint | recovery time, loss, duplicates, lag | Never claim exactly-once without evidence |

### Latency contract

Record explicit timestamps:

- `event_time`: original or live event time;
- `ingest_time`: Kafka/producer ingestion time;
- `processed_time`: streaming result time;
- `served_time`: API response time when used;
- browser click/render timestamps for end-to-end latency.

Streaming latency is `processed_time - ingest_time`. End-to-end latency is browser render time minus browser click time. Historical 2019 event time is never used as current system latency.

## Test plan

| Test layer | Examples | Minimum acceptance |
|---|---|---|
| Unit | event validation, interaction weights, score normalization, time decay, cold-start routing | deterministic expected outputs |
| Data quality | nulls, invalid price, bad event type, duplicate `event_id`, schema drift | invalid rows reach DLQ and counts reconcile |
| Batch integration | sample October through Silver, Gold, ALS, candidates | repeatable run and non-zero candidate output |
| Streaming integration | replay event through Kafka, Spark, Cassandra | state row changes and checkpoint created |
| API contract | products, events, recommendations, health | valid status/schema and unknown-user fallback |
| UI smoke | open product, add/remove cart, checkout, recommendations refresh | events match fixed semantics |
| Recovery | terminate/restart stream | measured duplicate/loss behavior documented |
| Performance | benchmark scripts at fixed factor values | results include workload/config and units |
| Reproducibility | fresh sample run | commands work without hidden local state |

## Risk register and rescue plan

| Risk | Trigger | Impact | Rescue action |
|---|---|---|---|
| Full dataset is too large for student hardware | Sample succeeds but full run exceeds available disk/RAM/time | High | Use sample for development, run full October only for selected evidence, report hardware limits, keep scripts scalable |
| Kubernetes access is unavailable | No local cluster or cloud account by Week 3 | High | Use Minikube/kind if supported; otherwise use an approved cloud-equivalent and preserve a deployment manifest plus smoke evidence |
| Spark/Cassandra integration is unstable | Sink retries or schema mismatch block G2 | High | Start with deterministic upserts and a narrow table; keep a JSON/Parquet sink fixture for debugging, but do not remove Cassandra from final scope |
| Streaming state grows unexpectedly | Memory or state rows grow with replay | High | Bound session windows, measure state size, test 2/5/10-minute watermarks, document chosen bound |
| Benchmark results are not reproducible | Same script gives different workload or metrics | Medium | Freeze config, seed replay, record machine/runtime versions, store raw results and command line |
| UI consumes too much time | Backend path works but frontend backlog grows after Week 2 | Medium | Keep catalog/detail/cart/recommendation screens only; cut polish and optional event panels |
| Cold-start overlap is low | Few November users/products occur in October | High | Measure overlap before ALS evaluation, add category/global popularity fallback, report coverage explicitly |
| Team integration is late | Interfaces are still changing after Day 10 | High | Freeze event/API/Cassandra contracts; schedule daily 20-minute integration check |
| Exactly-once claim is challenged | Restart produces duplicates or Cassandra writes are not transactional | High | Change report language to at-least-once delivery with idempotent upserts and measured restart behavior |

## Definition of done

The project is accepted when all of the following are true:

1. October batch pipeline runs in sample mode and has at least one documented full-data run or a documented hardware limitation.
2. HDFS Bronze, Silver Parquet, Gold aggregates, ALS candidates, Kafka topics, Spark Structured Streaming, session intent, Cassandra state, FastAPI, and React/Vite demo are present.
3. Live clickstream semantics match the canonical event contract.
4. Re-ranking changes recommendations after a dominant session interest.
5. Known-user, new-user-with-clicks, and completely new-user fallback paths work.
6. Recommendation metrics include NDCG@10 and HitRate@10; Time-to-Adapt is attempted.
7. Spark evidence includes aggregation/transform/join/optimization examples.
8. Distributed evidence includes throughput/lag/latency and at least 1/2/4 executor comparison if hardware permits.
9. Streaming and end-to-end latency are reported separately.
10. Restart/recovery behavior and exactly-once limitations are documented.
11. A Kubernetes or cloud-equivalent smoke deployment is demonstrated.
12. Reproduction commands, configuration, screenshots, raw benchmark outputs, and limitations are archived.

## Open questions to confirm

These do not block the baseline plan, but the answers will change estimates or the rescue branch:

1. What are the three members’ names, skill levels, and preferred workstreams?
2. Is the full 14.68 GB dataset already downloaded, and where is it stored?
3. What hardware is available per student and for the shared run: RAM, CPU, disk, and GPU if any?
4. Is a Kubernetes cluster, Minikube/kind, or cloud account already available? Is paid cloud usage allowed?
5. What is the exact final submission date and does the instructor require individual contribution evidence?
6. Is the full list of must-demonstrate Spark techniques graded as a rubric, or is the course page the only requirement source?
7. Are external services such as Docker Hub, GitHub Actions, or managed Cassandra permitted?

If no answer is provided, use the conservative defaults: local Docker Compose, sample data for development, one selected full-data batch run, Minikube/kind for deployment smoke testing, no paid cloud spend, and Member 1–3 placeholders.

## Autoplan review record

### Strategy review

- **Premise:** the project is a Big Data & Storage demonstration first, not a recommender research project. Accepted because it matches the persistent project context and the course requirements.
- **Architecture:** Lambda is selected because the fixed project already separates October batch history from November/live streaming. Switching to Kappa would add redesign cost without improving the four-week evidence story.
- **Scope:** the plan keeps the full course path but makes UI polish, 20k events/s, eight-executor scaling, and advanced ML optional. This is a time-boxed scope decision, not a change to the core architecture.
- **Competitive/academic risk:** a working web page without measured distributed behavior would miss the course emphasis. The plan gates the project on benchmark and recovery evidence, not only the demo.

### Design review

The UI is intentionally minimal. The hierarchy is: catalog/product action → current session intent → recommendations. Required states are loading, empty, error, unknown user, and stale recommendation delay. Accessibility requirements are keyboard-usable controls, visible focus, readable contrast, and buttons with explicit labels. The frontend is not allowed to grow into a marketplace.

### Developer experience review

The first reproducible command should run the sample path in under five minutes after services are available. The plan requires `.env.example`, DEV/FULL modes, one-command sample run, health endpoints, clear failure messages, and a clean-environment rehearsal. Each error should state what failed, what to check, and how to recover.

### Engineering review

The main engineering risks are data leakage, state growth, Cassandra sink semantics, and benchmark invalidity. The plan addresses each with fixed temporal splits, bounded windows/watermarks, deterministic idempotent keys, and controlled one-factor experiments. The architecture keeps ALS offline and makes score normalization explicit.

### Review coverage limitation

This workspace is not a Git repository, the installed gstack package is missing the sibling CEO/DX/Eng review skill files, and this host has no native subagent tool exposed. The review above is therefore a manual in-host review based on `PROJECT_CONTEXT_V2.md` and the course page. No Git diff, outside model review, or code-level verification was possible because no implementation exists yet.

## Decision audit trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---:|---|---|---|---|---|---|
| 1 | CEO | Keep Lambda Architecture | Mechanical | Explicit over clever | It matches the fixed batch-plus-streaming design and avoids a four-week redesign. | Kappa redesign |
| 2 | CEO | Keep Big Data evidence ahead of UI polish | Mechanical | Choose completeness | The course explicitly evaluates storage, processing, streaming, joins, optimization, and deployment. | Marketplace-like frontend scope |
| 3 | CEO | Make Kubernetes/cloud smoke deployment required but late | Taste | Pragmatic | It satisfies the course requirement while protecting the first two vertical slices. | Starting with Kubernetes |
| 4 | Eng | Treat exactly-once as a tested claim, not a default | Mechanical | Explicit over clever | Kafka checkpoints do not automatically make every Cassandra write exactly once. | Unqualified exactly-once claim |
| 5 | Eng | Use sample-first development with selected full-data runs | Mechanical | Bias toward action | Students need fast feedback while still producing scale evidence. | Full dataset for every iteration |
| 6 | Eng | Use deterministic event IDs and upsert-friendly Cassandra keys | Mechanical | Choose completeness | This supports deduplication, retry safety, and recovery measurement. | Blind append-only writes |
| 7 | DX | Keep one-command sample reproduction as a gate | Mechanical | Choose completeness | A demo that only works on one laptop is not defensible in the report. | Manual multi-step setup only |
| 8 | Design | Limit UI to catalog/detail/cart/recommendations | Mechanical | Boil lakes | These screens prove the event semantics and adaptive result without expanding product scope. | Auth, payments, search, seller/admin workflows |

## GSTACK REVIEW REPORT

**Status:** DONE_WITH_CONCERNS  
**Native review:** manual in-host review completed; no native subagent tool was available.  
**Outside review:** unavailable; no outside reviewer was enabled or callable.  
**Design review:** manual review completed because the plan includes a React/Vite demo.  
**DX review:** manual review completed for reproducibility and student setup.  
**Eng review:** manual review completed against the fixed architecture and course requirements.  
**Critical concerns:** available hardware, Kubernetes/cloud access, and the exact grading rubric remain unconfirmed.  
**Next action:** confirm the seven open questions, assign real names, and run the G1 preflight before committing to full-data benchmark targets.
