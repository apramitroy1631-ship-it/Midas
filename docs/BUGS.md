# Bug log

Bugs found and fixed in MIDAS, what each one looked like from the outside, why it
actually happened, and what changed. Newest areas first within each section. This
is a record of *resolved* problems — a short list of things that are still open is
at the bottom so nobody assumes they're handled.

"Where" points at the file(s) that carry the fix today.

---

## LLM providers and the pipeline

### 1. Gemini runs crashed with `'list' object has no attribute 'startswith'`
- **Symptom:** every Gemini-backed run failed at its first structured step.
- **Cause:** the LangChain Gemini wrapper doesn't always return `response.content`
  as a plain string — for some responses it's a list of parts. The provider called
  `.startswith()` on it.
- **Fix:** flatten the content (string or list of text parts) into one string before
  parsing.
- **Where:** `backend/app/services/llm/gemini_provider.py` (`_text_of`).

### 2. One transient API error killed an entire campaign run
- **Symptom:** a single 503 "model is experiencing high demand" ended a run that was
  otherwise fine.
- **Cause:** no retry anywhere — every provider call was a bare `invoke()`.
- **Fix:** a shared retry helper with exponential backoff and jitter, wrapped around
  every provider call (Gemini, OpenAI, Anthropic, Groq, and the shared tool loop).
  It retries only error shapes worth retrying (429/5xx/timeouts) and fails fast on
  the rest.
- **Where:** `backend/app/services/llm/retry.py`.

### 3. Retired Gemini model names returned 404
- **Symptom:** `gemini-1.5-pro`/`flash` → 404 NOT_FOUND; `gemini-2.5-pro` → "no longer
  available to new users".
- **Cause:** model names churn faster than the config was updated.
- **Fix:** moved to Google's `-latest` aliases, chosen by querying the live model
  list and test-calling the candidate rather than guessing. (Later superseded by the
  Groq routing, but the same lesson applied — see #5.)
- **Where:** `backend/app/core/config.py`, `settings.py`.

### 4. Gemini "pro" model always hit its quota on a free key
- **Symptom:** `gemini-pro-latest` returned 429 immediately while flash worked.
- **Cause:** a free-tier key has almost no quota for pro models.
- **Fix:** routed every agent to flash until billing is attached, with a comment
  explaining how to restore the pro/flash split.
- **Where:** `backend/app/core/config.py`.

### 5. Groq's obvious model (`llama-3.3-70b-versatile`) didn't exist
- **Symptom:** first Groq run failed with `model_not_found`.
- **Cause:** Groq had retired it from its catalog since it was last known.
- **Fix:** listed Groq's live `/v1/models` endpoint and picked `openai/gpt-oss-120b`
  (tools + structured output) with `gpt-oss-20b` for SEO/Analytics.
- **Where:** `backend/app/core/config.py`, `backend/app/services/llm/usage.py`.

### 6. A spent Groq daily limit was retried instead of failing fast, with an unreadable error
- **Symptom:** a run with the daily token cap used up (`tokens per day (TPD)`) spent
  time retrying, then showed a raw JSON error dump to the user.
- **Cause:** the "this is a hard daily cap, don't retry" check only matched Gemini's
  wording (`perday`, `per_day`, `daily`); Groq says "tokens per day (TPD)".
- **Fix:** match Groq's wording too, and raise a plain-language `LLMQuotaError`
  ("daily usage limit reached, should free up in about 25m") instead of the raw
  payload. Per-minute limits (TPM) are still retried, as they should be.
- **Where:** `backend/app/services/llm/retry.py`.

### 7. A run failed at the last step with `Invalid JSON: EOF while parsing a list`
- **Symptom:** a blog run got through research, strategy and writing (~160s), then
  failed at SEO.
- **Cause:** the smaller `gpt-oss-20b` model returned JSON with an unclosed bracket,
  and the provider parsed by hand with no repair and no retry, so one stray character
  discarded the whole run.
- **Fix:** ask Groq for JSON mode (the API enforces syntactically valid JSON), validate
  against the schema, and retry once with the validation error fed back to the model.
  Also retries once if Groq itself reports no valid JSON was produced (hidden
  reasoning can consume the whole output budget).
- **Where:** `backend/app/services/llm/groq_provider.py`.

### 8. Simple runs (a LinkedIn post, an email) took 200+ seconds
- **Symptom:** the same multi-minute wait for a one-line email as for a researched blog.
- **Cause:** every run went through the full pipeline, and research/strategy/content
  each ran a tool-calling loop (2+ model calls) even though the tools mostly re-fetched
  brand memory already in the prompt.
- **Fix:** the orchestrator sets `light_mode` when no planned channel needs deep
  research (only `blog` does). Light runs skip the research node and use single-call
  generation in strategy/content. Blog runs are unchanged.
- **Where:** `backend/app/graph/builder.py`, `nodes.py`, `state.py`,
  `backend/app/agents/base.py`.

### 9. Research re-derived the same market facts on every run
- **Symptom:** the slowest step repeated for the same brand each time, and sometimes
  returned a different market size or growth rate than the run before.
- **Cause:** brand memory only stored strategic takeaways; nothing persisted the
  factual research, and Research had no instruction to use memory.
- **Fix:** a `market_facts` block in brand memory (audience, market size, growth,
  competitors, `researched_at`) written by the Learning agent and reused by Research
  while under 30 days old. Age is computed in Python, not by asking the model.
- **Where:** `backend/app/agents/research.py`, `learning.py`, `schemas/agents.py`,
  `schemas/brand.py`, `graph/nodes.py`.

### 10. A stuck run had no way to be cancelled
- **Symptom:** a run hung on a rate-limited call; the UI "Stop run" button did
  nothing server-side.
- **Cause:** "Stop" only aborts the browser's stream; the backend thread keeps going
  and the run record stays `running` forever.
- **Fix (workaround only):** restarted the backend and marked the run failed by hand.
  A real cancel endpoint is still open — see below.

### 10a. LinkedIn posts came out too long, and "regenerate" over- or under-corrected
- **Symptom:** LinkedIn posts ran blog-sized. Regenerating with "make it shorter" collapsed
  the post to almost nothing, and unrelated feedback (tone, a missing detail) also changed
  the length.
- **Cause:** the Content agent had no length guidance at all ("write natively per channel"),
  and a regenerate got the operator's comment plus the old draft with no idea how much to
  change, so the model guessed.
- **Fix:** per-channel word ranges (LinkedIn 60-150, email 80-200, blog 600-1,200) given to
  the model as numbers. A regenerate now gets a target computed in code: length held
  steady (+/-10%) unless the feedback is about length; an explicit number ("under 100
  words") is honoured; "shorter" is a cut of about a quarter to a third, not a collapse;
  "longer" grows by about a third. The prompt also says to change only what the feedback
  asks. The result is checked afterwards and retried once if it ignores the range.
- **Where:** `backend/app/agents/channel_specs.py`, `content.py`,
  `backend/app/services/regenerate.py`.

### 10b. Regenerate flagged a LinkedIn post for a blog's word count, and stopped after one fix
- **Symptom:** after a regenerate the editor said a LinkedIn post was "well below the
  required 800-1000 words", and it stayed flagged.
- **Cause:** the new brand-rule check judged the asset against the whole campaign's success
  criteria, which included the blog's length target. It also allowed only one automatic fix,
  and the fix pass was told to satisfy that criterion while the length rule capped the post
  at 150 words, so the two contradicted each other.
- **Fix:** the review is scoped to the asset's own channel (other channels' targets and
  campaign-wide outcomes such as open rates aren't grounds for a blocking issue, and the
  channel's expected length is stated). The fix step is now the normal qa -> revise -> content
  loop, repeated up to the tenant's revision budget (capped globally), with the operator's
  feedback still applied on every pass. A draft still failing once the budget is spent is saved
  with the issues shown.
- **Where:** `backend/app/services/regenerate.py`, `agents/qa.py`, `agents/content.py`.

---

## Secrets and configuration

### 11. A real API key ended up in tracked files
- **Symptom:** the Gemini key was written into `docker-compose.yml` and
  `backend/.env.example`, both committed to git.
- **Cause:** the key was pasted straight into the config files instead of a
  git-ignored location.
- **Fix:** reverted the template file, switched compose to `${GEMINI_API_KEY}`
  substitution, and moved the real value to a git-ignored root `.env`. Caught before
  anything was pushed.
- **Where:** `docker-compose.yml`, `backend/.env.example`, `.gitignore`.

### 12. "Can't reach the API" on sign-in (local)
- **Symptom:** sign-in failed with "Is the backend running on that address?" while the
  backend was healthy.
- **Cause:** the base URL was `http://127.0.0.1:8000` — the container's internal port.
  Docker maps it to **8100** on the host.
- **Fix:** use `http://127.0.0.1:8100`. No code change; the deploy docs now describe
  the URL setup.

### 13. "Invalid API key" — wrong secret used
- **Symptom:** signing in with a key that "looked right" was rejected.
- **Cause:** the value used was the platform `ADMIN_API_KEY`, not the tenant's
  `bx_live_…` service key. They are different credentials; the tenant key is shown
  once at creation and stored only as a hash.
- **Fix:** documented the difference; use the tenant key to sign in, the admin key only
  to register the first login.

### 14. Users created before roles existed had no `role`
- **Symptom:** no account could open the Team screen, and nobody could be made admin.
- **Cause:** the `role` field was added after those users were created, so it's absent
  from their documents — and only an existing admin can grant it (chicken-and-egg).
- **Fix:** one-time bootstrap by setting `role: "admin"` directly on the first user;
  `POST /v1/auth/register` now always creates the first user as admin.
- **Where:** `backend/app/api/routes_auth.py`, `backend/app/db/users.py`.

---

## Authentication and sessions

### 15. The Team panel never appeared for admins
- **Symptom:** signed in as admin (or with the tenant key), no Team section in
  Settings — even after signing out and back in.
- **Cause:** `store.save()` rebuilds the saved connection field by field, and `role`
  wasn't in that list, so it was silently dropped on every sign-in.
- **Fix:** include `role` when saving.
- **Where:** `web/src/lib/store.ts`.

### 16. "Log out" didn't actually log out
- **Symptom:** removing a connection only cleared the browser; the session token stayed
  valid on the server for up to 30 days.
- **Cause:** `session_repo.revoke()` existed but no endpoint called it.
- **Fix:** `POST /v1/auth/logout` revokes the session (no-op for a raw tenant key), and
  the new top-bar **Log out** button and the Settings disconnect both call it.
- **Where:** `backend/app/api/routes_auth.py`, `web/src/App.tsx`, `web/src/lib/api.ts`.

### 17. Opening the deployed app signed you straight in
- **Symptom:** clicking the Vercel link logged the visitor in with no credentials.
- **Cause:** the session was stored in `localStorage` indefinitely, so anyone on that
  browser inherited it.
- **Fix:** sessions live in `sessionStorage` by default (gone when the tab/browser
  closes); a "Keep me signed in on this device" checkbox opts into the old behaviour.
  Sessions saved by older versions are discarded on the next load.
- **Where:** `web/src/lib/store.ts`, `web/src/views/Connect.tsx`.

### 18. Every sign-in required typing the backend URL
- **Symptom:** people had to paste the Railway URL before they could sign in.
- **Cause:** the field defaulted to the local dev address with no way to preset it.
- **Fix:** read `VITE_API_BASE_URL` at build time; when set, the field is hidden.
- **Where:** `web/src/views/Connect.tsx`, `web/src/vite-env.d.ts`, `web/.env.example`,
  `docs/DEPLOY.md`.

---

## Interface

### 19. Content calendar: clicking a date looked like it did nothing
- **Symptom:** clicking dates in the lower rows seemed to need two clicks or did nothing.
- **Cause:** the popover *was* opening, but the card's `overflow: hidden` (there for its
  top gradient bar) clipped it whenever it rendered below the card's edge.
- **Fix:** let the calendar card overflow.
- **Where:** `web/src/styles.css`, `web/src/components/ContentCalendar.tsx`.

### 20. Calendar popover ran over the metric cards below it
- **Symptom:** for dates near the bottom of the grid, the day's content list covered the
  stats row.
- **Cause:** the popover always opened downward at a fixed, tall size.
- **Fix:** smaller popover; cells in the lower half open it upward so it stays inside the
  card. Hovering a date now shows the same highlight as a selected one.
- **Where:** `web/src/components/ContentCalendar.tsx`, `web/src/styles.css`.

### 21. Rich Text canvas was unreadable in dark mode
- **Symptom:** the email preview's headline and body were nearly invisible.
- **Cause:** the HTML carries inline styles for a white email background (near-black
  text) but was rendered on the app's dark surface.
- **Fix:** the canvas is always a white "paper" surface, matching what recipients see.
- **Where:** `web/src/styles.css` (`.rich-editor`).

### 22. Clicking the sidebar collapse button shifted the rest of the screen
- **Symptom:** layout dimensions changed depending on whether the sidebar or its collapse
  button was clicked; the peek-on-hover overlay could also get stuck open.
- **Cause:** the collapse/peek/idle-timer behaviour was complex, and an `!important`
  width override stopped the CSS transition from animating back.
- **Fix:** removed collapse, peek and the idle timer entirely; the sidebar is fixed.
- **Where:** `web/src/App.tsx`, `web/src/styles.css`.

### 22a. One long blog filled the whole Content Library
- **Symptom:** a card's full body was printed, so a long blog dwarfed every other card, and
  bulleted LinkedIn copy ran together into one paragraph.
- **Cause:** the card body had no height cap and collapsed line breaks.
- **Fix:** cards are a 7-line preview (clicking opens the full text) and keep line breaks.
- **Where:** `web/src/styles.css` (`.asset-body`).

### 22b. Regenerate looked frozen for 30-60+ seconds
- **Symptom:** clicking Regenerate only changed the button label, with no sign of progress.
- **Cause:** a single request with no feedback while the server writes, reviews and revises.
- **Fix:** a progress panel (easing bar, estimated stages, elapsed time), a shimmer over the
  content being rewritten, and a highlight when the new version lands. Stages are labelled as
  estimates because the server doesn't report them; motion respects reduced-motion settings.
- **Where:** `web/src/components/RegenProgress.tsx`, `AssetEditor.tsx`, `web/src/styles.css`.

---

## Still open

- **No cancel for a running campaign.** "Stop run" only stops the browser's stream; the
  server keeps working. Needs a cancellation flag the graph checks between steps.
- **Duplicate tenants in the production database.** Three "CMART Solutions Pvt Ltd"
  tenant documents were created minutes apart; a login points at the first, but the one
  with real usage is the third.
- **The shared Groq daily token cap (200,000 tokens/day per model)** is a provider limit,
  not a bug — it needs a paid tier or a fallback provider. Runs now fail cleanly with a
  readable message when it's hit.
