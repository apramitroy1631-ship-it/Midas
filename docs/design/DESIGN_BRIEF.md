# MIDAS — Design Brief

Written for whoever picks up the design or product work next — not an engineer, and
not someone who was in the room when this was built. If you're about to redesign a
screen, start here: what it's *for* determines what "better" even means for it.

## What MIDAS actually is

**M**arketing **I**ntelligence & **D**ecision **A**utomation **S**ystem.

It's a system that runs marketing campaigns for CMART Solutions **without a person
approving each step**. Not "drafts content for a human to review" — it researches,
strategizes, writes, checks its own work, and publishes, and the only human
involvement is deciding the policy it operates under (how much autonomy it gets, what
it's never allowed to claim) ahead of time.

The console is the window into that system: not a tool you *use* to make content, but
a place you go to see what an autonomous system has been doing, occasionally point it
at a new goal, and adjust the rules it operates within.

**This matters for design because most dashboards are built around a person doing the
work.** This one is built around a person supervising work that already happened, or
is happening right now, without them. That's a different job: less "help me create
something," more "help me trust and understand what already got created."

## Who's using it

One person (or a small team) at CMART, checking in on a system that runs mostly by
itself. Not a large org with dozens of accounts and roles — a single company watching
its own autonomous marketing operation. That's why there's no multi-tenant switcher in
the UI: there's one thing to watch, not several.

## The core idea each screen has to communicate

Every screen exists to answer one of these questions. If a redesign doesn't make the
relevant question *easier* to answer, it's not actually an improvement, regardless of
how it looks.

| Screen | The question it answers |
|---|---|
| **Dashboard** | "Is everything okay, and what's it been doing?" — the one-glance status check. Numbers here should read as *outcomes* (assets published, quality scores), not internal system metrics. |
| **New Campaign** | "What do I want it to go do?" — and critically, you can leave the goal blank and it picks one itself. The screen has to make that feel intentional, not like a missing required field. |
| **Campaign History** | "What has it actually done, in detail?" — the full trace of every agent's reasoning on every past run. This is where trust gets built or lost: if someone doubts an output, this is where they come to check the work. |
| **Content Library** | "What's actually live right now?" — the finished product. This should feel like a portfolio of real, publishable work, not a database table. |
| **Decision Log** | "Why did it do what it did, and can I prove that later?" — the accountability trail. This screen exists *because* no human signs off — it's the thing that stands in for that sign-off. |
| **Brands** | "What is it not allowed to say, and what does it know about our voice?" — the boundaries and the accumulated memory. Content restrictions here are absolute; everything else is guidance. |
| **Settings** | "How much rope does it have?" — autonomy level, revision budget, guardrails. The one screen that changes *behavior*, not just displays it. |

## The idea that has to survive any redesign: the self-correction loop

The single most important thing happening in this product is invisible unless you
design for it: **when the system's own quality check finds a problem, it doesn't stop
and wait for a person — it sends the specific issue back to whichever agent can fix
it, and tries again.** A revision cycle is not an error state. It's the system doing
exactly what it's supposed to do in place of a human editor.

Whatever a screen looks like, if it shows a campaign run, it needs to make a revision
cycle *legible as a success*, not something that looks like a failure that happened to
get papered over. This is the one place a "better-looking" redesign can accidentally
make the product worse — by making revision cycles look like errors instead of the
autonomy actually working.

## Design constraints that came from real decisions, not taste

- **No tenant switcher.** MIDAS is architected multi-tenant underneath (real data
  isolation, enforced at the database layer — see `docs/ARCHITECTURE.md`), but this
  deployment runs for one company. Don't add multi-account UI back in without a real
  reason; it was removed deliberately, not because it was hard to build.
- **Status is always color *and* text.** A colored dot alone is not an accessible or
  screenshot-safe way to convey "published" vs "blocked" vs "revising." Every status
  indicator pairs a color with a word.
- **Numbers that are machine-generated (IDs, timestamps, scores) are visually distinct
  from prose a person or the agents wrote** — currently done with a monospace
  typeface. Whatever mechanism you use, keep that distinction; it's what lets someone
  scan a screen and separate "data" from "writing" without reading either closely.
- **Every autonomous decision gets logged with a reason.** If a new screen produces an
  outcome (published, dropped, changed), it needs an entry in the Decision Log audit
  trail — that's the thing that makes "no human review" defensible rather than
  reckless.

## Where the actual reference material lives

- **`docs/design/concept/console-concept.html`** — a from-scratch visual concept
  (published as a standalone page) exploring a cleaner, more minimal direction for
  this console. Not the shipped product's design — a proposal.
- **`docs/design/BuildX-UIUX-Demo-Design.pdf`** — a walkthrough deck of the *shipped*
  console as it existed at an earlier point, screen by screen, with the reasoning
  behind each one. Useful for understanding intent even where the visual style has
  since moved on.
- **`web/src/styles.css`** — the actual, current design tokens (color, type, spacing)
  the shipped console runs on right now. This is ground truth for what's live; the
  concept file and the PDF are both proposals/history, not the current state.
- **`docs/ARCHITECTURE.md`** — for when "why does it work this way" needs a real
  technical answer rather than a product one.
