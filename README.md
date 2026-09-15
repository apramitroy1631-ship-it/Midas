# MIDAS — Marketing Intelligence & Decision Automation System

A hierarchical agent system that plans, researches, writes, optimises, reviews, and
publishes marketing content **with no human in the loop**.

QA failures don't stop the pipeline for a person — they trigger a revision cycle. The
Campaign Director can set its own goals from brand memory. Every autonomous decision
is logged. This deployment runs for a single company (see `backend/scripts/seed.py`),
though the system underneath is architected multi-tenant — see
[docs/design/DESIGN_BRIEF.md](docs/design/DESIGN_BRIEF.md) for what that means and why.

**→ [docs/design/DESIGN_BRIEF.md](docs/design/DESIGN_BRIEF.md)** — what MIDAS is, who
it's for, and what each screen means — written for whoever works on the product or
design next, not for an engineer.
**→ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the self-correction loop, the
graph, multi-tenancy, and why autonomy is a policy flag rather than a hard-coded
behaviour.
**→ [docs/API.md](docs/API.md)** — route reference and the SSE streaming contract.
**→ [docs/DEPLOY.md](docs/DEPLOY.md)** — hosting the console on Vercel and the
backend on Railway (or any container host).

---

## Repository layout

```
backend/    FastAPI control plane + LangGraph agent runtime — see backend/README.md
web/        React console (Vite, no router) — see web/README.md
docs/       architecture, API reference, and the design brief
sandbox/    the pipeline-bench prototypes evaluated before this was built (reference only)
```

## Quickstart

**Backend — Docker (simplest):**

```bash
docker compose up --build -d                    # backend + MongoDB together
docker compose exec backend python -m scripts.seed   # prints the tenant's API key — save it, shown once
```

**Backend — without Docker**, if you'd rather: requires Python 3.11+ and
MongoDB reachable at `localhost:27017`.

```bash
cd backend
python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env
.venv/Scripts/python.exe -m scripts.seed        # prints the tenant's API key — save it, shown once
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8100
```

**Console** (requires Node 20+):

```bash
cd web
npm install && npm run dev                      # http://localhost:5175
```

Open the console, paste the key from the seed step. That's the whole setup — the
console is single-tenant by design; there's no "add another" affordance in the UI
(the backend can still provision more via `POST /v1/admin/tenants` if you ever need
a second one — see docs/DEPLOY.md).

By default `LLM_PROVIDER=simulator` in `backend/.env` — no API key or network needed
to see the full pipeline run, including a real QA-failure → revision → pass cycle.
Switch to `openai`/`anthropic`/`ollama` with a funded key for real inference; nothing
else changes. Details: [docs/ARCHITECTURE.md § LLM provider](docs/ARCHITECTURE.md#llm-provider).

## Testing

```bash
cd backend && .venv/Scripts/python.exe -m pytest
```

Covers tenant-isolation enforcement, the self-correction routing logic, and the
agent schema contracts — see [backend/README.md § Testing](backend/README.md#testing).
