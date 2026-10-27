"""A small kit for drawing the README's cards as standalone SVG files.

GitHub shows each card through <img>, and an SVG loaded that way can't fetch anything: no web
fonts, no scripts. So every card carries its own fonts, trimmed to the glyphs it uses, and all
motion is plain CSS keyframes. Readers who ask for reduced motion get each card paused at one
chosen moment (`freeze`), with purely decorative loops switched off.

Cards are built as ElementTree documents, then serialised once at the end.
"""

import base64
import io
import itertools
import pathlib
import xml.etree.ElementTree as ET
from collections import defaultdict

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

REPO = pathlib.Path(__file__).resolve().parent.parent
FONTS = REPO / "fonts"
LOGOS = REPO / "logos"

SVG_NS = "http://www.w3.org/2000/svg"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# Static cuts of the two families the site uses. OFL; licences sit next to the files.
FACE_FILES = {
    ("Grotesk", 400): "SpaceGrotesk-Regular.ttf",
    ("Grotesk", 500): "SpaceGrotesk-Medium.ttf",
    ("Grotesk", 700): "SpaceGrotesk-Bold.ttf",
    ("Mono", 400): "SpaceMono-Regular.ttf",
}

# The site's light theme (cream) and its dark theme (Tokyo Night), from design/DIRECTION.md
# and content/themes.ts in the portfolio repo. `hot` is a second, rarer highlight for the
# one number in a ticker that matters; `band` is the footer's recessed slab.
PALETTES = {
    "light": {
        "floor": "#F7F5EE", "glow": "rgba(255,255,255,0.75)", "grid": "rgba(22,22,22,0.06)",
        "face": "#FFFFFF", "sunk": "#F4F2EA", "titlebar": "#FDF7C4", "band": "#ECE9E0",
        "ink": "#161616", "ink2": "rgba(22,22,22,0.74)", "ink3": "rgba(22,22,22,0.60)",
        "accent": "#FACC00", "on_accent": "#161616", "line": "#161616", "hot": "#C2410C",
    },
    "dark": {
        "floor": "#1A1B26", "glow": "rgba(192,202,245,0.05)", "grid": "rgba(192,202,245,0.07)",
        "face": "#16161E", "sunk": "#1F2335", "titlebar": "#24283B", "band": "#222433",
        "ink": "#C0CAF5", "ink2": "#A9B1D6", "ink3": "#949EC8",
        "accent": "#E0AF68", "on_accent": "#1A1B26", "line": "#C0CAF5", "hot": "#FF9E64",
    },
}

EASE_OUT = "cubic-bezier(0.16,1,0.3,1)"  # the site's one deceleration curve


def num(v):
    """Attribute value: numbers trimmed to two decimals, everything else as is."""
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def pct(t, cycle):
    return f"{min(t / cycle, 1) * 100:.3f}".rstrip("0").rstrip(".") + "%"


# ------------------------------------------------------------------- fonts

class Face:
    """One font file: advance widths for layout, and @font-face CSS for a set of glyphs."""

    _loaded = {}

    @classmethod
    def of(cls, family, weight):
        key = (family, weight)
        if key not in cls._loaded:
            cls._loaded[key] = cls(FONTS / FACE_FILES[key])
        return cls._loaded[key]

    def __init__(self, path):
        self.path = path
        font = TTFont(path)
        self.em = font["head"].unitsPerEm
        metrics = font["hmtx"].metrics
        self.widths = {cp: metrics[glyph][0] for cp, glyph in font.getBestCmap().items()}
        self.missing = metrics[".notdef"][0]

    def measure(self, text, size, track=0.0):
        """Rendered width in px. Kerning is stripped from the embedded fonts, so this is exact."""
        units = sum(self.widths.get(ord(ch), self.missing) for ch in text)
        return size * (units / self.em + track * len(text))

    def css(self, family, weight, chars):
        # Keep the file's own timestamp, or every build rewrites every card.
        font = TTFont(self.path, recalcTimestamp=False)
        options = Options()
        options.layout_features = []   # no kerning or ligatures: what we measure is what renders
        options.hinting = False
        subsetter = Subsetter(options=options)
        subsetter.populate(text="".join(sorted(chars)))
        subsetter.subset(font)
        font.flavor = "woff"
        out = io.BytesIO()
        font.save(out)
        data = base64.b64encode(out.getvalue()).decode("ascii")
        return (f"@font-face{{font-family:{family};font-weight:{weight};"
                f"src:url(data:font/woff;base64,{data}) format('woff')}}")


def measure(text, size, weight=400, track=0.0, mono=False):
    face = Face.of("Mono", 400) if mono else Face.of("Grotesk", weight)
    return face.measure(text, size, track)


def mono_width(size):
    """Space Mono is monospaced, so one figure's advance is every character's."""
    return measure("0", size, mono=True)


def fit(lines, width, *, start, weight=400, track=0.0):
    """The largest size, at most `start`, in quarter pixels, at which every line fits `width`."""
    widest = max(measure(line, 1, weight, track) for line in lines)
    return min(start, int(width / widest * 4) / 4)


# -------------------------------------------------------------------- card

class Card:
    """One SVG file under construction."""

    def __init__(self, width, height, theme, alt, freeze):
        self.width, self.height = width, height
        self.theme = theme
        self.colours = PALETTES[theme]
        self.freeze = freeze
        self.rules = []
        self.glyphs = defaultdict(set)
        self._serial = itertools.count()
        self.root = ET.Element("svg", {
            "xmlns": SVG_NS, "width": num(width), "height": num(height),
            "viewBox": f"0 0 {num(width)} {num(height)}", "role": "img", "aria-labelledby": "alt",
        })
        ET.SubElement(self.root, "title", id="alt").text = alt
        self.defs = ET.SubElement(self.root, "defs")
        self.style = ET.SubElement(self.root, "style")

    # -- basics

    def colour(self, token):
        return self.colours.get(token, token)

    def new_id(self, stem):
        return f"{stem}{next(self._serial)}"

    def add(self, tag, parent=None, **attrs):
        """Append an element. `stroke_width` becomes stroke-width; a trailing _ is dropped."""
        clean = {k.rstrip("_").replace("_", "-"): num(v) for k, v in attrs.items() if v is not None}
        return ET.SubElement(self.root if parent is None else parent, tag, clean)

    def group(self, parent=None, **attrs):
        return self.add("g", parent, **attrs)

    def text(self, x, y, s, *, size, weight=400, mono=False, ink="ink", track=0.0, anchor=None,
             parent=None, **attrs):
        family, weight = ("Mono", 400) if mono else ("Grotesk", weight)
        self.glyphs[(family, weight)].update(s)
        el = self.add("text", parent, x=float(x), y=float(y), font_family=family, font_weight=weight,
                      font_size=size, fill=self.colour(ink), letter_spacing=f"{track}em" if track else None,
                      text_anchor=anchor, **attrs)
        el.set(XML_SPACE, "preserve")
        el.text = s
        return el

    def runs(self, x, y, parts, *, size, parent=None):
        """A monospace line in several colours; parts are (text, colour) pairs."""
        el = self.text(x, y, "", size=size, mono=True, parent=parent)
        for s, ink in parts:
            self.glyphs[("Mono", 400)].update(s)
            ET.SubElement(el, "tspan", fill=self.colour(ink)).text = s
        return el

    def eyebrow(self, x, y, s, parent=None):
        return self.text(x, y, s, size=11, weight=500, ink="ink2", track=0.16, parent=parent)

    # -- shapes

    def block(self, x, y, w, h, *, fill="face", radius=14, drop=6, stroke=2.0, parent=None):
        """A neobrutalist block: a hard offset shadow, then the bordered face on top."""
        self.add("rect", parent, x=float(x + drop), y=float(y + drop), width=float(w), height=float(h),
                 rx=radius, fill=self.colour("line"))
        return self.add("rect", parent, x=float(x), y=float(y), width=float(w), height=float(h), rx=radius,
                        fill=self.colour(fill), stroke=self.colour("line"), stroke_width=stroke)

    def floor(self, x, y, w, h, *, cell=40):
        """The site's canvas floor: warm paper, a faint grid and a soft light from above."""
        self.block(x, y, w, h, fill="floor")
        grid, glow, clip = self.new_id("grid"), self.new_id("glow"), self.new_id("clip")
        pattern = self.add("pattern", self.defs, id=grid, width=cell, height=cell,
                           patternUnits="userSpaceOnUse", x=x, y=y)
        self.add("path", pattern, d=f"M0 0.5H{cell}M0.5 0V{cell}", stroke=self.colour("grid"), fill="none")
        light = self.add("radialGradient", self.defs, id=glow, cx="50%", cy="0%", r="75%")
        self.add("stop", light, offset="0", stop_color=self.colour("glow"))
        self.add("stop", light, offset="1", stop_color=self.colour("glow"), stop_opacity="0")
        shape = self.add("clipPath", self.defs, id=clip)
        self.add("rect", shape, x=x, y=y, width=w, height=h, rx=14)
        inside = self.group(clip_path=f"url(#{clip})")
        self.add("rect", inside, x=x, y=y, width=w, height=h, fill=f"url(#{grid})")
        self.add("rect", inside, x=x, y=y, width=w, height=h, fill=f"url(#{glow})")
        self.add("rect", x=x, y=y, width=w, height=h, rx=14, fill="none", stroke=self.colour("line"),
                 stroke_width=2)

    def window(self, x, y, w, h, title, *, bar=32):
        """A block with a title bar and three empty dots, like the site's canvas windows."""
        self.block(x, y, w, h)
        clip = self.new_id("win")
        shape = self.add("clipPath", self.defs, id=clip)
        self.add("rect", shape, x=x, y=y, width=w, height=h, rx=14)
        self.add("rect", self.group(clip_path=f"url(#{clip})"), x=x, y=y, width=w, height=bar,
                 fill=self.colour("titlebar"))
        self.add("line", x1=x, y1=y + bar, x2=x + w, y2=y + bar, stroke=self.colour("line"), stroke_width=2)
        self.add("rect", x=x, y=y, width=w, height=h, rx=14, fill="none", stroke=self.colour("line"),
                 stroke_width=2)
        for i in range(3):
            self.add("circle", cx=x + 18 + 15 * i, cy=y + bar / 2, r=4.2, fill="none",
                     stroke=self.colour("line"), stroke_width=1.6)
        self.text(x + 70, y + bar / 2 + 4.5, title, size=12.5, weight=500, ink="ink2")

    def logo(self, x, y, size, filename, *, tint=False, parent=None):
        """A logo file embedded as a data URI. `tint` repaints a near-black mark in ink."""
        data = (LOGOS / filename).read_bytes()
        mime = "image/png" if filename.endswith(".png") else "image/svg+xml"
        href = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        return self.add("image", parent, x=float(x), y=float(y), width=size, height=size, href=href,
                        filter=f"url(#{self.ink_filter()})" if tint else None)

    def ink_filter(self):
        if not hasattr(self, "_ink_filter"):
            self._ink_filter = self.new_id("ink")
            f = self.add("filter", self.defs, id=self._ink_filter)
            self.add("feFlood", f, flood_color=self.colour("ink"), result="paint")
            self.add("feComposite", f, in_="paint", in2="SourceAlpha", operator="in")
        return self._ink_filter

    # -- motion

    def animate(self, el, frames, seconds, *, ease="linear", delay=0.0, loop=False, origin=None, deco=False):
        """Run one keyframe animation on el. `deco` marks loops that reduced motion turns off."""
        name = self.new_id("m")
        self.rules.append(f"@keyframes {name}{{{frames}}}")
        style = [f"animation:{name} {seconds:g}s {ease} {delay:g}s {'infinite' if loop else '1'} both"]
        if origin:
            style.append(f"transform-box:fill-box;transform-origin:{origin}")
        if el.get("style"):
            style.insert(0, el.get("style"))
        el.set("style", ";".join(style))
        if deco:
            el.set("class", "deco")
        return el

    def show(self, el, windows, cycle, *, loop=True):
        """Show el only inside (start, stop) windows of a cycle, cutting in and out.

        stop=None keeps it to the end of the cycle."""
        def visible(t):
            return any(a <= t and (b is None or t < b) for a, b in windows)
        moments = sorted({0.0, float(cycle)} | {t for w in windows for t in w if t is not None})
        frames = "".join(f"{pct(t, cycle)}{{opacity:{int(visible(t))}}}" for t in moments)
        return self.animate(el, frames, cycle, ease="steps(1,end)", loop=loop)

    def flipbook(self, x, y, frames, times, cycle, *, size, loop=True, parent=None, **style):
        """frames[i] from times[i] until the next: a strip of lines, one line visible at a time.

        Frames are strings, or lists of (text, colour) runs for monospace lines."""
        pitch = size * 1.7
        mono = style.get("mono", False) or not isinstance(frames[0], str)
        widest = max(measure(f if isinstance(f, str) else "".join(s for s, _ in f), size,
                             style.get("weight", 400), style.get("track", 0.0), mono) for f in frames)
        clip = self.new_id("strip")
        slot = self.add("clipPath", self.defs, id=clip)
        self.add("rect", slot, x=float(x - 2), y=float(y - size), width=float(widest + 4), height=float(size * 1.3))
        holder = self.group(parent, clip_path=f"url(#{clip})")
        strip = self.group(holder)
        for i, f in enumerate(frames):
            if isinstance(f, str):
                self.text(x, y + i * pitch, f, size=size, parent=strip, **style)
            else:
                self.runs(x, y + i * pitch, f, size=size, parent=strip)
        stops = [(0.0, 0)] + [(t, i) for i, t in enumerate(times)] + [(float(cycle), len(frames) - 1)]
        keyframes = "".join(f"{pct(t, cycle)}{{transform:translateY({-i * pitch:.2f}px)}}" for t, i in stops)
        self.animate(strip, keyframes, cycle, ease="steps(1,end)", loop=loop)
        return holder

    def typewriter(self, x, y, s, start, cycle, *, cps, size, cover="face", ink="ink", parent=None):
        """Type s from `start` by drawing it whole, then pulling back a cover in the card's colour
        one character width per step. Returns the line and the moment it finishes."""
        line = self.group(parent)
        self.text(x, y, s, size=size, mono=True, ink=ink, parent=line)
        done = start + len(s) / cps
        sheet = self.add("rect", line, x=float(x - 1), y=float(y - size), width=float(len(s) * mono_width(size) + 2),
                         height=float(size * 1.4), fill=self.colour(cover))
        self.animate(sheet, f"0%,{pct(start, cycle)}{{transform:scaleX(1);animation-timing-function:steps({len(s)},end)}}"
                            f"{pct(done, cycle)},100%{{transform:scaleX(0)}}", cycle, loop=True, origin="right")
        return line, done

    # -- output

    def svg(self):
        faces = [Face.of(*key).css(*key, chars) for key, chars in sorted(self.glyphs.items()) if chars]
        still = (f"@media (prefers-reduced-motion: reduce){{"
                 f"*{{animation-delay:-{self.freeze:g}s!important;animation-play-state:paused!important}}"
                 f".deco{{animation:none!important}}}}")
        self.style.text = "\n".join(faces + self.rules + [still])
        return ET.tostring(self.root, encoding="unicode") + "\n"
