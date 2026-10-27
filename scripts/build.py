#!/usr/bin/env python3
"""Draw every card the profile README shows, once per theme, into assets/.

    pip install fonttools
    python3 scripts/build.py            # all cards
    python3 scripts/build.py --views    # refresh only the profile-views pill (run on a schedule)

The facts are copied from the portfolio's content/data/*.json. When those change, change
them here too and rebuild; nothing links the two automatically.

Credit: the design follows amitgautamwork.com, itself inspired by aahil-khan.xyz (which drew
on yevtam.com and ajvadlaseen.com). The idea of a profile README drawn as animated SVG cards
comes from Aahil Khan's own profile README (github.com/aahil-khan/aahil-khan).
"""

import argparse
import math
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

from svgkit import EASE_OUT, Card, PALETTES, fit, measure, mono_width

REPO = pathlib.Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
VIEWS_FILE = REPO / "scripts" / "views.txt"
VIEWS_BADGE = "https://komarev.com/ghpvc/?username=amit-gautam-09"

WIDE = 840  # every full-width card; GitHub scales it to the README column


def ease_out_steps(target, steps):
    """Values on the way to target, slowing as they land, for a counter that settles."""
    return [target * (1 - (1 - k / steps) ** 3) for k in range(steps + 1)]


def back_to_back(start, count, every):
    return [start + k * every for k in range(count)]


# -------------------------------------------------------------------- hero

FUNNEL = [("prospects", 11_000), ("replies", 122), ("positive", 36), ("demos", 27), ("co-closed", 18)]

HERO_ALT = ("Amit Gautam, New Delhi, India. GTM engineer building outbound systems and AI workflows "
            "that turn cold lists into paying clients. A funnel.log window counts down this year's "
            "outbound: 11,000 prospects, 122 replies, 36 positive, 27 demos, 18 clients co-closed.")


def hero(theme):
    c = Card(WIDE, 404, theme, HERO_ALT, freeze=6)
    c.floor(2, 2, WIDE - 10, 394)
    left, column = 40, 430

    c.eyebrow(left, 58, "NEW DELHI, INDIA")
    rule_from = left + measure("NEW DELHI, INDIA", 11, 500, 0.16) + 14
    c.add("line", x1=float(rule_from), y1=54, x2=left + column, y2=54, stroke=c.colour("ink3"))

    # The name slides up out of a slot, one line after the other.
    size = fit(["AMIT", "GAUTAM"], column, start=100, weight=700, track=-0.03)
    for i, (word, baseline) in enumerate([("AMIT", 150), ("GAUTAM", 236)]):
        slot = c.new_id("slot")
        shape = c.add("clipPath", c.defs, id=slot)
        c.add("rect", shape, x=left - 12, y=float(baseline - size * 0.8), width=column + 24, height=float(size * 0.86))
        rider = c.group(c.group(clip_path=f"url(#{slot})"))
        c.text(left - 4, baseline, word, size=size, weight=700, track=-0.03, parent=rider)
        c.animate(rider, f"from{{transform:translateY({size * 0.9:.0f}px)}}to{{transform:none}}", 0.8,
                  ease=EASE_OUT, delay=0.1 + 0.14 * i)

    # The headline from the site; its middle line fades up, then a highlighter runs under it.
    lead, middle, tail = ("GTM engineer building", "outbound systems and AI workflows",
                          "that turn cold lists into paying clients.")
    fs = min(fit([lead, tail], column, start=22), fit([middle], column, start=22, weight=700))
    c.text(left, 294, lead, size=fs)
    marker = c.add("rect", x=left, y=329, width=float(measure(middle, fs, 700)), height=5, rx=1.5,
                   fill=c.colour("accent"))
    c.animate(marker, "from{transform:scaleX(0)}to{transform:scaleX(1)}", 0.6, ease=EASE_OUT, delay=1.3,
              origin="left")
    bold = c.group()
    c.text(left, 324, middle, size=fs, weight=700, parent=bold)
    c.animate(bold, "from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}", 0.5,
              ease=EASE_OUT, delay=0.7)
    c.text(left, 354, tail, size=fs)

    # funnel.log: each stage arrives, then its bar fills. Bars are log-scaled, or the last four
    # would vanish next to the first.
    wx, wy, ww, wh = 500, 92, 296, 250
    c.window(wx, wy, ww, wh, "funnel.log")
    c.text(wx + 20, wy + 58, "clickpost outbound, 2026", size=11, mono=True, ink="ink3")
    bar_x, bar_full = wx + 104, 108
    scale = math.log10(FUNNEL[0][1])
    for i, (stage, count) in enumerate(FUNNEL):
        y, at = wy + 92 + 27 * i, 0.9 + 0.2 * i
        final = i == len(FUNNEL) - 1
        row = c.group()
        c.text(wx + 20, y, stage, size=12, mono=True, ink="ink" if final else "ink2", parent=row)
        c.text(wx + ww - 20, y, f"{count:,}", size=12, mono=True, anchor="end", parent=row)
        c.animate(row, "from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}", 0.4,
                  ease=EASE_OUT, delay=at)
        bar = c.add("rect", x=bar_x, y=y - 10, width=float(max(10, bar_full * math.log10(count) / scale)), height=11,
                    rx=2.5, fill=c.colour("accent" if final else "sunk"), stroke=c.colour("line"), stroke_width=1.5)
        c.animate(bar, "from{transform:scaleX(0)}to{transform:scaleX(1)}", 0.6, ease=EASE_OUT, delay=at + 0.15,
                  origin="left")

    # A prompt waiting on the next follow-up.
    py = wy + wh - 24
    prompt = "> next: follow up"
    c.runs(wx + 20, py, [("> ", "ink3"), ("next: follow up", "ink2")], size=12)
    cursor = c.add("rect", x=float(wx + 22 + len(prompt) * mono_width(12)), y=py - 10, width=float(mono_width(12)),
                   height=13, fill=c.colour("ink"))
    c.animate(cursor, "0%{opacity:1}50%{opacity:0}100%{opacity:0}", 1.1, ease="steps(1,end)", loop=True, deco=True)
    return c.svg()


# ----------------------------------------------------------------- buttons

BUTTONS = {"site": "Portfolio", "resume": "Résumé PDF ↓", "linkedin": "LinkedIn ↗", "email": "Email ↗"}


def pill(c, width):
    return c.block(2, 4, width, 44, radius=22, drop=4)


def button(theme, key):
    label = BUTTONS[key]
    width = 22 + measure(label, 15, 500) + (52 if key == "site" else 22)
    c = Card(math.ceil(width + 8), 56, theme, label.rstrip(" ↓↗"), freeze=1)
    pill(c, width)
    c.text(22, 31, label, size=15, weight=500)
    if key == "site":
        cx = width - 15 - 6
        c.add("circle", cx=float(cx), cy=26, r=15, fill=c.colour("accent"), stroke=c.colour("line"), stroke_width=1.5)
        arrow = c.group()
        c.text(cx, 31.5, "→", size=16, weight=700, ink="on_accent", anchor="middle", parent=arrow)
        c.animate(arrow, "0%,100%{transform:translateX(0)}50%{transform:translateX(2.5px)}", 1.6,
                  ease="ease-in-out", loop=True, deco=True)
    return c.svg()


def views_pill(theme, views):
    label = f"{views:,} profile views"
    width = 42 + measure(label, 15, 500) + 22
    c = Card(math.ceil(width + 8), 56, theme, label, freeze=0)
    pill(c, width)
    ring = c.add("circle", cx=27, cy=26, r=5, fill=c.colour("accent"), opacity=0)
    c.animate(ring, "0%{opacity:.6;transform:scale(1)}100%{opacity:0;transform:scale(2.6)}", 2, ease="ease-out",
              loop=True, origin="center", deco=True)
    c.add("circle", cx=27, cy=26, r=5, fill=c.colour("accent"), stroke=c.colour("line"), stroke_width=1.5)
    c.text(42, 31, label, size=15, weight=500)
    return c.svg()


def draw_views():
    views = int(VIEWS_FILE.read_text().strip())
    for theme in PALETTES:
        (ASSETS / f"btn-views-{theme}.svg").write_text(views_pill(theme, views), encoding="utf-8")


def refresh_views():
    """Read the visit counter's badge and redraw the pill if the count went up."""
    request = urllib.request.Request(VIEWS_BADGE, headers={"User-Agent": "amit-gautam-09 profile build"})
    with urllib.request.urlopen(request, timeout=20) as response:
        badge = ET.fromstring(response.read())
    labels = [t.text.strip() for t in badge.iter("{http://www.w3.org/2000/svg}text") if t.text]
    latest = int(next(s for s in reversed(labels) if re.fullmatch(r"[\d,]+", s)).replace(",", ""))
    known = int(VIEWS_FILE.read_text().strip())
    if latest > known:
        VIEWS_FILE.write_text(f"{latest}\n")
        draw_views()
    print(f"profile views: {max(latest, known)}")


# ------------------------------------------------------------------- stats

STATS = [
    ("STUDENTS SCALED", 5000, "{:,.0f}", "+", "Distance Connect, as founder"),
    ("POSITIVE-REPLY RATE", 53.3, "{:.1f}%", "", "up from 8.3%, after a copy rewrite"),
    ("WEBHOOK EVENTS", 19.7, "{:.1f}K", "+", "handled by the outbound CRM"),
]
STATS_ALT = ("By the numbers: 5,000+ students scaled at Distance Connect, as founder. A 53.3% "
             "positive-reply rate, up from 8.3% after a copy rewrite. 19.7K+ webhook events handled "
             "by the outbound CRM.")


def stats(theme):
    c = Card(WIDE, 150, theme, STATS_ALT, freeze=5)
    gutter = 18
    width = (WIDE - 10 - gutter * (len(STATS) - 1)) / len(STATS)
    for i, (label, target, pattern, suffix, note) in enumerate(STATS):
        x = 2 + i * (width + gutter)
        c.block(x, 2, width, 136)
        c.eyebrow(x + 22, 34, label)
        values = [pattern.format(v) for v in ease_out_steps(target, 9)]
        values[-1] += suffix
        times = back_to_back(0.3 + 0.18 * i, len(values), 0.09)
        c.flipbook(x + 22, 90, values, times, times[-1] + 0.1, size=44, weight=700, track=-0.02, loop=False)
        c.text(x + 22, 118, note, size=12.5, ink="ink2")
    return c.svg()


# -------------------------------------------------------------------- work

def work_head(theme):
    c = Card(WIDE, 96, theme, "Selected work: four projects, each with a full write-up on amitgautamwork.com",
             freeze=1)
    c.eyebrow(4, 30, "SELECTED WORK")
    c.text(4, 70, "Selected projects", size=30, weight=700, track=-0.015)
    c.text(WIDE - 4, 70, "write-ups on amitgautamwork.com", size=13, ink="ink2", anchor="end")
    c.add("line", x1=4, y1=94, x2=WIDE - 4, y2=94, stroke=c.colour("line"), stroke_width=2)
    return c.svg()


TICK_X, TICK_SIZE = 548, 12          # the ticker column on each project card
TICK_ROWS = (62, 84, 106)
CYCLE, CLEAR = 10.0, 9.6             # tickers loop every CYCLE seconds and wipe at CLEAR


def project_card(theme, number, name, blurb, badge, meta, alt, freeze):
    """The left two thirds of a project card. Returns the card for its ticker to be added."""
    c = Card(WIDE, 142, theme, alt, freeze)
    c.block(2, 2, WIDE - 12, 128, drop=5)
    c.add("rect", x=24, y=24, width=34, height=24, rx=6, fill=c.colour("sunk"), stroke=c.colour("line"),
          stroke_width=1.5)
    c.text(41, 40.5, number, size=12, weight=700, anchor="middle")
    c.text(74, 44, name, size=24, weight=700, track=-0.01)
    badge_x = 74 + measure(name, 24, 700, -0.01) + 12
    badge_w = measure(badge, 9.5, 700, 0.08) + 20
    if badge_x + badge_w > TICK_X - 12 or 74 + measure(blurb, 14) > TICK_X - 12:
        raise ValueError(f"{name}: text runs into the ticker column")
    c.add("rect", x=float(badge_x), y=27, width=float(badge_w), height=20, rx=10, fill=c.colour("accent"),
          stroke=c.colour("line"), stroke_width=1.5)
    c.text(badge_x + 10, 40.6, badge, size=9.5, weight=700, ink="on_accent", track=0.08)
    c.text(74, 72, blurb, size=14, ink="ink2")
    c.text(74, 102, "  ·  ".join(meta), size=10, weight=500, ink="ink3", track=0.08)
    arrow = c.group()
    c.text(WIDE - 30, 42, "↗", size=20, weight=500, anchor="end", parent=arrow)
    c.animate(arrow, "0%,100%{transform:translate(0,0)}50%{transform:translate(2px,-2px)}", 2.4,
              ease="ease-in-out", loop=True, deco=True)
    return c


def tick(c, row, parts, at, column=0):
    """One ticker line that cuts in at `at` and clears with the rest at CLEAR."""
    if TICK_X + (column + sum(len(s) for s, _ in parts)) * mono_width(TICK_SIZE) > WIDE - 30:
        raise ValueError(f"ticker line too long: {parts}")
    line = c.runs(TICK_X + column * mono_width(TICK_SIZE), TICK_ROWS[row], parts, size=TICK_SIZE)
    c.show(line, [(at, CLEAR)], CYCLE)
    return line


def outbound_crm(theme):
    c = project_card(theme, "01", "Outbound CRM", "One record per prospect, across email and LinkedIn",
                     "USED DAILY · 5-PERSON TEAM", ["2026", "NEXT.JS", "TYPESCRIPT", "POSTGRESQL", "MCP"],
                     "01 Outbound CRM: one record per prospect, across email and LinkedIn. Used daily by a "
                     "5-person GTM team. Replies from Instantly and HeyReach merge into one record with an "
                     "owner.", freeze=5)
    tick(c, 0, [("in  ", "ink3"), ("instantly", "ink"), ("  reply", "ink2")], 0.3)
    tick(c, 1, [("in  ", "ink3"), ("heyreach", "ink"), ("   reply", "ink2")], 1.3)
    tick(c, 2, [("->  ", "ink3"), ("1 record", "hot"), (", owner + SLA", "ink2")], 2.4)
    return c.svg()


def shopflo(theme):
    c = project_card(theme, "02", "Shopflo lead pipeline", "A zero-cost replacement for a $250/month data tool",
                     "5 OF 8 CONVERTED", ["2026", "CLICKPOST", "INSTANTLY"],
                     "02 Shopflo lead pipeline: a zero-cost replacement for a $250/month data tool. 1,610 "
                     "checkout stores; 8 positive opportunities, 5 converted to paying clients.", freeze=6)
    cw = mono_width(TICK_SIZE)
    tick(c, 0, [("cost    ", "ink3"), ("$250/mo", "ink2")], 0.2)
    strike = c.add("rect", x=float(TICK_X + 8 * cw - 1), y=TICK_ROWS[0] - 5, width=float(7 * cw + 2), height=1.6,
                   fill=c.colour("hot"))
    c.show(strike, [(1.0, CLEAR)], CYCLE)
    tick(c, 0, [("$0", "ink")], 1.4, column=17)
    tick(c, 1, [("stores", "ink3")], 2.0)
    counts = [f"{v:,.0f}" for v in ease_out_steps(1610, 8)]
    counter = c.flipbook(TICK_X + 8 * cw, TICK_ROWS[1], counts, back_to_back(2.1, len(counts), 0.1), CYCLE,
                         size=TICK_SIZE, mono=True)
    c.show(counter, [(2.1, CLEAR)], CYCLE)
    tick(c, 2, [("opps    ", "ink3"), ("8", "ink"), ("   won ", "ink3"), ("5", "hot")], 3.4)
    return c.svg()


def eu_offer(theme):
    c = project_card(theme, "03", "EU withdrawal-rights offer", "A compliance offer built from the directive itself",
                     "3 QUALIFIED OPPS", ["2026", "CLICKPOST", "RESEARCH"],
                     "03 EU withdrawal-rights offer: a compliance offer built from EU Directive 2023/2673 "
                     "itself. 13,110 emails to 3,366 merchants; 36 replies, 3 qualified opportunities.", freeze=7)
    line, done = c.typewriter(TICK_X, TICK_ROWS[0], "$ read directive 2023/2673", 0.2, CYCLE, cps=18,
                              size=TICK_SIZE)
    c.show(line, [(0.0, CLEAR)], CYCLE)
    tick(c, 1, [("sent  ", "ink3"), ("13,110", "ink"), (" to ", "ink3"), ("3,366", "ink"), (" merchants", "ink2")],
         done + 0.5)
    tick(c, 2, [("reply ", "ink3"), ("36", "ink"), ("   opps ", "ink3"), ("3", "hot")], done + 1.5)
    return c.svg()


def distance_connect(theme):
    c = project_card(theme, "04", "Distance Connect", "Student–mentor EdTech, from zero to 5,000+ students",
                     "FOUNDER & CEO", ["2024", "PRODUCT", "PYTHON"],
                     "04 Distance Connect: student-mentor EdTech I founded and ran as CEO, from zero to "
                     "5,000+ students. Activation rose from 34% to 52%, 7-day retention from 42% to 58%.", freeze=7)
    cw = mono_width(TICK_SIZE)
    tick(c, 0, [("users", "ink3")], 0.2)
    fills = [f"[{'#' * k:<10}]" for k in range(0, 11, 2)]
    meter = c.flipbook(TICK_X + 8 * cw, TICK_ROWS[0], fills, back_to_back(0.3, len(fills), 0.25), CYCLE,
                       size=TICK_SIZE, mono=True, ink="ink2")
    c.show(meter, [(0.3, CLEAR)], CYCLE)
    tick(c, 0, [("5,000+", "ink")], 1.8, column=21)
    for row, label, before, after, at in [(1, "activ", "34%", "52%", 2.4), (2, "ret 7d", "42%", "58%", 3.4)]:
        tick(c, row, [(f"{label:<8}", "ink3"), (before, "ink2")], at)
        tick(c, row, [(" -> ", "ink3"), (after, "hot")], at + 0.5, column=11)
    return c.svg()


# ------------------------------------------------------------------- stack

# The site's toolbox (content/data/stack.json), in its own groups.
TOOLBOX = [
    ("GTM tools", [("Instantly", "instantly.png"), ("HeyReach", "heyreach.png"), ("Clay", "clay.png"),
                   ("Apollo.io", "apollo.png"), ("Apify", "apify.png"), ("Bitscale", "bitscale.png"),
                   ("Storeleads", "storeleads.png"), ("PhantomBuster", "phantombuster.png"),
                   ("OpenAI Ads", "openai.png"), ("Zoho Campaigns", "zoho.svg"), ("n8n", "n8n.svg"),
                   ("Zapier", "zapier.svg")]),
    ("Data & analytics", [("SQL", "lucide-database.svg"), ("Python", "python-original.svg"), ("Excel", "excel.png"),
                          ("Power BI", "powerbi.png"), ("Google Analytics", "googleanalytics.svg"),
                          ("Search Console", "googlesearchconsole.svg"), ("Mixpanel", "mixpanel.svg"),
                          ("Clarity", "clarity.png"), ("SimilarWeb", "similarweb.svg")]),
    ("Technology & AI", [("Next.js", "nextjs-original.svg"), ("TypeScript", "Typescript.svg"),
                         ("PostgreSQL", "postgresql-original.svg"), ("Neon", "neon.svg"),
                         ("Vercel", "vercel-original.svg"), ("Git", "git-original.svg"),
                         ("REST APIs", "lucide-braces.svg"), ("Webhooks", "lucide-webhook.svg"),
                         ("MCP", "modelcontextprotocol.svg"), ("Claude Code", "claudecode.svg"),
                         ("Prompt Engineering", "lucide-wand-sparkles.svg")]),
    ("Sales & GTM", [("ICP Building", "lucide-target.svg"), ("Lead Generation", "lucide-magnet.svg"),
                     ("Lead Scoring", "lucide-gauge.svg"), ("Positioning & Messaging", "lucide-megaphone.svg"),
                     ("Cross-Functional Collaboration", "lucide-users.svg")]),
]
# Near-black marks, repainted in the ink colour on the dark theme so they stay visible.
INK_MARKS = {"nextjs-original.svg", "vercel-original.svg", "modelcontextprotocol.svg", "openai.png", "bitscale.png",
             "similarweb.svg"}

CHAI = ["  .------.", "  |      |]", "  \\      /", "   `----'"]
STEAM = [("  ( (", "   ) )"), ("   ) )", "  ( ("), ("  ) (", "   ( )")]

CHIP_H, CHIP_GAP, ROW_GAP = 30, 12, 42


def lay_out_toolbox(left, right, top):
    """Flow each group's chips into rows. Returns label positions, chip boxes and the bottom edge."""
    labels, chips = [], []
    y = top
    for group, tools in TOOLBOX:
        labels.append((group.upper(), y))
        x, y = left, y + 14
        for name, logo in tools:
            w = measure(name, 13, 500) + 48
            if x + w > right:
                x, y = left, y + ROW_GAP
            chips.append((x, y, w, name, logo))
            x += w + CHIP_GAP
        y += CHIP_H + 30
    return labels, chips, y - 30


def stack(theme):
    labels, chips, bottom = lay_out_toolbox(40, WIDE - 48, 122)
    every = ", ".join(name for _, tools in TOOLBOX for name, _ in tools)
    c = Card(WIDE, math.ceil(bottom + 44), theme, f"What I build with: {every}. A cup of chai steams in the corner.",
             freeze=5)
    c.floor(2, 2, WIDE - 10, c.height - 10)
    c.eyebrow(40, 54, "TOOLBOX")
    c.text(40, 88, "What I build with", size=28, weight=700, track=-0.01)
    for label, y in labels:
        c.text(40, y, label, size=10.5, weight=500, ink="ink2", track=0.12)
    for n, (x, y, w, name, logo) in enumerate(chips):
        chip = c.group()
        c.block(x, y, w, CHIP_H, radius=8, drop=3, stroke=1.8, parent=chip)
        c.logo(x + 11, y + 7, 16, logo, tint=theme == "dark" and (logo in INK_MARKS or logo.startswith("lucide-")),
               parent=chip)
        c.text(x + 35, y + 19.5, name, size=13, weight=500, parent=chip)
        c.animate(chip, "from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}", 0.45,
                  ease=EASE_OUT, delay=0.15 + 0.025 * n)

    # Chai in the top corner, steam curling through three shapes.
    size, leading = 13, 15
    x = WIDE - 52 - mono_width(size) * 11
    for i, row in enumerate(CHAI):
        c.text(x, 66 + leading * i, row, size=size, mono=True, ink="ink2")
    beat = 0.6
    for k, (upper, lower) in enumerate(STEAM):
        puff = c.group()
        c.text(x + 2 * mono_width(size), 66 - 2 * leading, upper, size=size, mono=True, ink="ink3", parent=puff)
        c.text(x + 2 * mono_width(size), 66 - leading, lower, size=size, mono=True, ink="ink3", parent=puff)
        c.show(puff, [(k * beat, (k + 1) * beat)], beat * len(STEAM))
    return c.svg()


# ------------------------------------------------------------------ footer

ENVELOPE = [" ______ ", "|\\    /|", "|_\\__/_|"]


def footer(theme):
    c = Card(WIDE, 222, theme, "Let's build something. Happy to talk GTM engineering, outbound systems and AI "
             "workflows; email is the fastest way to reach me. An envelope flies into an inbox and a reply pops "
             "out.", freeze=7.6)
    c.block(2, 2, WIDE - 10, 212, fill="band")
    c.eyebrow(40, 54, "CONTACT")
    c.text(40, 96, "Let’s build something.", size=34, weight=700, track=-0.02)
    c.text(40, 124, "Happy to talk GTM engineering, outbound systems and AI workflows. Email is fastest.",
           size=14, ink="ink2")

    size, leading = 13, 14
    ground = 198
    c.add("line", x1=40, y1=ground, x2=WIDE - 200, y2=ground, stroke=c.colour("ink3"), stroke_width=1.5,
          stroke_dasharray="2 7", stroke_linecap="round")
    tray_x, tray_w = WIDE - 182, 120
    c.add("path", d=f"M{tray_x} {ground - 22}V{ground}H{tray_x + tray_w}V{ground - 22}", fill="none",
          stroke=c.colour("line"), stroke_width=2, stroke_linejoin="round")
    c.text(tray_x + tray_w / 2, ground - 7, "inbox", size=11, mono=True, ink="ink3", anchor="middle")

    # The envelope flies in from the left, drops into the tray and is gone; a reply pops out.
    cycle, lands = 10.0, 4.6
    flight = c.group()
    wobble = c.group(flight)
    for i, row in enumerate(ENVELOPE):
        c.text(0, ground - 44 + leading * i, row, size=size, mono=True, parent=wobble)
    stop_x = tray_x + (tray_w - 8 * mono_width(size)) / 2
    c.animate(flight, f"0%{{transform:translate(40px,0);opacity:1}}"
                      f"{100 * lands / cycle:.2f}%{{transform:translate({stop_x:.1f}px,0);opacity:1}}"
                      f"{100 * (lands + 0.5) / cycle:.2f}%,100%{{transform:translate({stop_x:.1f}px,14px);opacity:0}}",
              cycle, ease="cubic-bezier(0.45,0,0.25,1)", loop=True)
    c.animate(wobble, "0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}", 0.5, ease="ease-in-out",
              loop=True, deco=True)

    reply = "+1 positive reply"
    bubble = c.group()
    centre, base = tray_x + tray_w / 2, ground - 52
    bw = len(reply) * mono_width(12) + 20
    c.add("rect", bubble, x=float(centre - bw / 2), y=base - 15, width=float(bw), height=22, rx=11,
          fill=c.colour("accent"), stroke=c.colour("line"), stroke_width=1.5)
    c.text(centre, base, reply, size=12, mono=True, ink="on_accent", anchor="middle", parent=bubble)
    c.show(bubble, [(lands + 0.5, cycle - 0.4)], cycle)
    return c.svg()


# -------------------------------------------------------------------- main

CARDS = {
    "hero": hero, "stats": stats, "work-head": work_head, "work-outbound-crm": outbound_crm,
    "work-shopflo": shopflo, "work-eu-offer": eu_offer, "work-distance-connect": distance_connect,
    "stack": stack, "footer": footer,
}


def build_all():
    ASSETS.mkdir(exist_ok=True)
    for stale in ASSETS.glob("*.svg"):
        stale.unlink()
    for theme in PALETTES:
        for name, draw in CARDS.items():
            (ASSETS / f"{name}-{theme}.svg").write_text(draw(theme), encoding="utf-8")
        for key in BUTTONS:
            (ASSETS / f"btn-{key}-{theme}.svg").write_text(button(theme, key), encoding="utf-8")
    draw_views()
    for path in sorted(ASSETS.glob("*.svg")):
        print(f"{path.stat().st_size // 1024:>4} KB  {path.name}")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cli.add_argument("--views", action="store_true", help="only refresh the profile-views pill")
    if cli.parse_args().views:
        refresh_views()
    else:
        build_all()
