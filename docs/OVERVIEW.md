# MIDAS — Product Overview

A general-purpose primer on what this system is, who it's for, and what it can
actually do today. If you need "why does the code work this way," see
[ARCHITECTURE.md](ARCHITECTURE.md). If you're redesigning a screen, see
[design/DESIGN_BRIEF.md](design/DESIGN_BRIEF.md). This doc is the one to hand
someone who's never seen the product before and needs the whole picture in one
read.

## The one-line version

MIDAS is a marketing team that runs itself: it plans campaigns, researches the
market, writes the content, checks its own work, and publishes — for a real
company (CMART Solutions), with no person approving any individual step.

## What problem this actually solves

Most "AI marketing tools" produce a draft and hand it to a person to review,
edit, and publish. That's still a human bottleneck — someone has to be
available, has to review every output, and the system never gets faster than
that person's attention allows.

MIDAS is built the other way around. A human sets the **policy** once (how
autonomous it's allowed to be, what it can never claim, how many times it's
allowed to revise its own work) — and after that, campaigns run end to end
without anyone in the loop. The question the product answers isn't "help me
write this post," it's "run the marketing operation and show me what
happened."

## Who it's for

One company (or a small team inside one), watching a system that runs mostly
by itself. This specific deployment operates for CMART Solutions Pvt Ltd, an
ETRM/CTRM energy-trading consultancy — but the system underneath is
architected multi-tenant (real data isolation enforced at the database layer,
not just by convention), so standing up a second company on the same codebase
is a supported path, not a rewrite.

There's no "many accounts, many roles, many dashboards" complexity here by
design. It's one operation, with a small set of people who can sign in, some
of whom can also manage who else is allowed to.

## How a campaign actually happens

A run passes through up to eleven steps, executed by seven specialist agents,
coordinated by one manager:

```
orchestrate → research → strategy → content → seo → qa
                              ↑                       │
                           revise ←──── critical issues, budget remaining
                                                      │
                              clean ──────────────────┴──→ publish → analytics → learn
                                                      │
                budget spent, issues open ────────────┴──→ arbitrate → publish │ abandon
```

- **Orchestrate** — the Campaign Director. If you give it a goal, it sharpens
  it; if you don't, it reads brand memory (what's worked, what's exhausted,
  what's never been tried) and picks one itself. It also decides which
  channels to target and what the research agent needs to answer.
- **Research** — grounds the plan in real numbers: audience profile, market
  size, growth rate, competitors. Checks brand memory first and reuses
  recently-confirmed facts instead of re-deriving the same analysis from
  scratch every run (facts are considered fresh for 30 days).
- **Strategy** — turns research into a concrete plan: objectives, tactics,
  budget allocation per channel.
- **Content** — writes the actual copy, natively per channel (a LinkedIn post
  and an email are different pieces of writing, not the same words resized).
- **SEO** — keywords, meta tags, slugs, distribution notes per asset.
- **QA** — the gate that replaces a human reviewer. Scores brand safety and
  goal alignment, flags critical vs. advisory issues, and decides pass/fail.
- **Revise** (when needed) — QA's specific issues go back to Content as a
  revision brief, which fixes exactly what was flagged and nothing else. This
  loop is the core of the whole system: **a revision cycle is not an error,
  it's the autonomy working as intended** — the thing that replaces a human
  editor's back-and-forth.
- **Arbitrate** (when the revision budget runs out) — assets that individually
  cleared QA still ship; the rest are dropped and the reason is logged. A run
  always ends in a recorded outcome, never in limbo.
- **Publish** — writes to the content library (or a review queue, if the
  tenant's policy requires human sign-off instead of full autonomy).
- **Analytics** — a performance forecast for what just shipped.
- **Learn** — the compounding step. Writes insights, winning angles, exhausted
  angles, and confirmed market facts back into brand memory, so the *next*
  run is planned against what this one learned, not from zero.

**Channel-aware depth:** a short-form run (LinkedIn, email) skips the research
step and the tool-calling overhead in strategy/content entirely — brand memory
already in context stands in for research on something that doesn't need deep
grounding. A run that includes a blog channel gets the full pipeline. This is
what keeps a simple campaign from taking as long as a researched one.

## What you can actually do with it today

**Dashboard** — the one-glance status check: campaign runs, assets published,
self-directed vs. operator-directed runs, quality scores, and a content
calendar showing what's live and what's scheduled, day by day.

**New Campaign** — three ways to start a run:
- Fill in a brief (goal, audience, channels, budget) and launch it.
- **On-demand content** — a floating modal where you just write a prompt;
  channel is auto-detected from what you wrote (mentions LinkedIn/post →
  LinkedIn, mail/letter/email → email, both or neither → all three) and the
  pipeline runs straight from that.
- **Scheduled** — instead of running now, set a date range and which weekdays
  within it the campaign should fire. It sits idle and only runs on a day you
  actually picked; nothing executes outside an explicit on-demand click or a
  schedule you set.

**Campaign History** — the full trace of every run, filterable by trigger and
status: every agent's reasoning, every revision cycle, every score, replayable
in detail. This is where trust gets built or checked — if an output looks
wrong, this is where you go to see exactly why the system produced it.

**Content Library** — everything actually published, filterable by channel,
brand, and date, with multi-select bulk delete for clearing test content.
Each asset can be edited directly (HTML / rich text / plain text, exportable
for Outlook), and if you're not happy with a result, **"Not happy with this?
Tell us what's wrong"** takes your feedback and regenerates just that one
asset — reusing the campaign's existing research and strategy instead of
re-running the whole pipeline, so a targeted fix takes a fraction of the time
a new run would. The rewrite is sized in code (so "shorter" means a real but
not total cut, and unrelated feedback doesn't change the length), remembers
earlier feedback on that asset, and then goes through the same review loop as
a normal run: it's checked against the brand's rules and, if the review finds a
blocking issue, revised and re-checked up to the tenant's revision budget. The
review only judges that one channel's asset, so another channel's targets can't
fail it. A live progress panel shows the stages while it works.

**Decision Log** — the accountability trail: every autonomous decision
(published, dropped, partially published, abandoned), why, filterable by
origin, trigger, and actor. This exists specifically *because* no human signs
off on anything — it's what stands in for that sign-off.

**Brands** — voice, USP, target audience, hard content restrictions (absolute
— the system won't write around the edge of one), and the accumulated memory
a brand carries between runs.

**Settings** —
- **Autonomy & guardrails**: how much the system decides on its own, whether
  it publishes automatically or parks output for review, the revision budget,
  and hard rules (forbidden claims, banned phrases, required disclaimers).
- **Autopilot**: a tenant-wide schedule that has the Campaign Director pick
  its own goal and run unattended, on an interval.
- **Team**: admins can add teammates, promote/demote, or remove them — no
  shared master secret required for day-to-day use. Anyone can change their
  own password.
- **Developer Logs**: live application log activity, filterable by category,
  level, and date — for when something needs debugging without SSH access.

## Autonomy is a policy, not a hard-coded behavior

Every tenant sets its own: fully autonomous (QA failures loop back to the
writer, clean output publishes itself) or review-required (identical
pipeline, but finished content parks in a queue instead of going live). The
pipeline the agents run is the same either way — autonomy is a flag the
policy sets, not a different code path.

## What's underneath, briefly

- **Multi-tenant by construction, single-tenant in operation.** Every query
  is filtered by tenant at the data layer (not by caller discipline) — a
  crafted request can't widen its own scope. See
  [ARCHITECTURE.md](ARCHITECTURE.md).
- **LLM-provider agnostic.** Gemini, Groq, OpenAI, Anthropic, or a local
  Ollama model — swappable per agent, per tenant, without touching the graph
  itself. Currently routed to Groq for local development (generous free
  tier, avoids Gemini's tight daily cap); production can run a different mix.
- **Two authentication paths**: a tenant service key for scripts/ops, or
  individual email+password logins for people, with session tokens that are
  actually revoked on logout, not just forgotten client-side.

## Where this runs

Backend (FastAPI + LangGraph + MongoDB) on Railway or any container host;
console (React/Vite) on Vercel or any static host; local development via one
`docker-compose up`. See [DEPLOY.md](DEPLOY.md) for the specifics,
[API.md](API.md) for the route reference, and [SCHEMAS.md](SCHEMAS.md) for
every stored field.
