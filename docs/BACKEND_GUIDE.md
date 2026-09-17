# MIDAS — Backend Architecture

For the backend engineer. What's actually running, why it's shaped this
way, and where to make your first change. Written to get you productive,
not to be read cover to cover — jump to whatever section your task touches.

## Mental model

MIDAS runs marketing campaigns end to end with nobody approving a step. A
campaign is a graph of agents — Director, Research, Strategy, Content, SEO,
QA — that hands off from one to the next, and when QA finds a real problem,
the graph routes back to the writer instead of stopping for a person. That
loop is the actual product; everything else in this codebase exists to
support it safely (tenant isolation), observably (the decision log), or
configurably (autonomy policy, model routing).

> **If you remember one thing:** "no human in the loop" is a policy setting
> per tenant (`policy.autonomy`), not a hard-coded behaviour. The identical
> graph runs either way — the only difference is whether `publish_node`
> writes `status: "published"` or `status: "pending_review"`.

## Repo layout

```
backend/
  app/
    agents/        one file per specialist — prompt + schema + build_prompt()
    api/           FastAPI routers (routes_runs, routes_brands, routes_tenants, routes_autopilot, routes_auth)
    core/          settings.py (env config), config.py (agent → model routing), logging.py
    db/            mongo.py (client + indexes), scoped.py (tenant-isolated collection wrapper),
                   tenants.py / users.py / sessions.py (the three unscoped collections)
    graph/         builder.py (the LangGraph itself), nodes.py, runner.py (streams it), state.py
    schemas/       Pydantic models — agents.py (LLM I/O contracts), run.py, brand.py, tenant.py
    services/
      llm/         provider abstraction: openai/anthropic/gemini/ollama/simulator, react_engine.py, usage.py
      autopilot.py background scheduler loop
    tenancy/       auth.py (request → tenant resolution), context.py (contextvar the scoping reads)
    tools/         LangChain tools the agents can call (brand memory lookups, research)
  scripts/seed.py  provisions the one CMART tenant this deployment runs for
  tests/
Dockerfile, railway.json    at the repo root, not backend/ — see docs/DEPLOY.md for why
docker-compose.yml          local dev: backend + Mongo together
```

## The agent pipeline

Defined in `app/graph/builder.py` with LangGraph's `StateGraph`. State is a
single `TypedDict` (`RunState`, in `state.py`) that every node reads from
and returns a partial update into — LangGraph merges the deltas for you.

```
orchestrate → research → strategy → content → seo → qa
                                       ^                 \
                                       |                  v
                                     revise         (clean) → publish → analytics → learn → END
                              (critical issue,
                               budget left)
```

QA routes to `revise` (loops back to `content`) on a critical issue with
revision budget left, to `arbitrate` once the budget is exhausted (drops
the offending channel(s), publishes the rest), or straight to `publish` on
a clean pass. `arbitrate` is the floor: it guarantees the graph terminates
even if the writer never satisfies QA on some channel. Nothing in this
system ever parks indefinitely waiting on a person.

### Each node, in one line

| Node | Does |
|---|---|
| orchestrate | Sharpens or invents the goal, picks channels + budget split, writes the delegation brief. Everything downstream is bound by its plan. |
| research | Runs the ReAct tool loop (brand memory, past campaigns) to ground the plan in facts. |
| strategy | Turns the plan into channel-level tactics and budget allocation. |
| content | Writes one asset per planned channel. On a revision pass, receives QA's exact issues and must address each one explicitly — this is what replaces a human editor's notes. |
| seo | Per-asset keyword/meta/slug optimisation. |
| qa | Scores brand safety + goal alignment, flags issues as `critical` (blocking) or `advisory`. |
| publish | The only node with real write logic: inserts each asset into `assets`, honouring the tenant's `auto_publish` policy. |
| analytics / learn | Simulated performance read + writes back to `brand.memory` so the next run doesn't repeat an exhausted angle. |

A node is a thin adapter — pull what its agent needs out of state, call
`Agent.run()`, put the typed result back (`app/graph/nodes.py`). The agent
classes themselves (`app/agents/*.py`) are just a system prompt, an output
schema, and a `build_prompt()` method; `Agent.run()` in `app/agents/base.py`
handles model resolution, the tool loop, and usage attribution identically
for all of them.

## Tenant isolation

Enforced in the data layer, not the application layer — that's the whole
point of `app/db/scoped.py`'s `ScopedCollection`. Every query is
intersected with the tenant bound to the current request; a handler cannot
widen the scope, because a crafted filter like `{"tenant_id": "someone-else"}`
is *overwritten*, not merged.

```python
class ScopedCollection:
    def _scope(self, query):
        scoped = dict(query or {})
        scoped["tenant_id"] = current_tenant()   # last write wins — cannot be overridden
        return scoped
```

`current_tenant()` reads a `contextvars.ContextVar` set once per request by
`require_tenant` (`app/tenancy/auth.py`) and carried across the worker
thread a run executes on (`graph/runner.py` copies the context explicitly
for this reason — see the comment there if you're touching threading).

> **Practical rule:** if you're adding a new collection that belongs to one
> tenant, wrap it in `ScopedCollection` and never call `app/db/mongo.py`'s
> `raw()` directly for it. `raw()` exists only for the collections that
> define tenancy itself — `tenants`, `users`, `sessions`.

## Authentication

One header, two kinds of credential. `require_tenant` checks the
`X-API-Key` header's prefix and routes accordingly:

- **Tenant key** — `bx_live_…`. A shared service credential, hashed
  (SHA-256) in `tenants.api_key_hash`. Shown once at creation via
  `POST /v1/admin/tenants` (needs `X-Admin-Key`).
- **Session token** — `sess_…`. Personal, minted by `POST /v1/auth/login`.
  Resolves to a tenant via the `sessions` collection. 30-day TTL, checked
  on every request.

Registration (`POST /v1/auth/register`) is admin-gated, not open — an
autonomous system that runs real campaigns can't let anyone who finds the
URL create their own login. You provision one account per teammate with
the admin key; after that they sign in with their own email/password.

## LLM providers

`app/services/llm/llm_factory.py` resolves a provider per agent, in this
order: tenant's `model_overrides` → global `AGENT_MODEL_MAP`
(`app/core/config.py`) → `settings.llm_provider` fallback. One exception:
if `LLM_PROVIDER=simulator`, that overrides everything — it's an
environment-level switch, not a per-agent preference, so you can't
accidentally leave one agent hitting a real API while testing.

| Provider | File | Notes |
|---|---|---|
| openai | openai_provider.py | Native structured-output `.parse()` for mode 1; `ChatOpenAI` for tool binding. |
| anthropic | anthropic_provider.py | No native structured output — JSON-schema-in-system-prompt + manual `model_validate_json`. |
| gemini | gemini_provider.py | Same shape as Anthropic's, via `langchain-google-genai`. Free tier at aistudio.google.com. |
| ollama | ollama_provider.py | OpenAI-compatible local endpoint, zero cost, needs a machine that can run the model. |
| simulator | simulator_provider.py | No network call — regex-scrapes the prompt it's handed to produce schema-valid, deterministic-ish output. |

### The simulator, and its one sharp edge

It's not a mock in the usual sense — it's prompt-derived: `_channels(prompt)`
and friends pull real values (goal, brand name, channel list) back out of
the text the agent actually built, so the graph shape, streaming, and
persistence all get exercised for free. The QA pass it simulates isn't a
rubber stamp either — the first pass raises a real critical issue and the
revision pass clears it, so the self-correction loop runs for real.

> **Gotcha we hit building the channel-override feature:** different agents
> serialise their channel list differently — a plan's
> `channels: [{"channel": "email", ...}]` vs. a strategy's flat
> `channels: ["email"]`. The simulator's channel-scraper has to check for
> both shapes explicitly (`_channels()` in `simulator_provider.py`), or a
> downstream step silently falls back to scanning the brand's
> `preferred_channels` and ignores whatever the operator actually asked
> for. If you add a new per-channel field anywhere, make sure this scraper
> still finds it.

## Autopilot

`app/services/autopilot.py` — a background `asyncio` task started in
`main.py`'s lifespan (only if `AUTOPILOT_ENABLED=true`), sweeping every
`AUTOPILOT_SWEEP_SECONDS` for tenants whose `autopilot.enabled` is on and
whose `next_run_at` is due. It calls `graph/runner.py`'s `run_sync()` — the
blocking variant, since there's no SSE client to stream to.

## API surface

Full reference: `docs/API.md`. The shape worth internalising:
`POST /v1/runs/stream` is the one real-time endpoint (Server-Sent Events,
not WebSocket — one-directional is all the console needs), everything else
is a normal REST resource scoped by the auth dependency on the router.

```python
router = APIRouter(prefix="/v1", tags=["Runs"], dependencies=[Depends(require_tenant)])
```

## Common changes, and where they live

| Task | Start here |
|---|---|
| Add a new agent to the pipeline | `agents/<name>.py` (copy an existing one's shape) → register in `graph/nodes.py` and `graph/builder.py` → add its model to `core/config.py`'s `AGENT_MODEL_MAP` → teach the simulator to fake it in `_SYNTH` (bottom of `simulator_provider.py`). |
| Add a new LLM provider | New file in `services/llm/` implementing `BaseLLM`'s two methods → register in `llm_factory.py`'s `_build()`. |
| Add a field to an asset/run | Update the Pydantic schema in `schemas/run.py` *and* wherever the document is actually constructed (`publish_node` for assets, `runner.py`'s `_finalise` for runs) — the schema alone doesn't make Mongo write it. |
| Change a tenant's guardrails | `PATCH /v1/me` (self-service, tenant-scoped) vs. `PATCH /v1/admin/tenants/{id}` (admin-only, can also raise quota). |
| New Mongo index | `db/mongo.py`'s `ensure_indexes()`, run at startup. |

## Running & deploying

- **Local:** `docker compose up --build -d` then
  `docker compose exec backend python -m scripts.seed`. Full test suite:
  `pytest` (28 tests today — tenant isolation, revision routing, agent
  schema contracts).
- **Env config:** everything in `backend/.env.example`, loaded by
  `core/settings.py`. `LLM_PROVIDER=simulator` is the safe default —
  flipping it to `gemini`/`openai`/`anthropic` needs the matching API key
  set too.
- **Deploy:** Railway builds the root-level `Dockerfile` directly (not
  `backend/Dockerfile`, which is local-dev-only) — see `docs/DEPLOY.md` for
  the full walkthrough and why the Root Directory dashboard setting was
  abandoned in favour of this.
- **Health check:** `GET /health` reports Mongo connectivity —
  `"degraded"` almost always means `MONGODB_URI` isn't wired to the right
  variable name.

---

See also: [Data Schemas](SCHEMAS.md) · [Frontend Guide](FRONTEND_GUIDE.md) ·
[Testing Guide](TESTING_GUIDE.md) · full detail beyond this summary:
[ARCHITECTURE.md](ARCHITECTURE.md)
