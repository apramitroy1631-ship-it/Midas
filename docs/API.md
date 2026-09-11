# API reference

Authenticate tenant-scoped routes with `X-API-Key`. Tenant provisioning uses
`X-Admin-Key` instead — it is a separate, higher-privilege credential that should
never be handed to a tenant.

| Route | Description |
|---|---|
| `POST /v1/admin/tenants` | Provision a tenant; returns the API key once, never again |
| `GET/PATCH /v1/me` | Current tenant: policy, quota, usage |
| `GET/POST/PATCH/DELETE /v1/brands` | Brand CRUD |
| `POST /v1/runs/stream` | Start a run, stream every agent step as SSE |
| `GET /v1/runs`, `/v1/runs/{id}` | Run history and full agent trace |
| `GET /v1/assets` | Content library |
| `GET /v1/audit` | Every autonomous decision, with reasoning |
| `GET /v1/stats` | Dashboard headline numbers |
| `GET /v1/autopilot`, `POST /v1/autopilot/tick` | Unattended operation |

## Streaming a run

`POST /v1/runs/stream` emits Server-Sent Events: `start`, one `step` per node
(including each revision cycle), then `done` or `error`.

```json
{"brand_id": "...", "goal": null, "target_audience": null, "budget": 8000}
```

Omitting `goal` lets the Campaign Director choose one from brand memory — this is
what the "self-directed" badge in the console means.

### CRLF gotcha

`sse-starlette` separates fields and events with **CRLF**, not `\n\n`. A client that
splits on `"\n\n"` connects successfully, the backend runs the full pipeline, and the
client silently receives *nothing* — no error, just an empty stream. Normalise before
splitting:

```ts
buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
```

See [`web/src/lib/api.ts`](../web/src/lib/api.ts) for the working implementation. The
same latent bug exists in `sandbox/agent-dashboard/src/sse.ts`, the earlier prototype
dashboard, left unfixed there since that folder is kept for reference only.

## Errors

Standard FastAPI/Pydantic error shapes: `{"detail": "..."}` for a single message, or
a validation error array for a malformed body. Cross-tenant access attempts return
`404` (never `403`) so a probing client cannot distinguish "not yours" from
"doesn't exist" — see [Architecture → Multi-tenancy](ARCHITECTURE.md#multi-tenancy).
