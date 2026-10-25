# Implementation Plan: Live Adaptive Recommendation Demo UI

Status: Draft for review
Owner: Frontend
Reviewer: Project maintainer / serving-and-frontend owner
Branch: `feature/streaming-vertical-slice`

## Outcome

Turn the current operator-style dashboard into a short, repeatable demonstration of the project's core idea:

> A user's long-term preference and current session intent combine to change the recommendation shelf in real time.

The presenter should be able to select a known user, run a guided phone/audio scenario, see canonical live events appear, and understand why the ranked shelf changed without reading raw infrastructure details.

## Source-of-truth constraints

- This is a frontend presentation change. Do not change the event schema, API contracts, ranking weights, product IDs, or October/November/live-data boundaries.
- A `view` is emitted only when the user clicks View. A `cart` is emitted only when the user explicitly clicks Cart.
- The catalog remains sourced from the same product universe. Any friendly product label or placeholder visual is cosmetic; `product_id` remains the join key.
- The live demo must continue to represent newly generated browser events. Do not describe historical replay as live traffic.
- Keep the UI within catalog, product interaction, cart, and recommendations. Do not add authentication, payments, search, seller workflows, or a separate analytics product.

## Current-state findings

Evidence: static read of `web/src/App.jsx` and `web/src/index.css`.

- `App.jsx` currently exposes catalog, recommendations, session controls, health, event emission, and recommendation refresh in one component.
- The two-column layout gives catalog and recommendations equal visual weight, so the adaptive result is not the clear hero.
- The current copy leads with Kafka/Spark/Cassandra/FastAPI rather than the user-visible outcome.
- Recommendation cards expose raw IDs and score components, but do not explain the before/after change in a single place.
- The activity feed is useful evidence but currently appears as a raw log at the bottom.
- Loading, empty, fallback, offline, and failed-event states are present only as text or badges and need a stronger visual treatment.
- `web/package.json` has React/Vite but no GSAP dependency.

## Design narrative

### 1. Orient

Hero copy: `Adaptive recommendations, live`.

Supporting copy: `Long-term preference + current session intent`.

Keep service health visible, but secondary. Move the technical stack into a small “System path” explanation rather than the headline.

### 2. Establish a baseline

Show the selected persona and session clearly. Add a compact “Current session intent” panel with:

- dominant category, derived from the current event log or returned recommendation metadata;
- event count;
- a simple signal-strength treatment;
- a baseline/current label so the user knows what is changing.

If the session has no events, show `No active intent yet` rather than implying that a model has inferred one.

### 3. Let the user act

Make the catalog the “Try the system” surface. Keep direct View and Cart actions. Rename the two scenario buttons to presentation-ready actions such as `Explore smartphones` and `Explore audio`, while retaining the existing event semantics.

### 4. Make the signal visible

After each event:

1. acknowledge the clicked product;
2. append the event to a chronological activity timeline;
3. update the current intent summary;
4. refresh recommendations;
5. show which recommendation cards changed and why.

### 5. Explain the result

Make the recommendation shelf the dominant panel. Add a clear explanation block:

```text
Why this changed
Long-term preference      60%
Current session intent    25%
Popularity                 10%
```

Keep returned score values and raw IDs available as secondary detail. Do not invent model claims that are not in the API response.

## Proposed layout

```text
[Adaptive recommendations, live]                 [Serving healthy]
[User persona] [Session] [New session] [Refresh]

[Current session intent: exploring smartphones | 3 events]

[Recommended for you / Why this changed]         [Try the system]
[ranked adaptive shelf]                           [catalog + scenario actions]

[Live session timeline: VIEW -> VIEW -> CART -> shelf refresh]
```

On narrow screens, stack the recommendation shelf before the catalog so the result remains visible without excessive scrolling.

## Implementation steps

### Step 1: Add the animation dependencies

Update `web/package.json` and `web/package-lock.json` with `gsap` and `@gsap/react`.

Use the existing Vite/React setup. Do not add a component framework, state-management library, chart library, or image service for this change.

### Step 2: Reshape `App.jsx` into readable UI sections

Keep the existing fetch and event behavior, but extract presentational components or local render helpers for:

- `DemoHeader`;
- `SessionControls`;
- `IntentSummary`;
- `RecommendationShelf`;
- `CatalogPanel`;
- `ActivityTimeline`;
- `StatusState`.

Keep network and event orchestration in `App`. If a helper needs derived data, pass it explicitly rather than duplicating recommendation or event logic.

Add derived UI state only where needed:

- `lastEventId` or equivalent for animating the newly appended event;
- previous recommendation IDs/ranks for changed-card treatment;
- `demoStep` only if the guided scenario needs visible progress.

Do not change the payload sent by `emitEvent`.

### Step 3: Make states explicit

Implement visually distinct states for:

- checking health;
- healthy service;
- degraded/offline service;
- recommendations loading;
- empty recommendation result;
- cold-start fallback;
- event accepted;
- event failed or network failed.

The user must be able to tell whether an event reached the API. Never show a successful-looking “live update” when the request failed.

### Step 4: Implement the visual system in `index.css`

Retain the existing dark palette, but establish semantic tokens:

- system activity: cyan;
- long-term preference / ALS: blue-violet;
- session intent / adaptive result: lime;
- popularity/fallback: amber;
- errors: red.

Improve hierarchy with:

- a larger recommendation hero surface;
- stronger card titles and readable product labels;
- consistent panel spacing and focus states;
- a timeline treatment for events;
- a responsive single-column layout below the existing breakpoint;
- `:focus-visible` styles and adequate contrast.

Avoid adding generated images or external fonts. Placeholder product visuals may use CSS/category metadata only.

### Step 5: Add GSAP motion in a scoped React hook

Create a small animation layer in `App.jsx` or a nearby frontend utility. Prefer `useGSAP()` with a root ref.

Animation behavior:

- initial entrance: short timeline for hero, controls, intent summary, recommendation shelf, catalog, and timeline;
- event acknowledgment: transform/scale pulse on the clicked action and a short highlight on the new timeline item;
- recommendation refresh: stagger changed cards into view and use transform/opacity rather than layout properties;
- loading transition: keep the shelf footprint stable and animate content state changes without causing layout jumps.

Use timeline labels and position parameters for the initial sequence. Use `autoAlpha` for elements that should become non-interactive when hidden.

Use `gsap.matchMedia()` for responsive setup and `prefers-reduced-motion: reduce`. Reduced-motion mode should remove decorative movement while preserving state changes and status text.

Any GSAP work triggered after render must be wrapped with `contextSafe()`. Scope selectors to the app root and ensure cleanup/revert on unmount.

Do not add ScrollTrigger to the core dashboard. The evaluator must see the complete cause-and-effect loop in one viewport. A future presentation-only scroll narrative can be considered separately.

### Step 6: Add focused frontend verification

At minimum, verify:

- `npm run build` succeeds in `web/`;
- `View` still emits exactly one `view` event;
- `Cart` still emits exactly one `cart` event;
- guided phone/audio actions preserve their existing event sequence;
- a failed event request is visibly marked as failed;
- loading and empty recommendation states do not leave stale recommendation content visible;
- changing persona or starting a new session refreshes the shelf and resets the session presentation;
- reduced-motion mode renders the same information without decorative movement;
- keyboard focus is visible for controls and actions.

If a browser runner is available, capture one screenshot before interaction and one after the guided smartphone scenario under `evidence/` with the source commit and command recorded. If no browser runner is available, record the limitation rather than claiming visual verification.

## Acceptance criteria

- A first-time viewer can explain what changed without knowing Kafka, Spark, Cassandra, or ALS.
- The primary visual focus is the recommendation result and its explanation.
- The guided smartphone scenario works from a fresh session and visibly produces a sequence of events followed by a shelf refresh.
- A user can distinguish long-term preference, current session intent, popularity/fallback, loading, and failure states.
- The original event semantics and API payload remain unchanged.
- The layout works at desktop and narrow viewport widths.
- Motion is subtle, interruptible, cleaned up on unmount, and disabled/reduced when requested by the operating system.
- `npm run build` passes and relevant UI evidence is captured or the missing browser coverage is documented.

## Out of scope

- Backend/API/schema changes.
- Recommendation algorithm or ranking-weight changes.
- Product-image ingestion or a new product metadata service.
- Full ecommerce flows such as authentication, checkout, payments, or search.
- Scroll-driven storytelling in the main dashboard.
- New infrastructure, deployment, analytics, or monitoring systems.
- Per-click ALS retraining or claims of exactly-once behavior.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Animation obscures whether an event succeeded | Render status text from the actual request result; animation is secondary. |
| Recommendation refresh races with rapid clicks | Preserve the existing loading state and make the latest response authoritative; avoid optimistic recommendation claims. |
| GSAP animations leak across React renders | Use `useGSAP()` scope, `contextSafe()`, and automatic cleanup. |
| Raw IDs remain hard to understand | Add cosmetic labels while retaining IDs in secondary metadata. |
| UI implies intent before events exist | Show an explicit no-intent state until event evidence exists. |
| The redesign becomes a dashboard rewrite | Limit edits to the three frontend files plus package lock and optional evidence. |
| Browser visual evidence is unavailable | Mark the check as unverified and do not call the UI complete. |

## Verification commands

```bash
cd web
npm install
npm run build
```

Before implementation begins, also run:

```bash
git diff --check
git status --short
```

## Review questions

1. Is the “watch the system adapt” narrative the right demo story for the course evaluation?
2. Should the recommendation shelf be the dominant surface on desktop, or should catalog and shelf remain equal?
3. Are `gsap` and `@gsap/react` acceptable dependencies for this demo, or should the motion remain CSS-only?
4. Is a guided scenario appropriate, given that it emits real browser events, or should the demo remain fully manual?

## Review record

### Evidence used

- `CONTRIBUTING.md`
- `docs/designs/PROJECT_CONTEXT_V2.md`
- `docs/designs/adaptive-session-aware-recommender.md`
- `TODOS.md`
- `web/src/App.jsx`
- `web/src/index.css`
- `web/package.json`
- GSAP React, core, timeline, and ScrollTrigger guidance

### Review coverage

- Static repository review: complete.
- Native gstack autoplan review: unavailable. Required `~/.claude/skills/gstack/bin/gstack-skill-start` was not present in the environment.
- Outside Codex review: unavailable. The gstack Codex probe helper was not present in the environment during the prior skill invocation.
- Browser visual review: not run; this is a plan-only turn.

### Decision audit trail

| Decision | Classification | Rationale |
|---|---|---|
| Make the recommendation shelf the primary surface | Taste | The course value is the visible adaptive result; the current equal split hides it. |
| Keep the core dashboard in one viewport | Design/engineering | The demo must communicate causality without requiring scroll choreography. |
| Use GSAP core timelines plus `useGSAP()` | User-directed | The user explicitly requested GSAP; scoped cleanup and reduced-motion support keep it safe in React. |
| Do not add ScrollTrigger to the core flow | Engineering | Scroll-linked motion is unnecessary for the evaluator path and would add failure modes. |
| Keep backend contracts unchanged | Mechanical | The project context fixes event semantics and product IDs as shared contracts. |

### Completion status

Plan drafted for user review. No implementation changes were made.

