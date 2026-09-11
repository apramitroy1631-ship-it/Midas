# Console

Vite + React. No router — the app is a single always-mounted shell (`App.tsx`) that
swaps which view renders based on local state, since every view shares one live
tenant connection and switching tenants needs to reset all of them together.

## Layout

```
src/
  lib/
    types.ts      shared TypeScript types, mirroring the backend's Pydantic schemas
    api.ts         typed fetch wrappers + the SSE stream reader for /v1/runs/stream
    store.ts       tenant connections (API keys), kept in localStorage only —
                   never sent anywhere but the API this browser is pointed at
  components/
    ui.tsx          primitives: Card, Badge, Field, Drawer, etc.
    AgentRail.tsx   the live agent-pipeline view — one node per graph step,
                    with a node-specific detail renderer for each agent's output
  views/          one file per screen: Overview, Launch, Runs, Library, Brands,
                  Audit, Settings, Connect
  App.tsx         shell: sidebar nav, tenant switcher, view routing
```

`views/` rather than `pages/`: there is no URL-based routing here (a page reload
always lands on Overview), so "page" would overstate what these are — each is a
view the shell swaps in, not a route.

## Running

```bash
npm install
npm run dev       # http://localhost:5175
```

Points at whichever backend URL and tenant API key you enter on first run (stored
per-browser, see `lib/store.ts`) — no build-time configuration needed.

```bash
npm run build      # type-checks (tsc -b) then produces dist/
```
