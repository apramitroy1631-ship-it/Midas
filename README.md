# BuildX — Autonomous Multi-Tenant Marketing

A hierarchical agent system that plans, researches, writes, optimises, reviews, and
publishes marketing content **per tenant, with no human in the loop**.

Where the earlier `pipeline-bench` prototypes stopped at a single-brand pipeline with
an auto-passing QA step, this adds the three things that were missing: real tenant
isolation, a manager agent that decides what a run is for, and a QA gate that can
send work back instead of stopping for a person.

---

## What makes it autonomous

The interesting property is not that no one clicks approve — it is what happens when
something is **wrong**. A pipeline with no human and no recovery just publishes bad
content. This one has three layers of recovery, all agent-driven:

| Situation | What happens | Who decides |
|---|---|---|
| QA finds a blocking issue | The specific issues go back to the writer as a revision brief; the writer fixes them and QA re-reviews | QA agent |
| Revision budget runs out with issues still open | Assets that individually cleared QA still ship; assets with critical issues are dropped | Arbitration policy |
| Nothing survives | The run is abandoned and logged with the reason | Arbitration policy |

No path waits on a person. A run always terminates in a recorded outcome.

The system also sets its own agenda. Omit the goal and the Campaign Director reads
brand memory — what worked, what is exhausted, what has never been tried — and picks
the goal itself. Autopilot runs this on a schedule with nobody present.

And it compounds: the final `learn` node writes insights, winning angles, and
exhausted angles back into brand memory, which the Director reads at the start of the
next run. Run three is planned against what runs one and two taught it.

## The graph

```
orchestrate → research → strategy → content → seo → qa
                              ↑                       │
                           revise ←──── critical issues, budget remaining
                                                      │
                              clean ──────────────────┴──→ publish → analytics → learn
                                                      │
                budget spent, issues open ────────────┴──→ arbitrate → publish │ abandon
```

Eleven nodes, seven agents. The Campaign Director is hierarchically above the rest:
it writes the goal, the channel split, the research questions the research agent must
answer, and the success criteria the QA agent judges against. Specialists do not
choose their own scope.

## Multi-tenancy

Isolation is enforced in the data layer, not by caller discipline.
[`ScopedCollection`](backend/app/db/scoped.py) intersects every filter with the active
tenant and stamps every insert with it. A crafted filter cannot widen the scope —
`tenant_id` is overwritten, not merged — and a missing tenant binding raises rather
than reading across tenants.

Verified behaviour:

```
GET  /v1/brands/{other-tenants-brand}   → 404
POST /v1/runs/stream (other tenant's brand_id) → error: "Brand not found in this tenant."
```

Each tenant carries its own policy (autonomy, revision budget, forbidden claims,
banned phrases, required disclaimers), its own quota and budget, and optional
per-agent model routing.

## Autonomy is a policy flag, not a hard-coded behaviour

`PROJECT_OVERVIEW_BUILDX.md` makes a mandatory human approval gate non-negotiable for
the September deliverable. That conflicts with running unattended, so it is a tenant
setting rather than an architectural decision:

- `policy.autonomy = "autonomous"` — QA failures loop back to the writer; clean passes publish.
- `policy.autonomy = "review_required"` — the identical agent pipeline runs, but finished
  content is written as `pending_review` instead of publishing.

Switching costs one API call. Nothing in the graph changes.

---

## Running it

Requires Python 3.11+, Node 20+, and MongoDB on `localhost:27017`.

**Backend**

```bash
cd backend && python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt
```

```bash
cd backend && cp .env.example .env && .venv/Scripts/python.exe seed.py
```

`seed.py` provisions two tenants with distinct brands and prints their API keys —
**they are not retrievable afterwards**. Two tenants is the minimum that makes
isolation demonstrable.

```bash
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8100
```

**Console**

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5175, paste a tenant key. Add the second key from the tenant
switcher to see the datasets stay separate.

## LLM provider

`LLM_PROVIDER` in `backend/.env` selects the backend:

- `simulator` *(current default)* — no network, no credits. Produces schema-valid,
  prompt-derived output so the graph, streaming, persistence, and UI all run end to
  end. It is **not a model**: the copy is templated and the numbers are invented. It
  deliberately fails the first QA pass and clears on revision, so the self-correction
  loop is genuinely exercised rather than skipped by an always-passing reviewer.
- `openai` / `anthropic` / `ollama` — real inference. Set the matching API key.

The simulator exists because the OpenAI key carried over from `pipeline-bench` is
valid but has **no credits** (`insufficient_quota`). Fund it, set
`LLM_PROVIDER="openai"`, restart — no other change is needed.

Live web research (Tavily/Serper) is optional. Without keys those tools return a
structured `unavailable` observation and the agent proceeds on model knowledge,
recording `model-knowledge: no live search configured` in its sources. An unattended
system must not stall on missing optional config.

## API

Authenticate with `X-API-Key`. Tenant provisioning uses `X-Admin-Key`.

| | |
|---|---|
| `POST /v1/admin/tenants` | Provision a tenant; returns the key once |
| `GET/PATCH /v1/me` | Current tenant, policy, quota, usage |
| `GET/POST/PATCH/DELETE /v1/brands` | Brand CRUD |
| `POST /v1/runs/stream` | Start a run, stream every agent step as SSE |
| `GET /v1/runs`, `/v1/runs/{id}` | History and full agent trace |
| `GET /v1/assets` | Content library |
| `GET /v1/audit` | Every autonomous decision |
| `GET /v1/stats` | Dashboard headline numbers |
| `GET /v1/autopilot`, `POST /v1/autopilot/tick` | Unattended operation |

`POST /v1/runs/stream` emits `start`, `step` (one per node, including each revision
cycle), then `done` or `error`. **Note:** `sse-starlette` separates events with CRLF.
A client that splits on `"\n\n"` silently receives nothing — see the normalisation in
[`web/src/lib/api.ts`](web/src/lib/api.ts). The same latent bug is in
`pipeline-bench/agent-dashboard/src/sse.ts`.

## Layout

```
backend/app/
  tenancy/     tenant context + API-key auth
  db/scoped.py where isolation is actually enforced
  agents/      seven agents: prompt + typed contract each
  graph/       state, nodes, builder (the revision loop), runner (threaded SSE)
  services/    LLM providers, usage metering, autopilot scheduler
web/src/
  views/       mission control, launch, runs, library, brands, audit, settings
  components/  AgentRail — the live pipeline view
```

## Not built

Deliberately out of scope, matching the overview doc: analytics dashboards beyond the
forecast, real channel publishing (assets land in the library, not on LinkedIn),
nested tenant hierarchies, fine-tuning, and the Spring Boot control plane — the
control plane is FastAPI here, since a second language would have tripled the surface
area without changing what the demo proves.
