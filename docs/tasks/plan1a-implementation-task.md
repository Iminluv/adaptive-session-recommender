# Plan1A Implementation Task

Status: G1 complete; G2 batch and serving baseline complete; G3 streaming next.

Branch: `feature/plan1a-contracts-fixture`

Parent plan: [implementation-plan-plan1a.md](../implementation-plan-plan1a.md)

## Objective

Build a small, demonstrable adaptive e-commerce recommender that satisfies the course workflow:

```text
historical data -> batch processing -> recommendations
                         +
live events -> Kafka -> Structured Streaming -> session intent
                         +
recommendation API/UI -> adaptive re-ranking
```

The project will use a small reproducible fixture first, then the REES46 e-commerce data when the environment is verified. The owner's computer is the initial execution target. Oracle is an optional later deployment target.

## Scope for the first implementation

Included:

- Canonical event schema and validation.
- Deterministic replay and duplicate handling.
- October/history batch path.
- ALS candidate generation with a fallback recommender.
- Kafka event replay.
- Structured Streaming session-intent calculation.
- Cassandra persistence for the narrow serving state.
- FastAPI recommendation endpoint.
- Minimal UI for demonstrating recommendation changes.
- Tests and evidence artifacts for the complete sample workflow.

Deferred:

- Full production-scale throughput claims.
- Per-click model retraining.
- Complex machine-learning models or GraphFrames.
- Authentication, payments, search, seller/admin features.
- Multi-cloud production deployment.

## Required implementation order

### G0 — Project and environment gate

1. Confirm that the deletion of the tracked `Documentation/` files is intentional and that `docs/` is the active documentation root.
2. Record Python, Java, Spark, Kafka, Cassandra, Docker, and frontend versions.
3. Record available CPU, memory, disk, and whether kind/Minikube is available.
4. Prepare a local Kubernetes smoke test after the Docker engine is running; confirm cloud deployment requirements with the instructor if needed.

G0 decisions are recorded. Install runtime dependencies as needed; cloud signup does not block local work.

### G1 — Contracts and fixture

1. Add the canonical event model.
2. Add validation, stable error codes, and deterministic event IDs.
3. Add a tiny fixture containing valid, invalid, duplicate, late, and anonymous-user events.
4. Add unit tests and a fixture manifest.

Exit condition: the fixture validates reproducibly and the unit tests pass. Current result: 6 unit tests pass; the sample contains 4 valid records, 1 invalid record, and 1 duplicate ID.

### G2 — Batch and serving baseline

1. Read history data.
2. Write Silver Parquet records.
3. Build Gold aggregates.
4. Train ALS candidates using positive interactions.
5. Store candidates and product statistics.
6. Expose the first recommendation API with known-user, new-user, and anonymous fallbacks.

Exit condition: one command produces candidates and the API returns recommendations from the fixture. Current result: `make batch-sample` generates Silver Parquet and Gold ALS candidates; `make api-sample` passes with known-user ALS candidates, unknown-user popularity fallbacks, and event ingestion probe.

### G3 — Streaming and adaptive behavior

1. Replay events into Kafka.
2. Validate and route invalid records to a dead-letter path.
3. Deduplicate using deterministic event IDs.
4. Apply event-time watermarking and bounded session windows.
5. Persist session intent and recent activity in Cassandra.
6. Re-rank batch candidates using session intent and fallback signals.

Exit condition: a simulated event changes the API response and the replay can be safely repeated.

### G4 — Demonstration, recovery, and deployment evidence

1. Add the minimal UI.
2. Add Compose health checks and an end-to-end sample command.
3. Capture logs, API responses, Cassandra state, and screenshots.
4. Demonstrate checkpoint/restart behavior.
5. Run a small fixed-workload benchmark.
6. Add kind/Minikube smoke manifests if accepted for the course requirement.

Exit condition: another team member can reproduce the demo from the documentation.

## Suggested team workflow

Use short branches from `main` and merge only after the relevant gate passes:

```text
main
  ├── plan1a-implementation       <- current integration branch
  ├── plan1a/contracts
  ├── plan1a/batch
  ├── plan1a/streaming
  └── plan1a/serving-ui
```

Recommended practice:

- Keep `main` stable and demoable.
- Make one coherent change per branch.
- Open a pull request or review diff before merging.
- Require tests and the relevant evidence artifact before merge.
- Merge contracts before batch, batch before streaming, and streaming before UI polish.
- Do not force-push shared branches.
- Do not commit raw or large generated datasets; document download and generation commands instead.

For a student project, the practical alternative is for the team to work directly on this integration branch while still making small commits and reviewing each other’s diffs. The important rule is that `main` remains a known-good fallback.

## Suggested commit sequence

1. `docs: add plan1a implementation task`
2. `build: add reproducible project scaffold`
3. `feat: add canonical event contracts and fixture`
4. `feat: add batch recommendation pipeline`
5. `feat: add recommendation API and fallbacks`
6. `feat: add Kafka replay and streaming session state`
7. `feat: add adaptive ranking and demo UI`
8. `test: add end-to-end evidence workflow`
9. `docs: add deployment and presentation runbook`

## Acceptance checklist

- [ ] `main` remains unchanged until reviewed work is merged.
- [ ] The `Documentation/` deletion is explained and resolved.
- [ ] A new environment can run the fixture workflow.
- [ ] Batch recommendations are reproducible.
- [ ] Duplicate and invalid events are handled deterministically.
- [ ] Late events do not corrupt session state.
- [ ] API fallbacks work for known, new, and anonymous users.
- [ ] A live event visibly changes the recommendation response.
- [ ] Restart/recovery behavior is demonstrated.
- [ ] All performance numbers include workload, machine, configuration, and units.
- [ ] Deployment evidence matches the instructor’s accepted requirement.

## Decisions requested from the owner

1. Should the deleted tracked `Documentation/` files be restored, or was their deletion intentional?
2. Is `plan1a-implementation` the desired shared integration branch, or should each member branch from it immediately?
3. Can kind/Minikube be used as the deployment demonstration if a cloud cluster is too expensive or unavailable?

