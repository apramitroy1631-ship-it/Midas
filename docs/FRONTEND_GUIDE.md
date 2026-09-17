# MIDAS — Frontend Guide

For the frontend engineer. The stack, the state model, the design tokens,
and where each piece actually lives. Written so you can find the right
file on the first try, not so you read it top to bottom.

## Stack

| | |
|---|---|
| Build | Vite 5 + TypeScript, strict mode. No CRA, no Next — `npm run dev` / `npm run build`. |
| UI | React 18, function components + hooks only. No class components anywhere. |
| Routing | **None.** One component (`App.tsx`) is always mounted; it swaps which view renders via a plain `useState<View>`, not a router. See [State model](#state-model). |
| Styling | One hand-written `styles.css`, CSS custom properties for theming. No Tailwind, no CSS-in-JS, no component library. |
| Icons | `lucide-react`. LinkedIn has no lucide icon (dropped for licensing) — `components/ChannelIcon.tsx` hand-draws that one glyph. |
| Data fetching | Plain `fetch`, wrapped in `lib/api.ts`. No React Query / SWR — state lives in `App.tsx` and flows down as props. |
| Streaming | Server-Sent Events, hand-parsed in `lib/api.ts`'s `streamRun()` — `EventSource` can't POST, so this is a manual `fetch` + `ReadableStream` reader. |

## File structure

```
web/src/
  App.tsx                the whole app shell — sidebar, topbar, view switch, all top-level state
  main.tsx               ReactDOM.render, nothing else
  styles.css              every class in the app, one file, organised by section comments
  lib/
    api.ts                request() wrapper + streamRun() + the `api` object (one method per endpoint)
    store.ts              localStorage — saved connections, active tenant, theme, sidebar-collapsed
    types.ts              every TS interface, hand-kept in sync with the backend's Pydantic schemas
    download.ts           client-side file download + HTML/RTF generation helpers
  views/                 one file per sidebar destination — Overview, Launch, Runs, Library, Brands, Settings, Audit, Connect
  components/
    ui.tsx                the shared primitive kit — Card, Stat, Badge, Field, Drawer, Toggle, etc.
    ContentCalendar.tsx    month-grid calendar on the Dashboard
    AssetEditor.tsx        the content "canvas" — HTML/Rich Text/Plain Text, Save, unsaved-changes guard
    ChannelIcon.tsx        channel → icon mapping
    AgentRail.tsx          the live agent-pipeline visualisation during a run
```

## State model

`App.tsx` is the single source of truth. It holds `conn`, `tenant`,
`brands`, `runs`, `assets`, `stats`, `audit`, and view-navigation state
(which screen, which run/asset is open), and passes them down as plain
props — there's no Context, no Redux, no Zustand. A view that changes
something calls a callback prop (usually named `onSaved` / `onChanged` /
`onFinished`) which triggers `App.tsx`'s `refresh()`, which re-fetches
everything from the API in parallel.

```ts
const refresh = useCallback(async () => {
  const [t, b, r, a, au, s, ap] = await Promise.all([
    api.me(conn), api.brands(conn), api.runs(conn),
    api.assets(conn), api.audit(conn), api.stats(conn), api.autopilot(conn),
  ]);
  // ...setTenant(t), setBrands(b), etc.
}, [conn]);
```

**Cross-view navigation** (e.g. New Campaign's "only Mail" flow jumping to
Content Library with a specific asset already open) works the same way as
everything else — no router, no query params. `App.tsx` holds
`openAssetId`; `Launch.tsx` calls `onOpenAsset(id)`, which sets that state
*and* switches `view` to `"library"` in one callback. `Library.tsx` just
reads `openAssetId` as a prop and renders the editor if it matches an
asset it has.

## Connection & auth

A `Connection` (`lib/types.ts`) is
`{id, label, apiKey, baseUrl, color, userEmail?}`, persisted in
`localStorage` via `lib/store.ts` — never sent anywhere but the API base
URL itself. There are two ways it gets populated in `views/Connect.tsx`:

- **Email/password** → `POST /v1/auth/login` → the response's
  `session_token` becomes `apiKey`, and `email` is saved as `userEmail`
  (used for the Dashboard's greeting).
- **Raw tenant key** (fallback toggle) → verified via `api.me()` before
  saving.

Either way, the app never needs to know which kind it has — `api.ts`
always sends it as the same `X-API-Key` header; the backend tells the two
apart by prefix (`bx_live_` vs `sess_`).

## Talking to the API

Everything goes through `lib/api.ts`'s `request<T>(conn, path, init)` — it
sets the auth header and throws a typed `ApiError` (carrying the HTTP
status) on a non-2xx response, with the backend's own `detail` message
where available. Add a new endpoint by adding one line to the exported
`api` object, not by calling `fetch` directly in a view.

```ts
updateAsset: (c: Connection, id: string, body: unknown) =>
  request<Asset>(c, `/v1/assets/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
```

The one exception is `streamRun()`, exported separately — SSE needs the
raw `fetch` + stream reader, not the JSON-in-JSON-out shape `request()`
assumes.

## Design tokens

Every color is a CSS custom property in `:root` (dark, the default) and
re-declared under `[data-theme="light"]` — **never** hardcode a hex value
in a component; reach for the token. Dark mode is MIDAS's own crimson/gold
brand identity; light mode is a deliberately different, calmer royal-blue
register — the two are not simple inversions of each other.

| Token | Meaning |
|---|---|
| `--bg` / `--surface` / `--surface-2` / `--surface-3` | Page background → card → hover/input → deepest nesting. |
| `--text` / `--text-muted` / `--text-dim` | Primary / secondary / tertiary text, in that order of decreasing contrast. |
| `--accent` / `--accent-2` | Brand pair. `--accent` is the primary-action color (buttons, active states); `--accent-2` is the secondary flourish (the calendar's "today" ring, the gold shimmer on the wordmark). |
| `--ok` / `--warn` / `--danger` / `--info` | **Semantic**, not brand — these never change meaning by theme. Used for status badges, banners, form validation. |
| `--radius` / `--radius-sm` / `--shadow` | Shared corner radii and elevation shadow, so nothing free-hands its own. |

Two font families, both Google Fonts: `--display` is Bricolage Grotesque
(headings, card titles, the wordmark), `--sans` is Inter (everything
else), `--mono` is the system mono stack (IDs, timestamps, code, anything
machine-generated — this distinction is deliberate, see
`docs/design/DESIGN_BRIEF.md`).

## Shared components (`components/ui.tsx`)

| Component | Notes |
|---|---|
| `Card` | `{title?, sub?, action?, children}` — the one container every panel uses. Has a built-in hover lift + top accent-line reveal. |
| `Stat` | Dashboard tile — `{label, value, hint?, tone?, icon?}`. |
| `Badge` / `StatusBadge` | `Badge` is generic (`tone: ok\|warn\|danger\|info\|muted`); `StatusBadge` maps a run/asset `status` string to the right tone + label automatically — always prefer it over a raw `Badge` for a status. |
| `Field` | Label + hint wrapper for a form control — every input in the app sits inside one. |
| `Drawer` | The right-side slide-over (Brands edit, run detail, content editor). Closes on its own X button, a backdrop click, *and* Escape — all three call the same `onClose` prop, so a component that needs to intercept closing (e.g. AssetEditor's unsaved-changes confirm) only has to wrap that one prop. |
| `Empty` | Icon + title + text + optional action — the empty-state pattern, used instead of a bare "no data" string anywhere a list can be empty. |

Formatting helpers, same file: `timeAgo(iso)`, `duration(ms)`,
`initials(name)` — small, pure, no dependencies. Use these instead of
re-deriving relative time or duration formatting in a view.

## Patterns worth copying

**Unsaved-changes confirm** (`AssetEditor.tsx`) — a local `dirty` boolean,
flipped `true` on every edit handler. One `requestClose()` function checks
it and either confirms or calls the real `onClose`; that function — not
the raw `onClose` — is what gets passed to `<Drawer>`. A footer button
whose label already states the intent ("Discard & close") calls `onClose`
directly, skipping the redundant second confirm.

**Client-side search/filter** (`Library.tsx`, `Runs.tsx`) — no backend
query params for search/date-range — the full `assets`/`runs` array is
already in memory from `refresh()`, so filtering is a plain `useMemo` over
it. Fine at this data scale; revisit if either list needs server-side
pagination later.

**Theme-aware inline styles** — where a component needs a color in a
`style={{}}` prop (can't be done in CSS alone — e.g. a dynamically-toned
Stat), it still pulls from `var(--token)` as a string, never a literal
hex, so it stays correct across both themes.

## Adding a new sidebar view

1. New file in `views/`, exporting a function component.
2. Add its id to the `View` union type and the `NAV` array (icon, label,
   sub-label, group) at the top of `App.tsx`.
3. Add its title to the `TITLES` record.
4. Render it in the big conditional block near the bottom of `App.tsx`'s
   JSX, inside the `.view-enter` wrapper (this is what gives every view
   its fade-in — **don't** add a `transform` to that wrapper or any
   ancestor of a `Drawer`: it silently breaks the drawer's
   `position: fixed` sizing. This bit us once — see the Testing Guide's
   "re-test this" note.)

---

See also: [Data Schemas](SCHEMAS.md) · [Backend Architecture](BACKEND_GUIDE.md) ·
[Testing Guide](TESTING_GUIDE.md)
