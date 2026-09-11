# Architecture

## What makes it autonomous

The interesting property is not that no one clicks approve — it is what happens when
something is **wrong**. A pipeline with no human and no recovery just publishes bad
content. This one has three layers of recovery, all agent-driven:

| Situation | What happens | Who decides |
|---|---|---|
| QA finds a blocking issue | The specific issues go back to the writer as a revision brief; the writer fixes them and QA re-reviews | QA agent |
| Revision budget runs out with issues still open | Assets that individually cleared QA still ship; assets with critical issues are dropped | Arbitration policy |
| Nothing survives | The run is abandoned and logged with the reason | Arbitration policy |

No path waits on a person. A run always terminates in a recorded outcome. See
[`app/graph/builder.py`](../backend/app/graph/builder.py) for the routing decisions and
[`tests/test_graph_routing.py`](../backend/tests/test_graph_routing.py) for the pinned
behaviour of each branch.

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
[`ScopedCollection`](../backend/app/db/scoped.py) intersects every filter with the
active tenant and stamps every insert with it. A crafted filter cannot widen the
scope — `tenant_id` is overwritten, not merged — and a missing tenant binding raises
rather than reading across tenants. This property is automated in
[`tests/test_scoped_isolation.py`](../backend/tests/test_scoped_isolation.py) and was
manually verified end-to-end:

```
GET  /v1/brands/{other-tenants-brand}   → 404
POST /v1/runs/stream (other tenant's brand_id) → error: "Brand not found in this tenant."
```

Each tenant carries its own policy (autonomy, revision budget, forbidden claims,
banned phrases, required disclaimers), its own quota and budget, and optional
per-agent model routing.

## Autonomy is a policy flag, not a hard-coded behaviour

The original project brief made a mandatory human approval gate non-negotiable for
the first deliverable. That conflicts with running unattended, so it is a tenant
setting rather than an architectural decision:

- `policy.autonomy = "autonomous"` — QA failures loop back to the writer; clean passes publish.
- `policy.autonomy = "review_required"` — the identical agent pipeline runs, but finished
  content is written as `pending_review` instead of publishing.

Switching costs one API call. Nothing in the graph changes.

## LLM provider

`LLM_PROVIDER` in `backend/.env` selects the backend:

- `simulator` *(current default)* — no network, no credits. Produces schema-valid,
  prompt-derived output so the graph, streaming, persistence, and UI all run end to
  end. It is **not a model**: the copy is templated and the numbers are invented. It
  deliberately fails the first QA pass and clears on revision, so the self-correction
  loop is genuinely exercised rather than skipped by an always-passing reviewer. See
  [`app/services/llm/simulator_provider.py`](../backend/app/services/llm/simulator_provider.py).
- `openai` / `anthropic` / `ollama` — real inference. Set the matching API key.

Live web research (Tavily/Serper) is optional. Without keys those tools return a
structured `unavailable` observation and the agent proceeds on model knowledge,
recording `model-knowledge: no live search configured` in its sources. An unattended
system must not stall on missing optional config.

## Not built

Deliberately out of scope: analytics dashboards beyond the forecast, real channel
publishing (assets land in the library, not on LinkedIn), nested tenant hierarchies,
fine-tuning, and a separate control-plane service — the control plane is FastAPI
here, in the same process as the agent runtime, since splitting it out would have
tripled the surface area without changing what the demo proves.
