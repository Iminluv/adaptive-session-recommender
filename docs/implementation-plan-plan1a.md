# Plan 1A Implementation Plan

**Status:** Decisions recorded; implementation not started
**Scope:** Full Lambda vertical slice on tiny data, then controlled expansion
**Branch:** `main`
**Implementation started:** No

This document turns the approved plan1a direction into an execution sequence. It is intentionally specific enough that three new students can divide the work and still produce one coherent workflow.

## 0. Pre-code gate

Do not start implementation until these items are resolved:

1. **Worktree integrity:** the tracked `Documentation/` directory deletion is intentional. The active project documentation is under `docs/`; do not restore the old directory or silently recreate it.
2. **Runtime baseline:** record Python, Java, Spark, Docker, Docker Compose, and Node versions in `docs/environment.md`.
3. **Hardware baseline:** record RAM, CPU, disk, Docker architecture, and whether kind/Minikube can run.
4. **Dataset access:** record where October and November files will live. Do not download the full dataset before profiling storage needs.
5. **Deployment decision:** select and verify the cloud/Kubernetes target before local pipeline implementation. Docker Compose remains available for local debugging, but it is not the first deployment milestone.

The first implementation commit should be a scaffold and fixture only. It must not include a full-data run, a frontend, or unmeasured performance claims.

## 1. Target outcome

The first usable milestone is:

```text
sample fixture
  -> canonical validation
  -> Spark batch
  -> Silver Parquet
  -> implicit feedback
  -> ALS candidates
  -> local serving response
```

The second milestone adds the adaptive path:

```text
replay/live event
  -> Kafka
  -> Structured Streaming
  -> validation + DLQ + deduplication
  -> event-time window + session intent
  -> Cassandra state
  -> FastAPI normalization + re-ranking
  -> recommendation change visible in the demo
```

The system demonstrates the course workflow. It does not claim production scale, production exactly-once behavior, or state-of-the-art recommendation accuracy.

## 2. Repository structure

Use one repository. Keep runtime boundaries explicit, but keep shared behavior in one Python package.

```text
.
├── README.md
├── Makefile
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── dataset.md
│   ├── environment.md
│   ├── course-evidence.md
│   ├── troubleshooting.md
│   ├── deployment.md
│   └── decision-log.md
├── data/
│   ├── sample/
│   ├── raw/                 # ignored, never committed
│   └── generated/           # ignored local outputs
├── src/adaptive_recommender/
│   ├── common/
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── validation.py
│   │   ├── event_ids.py
│   │   ├── errors.py
│   │   └── scoring.py
│   ├── batch/
│   │   ├── profile_dataset.py
│   │   ├── build_silver.py
│   │   ├── build_gold.py
│   │   ├── train_als.py
│   │   └── generate_candidates.py
│   ├── streaming/
│   │   ├── replay_producer.py
│   │   ├── stream_events.py
│   │   ├── session_intent.py
│   │   └── cassandra_sink.py
│   └── serving/
│       ├── repositories.py
│       ├── reranker.py
│       └── fallbacks.py
├── api/
│   └── main.py
├── web/
│   ├── package.json
│   └── src/
├── deploy/
│   ├── cassandra/
│   ├── kafka/
│   └── k8s/
├── tests/
│   ├── unit/
│   ├── batch/
│   ├── streaming/
│   ├── api/
│   └── e2e/
└── evidence/
    ├── README.md
    ├── commands/
    ├── logs/
    ├── metrics/
    └── screenshots/
```

Rules:

- `common/` owns contracts, IDs, validation, configuration, and pure scoring functions.
- `batch/` owns Spark batch jobs and offline ML.
- `streaming/` owns Kafka and Structured Streaming jobs.
- `serving/` owns storage access and recommendation composition.
- `api/` owns HTTP contracts only. It must not contain Spark transformations.
- `web/` owns browser event generation and display only.
- `evidence/` stores generated outputs, never secrets or the full dataset.

## 3. Data contracts

### 3.1 Canonical event

Every event crossing Kafka, tests, API, and Cassandra uses the same logical fields:

```json
{
  "schema_version": 1,
  "event_id": "stable-id",
  "event_time": "2019-11-01T00:00:00Z",
  "ingest_time": "2026-10-23T12:00:00Z",
  "event_type": "view",
  "product_id": 1004856,
  "category_id": 2053013555631882655,
  "category_code": "electronics.smartphone",
  "brand": "samsung",
  "price": 499.0,
  "user_id": "520088904",
  "user_session": "session-id",
  "event_source": "historical_replay"
}
```

Required rules:

- `event_time`, `event_type`, `product_id`, `user_id`, and `user_session` are required for the sample path.
- `price` must be non-negative when present.
- `event_type` is one of `view`, `cart`, `remove_from_cart`, or `purchase`.
- `event_time` is the source/business time. `ingest_time` is when the system received the event.
- Historical replay preserves source `event_time` and assigns a current `ingest_time`.
- Browser events create `event_id` once and reuse it on retries.
- Replay IDs use `sha256(source_file + row_number)`, so retrying a row produces the same ID.
- Invalid records go to `ecommerce.dlq` with a reason code. They are never silently dropped.

### 3.2 Event semantics

| Event | Browser meaning | Batch/stream meaning |
|---|---|---|
| `view` | Product detail opened | Positive weak interaction and session-category signal |
| `cart` | Add to cart clicked | Strong positive interaction and session-category signal |
| `remove_from_cart` | Remove clicked | Remove from active cart/session signal; do not use as positive ALS feedback |
| `purchase` | Successful checkout | Strong positive interaction and evaluation outcome |

### 3.3 Interaction weights

Start with configurable sample defaults:

```text
view = 1.0
cart = 3.0
purchase = 5.0
remove_from_cart = excluded from positive ALS feedback
```

The remove event contributes a penalty to current session intent, not a negative ALS rating. This avoids feeding unsupported negative values into an implicit-feedback training contract.

### 3.4 Deterministic outputs

Every job writes a small manifest containing:

```text
run_id
git_commit
config_hash
input_path
input_row_count
output_path
output_row_count
started_at
finished_at
```

This manifest is required for reproducibility and benchmark interpretation.

## 4. Storage and service contracts

### 4.1 Local paths

```text
data/generated/bronze/events/
data/generated/silver/events/year=2019/month=10/day=DD/
data/generated/gold/user_profiles/
data/generated/gold/product_stats/
data/generated/gold/implicit_feedback/
data/generated/gold/als_candidates/
```

The same logical layout is mounted under HDFS for the distributed-storage run. Do not use `user_id` or `product_id` as file partitions because both are high-cardinality keys.

### 4.2 Cassandra tables

Design tables from reads, not from a normalized relational model:

```sql
recommendation_candidates (
  user_id text,
  rank int,
  product_id bigint,
  als_score double,
  updated_at timestamp,
  PRIMARY KEY ((user_id), rank)
)

session_intent (
  user_id text,
  user_session text,
  category_code text,
  intent_score double,
  last_event_time timestamp,
  updated_at timestamp,
  PRIMARY KEY ((user_id, user_session), category_code)
)

product_stats (
  product_id bigint PRIMARY KEY,
  category_code text,
  brand text,
  popularity_score double,
  updated_at timestamp
)

live_recommendations (
  user_id text,
  rank int,
  product_id bigint,
  final_score double,
  reason text,
  updated_at timestamp,
  PRIMARY KEY ((user_id), rank)
)
```

The exact CQL types and partition keys must be checked against the selected Cassandra image before implementation. Sink writes must be idempotent and retry-safe.

### 4.3 API contract

| Endpoint | Request | Response | Failure behavior |
|---|---|---|---|
| `GET /health` | None | Service/dependency status | Non-200 when required dependency is unavailable |
| `GET /products?limit=20` | Optional limit | Product list | 400 for invalid limit, 503 for storage failure |
| `POST /events` | Canonical event | Accepted event ID and status | 422 for invalid schema; same ID is safe to retry |
| `GET /recommendations/{user_id}?limit=10` | User ID and limit | Ranked products, score components, reason | Valid fallback for unknown user; 503 only for unavailable serving storage |

The API returns a stable error shape:

```json
{
  "code": "SAMPLE_INPUT_MISSING",
  "message": "Sample input is missing",
  "fix": "Run `make sample-fixture`",
  "recovery": "Rerun `make sample`",
  "request_id": "request-id"
}
```

Never return secrets, credentials, or raw connection strings in errors.

## 5. Implementation waves

### Wave 0: recover the project contract

**Owner:** all members

Tasks:

1. Resolve the deleted `Documentation/` directory.
2. Confirm dataset location, hardware, runtime versions, and deployment access.
3. Create `docs/environment.md` and `docs/decision-log.md`.
4. Pin initial versions in `pyproject.toml`, Compose files, and `web/package.json`.
5. Add `.gitignore` rules for raw data, generated outputs, checkpoints, secrets, and evidence logs containing local paths.

Exit evidence: the team can explain the data split, runtime versions, and local start command.

### Wave 1: shared contracts and deterministic fixture

**Owner:** Member 1 with one review from Member 2

Implement:

- Pydantic or dataclass event model.
- Schema validation and reason codes.
- Replay/live event source enum.
- Deterministic event ID functions.
- Sample fixture with all four event types, null/category cases, duplicate, and late-event examples.
- Fixture manifest with source, selection rule, checksum, row count, and expected invalid count.
- `make check`, `make sample-fixture`, and `make test-unit`.

Exit evidence:

```text
make sample-fixture
fixture: created data/sample/events.jsonl
rows: <count>
checksum: <sha256>
invalid_rows: <count>
```

### Wave 2: October batch path

**Owner:** Member 1 with Member 3 serving review

Implement in this order:

1. Read the fixture with an explicit Spark schema.
2. Validate required fields and write invalid rows to a batch-quality report.
3. Write Bronze input to local/HDFS path.
4. Build Silver Parquet partitioned by date.
5. Reconcile input, valid, invalid, and Silver counts.
6. Build Gold user/product/category aggregates.
7. Build implicit feedback using the configured weights.
8. Train local-mode MLlib ALS on the October fixture.
9. Generate Top-50 candidates and write candidate manifest.
10. Seed candidate rows into Cassandra.

Required course evidence in this wave:

- windowed aggregate;
- pivot or unpivot;
- custom aggregation or equivalent grouped transformation;
- at least one broadcast join;
- explain plan showing join choice;
- Parquet partition pruning example;
- persistence/cache comparison on a repeated query.

Exit command:

```text
make batch-sample
```

Exit evidence: Silver row-count reconciliation, Gold sample rows, ALS parameters, candidate rows, Spark explain output, and one API fixture response.

### Wave 3: first serving response

**Owner:** Member 3 with Member 1 review

Implement:

- Cassandra repository for candidates and product stats.
- `GET /health` with dependency checks.
- `GET /products`.
- `GET /recommendations/{user_id}` using ALS candidates only at first.
- Popularity fallback for unknown users.
- API contract tests using a repository fixture or test Cassandra container.

Exit command:

```text
make api-sample
```

Exit evidence: a known user receives non-empty Top-K candidates, an unknown user receives a valid popularity fallback, and `/health` identifies dependency state.

### Wave 4: Kafka and replay

**Owner:** Member 2 with Member 1 review

Implement:

- Compose Kafka service and topic initialization.
- `ecommerce.replay`, `ecommerce.live`, and `ecommerce.dlq` topics.
- Replay producer that preserves event time and assigns ingest time.
- Configurable rate with a safe low default.
- Producer output containing sent count, rejected count, and final offset.
- Duplicate replay mode for recovery testing.

Exit command:

```text
make replay-sample RATE=10
```

Exit evidence: topic description, sent count, first/last event IDs, offsets, and a saved replay manifest.

### Wave 5: Structured Streaming and Cassandra state

**Owner:** Member 2 with Member 3 serving review

Implement in this order:

1. Read Kafka JSON with the canonical schema.
2. Route invalid events to DLQ with reason code.
3. Deduplicate on `event_id` within the configured watermark horizon.
4. Apply event-time watermark and a bounded session/window policy.
5. Aggregate recent session intent by user/session/category.
6. Write session intent with deterministic Cassandra keys.
7. Save checkpoint under a configurable path.
8. Expose query progress and late-event counters.

Use a windowed aggregation first. Do not start with custom state APIs unless the windowed design cannot express the required session behavior. This keeps the first streaming path compatible with the standard Structured Streaming model.

Exit command:

```text
make stream-sample
```

Exit evidence: checkpoint exists, valid/DLQ counts reconcile, session intent rows change, late-event counts are visible, and restarting the query produces a measured duplicate/loss result.

### Wave 6: adaptive serving and minimal UI

**Owner:** Member 3 with Member 2 streaming review

Implement pure serving functions first:

- normalize each score component to a bounded range;
- apply time decay to recent session events;
- combine ALS, intent, popularity, and brand components through configuration;
- remove already viewed/carted products when appropriate;
- provide known-user, new-user-with-clicks, and anonymous fallbacks;
- return a reason field such as `session_category`, `long_term_preference`, or `popular_fallback`.

Initial configurable weights may be:

```text
ALS = 0.60
session_intent = 0.25
popularity = 0.10
brand = 0.05
```

These are starting configuration values, not measured results. The UI includes only catalog, product detail, cart action, recommendation list, loading, empty, stale, and error states.

Exit evidence: a fixed scenario shows computer recommendations before smartphone clicks and smartphone-oriented recommendations after the replay/live event sequence, without retraining ALS.

### Wave 7: evaluation and distributed evidence

**Owner:** Member 1 for recommendation metrics; Member 2 for system benchmarks; Member 3 for demo evidence

Evaluation:

- train only on October;
- evaluate chronologically on November;
- compare popularity, ALS, and ALS plus re-ranking;
- calculate NDCG@10 and HitRate@10;
- attempt Time-to-Adapt and Purchase HitRate@10 only when the held-out events support them;
- report coverage and cold-start overlap.

System experiments:

| Experiment | Fixed factors | Outputs |
|---|---|---|
| CSV vs Parquet | Same rows and filter | Runtime, bytes read, partition behavior |
| Broadcast vs sort-merge | Same join and data | Explain plan, runtime, shuffle |
| Cache/persist | Same repeated query | First and repeated runtime, memory |
| AQE/skew | Same workload | Task duration, spill, skew behavior |
| Streaming load | Fixed replay rates | Input rate, processing rate, lag, P50/P95/P99 |
| Scaling | 1/2/4 executors if available | Throughput, latency, speedup, efficiency |
| Watermark | 2/5/10 minute comparison if feasible | Late accepted/dropped, state size, latency |

Every result records machine, runtime versions, config hash, input size, command, units, and raw output. No benchmark number is written before the run exists.

### Wave 8: recovery, deployment, and presentation

**Owner:** Member 2 deployment/recovery; all members acceptance

Implement and demonstrate:

1. Stop/restart the streaming job from checkpoint.
2. Replay duplicate events and inspect idempotent results.
3. Stop/restart Cassandra or simulate sink unavailability.
4. Run Compose from a clean environment.
5. Deploy the minimum stack to kind/Minikube or approved cloud equivalent.
6. Capture `/health`, pod/service status, port-forward command, and limitations.
7. Archive logs, screenshots, benchmark outputs, configs, and the demo script.

Do not claim exactly-once for the full Kafka-to-Cassandra path unless the restart evidence supports that exact claim. Otherwise report at-least-once delivery with deduplication and idempotent upserts.

## 6. Commands and expected artifacts

The exact command names become the contract after the scaffold lands:

| Command | Purpose | Required artifact |
|---|---|---|
| `make check` | Validate tools, versions, env, and ports | `evidence/commands/check.txt` |
| `make sample-fixture` | Create deterministic fixture | `data/sample/manifest.json` |
| `make test-unit` | Run pure contract/scoring tests | `evidence/commands/test-unit.txt` |
| `make up` | Start local dependencies | `evidence/commands/up.txt` |
| `make batch-sample` | Run October sample batch | `evidence/commands/batch-sample.txt` and manifest |
| `make api-sample` | Start/read sample serving path | `evidence/commands/api-sample.txt` |
| `make replay-sample RATE=10` | Replay a small November fixture | replay manifest and offsets |
| `make stream-sample` | Run the streaming query | query progress, checkpoint, DLQ counts |
| `make e2e-sample` | Run event-to-recommendation flow | before/after response and timestamps |
| `make benchmark NAME=parquet` | Run one controlled experiment | raw result plus config/machine metadata |
| `make deploy-smoke` | Run Kubernetes/cloud smoke test | health output and deployment log |
| `make down` | Stop local services | no source/data deletion |

The first command printed in `README.md` must be `make check`, followed by `make sample-fixture` and `make batch-sample`.

## 7. Test plan

### Unit tests

- event schema accepts valid events and rejects missing keys, invalid types, negative prices, and unknown event types;
- replay and browser event IDs remain stable across retries;
- interaction weights map exactly to the configured table;
- score normalization handles all-equal, empty, null, and negative-source-score inputs;
- reranking is deterministic for a fixed candidate/session fixture;
- cold-start routing chooses the correct branch.

### Batch integration tests

- October-only input assertion prevents November leakage;
- valid/invalid/Silver counts reconcile;
- all four event types appear in profiling output;
- fixture produces non-empty implicit feedback and candidates;
- repeated run produces the same manifest counts and candidate IDs.

### Streaming integration tests

- valid event reaches session state;
- invalid event reaches DLQ with stable reason;
- duplicate event does not increment session intent twice;
- late event produces an explicit accepted/dropped result;
- checkpoint directory is created;
- restart behavior is measured rather than assumed.

### API and UI tests

- `/health` reports dependency status;
- `/products` validates limit and returns stable schema;
- `/events` rejects invalid payloads and accepts retry-safe IDs;
- recommendation endpoint returns known-user, new-user, and anonymous fallbacks;
- browser open/cart/remove/purchase actions emit the canonical event types;
- UI displays loading, empty, stale, error, and successful recommendation states.

### E2E test

```text
start Compose
  -> run October batch fixture
  -> seed candidate tables
  -> start stream
  -> POST/replay smartphone events
  -> wait for session state
  -> GET recommendations
  -> assert category/reason changed
```

## 8. Acceptance gates

### G0: contract ready

- Documentation deletion resolved.
- Runtime and hardware recorded.
- Event schema and fixture manifest exist.
- Unit tests pass.

### G1: batch vertical slice

- `make batch-sample` succeeds on a clean local environment.
- Silver Parquet, Gold aggregates, ALS model/candidates, and manifest exist.
- No November input is used.
- API returns one candidate response.

### G2: adaptive backend path

- Event flows through Kafka, Structured Streaming, state, Cassandra, and API.
- Invalid, duplicate, and late-event outcomes are visible.
- Recommendation output changes after the fixed session scenario.

### G3: evidence ready

- Evaluation and controlled Spark benchmarks run with raw outputs.
- Latency separates event processing time from browser/API end-to-end time.
- Recovery behavior is measured.

### G4: submission ready

- Clean-environment rehearsal passes.
- Kubernetes/cloud smoke output exists.
- Report references real artifacts and states limitations.
- Demo and fallback recording are ready.

## 9. Work allocation

| Track | Primary owner | First deliverable | Review partner |
|---|---|---|---|
| Data/batch/ML | Member 1 | `docs/dataset.md`, fixture, G1 batch path | Member 3 |
| Streaming/infrastructure | Member 2 | Compose, Kafka replay, G2 stream path | Member 1 |
| Serving/frontend | Member 3 | API contract, re-ranking, minimal UI | Member 2 |
| Shared | All | schema, integration gates, evidence, report | second-member run required |

No track is complete when it only works on its owner's machine. The definition of complete is a documented command that a second member can run.

## 10. Risks and stop rules

| Risk | Stop rule | Response |
|---|---|---|
| Documentation deletion is intentional or unexplained | Before G0 | Ask owner; do not restore silently. |
| Full dataset exceeds disk/RAM/time | Before full run | Keep fixture, run selected full jobs, record limit. |
| Spark/Cassandra connector mismatch | At first sink test | Pin compatible versions; keep a narrow table and fixture sink for diagnosis. |
| Python state API becomes a time sink | After one failed prototype | Use event-time window aggregation and document the bound. |
| Frontend takes more than one day after G2 | At daily review | Freeze to catalog/detail/cart/recommendations and cut polish. |
| Kubernetes unavailable | By Wave 8 start | Try kind/Minikube; then use an approved cloud equivalent; preserve manifests. |
| Benchmark result cannot be reproduced | Any mismatch | Freeze config/input/machine metadata and rerun before reporting. |

## 11. Review checklist before coding

- [ ] Owner confirms whether deleted `Documentation/` files should be restored.
- [ ] User approves this implementation-plan document.
- [ ] Team members and tracks are assigned.
- [ ] Hardware and deployment access are recorded.
- [ ] Exact runtime versions are pinned.
- [ ] Dataset location and acquisition method are recorded.
- [ ] `docs/dataset.md` is written before the first pipeline job.
- [ ] The canonical schema and fixture are approved by all three members.
- [ ] The first branch/commit is limited to scaffold, fixture, and tests.

## 12. Items intentionally not implemented first

- React polish, authentication, payments, search, seller/admin features.
- Full-data execution for every iteration.
- Per-click ALS retraining.
- Production-grade exactly-once guarantee.
- 20,000 events/second or eight-executor claims without hardware evidence.
- Multi-cloud deployment.
- Advanced ML tuning, GraphFrames, and optional dashboards.

## Engineering Review Summary

### Scope challenge

The plan has many runtime boundaries because the course explicitly requires storage, batch processing, streaming, NoSQL, API/visualization, optimization, and deployment. The structure is still one repository with one shared contract package. No separate repositories, general platform framework, or production operations layer are included.

Scope result: accepted as the plan1a feature set, with implementation staged behind G0-G4 gates.

### Architecture findings

- **[P1, confidence 10/10] Worktree contract missing:** the tracked `Documentation/` directory is deleted in the current worktree. G0 blocks implementation until the owner restores it or confirms deletion is intentional. Evidence: `docs/implementation-plan-plan1a.md:14`.
- **[P1, confidence 8/10] Dependency compatibility is unresolved:** the plan names Spark, Kafka, Cassandra, Python, Java, and Node but exact versions are not yet pinned. Wave 0 makes this a prerequisite before connector or image work. Evidence: `docs/implementation-plan-plan1a.md:15-18`.
- **[P2, confidence 8/10] Replay event-time needs an explicit test:** replay keeps historical event time while ingest time is current. The plan requires a chronological replay test and separate latency timestamps so historical dates are not mistaken for processing latency. Evidence: `docs/implementation-plan-plan1a.md:158-162` and `docs/implementation-plan-plan1a.md:556-567`.

### Code-quality findings

- Shared schema, IDs, validation, scoring, and configuration are correctly centralized in `common/`.
- Spark transformations stay out of API handlers, and Cassandra access stays behind repositories. This limits coupling and makes pure unit tests possible.
- The first streaming implementation uses windowed aggregation before custom state APIs. This is the smaller, more testable path for new students.
- The `remove_from_cart` rule is intentionally kept out of positive ALS feedback and handled as current-session behavior. This prevents invalid negative assumptions in the implicit model.

### Test coverage diagram

```text
CODE PATHS                                      USER FLOWS
[GAP] common validation                         [GAP] make check -> sample fixture
  ├── valid event -> canonical object             ├── [→E2E] clean-machine batch run
  ├── invalid event -> reason/DLQ                 ├── [→E2E] browser event -> API
  └── duplicate ID -> deduplicate                 └── [→E2E] replay -> changed Top-K
[GAP] batch pipeline
  ├── October -> Silver -> Gold -> ALS
  ├── no-November leakage assertion
  └── empty/invalid input handling
[GAP] streaming pipeline
  ├── Kafka parse -> validation -> DLQ
  ├── duplicate/late event branches
  ├── checkpoint/restart branch
  └── Cassandra timeout/schema failure
[GAP] serving
  ├── known user -> ALS + session rerank
  ├── new user with clicks -> category fallback
  ├── anonymous -> popularity fallback
  └── empty candidates/dependency failure

COVERAGE: 0/4 paths implemented and tested | Code paths: 0/4 | User flows: 0/3
QUALITY: implementation not started; test plan and value cards are saved separately
```

The current test-plan artifact is [iminluv-main-eng-review-test-plan-20261023-201000.md](</Users/iminluv/.gstack/projects/Iminluv-adaptive-session-recommender/iminluv-main-eng-review-test-plan-20261023-201000.md>). It lists the exact critical paths, edge cases, and pending decisions for `/qa`.

### Performance review

No performance result is claimed because no implementation exists. The plan requires fixed workload, machine, config hash, units, and raw output for every comparison. It also separates event processing latency from browser/API latency. The first benchmark is a correctness and measurement harness, not a throughput target.

### What already exists

- Approved design: `docs/designs/adaptive-session-aware-recommender.md`.
- Deferred-scope list: `TODOS.md`.
- Prior autoplan artifacts: `.gstack/tmp/autoplan/`.
- Last committed project documentation: available through `git show HEAD:Documentation/...`; absent from the current worktree and therefore not silently replaced.

### Implementation tasks from this review

- [ ] **ENG-PLAN-01 (P1, human: 30min / CC: 5min)** — Worktree — resolve the deleted `Documentation/` directory and record the decision. Verify: `git status` is understood and the project context is available before G0.
- [ ] **ENG-PLAN-02 (P1, human: 1h / CC: 10min)** — Environment — pin exact runtime/container versions and record hardware/deployment capacity. Verify: `make check` design has a known expected output.
- [ ] **ENG-PLAN-03 (P1, human: 3h / CC: 20min)** — Contracts — implement the canonical event model, validation, deterministic IDs, errors, and fixture manifest. Verify: unit/value tests pass on valid, invalid, duplicate, and late fixtures.
- [ ] **ENG-PLAN-04 (P1, human: 4h / CC: 25min)** — Batch — implement October-only Silver/Gold/ALS/candidate path. Verify: G1 manifest and candidate response exist.
- [ ] **ENG-PLAN-05 (P1, human: 5h / CC: 30min)** — Streaming — implement Kafka replay, DLQ, deduplication, watermark/windowed session intent, checkpoint, and narrow Cassandra sink. Verify: G2 state/restart evidence exists.
- [ ] **ENG-PLAN-06 (P1, human: 4h / CC: 25min)** — Serving — implement API repositories, score normalization, re-ranking, and fallbacks. Verify: known/new/anonymous API contract tests pass.
- [ ] **ENG-PLAN-07 (P2, human: 4h / CC: 25min)** — Integration — add Compose health, E2E event path, recovery run, and evidence capture. Verify: second-member sample run succeeds.
- [ ] **ENG-PLAN-08 (P2, human: 3h / CC: 20min)** — Deployment — add kind/Minikube smoke manifests and deployment runbook. Verify: `/health` is reachable and output is archived.

### Unresolved decisions

- The owner must decide whether the deleted `Documentation/` directory is intentional.
- The team must pin exact runtime versions after checking hardware.
- The team must confirm the instructor's acceptance of kind/Minikube as the Kubernetes/cloud deployment evidence.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---:|---|---|
| Scope Challenge | `/plan-eng-review` | Prevent scope/structure mistakes | 1 | DONE_WITH_CONCERNS | One worktree blocker and two implementation prerequisites. |
| Architecture | `/plan-eng-review` | Data flow and service boundaries | 1 | DONE_WITH_CONCERNS | Architecture is coherent; version and replay-time contracts need G0 proof. |
| Code Quality | `/plan-eng-review` | Shared contracts and coupling | 1 | DONE | Shared package boundaries and pure scoring path are explicit. |
| Test Review | `/plan-eng-review` | Regression and E2E coverage | 1 | DONE_WITH_CONCERNS | Tests are specified, but 0 runtime paths are implemented yet. |
| Performance | `/plan-eng-review` | Benchmarks and resource risks | 1 | DONE_WITH_CONCERNS | Measurement protocol exists; no measurements exist. |
| Outside Review | External reviewer | Independent second opinion | 0 | UNAVAILABLE | No outside reviewer was enabled or callable. |

**OUTSIDE COVERAGE:** unavailable; `codex_reviews` is not enabled in the local gstack configuration. No outside completion credit is claimed.

**VERDICT:** plan1a is implementation-ready after the G0 worktree decision. Do not start pipeline coding while the tracked documentation deletion is unexplained.

**UNRESOLVED DECISIONS:**
- Confirm whether to restore or intentionally keep deleted `Documentation/` files.
- Confirm exact runtime versions and available hardware.
- Confirm kind/Minikube acceptance for the deployment requirement.
