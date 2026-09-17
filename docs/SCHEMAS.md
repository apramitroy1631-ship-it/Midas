# MIDAS — Data Schemas

MongoDB collection shapes for the five things MIDAS actually stores. Every
field below is pulled directly from the Pydantic schemas and the code that
writes each document — this isn't a proposal, it's what's running today.

**One thing to know before any of this makes sense:** almost every collection
carries a `tenant_id`, and every query MIDAS runs against them is filtered by
it in the data layer (`app/db/scoped.py`), not by the caller. A tenant's own
code cannot construct a query that reads across into another tenant's
documents — the filter is added after the fact and can't be overridden.
`tenants`, `users`, and `sessions` are the three exceptions, for the obvious
reason that they're what *define* the tenant boundary in the first place.

---

## `brands` — tenant-scoped

A brand is what the agents are bound by on every run — voice, USP, and above
all its `content_restrictions`, which QA treats as absolute rather than
advisory. `memory` is the one field the agents write to themselves: the
`learn` node updates it after every run, and the orchestrator reads it
before planning the next one.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | Primary key. |
| `tenant_id` | string | Stamped on write, never client-settable. |
| `name` | string | |
| `description` | string | |
| `industry` | string | |
| `tone` | string | Written as direction to a copywriter, not adjectives — see `docs/design/DESIGN_BRIEF.md`. |
| `usp` | string | The one claim competitors can't make. |
| `target_audience` | string | Default; a run can override it. |
| `website` | string | |
| `memory.past_campaigns` | string[] | Appended by the learn node. |
| `memory.latest_insights` | string[] | Appended by the learn node. |
| `memory.winning_angles` | string[] | Angles the orchestrator should reuse. |
| `memory.exhausted_angles` | string[] | Angles the orchestrator must not repeat. |
| `memory.brand_guidelines.visual_style` | string | |
| `memory.brand_guidelines.preferred_channels` | string[] | e.g. `["linkedin","blog","email"]`. |
| `memory.brand_guidelines.content_restrictions` | string[] | **Absolute.** A breach fails QA outright — the only hard-blocking rule in the whole system. |
| `created_at` / `updated_at` | ISO 8601 string | UTC, second precision. |

Referenced by → `runs.brand_id`, `assets.brand_id`.
Collection: `brands`. Source: `app/schemas/brand.py`.

---

## `runs` (campaigns) — tenant-scoped

One document per campaign run. This is the full agent trace — plan,
research, strategy, content, SEO, QA, analytics, learning — plus every SSE
event that streamed to the console while it ran, so a run stays fully
replayable after the fact.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | = `run_id` everywhere else. |
| `tenant_id`, `brand_id` | string | |
| `brand_name` | string | Denormalised at write time — avoids a join for the run list. |
| `status` | string | `queued` → `running` → `published` / `published_partial` / `review_pending` / `abandoned` / `failed`. |
| `goal` | string | Final, sharpened goal — may differ from the operator's input. |
| `goal_origin` | string | `operator` or `self-directed` (no goal was supplied; the Director picked one). |
| `trigger` | string | `manual` / `autopilot` / `api`. |
| `budget` | float | USD, operator-supplied. |
| `plan` / `research` / `strategy` / `content` / `seo` / `qa_report` / `analytics` / `learning` | object | One raw dump per agent. |
| `revisions` | int | How many times content went back for a fix. |
| `dropped_channels` | string[] | Non-empty only after arbitration. |
| `qa_passed` | bool \| null | |
| `brand_safety_score` / `goal_alignment_score` | int \| null | 0–100, QA's own scoring. |
| `asset_count` | int | |
| `usage` | object | `{prompt_tokens, completion_tokens, cost_usd, llm_calls, tokens_by_agent}`. |
| `duration_ms` | int | |
| `events` | object[] | The full SSE trace: `{node, label, status, revision, output, at, elapsed_ms}` per step. |
| `error` | string \| null | |
| `created_at` / `updated_at` | ISO 8601 string | |

Referenced by → `assets.run_id`, `audit.run_id`.
Collection: `runs`. Source: `app/schemas/run.py`, written by `app/graph/runner.py`.

---

## `assets` (content) — tenant-scoped

The actual content library — one document per published (or
pending-review) piece. This is the collection the Content Library screen
and the content-canvas editor both read and write.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | |
| `tenant_id`, `run_id`, `brand_id` | string | |
| `brand_name` | string | Denormalised. |
| `channel` | string | `email` / `blog` / `linkedin` today; the schema doesn't constrain it to those three. |
| `headline` | string | Editable via `PATCH /v1/assets/{id}`. |
| `body` | string | Editable. |
| `call_to_action` | string | Editable. |
| `status` | string | `published` or `pending_review`, decided at write time by the tenant's autonomy policy. |
| `seo` | object \| null | `{primary_keyword, secondary_keywords[], meta_title, meta_description, slug, hashtags[]}`. |
| `goal` | string | Copied from the parent run's plan. |
| `brand_safety_score` / `goal_alignment_score` | int \| null | Copied from the run's QA report at publish time. |
| `created_at` / `updated_at` | ISO 8601 string | `updated_at` moves on every content-canvas save. |

Points to → `runs._id` via `run_id`, `brands._id` via `brand_id`.
Collection: `assets`. Source: `app/schemas/run.py` (`AssetResponse`,
`AssetUpdate`), written by the `publish` graph node in `app/graph/nodes.py`,
edited via `app/api/routes_runs.py`.

---

## `audit` (decision log) — tenant-scoped

The accountability trail. This collection exists *because* nothing waits
for a human sign-off — every autonomous decision gets one entry here with a
reason, which is what makes "no human in the loop" defensible after the
fact rather than just a claim.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | |
| `tenant_id`, `run_id`, `brand_id` | string | |
| `action` | string | `run.published` / `run.published_partial` / `run.review_pending` / `run.abandoned` / `run.failed`. |
| `actor` | string | Always `system:autonomous` today — reserved for a future human-actor case. |
| `trigger` | string | Same vocabulary as `runs.trigger`. |
| `detail.goal` / `goal_origin` | string | |
| `detail.revisions` | int | |
| `detail.assets` | int | Count published. |
| `detail.dropped_channels` | string[] | What arbitration dropped, if anything. |
| `detail.qa_passed` | bool \| null | |
| `detail.cost_usd` | float | |
| `created_at` | ISO 8601 string | |

One audit entry is written per *run*, not per agent step — the step-by-step
reasoning (why QA flagged something, what the revision changed) lives in
`runs.events` and `runs.qa_report.issues[]`, not duplicated here. The
Decision Log screen in the console reads both.

Points to → `runs._id`.
Collection: `audit`. Source: `app/graph/runner.py` (`_finalise`), read via
`GET /v1/audit` in `app/api/routes_runs.py`.

---

## `users` — not tenant-scoped

Personal logins, separate from a tenant's own API key on purpose: a tenant
key is a shared service credential, never rotated per person; a user
account is one person's own login, created by an admin
(`POST /v1/auth/register`, gated by `X-Admin-Key`) rather than open
self-signup.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | |
| `tenant_id` | string | Which tenant this login belongs to. |
| `email` | string | Unique index — lower-cased on write. |
| `phone` | string \| null | Stored, not yet OTP-verified. |
| `password_hash` | string | PBKDF2-HMAC-SHA256, 200,000 rounds. |
| `password_salt` | string (hex) | 16 random bytes per user. |
| `created_at` | ISO 8601 string | |

Collection: `users` (unique index on `email`). Source: `app/db/users.py`.

---

## `sessions` — not tenant-scoped

Issued on a successful `/v1/auth/login`. The console sends the raw token
back as the same `X-API-Key` header a tenant key would use — the `sess_`
prefix (vs. a key's `bx_live_`) is what lets one header carry either
credential without ambiguity. See `app/tenancy/auth.py`.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | |
| `tenant_id`, `user_id` | string | |
| `token_hash` | string | SHA-256 of the raw token — the raw value is never stored. |
| `created_at` / `expires_at` | ISO 8601 string | 30-day TTL, checked on every request, not enforced by a Mongo TTL index yet. |

Collection: `sessions` (unique index on `token_hash`). Source: `app/db/sessions.py`.

---

## `tenants` — defines the tenant boundary

The one collection deliberately *not* scoped by tenant_id — it's what every
other scoping decision is keyed off. A raw API key is shown exactly once at
creation and never stored; only its SHA-256 hash lives here.

| Field | Type | Notes |
|---|---|---|
| `_id` | string (uuid) | |
| `name`, `slug` | string | `slug` unique-indexed. |
| `status` | string | `active` by default. |
| `api_key_hash` | string | SHA-256, unique-indexed. Raw key is `bx_live_` + 32 random bytes, base64url. |
| `api_key_prefix` | string | First few chars, shown in Settings for identification only. |
| `policy` | object | `{autonomy, auto_publish, max_revision_cycles, forbidden_claims[], required_disclaimers[], banned_phrases[]}`. |
| `autopilot` | object | `{enabled, interval_minutes, brand_id, last_run_at, next_run_at}`. |
| `limits` | object | `{monthly_run_quota, monthly_budget_usd}`. |
| `usage` | object | `{runs_this_period, spend_usd, period}` — rolls over automatically when the month changes. |
| `model_overrides` | object | Per-agent provider/model override, keyed by agent name. |
| `created_at` / `updated_at` | ISO 8601 string | |

Collection: `tenants` (unique indexes on `slug` and `api_key_hash`).
Source: `app/schemas/tenant.py`, `app/db/tenants.py`.

---

See also: [Backend Architecture Guide](BACKEND_GUIDE.md) ·
[Frontend Guide](FRONTEND_GUIDE.md) · [Testing Guide](TESTING_GUIDE.md)
