# Backend

FastAPI control plane + LangGraph agent runtime, in one process. See
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for why it's shaped this way and
[`../docs/API.md`](../docs/API.md) for the route reference.

## Layout

```
app/
  tenancy/        API-key auth + the ambient tenant binding every query relies on
  db/
    scoped.py       where multi-tenant isolation is actually enforced
    tenants.py      the one deliberately unscoped collection — it defines the scopes
    mongo.py        client, indexes
  schemas/        Pydantic contracts: tenant/brand/run shapes, and the seven
                  agent input/output schemas the LLM providers validate against
  agents/         one file per agent — a system prompt + a typed contract each
  graph/
    state.py        the TypedDict threaded through every node
    nodes.py         thin adapters: pull from state, run an agent, put the result back
    builder.py       the graph wiring — this is where the revision/arbitration
                     routing lives (_after_qa, _after_arbitrate)
    runner.py        drives a run on a worker thread and streams it back as SSE
  services/
    llm/             one provider per backend (openai/anthropic/ollama/simulator),
                     all implementing the same BaseLLM contract
    autopilot.py     the unattended scheduler
  api/            route handlers — thin; the logic lives in graph/ and services/
scripts/
  seed.py         provisions demo tenants + brands (run as `python -m scripts.seed`)
tests/            see Testing, below
```

## Running

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env
```

```bash
.venv/Scripts/python.exe -m scripts.seed        # prints two tenant API keys, once
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8100
```

Requires MongoDB reachable at `MONGODB_URI` (default `mongodb://localhost:27017`).

## Testing

```bash
.venv/Scripts/python.exe -m pytest
```

Tests that touch Mongo use a dedicated `buildx_test` database (never the real one)
and drop it at the end of the session — see [`tests/conftest.py`](tests/conftest.py).
No API keys or a running server are required; the suite covers:

- `test_tenancy_context.py` — the ContextVar-based tenant binding, in isolation
- `test_scoped_isolation.py` — a tenant can never read, update, or delete another
  tenant's documents, even with a crafted filter (automates the manual isolation
  walkthrough in the architecture doc)
- `test_graph_routing.py` — the self-correction loop's decisions (publish / revise /
  arbitrate / abandon) as pure functions, no LLM or DB needed
- `test_agent_schemas.py` — the typed contracts between agents reject malformed
  shapes rather than silently accepting them
