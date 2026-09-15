# Deploying BuildX

Two separate deployments, because the frontend and backend have genuinely
different hosting needs — see [ARCHITECTURE.md](ARCHITECTURE.md) for why the
backend runs its own long-lived process (the autopilot scheduler) rather than
responding request-by-request.

| | Hosts | Why |
|---|---|---|
| `web/` | Vercel | Static build, no server-side state — Vercel's core use case |
| `backend/` | Railway (or any container host) | Needs a persistent process for the autopilot scheduler, long-lived SSE streams, and a real MongoDB connection — a serverless platform's per-request execution model doesn't fit any of the three |

Deploy order doesn't matter — the console asks for its backend URL at runtime
(the Connect screen), not at build time, so either side can go first and get
pointed at the other afterward with no rebuild.

## Frontend — Vercel

1. Sign up at [vercel.com/signup](https://vercel.com/signup) with **Continue
   with GitHub** (this repo is already on GitHub, so this avoids typing any
   credentials into a separate form).
2. **Add New → Project**, import this repo.
3. On the config screen, set **Root Directory to `web`** — this is the one
   setting that matters. The repo has `backend/` and `web/` side by side, so
   Vercel needs to be told which one is the frontend. Framework Preset should
   auto-detect as Vite once the root directory is set; leave the build
   command (`npm run build`) and output directory (`dist`) on their defaults.
4. Deploy. No environment variables needed — the app takes its backend URL
   and tenant API key at runtime via the Connect screen (`web/src/lib/store.ts`
   persists them in that browser's `localStorage`, never at build time).

## Backend — Railway

1. Sign up at [railway.app](https://railway.app) with GitHub, same reasoning
   as above.
2. **New Project → Deploy from GitHub repo**, select this repo. **No "Root
   Directory" setting needed** — the repo ships a `Dockerfile` and
   `railway.json` at the repo root specifically so Railway finds them
   without depending on that per-service field (which proved unreliable to
   configure through the dashboard: repeated deploys kept ignoring it and
   analyzing the whole repo root via Railpack instead of the intended
   folder). The root `Dockerfile` copies only from `backend/` — see its
   comments, and [`../backend/Dockerfile`](../backend/Dockerfile) for the
   equivalent used for local development.
3. **Add a database**: in the project, **New → Database → Add MongoDB**.
   Railway provisions a Mongo instance and exposes its connection string as
   a variable on that service (commonly `MONGO_URL` — check the Mongo
   service's Variables tab for the exact name it generated).
4. On the **backend service's** Variables tab, set:

   | Variable | Value |
   |---|---|
   | `ADMIN_API_KEY` | a long random string you generate — this is the master key for provisioning tenants, keep it secret |
   | `MONGODB_URI` | reference the Mongo service's connection string (Railway lets you pick another service's variable directly in this UI — search for the Mongo service and select its URL variable rather than retyping it) |
   | `MONGODB_DB_NAME` | `buildx` |
   | `LLM_PROVIDER` | `simulator` to start (no key needed, exercises the full pipeline — see [ARCHITECTURE.md § LLM provider](ARCHITECTURE.md#llm-provider)), or `openai`/`anthropic` with a funded key for real inference |
   | `OPENAI_API_KEY` | only if `LLM_PROVIDER=openai` |
   | `ANTHROPIC_API_KEY` | only if `LLM_PROVIDER=anthropic` |
   | `AUTOPILOT_ENABLED` | `true` |

   Everything else in [`backend/.env.example`](../backend/.env.example) has a
   working default and only needs setting if you want to change it.
5. Deploy. Railway assigns a public URL under **Settings → Networking →
   Generate Domain** if one isn't already there.
6. **Seed a tenant** against the deployed backend so there's something to
   connect to:

   ```bash
   curl -X POST https://<your-railway-domain>/v1/admin/tenants \
     -H "X-Admin-Key: <your ADMIN_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"name": "Your Company"}'
   ```

   The response includes an `api_key` — copy it now, it's shown exactly once.

## Connecting them

Open the Vercel URL, paste the Railway URL as the API base and the seeded
key as the tenant API key on the Connect screen. That's the whole
integration step — nothing to configure on either host's side beyond this.

## Verifying it worked

```bash
curl https://<your-railway-domain>/health
```

`{"status":"ok","database":"up",...}` means Mongo connected. `"degraded"`
with `"database":"down"` means the `MONGODB_URI` variable isn't wired up
correctly yet — check the Mongo service's actual variable name in step 3.
