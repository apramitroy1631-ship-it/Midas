# Pipeline Bench — deploy guide

Three folders, three deploys. Do them in this order (dashboard needs the backend URLs).

## 1. `kartik-repo/` → Railway

Modified from the original: added `app/api/routes_stream.py` (SSE endpoint,
`POST /brands/{brand_id}/campaigns/stream`) and registered it in `app/main.py`.
Nothing else changed — the original blocking endpoints still work.

```
cd kartik-repo
railway login
railway init
railway add --database mongo      # or attach MongoDB Atlas instead — either works
railway up
```

Then in the Railway dashboard, set these env vars on the service (from `.env.example`):
```
OPENAI_API_KEY=...           # or ANTHROPIC_API_KEY
MONGODB_URI=...              # auto-filled if you used `railway add --database mongo`
TAVILY_API_KEY=...
SERPER_API_KEY=...
```
Railway gives you a public URL like `https://kartik-backend-production.up.railway.app` —
that's what goes in the dashboard's "Backend URL" field on the Kartik tab.

Sanity check once deployed: `curl https://<your-url>/health` → `{"status":"ok"}`.

## 2. `shivay-repo/` → Railway

Modified from the original: added `src/server.ts` (Express + SSE endpoint,
`POST /campaign/stream`), and `server`/deps in `package.json`. The original
`npm start` CLI script (`src/index.ts`) is untouched.

```
cd shivay-repo
railway login
railway init
railway up
```

Set the start command in Railway's service settings to:
```
npm run server
```
Env vars (from `.env.example` / README):
```
LLM_PROVIDER=openai      # or groq — gpt4free default is not reliable enough to demo on
OPENAI_API_KEY=...
PORT=8080                # Railway sets this automatically, safe to leave unset
```
Sanity check: `curl https://<your-url>/health` → `{"status":"ok"}`.

## 3. `agent-dashboard/` → Vercel

Plain Vite + React + TS app, zero server-side code — Vercel auto-detects it.

```
cd agent-dashboard
npm install
vercel login
vercel --prod
```

Open the deployed URL, paste both Railway URLs into the "Backend URL" field
(switch tabs to set each one), fill in the campaign brief on the left, hit
**RUN CAMPAIGN**, and watch the timeline fill in live as each agent finishes.

### If SSE gets buffered/stalls in production
Some proxies buffer streaming responses. If the timeline doesn't update live:
- Kartik (FastAPI): confirm `sse-starlette` responses aren't behind a proxy
  that buffers (Railway doesn't, by default — a corporate VPN in front might).
- Shivay (Express): same — check nothing sits between Railway and the browser
  stripping `Cache-Control: no-cache` / `Connection: keep-alive` headers.

## What's genuinely new vs. the two forked repos

| File | Repo | What it adds |
|---|---|---|
| `app/api/routes_stream.py` | kartik-repo | SSE endpoint using `graph.stream()` instead of `.invoke()` |
| `src/server.ts` | shivay-repo | Express server + SSE endpoint wrapping the CLI-only `masterGraph` |
| `agent-dashboard/` | new | Whole testing UI — tab switcher, live pipeline rail, JSON output viewer |

Everything else in both repos is unmodified — safe to `git pull` upstream changes later without conflicts in the agent/graph logic itself.
