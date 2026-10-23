# Project Contribution Rulebook

This is the project-wide guide for every contribution: features, fixes, experiments, tests, documentation, data changes, infrastructure, and releases. It is not tied to one milestone or implementation plan.

If an assignment, security requirement, or repository policy conflicts with this guide, follow the higher-priority rule and record the decision in the project decision log.

## 1. Before starting work

1. Read `README.md` and the relevant design or requirements document.
2. Check `git status` and `git branch --show-current`.
3. Search existing issues, tasks, documentation, and decisions before creating duplicate work.
4. Define the expected result and the command or test that will prove it.
5. Confirm the owner and reviewer when working as a team.
6. Keep unrelated local changes untouched.

Do not start by rewriting architecture, schemas, or public APIs without checking the existing source of truth.

## 2. General principles

- Prefer a small, complete change over a large speculative change.
- Keep behavior, configuration, and documentation consistent in the same pull request.
- Make failures visible. Do not silently discard invalid input or ignore errors.
- Keep development reproducible on another teammate's machine.
- Keep external side effects at clear boundaries.
- Never commit secrets, private data, or machine-specific files.
- Record durable architecture and scope decisions.
- Measure performance with a stated workload, environment, and unit.
- Treat demos, mocks, and fixtures as different from production evidence.
- Do not claim behavior that has not been tested or measured.

## 3. Ownership and roles

Each task has one directly responsible owner and at least one reviewer. Ownership means keeping the work understandable and verifiable, not preventing others from contributing.

Common ownership areas are:

| Area | Typical responsibility |
|---|---|
| Product/requirements | User outcome, acceptance criteria, scope |
| Data/ML | Dataset contracts, transformations, models, evaluation |
| Backend/API | Service behavior, validation, persistence, errors |
| Frontend/client | User interaction, display, client-side state |
| Infrastructure | Runtime, containers, deployment, monitoring, recovery |
| Quality | Tests, regression checks, reproducible evidence |
| Documentation | Setup, reference, decisions, troubleshooting, handoff |

For every task, record the owner, reviewer, inputs, expected output, verification command, evidence location, and dependencies.

## 4. Branches

`main` is the shared, reviewable branch. Do not develop directly on it.

Create a branch from the latest base branch:

`git switch main`, `git pull --ff-only origin main`, then `git switch -c <type>/<short-description>`.

Use lowercase kebab-case names with one of these prefixes:

| Prefix | Use | Example |
|---|---|---|
| `feature/` | New user or system capability | `feature/recommendation-api` |
| `fix/` | Correction to existing behavior | `fix/late-event-validation` |
| `test/` | Test-only work | `test/api-error-cases` |
| `docs/` | Documentation-only work | `docs/contributor-guide` |
| `refactor/` | Internal restructuring without intended behavior change | `refactor/shared-config` |
| `chore/` | Tooling, dependency, or maintenance work | `chore/pin-runtime-versions` |
| `experiment/` | Time-boxed investigation or prototype | `experiment/ranking-baseline` |

Branch rules:

- Keep one coherent task per branch.
- Keep branches short-lived and update them from `main` before review.
- Do not reuse a merged branch.
- Never force-push a shared branch. Use `--force-with-lease` only on a personal branch after checking nobody else uses it.
- Do not commit raw datasets, credentials, local database files, build output, or generated benchmark results unless explicitly required.

## 5. Tasks and scope

Before coding, answer:

1. What outcome does this change provide?
2. What files, services, data, or users can it affect?
3. What is explicitly out of scope?
4. How will we prove it works?

Use task titles such as `api: add recommendation fallback`, `data: validate event schema`, `docs: explain local setup`, or `fix: handle empty result set`.

If the change affects a public API, database schema, event contract, deployment shape, security behavior, or evaluation method, update the source-of-truth documentation in the same pull request.

## 6. Commits

Make small commits that explain one change. Use an imperative conventional subject, for example:

- `feat(api): add recommendation fallback`
- `fix(validation): reject negative prices`
- `test(streaming): cover duplicate events`
- `docs: add recovery runbook`
- `refactor(config): centralize environment loading`
- `chore: pin container versions`

Keep the subject under 72 characters when practical. Do not mix formatting-only changes with behavior changes. Explain non-obvious reasoning in the body.

Before committing, run `git diff --check` and `git status`. Stage named files only. Avoid `git add -A` when unrelated work may exist.

## 7. Pull requests

Open a pull request from the task branch into `main` when the change is coherent and reviewable. Use this structure:

```markdown
## What changed

## Why

## How to verify

## Evidence

## Risks and limitations

## Follow-up work
```

Every pull request needs:

- one reviewer who understands the affected area;
- passing relevant checks, or an explicit explanation for what could not run;
- no unrelated files;
- updated documentation for changed contracts or workflows;
- tests for normal behavior and important failure paths;
- evidence for user-visible, cross-service, data, or deployment behavior.

Review behavior, not just style. Check compatibility, input validation, error handling, edge cases, security, performance impact, test value, and reproducibility.

The author resolves comments or explains why a comment is not applied. The reviewer approves only after relevant checks are rerun.

## 8. Merge and release policy

Merge only when the pull request targets `main`, review is complete, relevant checks pass, the diff has no accidental files, documentation is current, and follow-up work is recorded.

Use squash merge for task branches unless the project explicitly needs to preserve commit history. After merging, update the local base branch and delete the merged branch.

Do not merge an unreviewed branch, a branch with unexplained failing checks, or a feature that works on only one machine. Do not release or deploy from an unreviewed local branch.

For releases or deployments, record the version/commit, environment, migration steps, health check, rollback or cleanup procedure, and observed result.

## 9. Local development

The normal workflow is:

1. Check the environment and dependencies.
2. Start only the services needed for the task.
3. Make the smallest change that demonstrates the behavior.
4. Run focused tests.
5. Run the broader project checks.
6. Capture evidence when the change crosses a service or environment boundary.
7. Stop local services when finished.

If the project provides a Makefile, task runner, or setup script, use its documented commands. If a command is missing or broken, fix the command or document the temporary workaround. Do not rely on undocumented machine-specific steps.

## 10. Data and configuration

- Define shared schemas in one source-of-truth module or document.
- Validate data at boundaries.
- Preserve identifiers used for joins and references.
- Make timestamps and time zones explicit.
- Make retry and deduplication behavior explicit for event-driven work.
- Keep raw input immutable; write named transformed outputs.
- Keep full datasets and generated outputs out of version control unless explicitly required.
- Store example configuration in `.env.example`; never commit `.env` or live credentials.
- Record dataset source, checksum, license/usage notes, selection rules, and known limitations.
- Record configuration, input size, output size, and run identifier for reproducible jobs.

## 11. Code organization

Keep shared contracts and pure logic separate from I/O. Keep adapters at the edges. Keep public HTTP or CLI layers thin. Do not put database queries, distributed transformations, or business rules into presentation handlers when they belong in a service module.

Use one configuration path. Avoid duplicate validation rules. Prefer deterministic output in tests and examples. Comments should explain why a non-obvious choice exists, not restate the code.

When changing a boundary, update both sides of the contract and add a contract test.

## 12. Testing

Use the smallest test level that proves the behavior, then add integration coverage where boundaries matter.

| Level | Purpose |
|---|---|
| Unit | Pure functions, validation, formatting, calculations |
| Integration | Database, queue, filesystem, service, or framework boundary |
| API/UI | Public request/response and important user flows |
| End-to-end | Complete workflow across services |
| Recovery | Restart, retry, timeout, migration, or failure behavior |

Cover important edge cases: missing input, invalid input, empty results, duplicates, late or repeated requests, unknown identifiers, permission failures, unavailable dependencies, retries, and restart after partial work.

Tests must not depend on a developer's private files, credentials, or full production dataset unless clearly marked and intentionally run as an environment test.

## 13. Evidence and performance

Evidence is part of the contribution when a change affects behavior beyond one pure function. Save commands, logs, screenshots, metrics, or response samples under the project's evidence directory with a date, purpose, and source commit.

Every benchmark states the machine/container, dependency versions, input and workload, units, warm-up method, and whether the result is measured or estimated. Compare like with like. Keep raw output, including poor results. Never turn a mock or small fixture run into a production-scale claim.

## 14. Documentation

Update documentation in the same pull request as the behavior it describes.

| Change | Documentation to update |
|---|---|
| Setup or dependency | README, environment guide, troubleshooting |
| Public API or CLI | Reference documentation and examples |
| Architecture or durable decision | Design document and decision log |
| Data/schema change | Data contract and migration notes |
| Deployment/recovery change | Deployment and rollback runbook |
| User-visible behavior | Tutorial or usage guide |

Use exact commands, expected results, prerequisites, troubleshooting, and links to the source of truth. Do not document behavior that has not been verified.

## 15. Security and safety

- Never commit secrets, tokens, private keys, personal data, or private endpoints.
- Use least-privilege credentials and local test values.
- Review logging for accidental sensitive data.
- Confirm destructive targets before deleting data, dropping schemas, cleaning namespaces, or rewriting history.
- Prefer reversible cleanup and dry runs.
- Report security concerns privately to the project owner instead of opening a public issue with exploit details.

## 16. Handoffs

When stopping work, leave a handoff in the pull request or task file containing: completed work, verification commands, current state, known problems, next exact step, and files to read first.

Never hand off only a branch name or “it mostly works.” Another contributor should be able to reproduce the current state without a private conversation.

## 17. Definition of done

A contribution is done when the intended behavior is implemented, relevant tests pass, failure paths are covered, documentation is current, evidence is saved when needed, a teammate approves the change, no secrets or unrelated artifacts are in the diff, and another contributor can verify it from a clean checkout.

## 18. Quick checklist

Before coding: read the source of truth, confirm scope/owner/reviewer, create the correct branch, identify affected contracts, and write the verification command.

Before a pull request: run formatting/lint/type checks where available, run focused and relevant broader tests, inspect `git status` and the diff, update documentation, and remove secrets/generated junk.

Before merge: reviewer approval, passing checks, correct target branch, recorded limitations, and a clear rollback or follow-up if needed.

After merge: update local `main`, delete the merged branch, and tell the team what changed and what comes next.

## Current project appendix

The current repository uses Plan1A as one implementation milestone. Its specific architecture and commands belong in [the Plan1A implementation plan](docs/implementation-plan-plan1a.md), not in this global rulebook. Future milestones should follow this guide and add their own scoped plan when necessary.
