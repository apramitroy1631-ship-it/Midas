"""Builds the BuildX UI/UX demo design deck.

Deliberately drawn with reportlab's low-level canvas API rather than Platypus
flowables. The deck's chrome — cover, section dividers, fonts, accent color,
card and badge treatment — is styled to match cmartsolutions.com (the
consulting firm this was built under): near-black ground, a single restrained
red accent rather than a multi-color badge system, Bricolage Grotesque for
display type, Inter for body copy. Tokens were read directly off the live
site's computed styles (background, the "Operations" headline word, the
"Get in Touch" button, card borders, the active-nav underline) — see the
exact values in the comments below.

This is the deck's OWN presentation layer, not the product's. The embedded
screenshots and the "Color & Type" slide documenting the app's actual CSS
tokens are untouched — BuildX's shipped UI is still blue/purple, since a
product rebrand wasn't part of this request. See APP_ACCENT / APP_ACCENT_2
below for those real, unchanged tokens.

Every screenshot embedded is a real capture of the running app (see
shot-tool/shots.mjs) — nothing here is a mockup.
"""
from __future__ import annotations

import os

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
SCREENS = os.path.join(HERE, "shot-tool", "screens")
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "BuildX-UIUX-Demo-Design.pdf")

# ---------------------------------------------------------------------------
# Design tokens — read directly off cmartsolutions.com's computed styles.
# ---------------------------------------------------------------------------
BG = HexColor("#070707")           # body background: rgb(7,7,7)
SURFACE = HexColor("#0d0d0d")      # card bg: rgba(255,255,255,0.024) over BG
SURFACE_2 = HexColor("#141414")    # a touch more raised, for nested chrome
BORDER = HexColor("#2a2a2a")       # stronger neutral hairline
BORDER_SOFT = HexColor("#1c1c1c")  # card border: rgba(255,255,255,0.06) over BG
TEXT = HexColor("#ffffff")         # body text: rgb(255,255,255)
TEXT_MUTED = HexColor("#b3b3b3")   # ~70% white, matches the site's muted token
TEXT_DIM = HexColor("#787878")     # ~45% white, matches "SCROLL TO EXPLORE"

ACCENT = HexColor("#d63d39")       # the "Operations" headline-word red
ACCENT_2 = HexColor("#8f2c2e")     # the "Get in Touch" button red (deeper)
PILL_RED = HexColor("#cc262e")     # the active-nav-underline / badge-pill red

# Real, UNCHANGED tokens from web/src/styles.css — the shipped app's own
# palette, used only on the "Color & Type" slide, which documents the actual
# running product rather than this deck's own chrome.
APP_BG = HexColor("#0a0b0e")
APP_SURFACE = HexColor("#101218")
APP_SURFACE_2 = HexColor("#161922")
APP_BORDER_SOFT = HexColor("#1a1e2a")
APP_ACCENT = HexColor("#6ea8fe")
APP_ACCENT_2 = HexColor("#b98cff")
OK = HexColor("#4ade80")
WARN = HexColor("#fbbf24")
DANGER = HexColor("#f87171")
RUNNING = HexColor("#38bdf8")
WHITE = HexColor("#ffffff")

PAGE_W, PAGE_H = 13.333 * 72, 7.5 * 72  # 16:9 slide format
MARGIN = 0.55 * 72

# ---------------------------------------------------------------------------
# Fonts — the two families cmartsolutions.com actually loads (confirmed via
# document.fonts): Bricolage Grotesque for display type, Inter for everything
# else. Embedded as TTF so the deck renders identically anywhere it's opened,
# not just on a machine with these fonts installed. Courier stands in for the
# site's own "Courier New" mono treatment on eyebrow labels like
# "SCROLL TO EXPLORE" — a system font, nothing to embed.
# ---------------------------------------------------------------------------
pdfmetrics.registerFont(TTFont("Bricolage", os.path.join(FONTS, "Bricolage-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Bricolage-SemiBold", os.path.join(FONTS, "Bricolage-SemiBold.ttf")))
pdfmetrics.registerFont(TTFont("Bricolage-Bold", os.path.join(FONTS, "Bricolage-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Bricolage-ExtraBold", os.path.join(FONTS, "Bricolage-ExtraBold.ttf")))
pdfmetrics.registerFont(TTFont("Inter", os.path.join(FONTS, "Inter-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Inter-Medium", os.path.join(FONTS, "Inter-Medium.ttf")))
pdfmetrics.registerFont(TTFont("Inter-SemiBold", os.path.join(FONTS, "Inter-SemiBold.ttf")))
pdfmetrics.registerFont(TTFont("Inter-Bold", os.path.join(FONTS, "Inter-Bold.ttf")))

DISPLAY = "Bricolage-ExtraBold"     # cover title, closing headline — weight 800, as on the site
DISPLAY_SB = "Bricolage-SemiBold"   # slide titles, screen titles, card headers
SANS = "Inter"                      # body copy
SANS_M = "Inter-Medium"
SANS_B = "Inter-SemiBold"           # matches the button's font-weight: 600
MONO = "Courier"
MONO_B = "Courier-Bold"


def slide_bg(c: canvas.Canvas, color=BG) -> None:
    c.setFillColor(color)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def radial_glow(c, cx, cy, max_r, color, peak_alpha, steps=28):
    """A smooth radial-gradient stand-in — reportlab has no true gradient
    fill for arbitrary shapes, so this paints many concentric rings, each a
    hair larger with a hair less alpha (quadratic falloff), from the outside
    in so the small high-alpha core ends up on top. Enough steps that the
    individual rings disappear into a continuous glow instead of banding."""
    c.saveState()
    c.setFillColor(color)
    for i in range(steps, 0, -1):
        t = i / steps
        r = max_r * t
        alpha = peak_alpha * (1 - t) ** 2
        if alpha <= 0.0015:
            continue
        c.setFillAlpha(alpha)
        c.circle(cx, cy, r, fill=1, stroke=0)
    c.restoreState()


def rounded(c, x, y, w, h, r, fill=None, stroke=None, lw=1):
    c.saveState()
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=1 if fill is not None else 0, stroke=1 if stroke is not None else 0)
    c.restoreState()


def text(c, x, y, s, font=SANS, size=10, color=TEXT, leading=None, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "left":
        c.drawString(x, y, s)
    elif align == "center":
        c.drawCentredString(x, y, s)
    elif align == "right":
        c.drawRightString(x, y, s)


def wrapped(c, x, y, s, font=SANS, size=10, color=TEXT_MUTED, max_width=300, leading=14):
    """Simple word-wrap for body copy; returns the y after the last line."""
    c.setFont(font, size)
    c.setFillColor(color)
    words = s.split()
    line = ""
    cy = y
    for w in words:
        trial = (line + " " + w).strip()
        if pdfmetrics.stringWidth(trial, font, size) > max_width and line:
            c.drawString(x, cy, line)
            cy -= leading
            line = w
        else:
            line = trial
    if line:
        c.drawString(x, cy, line)
        cy -= leading
    return cy


def footer(c, page_no, section=""):
    c.setFont(MONO, 8)
    c.setFillColor(TEXT_DIM)
    c.drawString(MARGIN, 0.35 * 72, "BUILDX — UI/UX DEMO DESIGN")
    if section:
        c.drawCentredString(PAGE_W / 2, 0.35 * 72, section.upper())
    c.drawRightString(PAGE_W - MARGIN, 0.35 * 72, str(page_no).zfill(2))
    c.setStrokeColor(BORDER_SOFT)
    c.setLineWidth(0.5)
    c.line(MARGIN, 0.55 * 72, PAGE_W - MARGIN, 0.55 * 72)


def status_dot(c, x, y, color, r=3.5):
    c.setFillColor(color)
    c.circle(x, y, r, fill=1, stroke=0)


def mark(c, key, title, level=0):
    """Registers the CURRENT page in the PDF's outline/bookmark panel, so the
    deck can be navigated by clicking a section in Acrobat/Preview's sidebar
    instead of scrolling — the difference between a 21-page PDF and a
    document someone can actually jump around in during a meeting.

    Bookmark titles are ASCII-sanitised (em dash -> hyphen): reportlab's
    outline entries mangle non-Latin1 punctuation into replacement-character
    boxes in some PDF viewers' sidebars. The on-slide text is unaffected —
    that's drawn as vector glyphs, an entirely different code path."""
    c.bookmarkPage(key)
    c.addOutlineEntry(title.replace("—", "-"), key, level=level)


def badge(c, x, y, label, color, filled=False):
    w = pdfmetrics.stringWidth(label, MONO_B, 8) + 16
    h = 16
    if filled:
        rounded(c, x, y, w, h, h / 2, fill=color)
        c.setFillColor(BG)
    else:
        rounded(c, x, y, w, h, h / 2, stroke=color, lw=1)
        c.setFillColor(color)
    c.setFont(MONO_B, 8)
    c.drawCentredString(x + w / 2, y + 5, label)
    return w


def fit_image(path, max_w, max_h):
    img = ImageReader(path)
    iw, ih = img.getSize()
    scale = min(max_w / iw, max_h / ih)
    return img, iw * scale, ih * scale


def image_frame(c, path, x, y, w, h, border=BORDER, shadow=True):
    """Draws a screenshot inside a thin bordered frame, scaled to fit (x,y)=top-left."""
    img, dw, dh = fit_image(path, w, h)
    fx = x + (w - dw) / 2
    fy = y - h + (h - dh) / 2
    if shadow:
        c.saveState()
        c.setFillColor(HexColor("#000000"))
        c.setFillAlpha(0.35)
        c.roundRect(fx - 3, fy - 5, dw + 6, dh + 6, 6, fill=1, stroke=0)
        c.restoreState()
    c.drawImage(img, fx, fy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(border)
    c.setLineWidth(1)
    c.roundRect(fx, fy, dw, dh, 4, fill=0, stroke=1)
    return fx, fy, dw, dh


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------


def cover(c):
    slide_bg(c)
    # The site's own hero glow, translated: a tight, hot red pool that falls
    # off fast — most of the page stays true black, same as the real hero,
    # rather than a wash across the whole slide.
    radial_glow(c, PAGE_W * 0.5, PAGE_H * 0.34, 300, ACCENT, 0.22)

    # logo mark — BuildX's own "BX", not CMART's diamond glyph: same red
    # treatment, a distinct identity.
    mx, my = MARGIN, PAGE_H - 1.35 * 72
    rounded(c, mx, my, 46, 46, 12, fill=ACCENT)
    c.setFont(DISPLAY_SB, 19)
    c.setFillColor(WHITE)
    c.drawCentredString(mx + 23, my + 16, "BX")
    text(c, mx + 60, my + 26, "BuildX", font=DISPLAY_SB, size=16, color=TEXT)
    text(c, mx + 60, my + 10, "AUTONOMOUS MARKETING", font=MONO, size=8.5, color=TEXT_DIM)

    text(c, MARGIN, PAGE_H - 2.6 * 72, "UI / UX Demo Design", font=DISPLAY, size=42, color=TEXT)
    text(
        c,
        MARGIN,
        PAGE_H - 3.2 * 72,
        "The console for a hierarchical, multi-tenant marketing agent system",
        font=SANS,
        size=15,
        color=TEXT_MUTED,
    )
    text(
        c,
        MARGIN,
        PAGE_H - 3.55 * 72,
        "that runs campaigns with no human in the loop.",
        font=SANS,
        size=15,
        color=TEXT_MUTED,
    )

    bx = MARGIN
    bx += badge(c, bx, PAGE_H - 4.2 * 72, "NO HUMAN IN THE LOOP", ACCENT, filled=False) + 12
    bx += badge(c, bx, PAGE_H - 4.2 * 72, "MULTI-TENANT", ACCENT, filled=False) + 12
    badge(c, bx, PAGE_H - 4.2 * 72, "LIVE CAPTURES", ACCENT, filled=False)

    # bottom meta strip
    c.setStrokeColor(BORDER_SOFT)
    c.setLineWidth(1)
    c.line(MARGIN, 1.05 * 72, PAGE_W - MARGIN, 1.05 * 72)
    text(c, MARGIN, 0.72 * 72, "Every screen in this deck is a real capture of the running application — not a mockup.", size=10, color=TEXT_DIM)
    text(c, PAGE_W - MARGIN, 0.72 * 72, "github.com/apramitroy1631-ship-it/Midas", font=MONO, size=9.5, color=TEXT_DIM, align="right")


def agenda_slide(c, page_no):
    slide_bg(c)
    radial_glow(c, PAGE_W - 40, -40, 260, ACCENT, 0.14)
    text(c, MARGIN, PAGE_H - 0.85 * 72, "What's in this deck", font=DISPLAY, size=28, color=TEXT)
    text(c, MARGIN, PAGE_H - 1.2 * 72, "Four sections, eleven real screens, one running system.", size=12, color=TEXT_MUTED)

    items = [
        ("01", "Design System", "The visual language, and the four rules the rest of the deck keeps proving."),
        ("02", "Getting In", "One credential, one tenant — how an operator connects."),
        ("03", "Operating the System", "Launch a run and watch the self-correction loop happen live — no human step."),
        ("04", "What the System Produces", "Published content, compounding brand memory, and a full decision log."),
    ]
    row_h = 1.05 * 72
    top = PAGE_H - 1.95 * 72
    for i, (num, title_, body) in enumerate(items):
        y = top - i * row_h
        c.setStrokeColor(BORDER_SOFT)
        c.setLineWidth(1)
        c.line(MARGIN, y - row_h + 22, PAGE_W - MARGIN, y - row_h + 22)
        text(c, MARGIN, y, num, font=MONO_B, size=13, color=ACCENT)
        text(c, MARGIN + 60, y, title_, font=DISPLAY_SB, size=16, color=TEXT)
        wrapped(c, MARGIN + 60, y - 20, body, size=10.5, color=TEXT_MUTED, max_width=PAGE_W - 2 * MARGIN - 60, leading=14)

    footer(c, page_no, "Agenda")


def exec_summary_slide(c, page_no):
    """The ten-second version, for the reader who only has ten seconds:
    real, verifiable numbers pulled from the actual run captured in this
    deck — not aspirational figures."""
    slide_bg(c)
    text(c, MARGIN, PAGE_H - 0.85 * 72, "At a glance", font=DISPLAY, size=28, color=TEXT)
    text(c, MARGIN, PAGE_H - 1.2 * 72, "What changes for the business — from the actual run behind this deck, not a projection.", size=12, color=TEXT_MUTED)

    tiles = [
        ("ZERO", "Human reviews to publish", "QA failures loop back to the writer automatically. A person is never the bottleneck between a draft and a live asset.", ACCENT),
        ("100%", "Tenant isolation, enforced", "Not a policy or a promise — every query is filtered by tenant at the data layer. One tenant's data cannot reach another's.", PILL_RED),
        ("93 / 88", "Brand safety / goal alignment", "QA's own scores on the real run behind this deck — the system grading its own output, unfiltered.", ACCENT_2),
        ("EVERY", "Decision logged, with a reason", "Nothing publishes, drops, or gets abandoned without a recorded reason — the accountability trail a reviewer would normally leave.", ACCENT),
    ]
    tile_w = (PAGE_W - 2 * MARGIN - 3 * 20) / 4
    tile_h = 2.75 * 72
    ty = PAGE_H - 1.7 * 72
    for i, (big, label, body, color) in enumerate(tiles):
        x = MARGIN + i * (tile_w + 20)
        rounded(c, x, ty - tile_h, tile_w, tile_h, 10, fill=SURFACE, stroke=BORDER_SOFT)
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.line(x + 16, ty - 16, x + 16, ty - tile_h + 18)
        text(c, x + 30, ty - 50, big, font=DISPLAY, size=29, color=color)
        wrapped(c, x + 30, ty - 74, label, font=SANS_B, size=11, color=TEXT, max_width=tile_w - 44, leading=14)
        wrapped(c, x + 30, ty - 110, body, size=9, color=TEXT_MUTED, max_width=tile_w - 44, leading=12.5)

    # A closing line that earns the empty space below the tiles rather than
    # leaving it looking unfinished — the "so what" for a reader who stops here.
    strip_y = ty - tile_h - 0.65 * 72
    c.setStrokeColor(BORDER_SOFT)
    c.setLineWidth(1)
    c.line(MARGIN, strip_y + 34, PAGE_W - MARGIN, strip_y + 34)
    text(c, MARGIN, strip_y, "The system runs itself. The record proves it did the right thing.", font=DISPLAY_SB, size=17, color=TEXT)
    text(c, MARGIN, strip_y - 24, "The eleven screens that back every number above follow, in order.", font=SANS, size=10.5, color=TEXT_DIM)

    footer(c, page_no, "At a glance")


def section_divider(c, index, total, title, subtitle):
    slide_bg(c)
    radial_glow(c, PAGE_W + 40, PAGE_H + 20, 320, ACCENT, 0.18)
    text(c, MARGIN, PAGE_H - 1.4 * 72, f"{index:02d} / {total:02d}", font=MONO, size=12, color=ACCENT)
    text(c, MARGIN, PAGE_H - 2.2 * 72, title, font=DISPLAY, size=36, color=TEXT)
    wrapped(c, MARGIN, PAGE_H - 2.8 * 72, subtitle, font=SANS, size=13, color=TEXT_MUTED, max_width=PAGE_W - 2 * MARGIN, leading=18)
    c.setStrokeColor(BORDER_SOFT)
    c.line(MARGIN, PAGE_H - 3.3 * 72, PAGE_W - MARGIN, PAGE_H - 3.3 * 72)


def principles_slide(c, page_no):
    slide_bg(c)
    text(c, MARGIN, PAGE_H - 0.85 * 72, "Design Principles", font=DISPLAY_SB, size=25, color=TEXT)
    text(c, MARGIN, PAGE_H - 1.15 * 72, "The visual language is a direct consequence of what the product has to prove.", size=11, color=TEXT_MUTED)

    principles = [
        ("Dark-first, not dark-only", "This is a monitoring surface people leave open on a second monitor for hours. Dark reduces eye strain over a long session; a full light-theme token swap exists for daytime use (the Theming screen, later in this deck), not an inverted hack."),
        ("Status is color, always paired with text", "Green/amber/red never carry meaning alone — every status dot sits beside a word (“published”, “blocked”, “abandoned”). Color-blind users and screenshots in Slack both still read correctly."),
        ("Monospace marks anything the system generated", "IDs, timestamps, scores, costs — machine output — render in mono. Prose the agents or a person wrote renders in the sans body font. The split lets your eye sort “data” from “writing” without reading either."),
        ("The autonomy badge is never absent", "“No human in the loop” sits in the top bar on every single screen, not just the launch view. The one fact a stakeholder must never lose track of is structurally impossible to scroll past."),
    ]

    col_w = (PAGE_W - 2 * MARGIN - 24) / 2
    positions = [
        (MARGIN, PAGE_H - 1.9 * 72),
        (MARGIN + col_w + 24, PAGE_H - 1.9 * 72),
        (MARGIN, PAGE_H - 3.75 * 72),
        (MARGIN + col_w + 24, PAGE_H - 3.75 * 72),
    ]
    card_h = 1.65 * 72
    for (title_, body), (x, y) in zip(principles, positions):
        rounded(c, x, y - card_h, col_w, card_h, 8, fill=SURFACE, stroke=BORDER_SOFT)
        text(c, x + 18, y - 30, title_, font=SANS_B, size=12.5, color=TEXT)
        wrapped(c, x + 18, y - 50, body, size=9.5, color=TEXT_MUTED, max_width=col_w - 36, leading=13)

    footer(c, page_no, "Design system")


def palette_slide(c, page_no):
    """Documents the SHIPPED APP's real design system — web/src/styles.css,
    unchanged. This deck's own chrome is styled to match cmartsolutions.com
    (see every other slide), but that is a fact about this document, not
    about the product, so the swatches and type samples below stay exactly
    what the running app actually uses: still blue/purple, not red."""
    slide_bg(c)
    text(c, MARGIN, PAGE_H - 0.85 * 72, "Color & Type", font=DISPLAY_SB, size=25, color=TEXT)
    text(c, MARGIN, PAGE_H - 1.15 * 72, "The shipped app's own tokens — web/src/styles.css, unchanged by this deck's cmartsolutions.com-matched cover and chrome.", size=11, color=TEXT_MUTED)

    swatches = [
        ("--bg", APP_BG, "page ground"),
        ("--surface", APP_SURFACE, "cards"),
        ("--surface-2", APP_SURFACE_2, "inputs / raised"),
        ("--border-soft", APP_BORDER_SOFT, "hairlines"),
        ("--accent", APP_ACCENT, "primary / links"),
        ("--accent-2", APP_ACCENT_2, "secondary tenant"),
        ("--ok", OK, "published / passed"),
        ("--warn", WARN, "revision / advisory"),
        ("--danger", DANGER, "abandoned / critical"),
        ("--running", RUNNING, "in progress"),
    ]
    sw = (PAGE_W - 2 * MARGIN - 9 * 14) / 10
    sy = PAGE_H - 2.4 * 72
    for i, (name, color, use) in enumerate(swatches):
        x = MARGIN + i * (sw + 14)
        rounded(c, x, sy, sw, sw, 8, fill=color, stroke=BORDER_SOFT if color in (APP_BG,) else None)
        text(c, x, sy - 16, name, font=MONO, size=8, color=TEXT_MUTED)
        wrapped(c, x, sy - 28, use, font=SANS, size=7.5, color=TEXT_DIM, max_width=sw, leading=9)

    text(c, MARGIN, PAGE_H - 4.1 * 72, "Typography (app)", font=DISPLAY_SB, size=14, color=TEXT)
    ty = PAGE_H - 4.55 * 72
    # Drawn in reportlab's built-in Helvetica deliberately, NOT this deck's
    # embedded Inter — the app genuinely uses a generic system-ui stack with
    # no webfont at all, and the caption below says so; sampling it in a
    # real webfont would quietly contradict that claim.
    text(c, MARGIN, ty, "Aa", font="Helvetica-Bold", size=34, color=TEXT)
    text(c, MARGIN + 70, ty - 5, "Sans — UI chrome, prose, agent-written copy", font=SANS, size=11, color=TEXT_MUTED)
    text(c, MARGIN + 70, ty - 20, "System sans-serif stack, no webfont dependency", font=SANS, size=9, color=TEXT_DIM)

    ty2 = ty - 65
    text(c, MARGIN, ty2, "01:23", font=MONO_B, size=30, color=APP_ACCENT)
    text(c, MARGIN + 70, ty2 - 5, "Mono — IDs, timestamps, scores, costs, code", font=SANS, size=11, color=TEXT_MUTED)
    text(c, MARGIN + 70, ty2 - 20, "Anything the system generated, never hand-written copy", font=SANS, size=9, color=TEXT_DIM)

    text(c, PAGE_W - MARGIN - 320, PAGE_H - 4.1 * 72, "Spacing & radius", font=DISPLAY_SB, size=14, color=TEXT, align="left")
    rules = [
        "Base radius 10px (cards), 6px (controls) — soft, not skeuomorphic",
        "1px hairline borders throughout — depth comes from color, not shadow",
        "Consistent 14–22px internal card padding, no bespoke spacing per view",
    ]
    ry = PAGE_H - 4.5 * 72
    for r in rules:
        c.setFillColor(APP_ACCENT)
        c.circle(PAGE_W - MARGIN - 316, ry + 3, 1.6, fill=1, stroke=0)
        wrapped(c, PAGE_W - MARGIN - 305, ry, r, size=9.5, color=TEXT_MUTED, max_width=300, leading=12)
        ry -= 28

    footer(c, page_no, "Design system")


def screen_slide(c, page_no, index, total, title, tag, tag_color, image_name, takeaway, points, stat=None):
    """One screen: a real screenshot, framed, plus an annotation panel.

    `takeaway` is the one line a reader skimming gets — bold, up top, before
    any implementation detail. `stat`, when given, is (big_text, label,
    color): a pulled-out number rendered above the takeaway, so a handful of
    screens carry more visual weight than the rest instead of all eleven
    reading as the identical template. `points` is capped at 3 when there's
    no stat, 2 when there is — the stat block earns its space by displacing
    a bullet, not by compressing everything else.
    """
    slide_bg(c)

    # header
    text(c, MARGIN, PAGE_H - 0.62 * 72, f"{index:02d}", font=MONO_B, size=11, color=ACCENT)
    text(c, MARGIN + 26, PAGE_H - 0.62 * 72, title, font=DISPLAY_SB, size=18, color=TEXT)
    badge(c, PAGE_W - MARGIN - 130, PAGE_H - 0.72 * 72, tag, tag_color)

    img_path = os.path.join(SCREENS, image_name)

    top_y = PAGE_H - 0.95 * 72
    bottom_y = 0.75 * 72
    avail_h = top_y - bottom_y

    img_w = PAGE_W * 0.6 - MARGIN
    image_frame(c, img_path, MARGIN, top_y, img_w, avail_h)

    col_x = MARGIN + img_w + 26
    col_w = PAGE_W - MARGIN - col_x - 20
    rounded(c, col_x - 18, bottom_y, col_w + 38, avail_h, 12, fill=SURFACE, stroke=BORDER_SOFT)

    cy = top_y - 24

    if stat:
        big, label, scolor = stat
        text(c, col_x, cy, big, font=DISPLAY, size=25, color=scolor)
        cy -= 20
        cy = wrapped(c, col_x, cy, label, font=SANS_B, size=9.5, color=TEXT, max_width=col_w, leading=12)
        cy -= 6
        c.setStrokeColor(BORDER_SOFT)
        c.setLineWidth(1)
        c.line(col_x, cy, col_x + col_w, cy)
        cy -= 18

    cy = wrapped(c, col_x, cy, takeaway, font=SANS_B, size=12.5, color=TEXT, max_width=col_w, leading=16)
    cy -= 16

    max_points = 2 if stat else 3
    for label, body in points[:max_points]:
        c.setFillColor(ACCENT)
        c.circle(col_x + 2, cy + 3, 2, fill=1, stroke=0)
        text(c, col_x + 12, cy, label, font=SANS_B, size=10, color=TEXT)
        cy -= 14
        cy = wrapped(c, col_x + 12, cy, body, size=9, color=TEXT_MUTED, max_width=col_w - 12, leading=12.5)
        cy -= 10

    footer(c, page_no, title)


def closing_slide(c, page_no):
    slide_bg(c)
    radial_glow(c, PAGE_W * 0.12, PAGE_H * 0.2, 260, ACCENT_2, 0.16)

    text(c, MARGIN, PAGE_H - 1.3 * 72, "What the design is actually arguing", font=DISPLAY, size=27, color=TEXT)
    wrapped(
        c,
        MARGIN,
        PAGE_H - 1.75 * 72,
        "Every screen in this deck exists to make one thing legible: a system is deciding things without you, "
        "and you can always see exactly what it decided and why. That is the whole design brief.",
        size=12,
        color=TEXT_MUTED,
        max_width=PAGE_W - 2 * MARGIN,
        leading=17,
    )

    rows = [
        ("The revision banner", "is the single most important element in the product — it's the moment a human would normally intervene, made visible instead of invisible."),
        ("The isolation card", "on Mission Control exists so “multi-tenant” isn't a claim in a README — it's a fact the operator can see about their own key, every time they load the page."),
        ("The tenant switcher", "makes cross-tenant separation demonstrable in seconds: two keys, two completely disjoint datasets, one UI."),
        ("The decision log", "stands in for the approval trail a human reviewer would normally leave — nothing ships without a reason recorded."),
    ]
    ry = PAGE_H - 2.6 * 72
    for label, body in rows:
        c.setFillColor(ACCENT)
        rounded(c, MARGIN, ry - 4, 5, 5, 1, fill=ACCENT)
        text(c, MARGIN + 16, ry, label, font=SANS_B, size=11.5, color=TEXT)
        wrapped(c, MARGIN + 16, ry - 16, body, size=10, color=TEXT_MUTED, max_width=PAGE_W - 2 * MARGIN - 16, leading=13.5)
        ry -= 62

    c.setStrokeColor(BORDER_SOFT)
    c.line(MARGIN, 1.05 * 72, PAGE_W - MARGIN, 1.05 * 72)
    text(c, MARGIN, 0.72 * 72, "backend/README.md · web/README.md · docs/ARCHITECTURE.md · docs/API.md", font=MONO, size=9, color=TEXT_DIM)
    text(c, PAGE_W - MARGIN, 0.72 * 72, "11 SCREENS · 21 PAGES", font=MONO, size=9, color=TEXT_DIM, align="right")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def main():
    c = canvas.Canvas(OUT, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("BuildX — UI/UX Demo Design")
    c.setAuthor("BuildX")
    c.setSubject("Console design walkthrough")

    page = 1
    cover(c)
    mark(c, "cover", "Cover", level=0)
    c.showPage()
    page += 1

    agenda_slide(c, page)
    mark(c, "agenda", "Agenda", level=0)
    c.showPage()
    page += 1

    exec_summary_slide(c, page)
    mark(c, "exec-summary", "At a Glance", level=0)
    c.showPage()
    page += 1

    section_divider(
        c, 1, 4, "Design System",
        "Tokens, type, and the four principles the rest of the deck keeps coming back to."
    )
    mark(c, "sec-design-system", "01 — Design System", level=0)
    c.showPage()
    page += 1

    principles_slide(c, page)
    mark(c, "principles", "Design Principles", level=1)
    c.showPage()
    page += 1

    palette_slide(c, page)
    mark(c, "palette", "Color & Type", level=1)
    c.showPage()
    page += 1

    section_divider(
        c, 2, 4, "Getting In",
        "Connecting to a tenant, and the first thing the operator sees."
    )
    mark(c, "sec-getting-in", "02 — Getting In", level=0)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 1, 11, "Connect", "ONBOARDING", ACCENT, "01b-connect-filled-crop.png",
        "One key in, one tenant's world — nothing to configure, nothing to leak.",
        [
            ("One credential, one tenant", "There's no login/signup flow to design — a tenant API key is the entire authentication model, verified against /v1/me before it's ever saved, so a bad key fails right here instead of three screens later."),
            ("Keys live in this browser only", "Never sent anywhere but the API this browser is pointed at, and never logged. The hint text says so explicitly, because a demo audience's first question is always “where does this go?”"),
            ("Several tenants, one shell", "Connecting a second key doesn't replace the first — it adds an entry to a switcher (see the Mission Control screen next), which is what makes the multi-tenant claim demonstrable rather than asserted."),
        ],
    )
    mark(c, "screen-connect", "Connect", level=1)
    c.showPage()
    page += 1

    section_divider(
        c, 3, 4, "Operating the System",
        "Mission control, launching a run, and watching the self-correction loop happen live."
    )
    mark(c, "sec-operating", "03 — Operating the System", level=0)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 2, 11, "Mission Control", "OVERVIEW", PILL_RED, "14-tenant-switcher.png",
        "Every operator sees, in one glance, exactly what their access can and can't touch.",
        [
            ("The autonomy badge, always present", "“No human in the loop” sits in the top bar on every screen in the product, not just this one — the fact that governs everything else is structurally impossible to lose track of."),
            ("Isolation stated, not implied", "The Isolation card names this exact tenant id and key prefix and says plainly what it can and can't reach. That sentence is true because the data layer enforces it, not because the UI asks nicely."),
        ],
        stat=("93 / 88", "Brand safety / goal alignment on this run", ACCENT),
    )
    mark(c, "screen-mission-control", "Mission Control", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 3, 11, "Launch — Brief", "IDLE", ACCENT_2, "03-launch-idle.png",
        "Give it a budget. It decides the rest — or takes your direction if you have one.",
        [
            ("The goal field is optional on purpose", "Leave it blank and the Campaign Director reads brand memory and picks one itself — the empty state's hint text says exactly this, so the self-directed mode isn't a hidden feature."),
            ("Autonomy is explained at the point of use", "The right-hand panel restates what “fully autonomous” means for this specific run, right where the operator is about to trigger one — not buried in a settings page they'd need to go find."),
            ("Revision budget is visible before you commit", "Seeing “2 cycles” here, not after a run fails, sets the right expectation for what “autonomous” is actually going to do if something goes wrong."),
        ],
    )
    mark(c, "screen-launch-brief", "Launch — Brief", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 4, 11, "Launch — Live Pipeline", "RUNNING", ACCENT, "05-launch-complete.png",
        "The step that used to need a person is now something you can watch happen.",
        [
            ("The single most important element in the product", "QA blocked the first draft; the revision banner shows the specific issues going back to the writer — with no human involved. This is the moment that would normally need a person, made visible instead of invisible."),
            ("Every node is a real decision, not a spinner", "Each step summarises what that agent actually concluded — 4 insights, 2 competitors, a specific market figure — while it's still running, via the SSE stream. Nothing here is a fake progress bar."),
        ],
        stat=("1", "Revision cycle — QA caught it, the writer fixed it, no human involved", ACCENT),
    )
    mark(c, "screen-launch-pipeline", "Launch — Live Pipeline", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 5, 11, "Launch — Agent Detail", "EXPANDED", PILL_RED, "06-launch-qa-detail.png",
        "Every judgment call the system makes is inspectable, not a black box.",
        [
            ("Click any step, see the actual agent output", "This is the QA agent's real structured response — scores, verdict, and every issue with its channel and a concrete fix — not a generic “completed” state."),
            ("Severity is explicit, never inferred from color alone", "Each issue is labelled critical or advisory in text next to the color, because a screenshot shared in Slack shouldn't need the reader to know the palette."),
            ("The meter bars make the score visceral", "93 and 88 read fine as numbers, but the filled bar next to each one is what makes “this passed comfortably” legible in half a second."),
        ],
    )
    mark(c, "screen-launch-detail", "Launch — Agent Detail", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 6, 11, "Runs — History & Trace", "AUDIT", ACCENT_2, "08-runs-drawer.png",
        "Nothing the system did is ever lost — replay any run, any time.",
        [
            ("A drawer, not a new page", "Opening a run's detail doesn't lose the list behind it — the table stays visible and dimmed, so comparing across runs doesn't mean losing your place."),
            ("Origin badge travels with the run permanently", "“self-directed” vs an operator-supplied goal stays attached to the run forever, not just at launch time — it's a fact about the decision, worth keeping."),
        ],
        stat=("100%", "Of every run's agent trace, replayable forever", PILL_RED),
    )
    mark(c, "screen-runs", "Runs — History & Trace", level=1)
    c.showPage()
    page += 1

    section_divider(
        c, 4, 4, "What the System Produces",
        "The content library, brand memory, the decision log, and the settings that decide how much rope the agents get."
    )
    mark(c, "sec-produces", "04 — What the System Produces", level=0)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 7, 11, "Content Library", "OUTPUT", ACCENT, "09-library.png",
        "What ships is what you see — no hidden approval queue slowing things down.",
        [
            ("Copy stays exactly as the agent wrote it", "Headline, body, and CTA render verbatim, with SEO keywords and hashtags surfaced as chips — the library is meant to be copy-pasted straight into a real channel."),
            ("Filterable the way a marketer actually thinks", "By brand, then by channel — the two dimensions someone managing several tenants' output would actually need to slice by."),
        ],
        stat=("ZERO", "Assets sitting in a review queue by default", ACCENT),
    )
    mark(c, "screen-library", "Content Library", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 8, 11, "Brands — Memory", "LEARNING", PILL_RED, "10-brands.png",
        "The system gets smarter about your brand with every campaign, automatically.",
        [
            ("The compounding loop, made visible", "“Learned by the system” shows the actual insights the last run wrote back — this is what lets the next run avoid repeating an angle, not a claim in a README."),
            ("Winning vs. exhausted, counted separately", "Two different badges, because they mean opposite things for planning: one says “do more of this,” the other says “this is used up, don't replan around it.”"),
            ("Restrictions are the one non-negotiable field", "Content restrictions are what QA treats as absolute — they're never optional in the edit drawer, because a breach here is what actually blocks a publish."),
        ],
    )
    mark(c, "screen-brands", "Brands — Memory", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 9, 11, "Decision Log", "AUDIT TRAIL", ACCENT_2, "12-audit.png",
        "A complete paper trail, without anyone having to write one.",
        [
            ("Cost sits next to the decision it paid for", "LLM spend is attributed per run right in this log, not hidden in a separate billing view — autonomy and cost are the same conversation."),
            ("Self-directed runs are flagged, not hidden", "A goal the system chose for itself carries the same “self” badge here as everywhere else — easy to audit which decisions were whose."),
        ],
        stat=("100%", "Of autonomous decisions logged with a reason", ACCENT_2),
    )
    mark(c, "screen-audit", "Decision Log", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 10, 11, "Settings — Autonomy Policy", "CONFIG", ACCENT, "13-settings.png",
        "Dial autonomy up or down with one toggle — the guardrails travel with it.",
        [
            ("Autonomy is a toggle, not a rebuild", "Flipping “Run fully autonomously” off doesn't change the agent pipeline at all — it just parks finished content as pending_review instead of publishing. One flag, same graph."),
            ("Guardrails are plain text, not a rules DSL", "Forbidden claims and banned phrases are one-per-line free text — QA is an LLM, so it can enforce a prose rule without a new schema every time policy changes."),
            ("The revision budget's consequence is spelled out inline", "The hint text under it explains arbitration in one sentence, right where you're setting the number — so changing it is an informed decision, not a guess."),
        ],
    )
    mark(c, "screen-settings", "Settings — Autonomy Policy", level=1)
    c.showPage()
    page += 1

    screen_slide(
        c, page, 11, 11, "Theming", "LIGHT MODE", PILL_RED, "15-light-theme.png",
        "Built for a daily driver, not a demo — day and night, zero relearning.",
        [
            ("A full token swap, not an inversion filter", "Every color on this screen is a deliberately chosen light-theme value — not a CSS filter over the dark palette — so contrast and hierarchy hold up exactly as intended."),
            ("Status colors are re-tuned, not reused verbatim", "Green/amber/red are darkened slightly for light backgrounds so they still meet contrast against white, rather than looking washed out."),
            ("Same data, same layout, zero relearning", "Nothing moves between themes — the only thing that changes is the palette, so switching mid-session costs the operator nothing."),
        ],
    )
    mark(c, "screen-theming", "Theming", level=1)
    c.showPage()
    page += 1

    closing_slide(c, page)
    mark(c, "closing", "Closing", level=0)
    c.showPage()

    c.save()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
