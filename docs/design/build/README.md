# Design deck build

Regenerates [`../BuildX-UIUX-Demo-Design.pdf`](../BuildX-UIUX-Demo-Design.pdf) — a
19-page walkthrough of the console, styled to match
[cmartsolutions.com](https://cmartsolutions.com)'s theme (near-black ground, a
single restrained red accent, Bricolage Grotesque + Inter). See the module
docstring in `build_pdf.py` for the exact tokens and where each one came from.

The deck's own chrome (cover, dividers, fonts, accent color, cards) is styled
to match the site. The embedded screenshots and the "Color & Type" slide
documenting the app's real CSS tokens are **not** — those show the actual
shipped BuildX console, which is still blue/purple, since this was a deck
restyle, not a product rebrand.

## Regenerating

1. **Capture fresh screenshots.** Requires the backend (`LLM_PROVIDER=simulator`
   works fine, no API key needed) and console dev server running, and two
   seeded tenants (`python -m scripts.seed` from `backend/`, after dropping
   any existing `buildx` database so the demo run isn't duplicated content).

   ```bash
   npm install playwright && npx playwright install chromium
   node shots.mjs "<vertex-tenant-api-key>" "<northwind-tenant-api-key>"
   ```

   Writes to `./screens/` (gitignored — these are regenerated each time, not
   canonical; run IDs and timestamps differ on every capture).

2. **Build the PDF.**

   ```bash
   python -m venv .venv && .venv/Scripts/python.exe -m pip install reportlab pillow
   .venv/Scripts/python.exe build_pdf.py
   ```

   Reads screenshots from `./screens/`, fonts from `./fonts/` (already
   committed — the exact Bricolage Grotesque + Inter weights cmartsolutions.com
   loads, fetched from Google Fonts and embedded as TTF so the PDF renders
   identically everywhere, not just where those fonts happen to be installed).

## Files here

```
build_pdf.py   the deck generator — canvas-drawn slides, not Platypus flowables
shots.mjs      Playwright script that drives the real running console and
               captures each screen (connect, mission control, a live run
               with an actual QA-block-then-revise cycle, runs, library,
               brands, audit, settings, theming)
fonts/         Bricolage Grotesque (ExtraBold/SemiBold/Bold/Regular) +
               Inter (Regular/Medium/SemiBold/Bold), embedded into the PDF
```
