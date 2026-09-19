# Deploying MIDAS

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
4. **Recommended:** under Project Settings → Environment Variables, add
   `VITE_API_BASE_URL` = your Railway URL (e.g.
   `https://midas-production-5000.up.railway.app`), then redeploy — Vite bakes
   it in at build time. With it set, the Connect screen no longer asks anyone
   for the API base URL; they just sign in. Leave it unset and the screen
   shows a base-URL field instead (defaulting to `http://127.0.0.1:8100`).
5. Deploy. Credentials are never baked in: sign-in happens at runtime and
   lasts for the tab/browser session by default (`sessionStorage`), or across
   visits if the user ticks "Keep me signed in" (`localStorage`) — see
   `web/src/lib/store.ts`.

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
   | `LLM_PROVIDER` | `simulator` to start (no key needed, exercises the full pipeline — see [ARCHITECTURE.md § LLM provider](ARCHITECTURE.md#llm-provider)); any other value (e.g. `gemini`) switches every agent to whatever `AGENT_MODEL_MAP` (`backend/app/core/config.py`) routes it to, currently Gemini |
   | `GEMINI_API_KEY` | a free-tier key from [aistudio.google.com](https://aistudio.google.com) — needed once `LLM_PROVIDER` is not `simulator`, since every agent is routed to Gemini |
   | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | only needed if you edit `AGENT_MODEL_MAP` back to one of those providers |
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

Open the Vercel URL and sign in with an email/password (or the seeded
tenant API key). If `VITE_API_BASE_URL` is set on Vercel there's no base URL to
paste; otherwise paste the Railway URL into the API base field first.

## Verifying it worked

```bash
curl https://<your-railway-domain>/health
```

`{"status":"ok","database":"up",...}` means Mongo connected. `"degraded"`
with `"database":"down"` means the `MONGODB_URI` variable isn't wired up
correctly yet — check the Mongo service's actual variable name in step 3.
