# MIDAS — Testing Guide

For QA. What to actually click through, what "correct" looks like at each
step, and the specific things that have broken before and are worth
re-checking. This isn't a generic app-testing checklist — every scenario
here is something this product does that most apps don't.

## 00 — Setup

You need a running backend + a console pointed at it. Ask whoever set up
your environment for:

| | |
|---|---|
| API base URL | e.g. `http://127.0.0.1:8100` (local) or a Railway URL (shared) |
| Login | Either an email + password, or a fallback tenant API key (`bx_live_…`) |

If `LLM_PROVIDER` is set to `simulator` (ask — it usually is for testing),
campaign runs cost nothing and finish in a few seconds with realistic,
schema-correct content. That's the normal way to test — you don't need a
real OpenAI/Gemini key to exercise the whole product.

## 01 — Sign-in

- [ ] **Email + password, correct credentials** → lands on the Dashboard
- [ ] **Email + password, wrong password** → "Invalid email or password" —
      not a stack trace, not a blank screen
- [ ] **"Have a tenant API key instead?" toggle** → switches the form; a
      valid key signs in the same as email/password would
- [ ] **Wrong base URL / backend not running** → "Can't reach the API. Is
      the backend running on that address?" — a plain-language error, not a
      raw fetch failure
- [ ] **Refresh the page after signing in** → stays signed in (session
      persists in this browser)

## 02 — Dashboard & content calendar

- [ ] **Greeting text** → changes with time of day (morning/afternoon/
      evening); clicking the italic tagline swaps it to a different one
- [ ] **Click a past day with no content** → "Nothing was published on this
      day." — no "publish content" button
- [ ] **Click today or a future day with no content** → "Nothing here yet"
      + a button that opens New Campaign
- [ ] **Click a day that already has content** → lists each piece with a
      status badge and channel icon; if the day is today/future, a "+
      Publish new content" option also appears below the list
- [ ] **Click one item in that list** → opens the content editor directly
      for that piece
- [ ] **Hover any day with content** → a visible lift + glow — should feel
      clickable before you click it
- [ ] **‹ › month navigation** → moves a full month; today's highlight
      only shows in the real current month

## 03 — New Campaign

This is the core feature — take extra time here.

- [ ] **Leave "Campaign goal" blank, launch with "All channels"** → the
      Director picks its own goal (shows as "self" origin) and 2–4
      channels; the agent pipeline runs step by step on the right
- [ ] **Select only one specific channel (e.g. Blog)** → the finished run
      produces exactly one asset, on that channel — check the Outcome
      card's asset count and the actual Content Library entry
- [ ] **Select two channels** → exactly those two, no more, no fewer
- [ ] **Select only Mail** → button changes to "✉ Generate email now"; on
      completion you're taken straight to Content Library with that email
      already open in the editor — you should never see the plain Outcome
      summary screen for this path
- [ ] **Stop a run mid-flight** → the ■ Stop button halts it cleanly, no
      crash
- [ ] **A run that needs a revision cycle** → shows up in the agent
      pipeline as a distinct step, styled as a normal part of the process —
      not as an error or a red banner (see note below)

> **Why the revision-cycle look matters:** QA sending content back for a
> fix is the system working as designed, not something going wrong. If a
> revision cycle ever visually reads like a crash or a failure state,
> that's a real bug worth flagging — it undermines the whole "no human in
> the loop" premise if a normal self-correction looks alarming.

## 04 — Content editor (the "canvas")

- [ ] **Open any email asset** → three tabs: HTML, Rich Text, Plain Text
- [ ] **Open a LinkedIn or Blog asset** → only two tabs — HTML and Rich
      Text. No Plain Text tab for these.
- [ ] **Edit text in any tab, then click Save** → drawer closes, no error;
      reopen the same asset — your edit is still there
- [ ] **Edit text, then click the X (not Save)** → a confirmation prompt
      asking to discard changes — appears every time, not just sometimes
- [ ] **Edit text, click outside the drawer** → same confirmation prompt
- [ ] **Edit text, press Escape** → same confirmation prompt
- [ ] **Confirm "discard"** → closes without saving; reopening shows the
      original, unedited content
- [ ] **Open an asset, make no edits, close it** → closes immediately — no
      confirmation prompt for an untouched asset
- [ ] **Rich Text tab's Bold/Italic/Underline/List buttons** → visibly
      format the selected text
- [ ] **Each tab's Download button** → a file actually downloads (`.html`
      / `.rtf` / `.txt`) and opens in a real app (try the .html one in a
      browser, the .rtf one in Word/Outlook)

## 05 — Content Library filters

- [ ] **Type a word from a real headline into Search** → count updates
      live, only matching cards remain
- [ ] **Brand filter + Channel filter together** → both apply at once
      (AND, not OR) — narrower, not wider, results
- [ ] **Date "From" / "To"** → only content created in that range; setting
      just one side works as an open-ended bound
- [ ] **"Clear filters"** → only appears once a filter is active; resets
      everything back to the full list
- [ ] **Filter down to zero results** → "Nothing matches" message, not a
      blank page

Campaign History has the same search + brand + date filtering — worth the
same pass.

## 06 — Brands

- [ ] **Add a brand with only the Name field filled** → saves — everything
      else is genuinely optional
- [ ] **Scroll the "New brand" form on a normal-height window** → every
      field is reachable, Save/Cancel don't feel cramped at the bottom
- [ ] **Add a Content restriction, then run a campaign that would
      plausibly violate it** → worth watching whether QA actually catches
      it — this is the one rule the system treats as absolute
- [ ] **Delete a brand with existing runs/assets** → confirmation prompt
      names the brand; after deleting, its old runs/assets still show in
      History/Library (nothing gets silently deleted with it)

## 07 — Settings

- [ ] **Toggle "Run fully autonomously" off** → a subsequent run's
      finished content should land as "pending review" rather than
      "published" — check its status in the Library
- [ ] **Revision budget field** → accepts 0–5; a run that never clears QA
      within that many cycles should hit arbitration, not loop forever
- [ ] **Isolation card (bottom)** → shows the tenant name, id, and key
      prefix — read-only, matches what's actually connected

## 08 — Theme & layout

- [ ] **Sun/moon toggle (top right)** → switches dark ↔ light instantly,
      persists across a refresh
- [ ] **Sidebar "Collapse"** → shrinks to icon-only; hovering an icon
      still shows its label as a tooltip; persists across a refresh
- [ ] **Resize the browser narrow (phone width)** → nothing overlaps or
      gets cut off; cards stack instead of overflowing sideways
- [ ] **A wide/tall monitor (1920×1080 or bigger)** → any drawer (Brands,
      content editor) still covers the full screen height — see the note
      below

> **Specifically re-test this one:** a real bug existed where, at certain
> screen sizes, the Brands/editor drawer only covered part of the screen
> and got visually cut off at the bottom. It's fixed, but it was subtle
> (only showed at larger viewports) — if a drawer ever looks short or
> leaves dead space beside it again, that's this bug back.

## 09 — Known limitations — not bugs, don't file these

- The content editor's "Save" rebuilds headline/body/CTA from whichever
  tab you last touched, split by paragraph breaks. An unusual paragraph
  structure (e.g. one giant single paragraph) may save differently than
  you'd expect — this is a documented limitation, not a crash.
- Rich Text formatting (bold/italic) doesn't carry into the downloaded
  `.rtf` file yet — the download is plain-text-backed. Report if the file
  fails to open at all; don't report missing bold.
- The simulator provider's copy is templated, not creative — don't judge
  writing quality against it. Switch `LLM_PROVIDER` to a real provider to
  test actual generation quality.
- A single-page phone-width layout hasn't had a dedicated design pass
  beyond "doesn't break" — functional, not polished, below ~400px.

---

See also: [Data Schemas](SCHEMAS.md) · [Backend Architecture](BACKEND_GUIDE.md) ·
[Frontend Guide](FRONTEND_GUIDE.md)
