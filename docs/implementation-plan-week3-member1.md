<!-- /autoplan restore point: "/Users/iminluv/Vscode/Bigdata/.gstack/tmp/autoplan/feature-streaming-vertical-slice-autoplan-restore-20261104-225230.md" -->
# Week 3 Implementation Plan: Member 1

**Status:** Phase 0 environment audit documented; readiness gate blocked pending source CSV acquisition. Java 17 and project Python dependencies are present. Phase 1 has not started. ALS cohort choice remains open before interpreting model metrics.
**Branch:** `feature/w3-member1-batch-eval` (isolated task branch created from `main` or `feature/streaming-vertical-slice`; never develop directly on the G2 gate branch)
**Owner:** Member 1
**Review partners:** Member 3 for recommendation evaluation; Member 2 for shared Spark benchmark work. These are the ownership assumptions from the team plan; no work or review from either member is treated as confirmed.
**Scope:** Week 3 recommendation evaluation and Member 1 batch evidence
**Source plans:** `docs/designs/DEVELOPMENT_PLAN.md`, `docs/implementation-plan-plan1a.md`, and `docs/designs/PROJECT_CONTEXT_V2.md`

## Implementation plan

## Outcome

Produce reproducible evidence on whether October-trained recommendations predict November behavior and whether session-aware re-ranking adapts more quickly than static ALS. Also measure the planned batch storage and Spark query comparisons using identical inputs and recorded machine/configuration details.

The checked-in fixture remains the fast development input. It is not a substitute for November holdout evaluation or for full-data performance claims.

## Current repo state and implications

These findings come from static reads of the current branch and its checked-in artifacts:

- `data/sample/events.jsonl` contains 11 fixture records on 2019-10-01, including one invalid row and one duplicate. It has no November holdout events.
- `src/adaptive_recommender/batch/run_sample.py` reads the project's 13-field JSONL event contract, filters October, trains MLlib ALS, and writes up to 50 candidates per user. It is explicitly a sample runner; it does not currently read the nine-column REES46 CSV files.
- `src/adaptive_recommender/serving/reranker.py` contains the current ALS/session-intent ranking behavior. It does not provide an offline temporal evaluator.
- `src/adaptive_recommender/serving/fallbacks.py` and `repositories.py` provide popularity fallback behavior, but a popularity baseline for offline evaluation still needs a defined October-only training universe and reproducible ranked output.
- `Makefile` has sample batch and end-to-end targets, but no dataset profiling, recommendation evaluation, or batch benchmark targets.
- `tests/` has contract, serving, API, replay, and session-intent tests; there is no evaluation or benchmark test suite.
- The repo contains no tracked full October/November CSVs and no `docs/dataset.md` acquisition/profile record. Generated batch manifests are for the tiny fixture, not the full REES46 data.
- The existing docs specify October as history/train and November as held-out test/replay. Live browser events are for demo/integration evidence and must not be used as the primary recommendation-quality test set.

The present batch reader cannot consume the planned REES46 source without a CSV/schema ingestion path. The plan therefore includes this adapter and its data-quality evidence before model evaluation.

## Scope

### Member 1 owns

1. Confirm and document the source, local location, file sizes, checksums, schema, date coverage, and resource requirements for the October and November REES46 files.
2. Add a source-compatible reader/normalization path for the original REES46 CSV schema without editing raw files or changing the live event contract.
3. Measure October/November user, product, category, and brand overlap and report cold-start coverage.
4. Implement chronological recommendation evaluation for October-only popularity and ALS baselines, plus ALS with session-aware re-ranking.
5. Attempt Time-to-Adapt and Purchase HitRate@10 when their input support and definitions are sufficient.
6. Compare CSV with Parquet and measure partition pruning using the same rows and query.
7. Lead the batch side of the shared broadcast-vs-sort-merge, cache/persist, and AQE/skew comparisons. Under the published team plan, Member 1 defines/runs the batch workloads; Member 2 reviews configuration and reproduces one variant if available.
8. Save raw results, concise summaries, commands, configurations, and limitations as reproducible evidence; update the dataset/evaluation documentation.

### Member 2 dependency/shared work

- Member 2 owns distributed streaming benchmarks and recovery/deployment tasks in the team plan.
- W3-08 names Member 1 and Member 2 together. Member 1 leads the batch query definitions and CSV/Parquet, partition-pruning, join, cache, and AQE/skew runs on the bounded batch sample. Member 2 owns streaming-rate/Kafka-lag/executor-scaling work, reviews shared Spark benchmark configuration, and reproduces one W3-08 variant if available. Do not attribute Member 2's streaming results to Member 1.
- If Member 2 does not participate in W3-08, Member 1 completes the batch-side work and records the missing peer reproduction; do not claim an independent second-member verification.

### Member 3 dependency/shared work

- Member 3 owns serving/reranking behavior. Use the current implementation and existing source-of-truth configuration for comparisons; do not wait for new work from Member 3 or silently change weights.
- Live demo screenshots and UI polish are outside this Member 1 plan. The demo is not an evaluation source.

### Out of scope

- Changes to live event semantics, API contracts, Cassandra schema, or recommendation weights solely to improve evaluation scores.
- Training on November data, using future events in earlier predictions, or tuning on the final November holdout without an explicitly recorded protocol decision.
- Per-click ALS retraining, advanced model search, production-scale throughput claims, or changes to the G4 deployment/recovery ownership.
- Committing raw CSVs, large generated Parquet outputs, local credentials, or machine-specific paths.

## Required decisions and input gates

Do not start the full-data run until these are answered and recorded in `docs/dataset.md` or the decision log:

1. **Local data availability:** The user has not downloaded the files yet. Acquire `2019-Oct.csv` and `2019-Nov.csv` from the [REES46 multi-category behavior dataset](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store), also listed on [REES46's datasets page](https://rees46.com/en/datasets). Record the exact local paths. Never silently substitute another REES46 dataset.
2. **Machine capacity:** The user's device is a Mac M4 with 16 GB RAM. A point-in-time check on 2026-11-05 found 88 GiB free. Homebrew OpenJDK 17.0.21.0.2 is installed at `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, and `.venv` contains PySpark 3.5.8, PyArrow 18.1.0, and NumPy 1.26.4. The `Makefile` configures `.venv/bin/python` and this JDK path; use those settings for Spark commands. Refresh free disk after download and record CPU/runtime versions and Spark execution mode. The source files are large; 16 GB RAM alone does not establish whether a full run fits.
3. **Course requirement and scale fallback:** The user approved a bounded-sample-first Week 3 target, increasing sample size only while measured resources remain manageable. The instructor's exact minimum has not been confirmed. Label every bounded run as a sample and do not present it as full-month evidence.
4. **Sampling method:** Use deterministic user-hash sampling, applying the same hash rule to October and November and retaining every event for each selected user. Start with a 0.1% user-hash feasibility pilot; it is not presumed large or dense enough for meaningful ALS results. Record selected users and event counts by month, interactions per user, interactions per item, user/item coverage, and October/November overlap. Label a pilot ALS run diagnostic until these statistics show adequate overlap; do not present low-coverage ALS metrics as representative. Increase the fraction only after checking observed memory, disk, runtime, and output size. Keep null-user events in separate counts and exclude them from user-ranking metrics. This preserves each sampled user's month-long sequence and October/November membership while a short date slice would discard most temporal coverage. It still requires downloading and scanning both raw CSVs; it reduces downstream materialization/model work, not initial download size or the CSV scan. **Open decision:** whether to train/evaluate ALS on all sampled October-warm users and report sparsity/coverage, or define a separate active-user ALS cohort (e.g. at least five October interactions) while retaining the full hash sample for population and cold-start reporting. Do not restrict the domain to electronics without approval; it would bias the multi-category/adaptation evaluation.
5. **Instructor requirement:** The user accepts reducing scope if full data is too large, but the instructor's minimum evidence requirement is not confirmed. Label every bounded run as a sample and do not present it as full-month evidence.
6. **Evaluation observation/repeat policy:** The user approved next-event prediction for October-warm users, binary NDCG@10/HitRate@10, repeated items allowed, and a separate cold-user fallback coverage slice. Under a single target item, binary vs. graded relevance cancels in NDCG; use binary for this next-event contract. Purchase HitRate is a separate conditional metric, not part of this denominator.
7. **Time-to-Adapt:** This remains optional/stretch as W3-06 is P1 in the project plan. Keep current candidate retrieval; report cross-category cases unreachable/undefined when the relevant category is absent from ALS candidates. Do not expand the serving candidate pool without a separate approval from the serving owner.
8. **W3-08 ownership:** Use the published ownership split above as the working assumption: Member 1 leads batch-side work and Member 2 owns streaming benchmarks and shared review/reproduction where available. Complete Member 1's assigned work without waiting; record any missing peer reproduction as not performed.
9. **Serving configuration:** `src/adaptive_recommender/serving/reranker.py` currently defaults to ALS/session/popularity/brand weights `0.35/0.50/0.10/0.05`, while `docs/designs/PROJECT_CONTEXT_V2.md` lists `0.50/0.35/0.10/0.05`. For the baseline, inspect and record the configuration actually used by the current service; do not wait for new Member 3 work or silently change weights. Do not tune on November. Any tuning requires a recorded October validation protocol.

The plan can progress through source acquisition, profiling, schema adaptation, unit tests, and fixture runs while the files are not yet downloaded, the instructor minimum is unknown, and current serving configuration is verified from code. The user has approved the bounded-sample-first target, deterministic user-hash sampling, next-event warm-user metric contract, no candidate-pool expansion, and using published member ownership as the working assumption. Increase the sample only while measured memory, disk, and runtime remain manageable. The reviewer's RAM/disk projections are risk estimates, not measurements from this Mac.

## Implementation sequence

### Phase 0: Data and environment readiness

**Purpose:** establish that the inputs match the plan and that the bounded pilot fits the available machine before scaling it.

1. Locate the two source files and record path, byte size, SHA-256, source URL, acquisition date, and license/attribution note. Keep them in an ignored local data directory; do not add the raw files to Git.
2. Inspect headers, parsability, event-time min/max, row counts, event types, nulls, invalid prices, identifier cardinalities, and skew for both files. Parse timestamps explicitly as UTC using the source format (`yyyy-MM-dd HH:mm:ss z`) and reconcile parse failures instead of relying on Spark's default timestamp parser.
3. Check October/November overlap for users, products, categories, and brands. Report both counts and proportions so cold-start severity is visible.
4. Define and record one deterministic user-hash predicate (for example, `pmod(xxhash64(cast(user_id AS string)), 1000) = 0`, with Spark version recorded), apply it identically to both months, and retain all rows for matching non-null users. Profile the 0.1% pilot's selected user counts, event counts by month, interactions/user and interactions/item distributions, catalog/user coverage, date coverage, null-user rows, and October/November overlap before writing derived tables. Account separately for the full raw-file download and scan. Treat the pilot as a pipeline/resource check; decide whether its graph supports ALS only after inspecting these diagnostics.
5. Write the exact source and profiling process to `docs/dataset.md`. State whether counts describe a full file or a bounded sample.
6. Check free disk before materializing outputs. Keep raw CSV immutable and write normalized/derived data under ignored `data/generated/` paths.

**Gate:** source identity, time ranges, file checksums, sample predicate, profiling counts, machine capacity, and accepted pilot scale are recorded. If the raw files are unavailable or the pilot exceeds measured capacity, stop before materialization and report the blocker; continue only with fixture work or a smaller explicitly labeled sample.

### Phase 1: REES46 input path and canonical offline tables

1. Add a dedicated REES46 CSV reader or batch input module. Do not overload the fixture reader in a way that breaks the existing `make batch-sample` path.
2. Map the nine source columns (`event_time`, `event_type`, `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`) into typed Spark columns. Preserve source fields and UTC event time. Derive `event_date` from the parsed UTC timestamp for date-partitioned Parquet. Preserve null `category_code`/`brand`; report their rates and make null-category events ineligible for category-intent metrics rather than inventing a category.
3. Keep offline evaluation columns separate from fields synthesized for live replay (`event_id`, `ingest_time`, `event_source`, `schema_version`). Do not invent those fields just to make offline metrics work.
4. Preserve repeated source events as observations. Aggregate repeated user/product interactions only where the October ALS training contract requires it. Do not deduplicate distinct behavioral events based only on equal product/user/timestamp values without a documented source rule.
5. Write deterministic, date-partitioned Parquet output and a manifest with source hashes, input/output counts, invalid counts, config hash, code commit, UTC timestamps, and output locations.
6. Do not reuse the sample runner's `StringIndexer.labels` plus local Python-list mapping for a larger dataset without proving its driver-memory cost is acceptable. Prefer a distributed ID mapping/join or another deterministic index strategy; test count and ID round-tripping on the bounded fixture first.
7. Add a bounded fixture/sample read mode for fast tests and local iteration. Sample selection must be deterministic and documented; do not claim it represents the full data distribution unless profiling supports that claim.

**Gate:** input row reconciliation, schema/null validation, October/November date partition checks, and repeatable fixture conversion pass. The source CSV remains unchanged.

### Phase 2: Freeze evaluation protocol

The user has approved the primary ranking contract below. Record it in the run config before implementation; keep the remaining conditional decisions open:

- next-event prediction, one target item per eligible event;
- October-warm users for ALS ranking metrics, with cold-user popularity fallback coverage reported separately;
- binary relevance for NDCG@10 and HitRate@10; with one target item, a relevance grade cancels from normalized DCG;
- repeated products remain eligible in this next-event metric; purchase HitRate is a separate conditional slice;
- session intent at prediction time uses only the prior prefix from that November session;
- K=10 as the primary cut-off; other K values only if the course/report requests them.

Time-to-Adapt remains optional. If run, report only sessions with an observable reachable category in the current candidate pool; mark other cross-category shifts unreachable/undefined. Candidate expansion, a different repeat policy, a different observation unit, or a different relevance protocol requires a recorded decision before metrics are changed.

The project context names NDCG@10 as primary and HitRate@10 as required. The user-approved primary contract is next-event prediction on October-warm users with binary target relevance, repeats allowed, and cold-user fallback coverage reported separately. Purchase HitRate@10 and Time-to-Adapt remain optional conditional metrics.

**Temporal leakage rule:** for a November prediction at time `t`, the October-trained model and popularity statistics may use October only. Session intent may use only events from the same November session strictly before `t`. The target event and all later November events must not affect that prediction. Save a test/fixture that fails if future events leak into features.

### Phase 3: Recommendation evaluation

Implement an evaluation module under `src/adaptive_recommender/evaluation/` using existing Spark/standard-library dependencies unless repository inspection reveals a concrete missing capability.

Compare these same-user/same-target ranked lists:

1. **October popularity:** global popularity, with category-conditioned popularity only for the cold-start/fallback slice if agreed in the protocol.
2. **October ALS:** candidates trained only from October events using the existing configured event weights and frozen ALS parameters unless a separate tuning decision is approved.
3. **October ALS + session-aware re-ranking:** the same ALS candidate source and the weights actually used by the checked-in serving code, with session intent reconstructed from only preceding November events. Record the code/config source; request Member 3's review when available, but do not block on it.

Implementation steps:

1. Build and persist October-only item/user/category statistics and ALS artifacts.
2. Generate enough ALS candidates for the evaluation K and measure candidate coverage; current sample code writes up to 50 per user. Record that the measured model cannot retrieve relevant targets absent from its candidate set.
3. Order November events deterministically by UTC event time plus a documented tie-break rule, then form evaluation examples according to the approved observation unit.
4. Construct prior-session state with native Spark cumulative windowing, not Python row-by-row iteration. Match the existing event weights (`view=1`, `cart=4`, `remove_from_cart=-3`, `purchase=5`). First aggregate weighted events into `(user_id, user_session, event_time, category_code)` timestamp buckets so equal-time events do not arbitrarily become prior to one another. Compute each category's cumulative raw score using a Spark window partitioned by user/session/category, ordered by timestamp, with `rowsBetween(unboundedPreceding, -1)`; apply the existing nonnegative tanh normalization and assemble the category state for each timestamp. Attach that prior state to all events in the current timestamp bucket. Keep static ALS rankings fixed and derive adaptive rankings from that same candidate pool to isolate reranking effect. Before reporting cross-category Time-to-Adapt, measure whether target-category items exist in the candidate pool; if not, mark those cases unreachable/undefined unless candidate expansion is separately approved.
5. Calculate NDCG@10 and HitRate@10 using the frozen relevance protocol. Calculate Purchase HitRate@10 only on the defined purchase subset. Calculate Time-to-Adapt only on sessions satisfying the agreed dominant-interest condition.
6. Report overall and cohort counts, including seen-user, cold-user, seen-item, cold-item, candidate coverage, empty candidate coverage, and session/evaluation-example counts. Report warm-user ranking metrics separately from all-user service coverage/fallback outcomes; do not mix users with no ALS list into the ALS-only denominator.
7. Include deterministic unit tests for metric calculations, tie handling, empty targets, short rankings, duplicate recommendations, cold-start eligibility, and chronology/no-leakage.
8. Emit machine-readable per-run JSON/CSV plus a short Markdown result table with definitions, denominators, data scope, limitations, and source commit.

**Gate:** all three approaches run on the same frozen evaluation examples; metric unit tests pass; each reported number has a denominator, input hash, config hash, model parameters, and data scope. No metric is reported without enough eligible examples.

### Phase 4: Batch and Spark evidence

Keep each experiment to one controlled factor at a time. Share the experiment definition with Member 2 for W3-08.

| Experiment | Controlled comparison | Required measurements | Evidence |
|---|---|---|---|
| CSV vs Parquet | On the same sampled October rows, filter `event_time >= 2019-10-01 00:00:00 UTC AND event_time < 2019-10-08 00:00:00 UTC`, then group by `category_code, event_type` and compute `count(*)` and `avg(price)`; select only those three columns plus `price` | elapsed runtime, bytes scanned/read when available, row counts, physical plan | Raw command/log, query plan, result summary |
| Partition pruning | Compare the exact Oct 1 half-open time range on unpartitioned Parquet with `event_date = '2019-10-01'` on date-partitioned Parquet; verify both return identical rows. Do not use `day(event_time)=1`, which can match the first day of other months. | rows/files/bytes read when observable, runtime, physical plan | Plan showing pruning behavior or explicit finding that sample size hid a benefit |
| Broadcast vs sort-merge | Join sampled Silver events to Gold product statistics on `product_id`, with identical projections/actions; compare a broadcast hint against a sort-merge hint only if the measured Gold side fits the configured broadcast threshold/local memory. | runtime, shuffle read/write, spill, task-duration summary, physical plan | Both plans and raw output; report if forced strategy is infeasible |
| Cache/persist | Reuse the same date-filtered session timestamp-bucket DataFrame for two fixed actions: category/event-type counts, then per-session category-intent aggregation; compare uncached and persisted runs including persistence materialization cost. | first and repeated runtime, materialization cost, memory/storage metrics when available | Run config and raw results |
| AQE/skew | Join sampled Silver events to product statistics on `product_id`; first report product-key frequency skew. Compare AQE off vs on, then (with AQE on) skew-join handling off vs on, changing one setting per comparison. | runtime, plan, max/median task duration, spill/skew metrics when available | Skew profile, before/after plans, raw results |

Benchmark execution:

1. Use the table's canonical workloads; freeze input partitions, exact schemas, projections, filters, join keys, actions, warm-up policy, and repetitions before the run. Report local runs as warm-cache or cold-cache; do not claim cold-disk comparisons unless the OS cache is controlled by a documented, safe method.
2. Use one run ID and config hash per variant. Do not compare results from different row counts, machines, Spark versions, or actions as if they were controlled.
3. Run the fixture first to check the harness, then the agreed bounded/full workload. Label every output with its scope.
4. Record host/cluster CPU, RAM, free disk, OS/architecture, Python/Java/Spark versions, executor settings, input hashes and bytes, command, units, warm-up, and raw per-run timings.
5. Explain when sample scale is too small to show reliable performance differences. Do not turn noisy results into an optimization claim.

**Gate:** every comparison has matching input/result row counts and a physical plan. Any unavailable Spark metric is marked unavailable with reason rather than inferred.

### Phase 5: Documentation and handoff

1. Add `docs/dataset.md` with provenance, acquisition, checksums, profiling, schema, overlap, sample rule, and storage requirements.
2. Add `docs/evaluation.md` with the frozen temporal split, relevance rules, observation unit, metrics/denominators, candidate coverage, cold-start findings, and limitations.
3. Add a batch benchmark section to the source-of-truth project report/evidence index, pointing to raw artifacts and commands.
4. Add Makefile targets only after selecting stable commands, keeping fixture targets fast and separate from full-data commands.
5. Record what Member 1 completed, what Member 2/3 need to review, the exact reproduction commands, and any run that could not be completed.

## Implementation progress log

### Phase 0 — environment/source audit (2026-11-05)

**Completed:** checked the active branch and preserved unrelated working-tree changes; checked for expected CSV files; checked free disk and OS architecture; corrected the first-pass default-shell checks by verifying the Homebrew JDK and project `.venv`; confirmed the Makefile runtime paths; created `docs/dataset.md` to record the source and audit.

**Observed:** 88 GiB free at the repository path; Apple Silicon `arm64`; system Python is 3.11.9; Homebrew OpenJDK 17.0.21.0.2 is present; `.venv` has PySpark 3.5.8, PyArrow 18.1.0, and NumPy 1.26.4; Makefile points to the project interpreter and JDK; neither expected CSV is present under the repository's `data/` directory or root.

**Gate:** BLOCKED pending the two source CSVs. No source profiling, download, or CSV materialization has occurred. Phase 1 has not started. Required to resume Phase 0: acquire both planned CSV files, refresh free-disk measurement, and run the documented profile using the configured project environment. The ALS cohort decision is needed before evaluating ALS metrics, but does not block source acquisition/profile work.

**Review checkpoint:** Antigravity's review of commit `13ce69a` found environment-scope corrections and a misplaced handoff item. Those corrections are recorded in a follow-up Phase 0 commit; wait for the user's next order before Phase 1.

## Proposed repository changes

Final filenames may be adjusted to existing conventions during implementation; do not create duplicate abstractions if an equivalent helper is found.

- `src/adaptive_recommender/batch/rees46.py` or equivalent: typed reader/normalization for original REES46 CSV inputs.
- `src/adaptive_recommender/evaluation/`: temporal split, ranking metrics, popularity/ALS/adaptive comparison, coverage, and conditional metrics.
- `src/adaptive_recommender/batch/benchmark.py` or equivalent: repeatable fixed-workload batch comparison runner.
- `Makefile`: separate profile, sample evaluation, full evaluation, and benchmark targets with explicit input/output variables.
- `tests/evaluation/` and batch tests: deterministic metrics, splits, leakage prevention, input mapping, and benchmark input parity.
- `docs/dataset.md`, `docs/evaluation.md`, and evidence index updates.
- `evidence/metrics/` and `evidence/benchmarks/`: compact summaries and manifests/raw command output. Large derived Parquet stays ignored under `data/generated/`.

No new dependency is planned. Confirm the existing PySpark/PyArrow stack can read the chosen inputs before proposing a dependency change.

## Verification plan

Run these after implementation, in order; this plan itself does not claim that they have run:

1. Focused unit tests for schema mapping, time ordering, metric math, cold-start cohorts, candidate coverage, and leakage.
2. Existing `make test-unit` to protect the current contract/serving/streaming paths.
3. A deterministic sample/bounded REES46 conversion and evaluation run; repeat it and compare counts/metric output within the documented determinism contract.
4. Row reconciliation: source rows = accepted + rejected; accepted October rows map only to training; November targets map only to test/replay.
5. Re-run each benchmark variant with fixed config and retain raw outputs. Use `git diff --check` and `git status` before handoff.
6. Request Member 3's review of recommendation evaluation assumptions and Member 2's review/reproduction of one shared W3-08 batch variant. If either review/reproduction is unavailable, record it as not performed; Member 1's work does not wait on it.

Do not run full data or benchmark workloads until data availability, hardware capacity, and instructor-required scale are confirmed.

## Completion checklist

- [ ] Official October and November files are located/acquired and recorded by checksum, size, and source.
- [ ] Dataset profile and user/product/category/brand overlap are documented.
- [ ] REES46 reader preserves raw source and creates typed date-aware derived data.
- [ ] Sample and full/bounded modes are clearly distinguished.
- [ ] Evaluation protocol decisions are written down before final metrics.
- [ ] Popularity, ALS, and ALS+session reranking use identical chronological targets.
- [ ] NDCG@10 and HitRate@10 are reported with denominators and coverage.
- [ ] Time-to-Adapt and Purchase HitRate@10 are reported only if eligibility/data support them.
- [ ] Cold-start and candidate coverage are reported.
- [ ] CSV/Parquet, pruning, join, cache, and AQE/skew evidence has matching workloads and saved raw outputs.
- [ ] Runtime/machine/config/input metadata accompanies every result.
- [ ] Tests and second-member review are complete; docs and evidence let another teammate reproduce the reported results.

## Effort and schedule notes

The existing task table estimates W3-05 at 7 hours, W3-06 at 5 hours (P1/stretch), W3-07 at 5 hours, and W3-08 at 8 hours shared by Members 1 and 2. These are the plan's estimates, not new measurements. Core W3-05 and W3-07 total 12 estimated Member 1 hours, within the team's 12–15 hour weekly expectation before data acquisition/profile prerequisites; W3-06 and Member 1's batch share of W3-08 are additional. Use the ownership split stated above as the working assumption; do not count Member 2's streaming work as Member 1 effort or report peer reproduction unless it occurs.

## Decisions and questions before the ALS evaluation run

1. After downloading the CSVs, what are their exact local paths and how much free disk is available? Java 17 and the project Spark dependencies are already present in the configured local environment.
2. Does the instructor require full-month evaluation/full-data benchmarks, or accept bounded sample evidence? The user approved bounded-sample-first, increasing the sample only when measured resources allow.
3. What minimum date coverage or sample size does the instructor expect? The working sample is a deterministic 0.1% user-hash feasibility pilot, scaled only after resource checks.
4. **ALS cohort (user decision needed):** Keep the uniform hash sample for ALS and report its observed sparsity/coverage, increasing the hash fraction if resources permit; or use a separate ALS-trained cohort restricted to users with at least five October interactions while retaining the uniform hash sample for population/cold-start reporting. Do not use an electronics-only restriction without approval because it narrows the multi-category evaluation.
5. For optional Time-to-Adapt, what threshold means the new category has entered Top-10 “meaningfully”? Candidate expansion is not approved; unreachable cross-category cases will otherwise be marked undefined.
6. Data acquisition method can be chosen when ready to download: browser download or Kaggle CLI. No acquisition script or download has been started; this choice does not block the plan or fixture-level work.

## Review record

## GSTACK REVIEW REPORT

This plan has not completed the full autoplan review pipeline. The current host is Codex, so the preflight could not use Codex as an outside reviewer because that would not be an independent second review. This tool session also did not provide the native Agent tool required for the independent Claude review phases. An in-host static review and a separate Antigravity CLI review were performed. The review coverage limit is explicit; no CEO/DX/Eng phase completion or full autoplan consensus is claimed.

### Static review findings

| Area | Finding | Plan response |
|---|---|---|
| Data readiness | The checked-in runner expects JSONL with synthetic project fields; the planned REES46 source is CSV with nine different fields. | Add a dedicated reader and profile gate; keep fixture runner and raw CSV unchanged. |
| Temporal validity | A per-event session-aware metric can leak the current target or future events if session intent is computed over the full November file. | Require strictly prior session-prefix state and a leakage test. |
| Candidate ceiling | ALS recommendations are currently capped at 50 and targets outside the model candidate set cannot be retrieved. | Measure and report candidate coverage; freeze candidate count/model settings before the final run. |
| Metric contract | The repo did not define a primary aggregation unit or repeat policy. | User approved next-event prediction for October-warm users, binary NDCG@10/HitRate@10, repeats allowed, and separate cold-user fallback coverage. ToA remains optional. |
| Capacity/evidence | No full-dataset profile or machine capacity record exists in the repo. | Gate full runs and require environment/input metadata for claims. |
| Scope/ownership | Core W3-05/07 sum to 12 estimated Member 1 hours; W3-06 is an additional P1/stretch task and W3-08 is shared. Data acquisition/profile work is still pending. | User approved keeping W3-06 optional and using the ownership split published in the plan as a working assumption; Member 1 should not wait for Member 2/3, and absent peer review/reproduction must be reported as not performed. |
| External review: resource scope | Antigravity argues full local processing should not be the Week 3 contract on a 16 GB laptop. Its exact memory and disk estimates are not measured on this machine, so they are treated as risk estimates, not verified limits. | User approved deterministic bounded-sample-first, with a 0.1% user-hash pilot and scale increases only after measured memory/disk/runtime checks. The instructor minimum remains unknown. |
| Sampling choice | A short calendar slice lowers volume but discards most month-long history and narrows temporal coverage. Row sampling can split users' histories and undermine warm-user and session-prefix evaluation. | Use the same deterministic user-hash predicate across both months and retain all rows for selected users. This preserves sampled-user chronology and cross-month membership; report event counts because equal user fractions do not imply equal event fractions. The pilot still requires downloading and scanning the source CSVs. |
| External review: recommender candidates | The serving path reranks only retrieved ALS candidates. A new session category outside that candidate set cannot be recommended by this path. | User approved retaining current candidate retrieval and marking such Time-to-Adapt cases unreachable/undefined; candidate-pool expansion is out of scope unless separately approved. |
| External review: evaluation contract | For a single target item, multiplying its relevance grade scales both DCG and IDCG and cancels in NDCG. Repeat-item filtering also changes the meaning of next-event vs. purchase metrics. | User approved next-event, warm-user, binary NDCG@10/HitRate@10, repeats allowed, and separate cold-user fallback coverage. |
| External review: factual discrepancy | Antigravity reported that `tests/` contains zero test files. Current repo inspection finds `tests/unit/test_api.py`, `test_contracts.py`, `test_serving.py`, plus streaming tests. | Treat that claim as incorrect; preserve the plan's accurate statement that tests exist but evaluation/benchmark test suites do not. |
| External review: workload estimate | The reviewer counts planned Week 1 tasks as 15–20 additional hours and extrapolates 45–50 total hours. The source plan does show those tasks, but the repo has completed the sample batch/ALS path; full-data acquisition/profiling and REES46 CSV support remain incomplete. | Do not report 45–50 as measured remaining work. Preserve the source estimate: W3-05/06/07 total 17 estimated Member 1 hours, plus an unassigned share of W3-08 and remaining full-data prerequisites. |
| Antigravity adversarial review, Round 2 | Conditional approval with three advisories: small hash samples may be too sparse for meaningful ALS; benchmark SQL/workloads need to be concrete; point-in-time session state should use native Spark cumulative windows. | Keep the 0.1% pilot as a feasibility/profile run and require graph/coverage diagnostics before interpreting ALS metrics; make the ALS cohort choice explicit and ask the user before restricting it. Freeze canonical benchmark workloads using actual REES46 fields and identical join keys/actions. Specify Spark cumulative windows over timestamp buckets so same-time events do not leak into one another. |
| Antigravity Phase 0 review | The initial audit checked only the default shell and Python, missing the installed Homebrew JDK and configured `.venv`. It also found the Phase 5 handoff item displaced below the Phase 0 log. | Verified OpenJDK 17.0.21.0.2, PySpark 3.5.8, PyArrow 18.1.0, NumPy 1.26.4, and Makefile paths in this checkout. Corrected the environment record and moved the handoff item into Phase 5. The remaining Phase 0 gate depends on source CSV acquisition and running the documented profile/resource checks; Phase 1 remains unstarted. |

### What already exists

- October sample batch and ALS candidate path: `src/adaptive_recommender/batch/run_sample.py`.
- Serving reranking and popularity fallback: `src/adaptive_recommender/serving/reranker.py`, `fallbacks.py`, and `repositories.py`.
- Sample/end-to-end verification: `Makefile`, `scripts/run_g2_e2e.py`, and `evidence/commands/e2e-sample.txt`.
- The October-train/November-test split and planned Week 3 tasks: `docs/designs/DEVELOPMENT_PLAN.md` and `docs/implementation-plan-plan1a.md`.

### Not in scope

Streaming throughput, Kafka lag, executor scaling, recovery, deployment, UI polish, and final report/presentation are assigned elsewhere or later in the project plan. Member 1 will provide batch-side inputs/evidence to shared report work but will not claim ownership of other members' results.

### Completion summary

Phase 0's environment/source audit is documented in `docs/dataset.md`; its readiness gate is blocked because the two CSVs are absent. The JDK and project Python dependencies are available and configured through the Makefile. Phase 1 and later phases have not started. The user supplied the device and scale-fallback preference; the ALS cohort choice remains open before evaluation. Each completed phase will be committed and reviewed before proceeding to the next. Native and outside autoplan review passes are unavailable in this Codex tool session; prior static review is not represented as full autoplan consensus.
