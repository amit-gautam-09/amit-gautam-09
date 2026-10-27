#!/usr/bin/env python3
"""Render the README locally and screenshot it, to check the cards before pushing.

    python3 scripts/preview.py              # the whole README, light and dark, every card finished
    python3 scripts/preview.py hero 1.2     # one card, light and dark, every animation paused at 1.2s

Pages go to .preview/ and screenshots to .shots/ (both ignored). The README pages lay README.md
out in a column as wide as GitHub's and pick each card's light or dark file the way GitHub does,
then screenshot with reduced motion forced, which shows every card in its finished state. The
paused pages inline one card and stop its animations at a given second, because headless
Chrome's clock can't be trusted to land anywhere in particular.
"""

import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PAGES_DIR, SHOTS_DIR = REPO / ".preview", REPO / ".shots"
THEMES = {"light": ("#ffffff", "#1f2328"), "dark": ("#0d1117", "#e6edf3")}
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "google-chrome", "chromium", "chrome"]
DARK_PICTURE = re.compile(r'<source media="\(prefers-color-scheme: dark\)" srcset="([^"]+)" /><img (alt="[^"]*") src="[^"]+"')
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def readme_page(theme):
    text = (REPO / "README.md").read_text(encoding="utf-8")
    if theme == "dark":
        text = DARK_PICTURE.sub(r'<img \2 src="\1"', text)
    blocks = []
    for block in text.split("\n\n"):
        block = LINK.sub(r'<a href="\2">\1</a>', block)
        blocks.append(block if block.lstrip().startswith("<") else f"<p>{block}</p>")
    background, ink = THEMES[theme]
    return (f'<!doctype html><meta charset="utf-8"><base href="../">'
            f"<style>body{{margin:0;background:{background};color:{ink};"
            f"font:16px/1.5 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif}}"
            f"main{{width:830px;margin:24px auto;padding:0 32px}}a{{color:#4493f8}}img{{max-width:100%}}"
            f"p{{margin:0 0 16px}}</style><main>{''.join(blocks)}</main>")


def paused_page(svg, seconds):
    return (f'<!doctype html><meta charset="utf-8"><style>body{{margin:0}}</style>{svg}'
            f"<script>document.getAnimations().forEach(a=>{{a.pause();a.currentTime={seconds * 1000:g}}})</script>")


def browser():
    for candidate in BROWSERS:
        if pathlib.Path(candidate).exists() or shutil.which(candidate):
            return shutil.which(candidate) or candidate
    return None


def screenshot(page, png, width, height, finished):
    exe = browser()
    if not exe:
        print("no Chrome or Edge found; open the pages in .preview/ yourself")
        return
    args = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
            f"--screenshot={png}", page.as_uri()]
    if finished:
        args.insert(1, "--force-prefers-reduced-motion")
    subprocess.run(args, capture_output=True, timeout=120)
    print(png if png.exists() else f"screenshot failed: {png}")


def main(argv):
    PAGES_DIR.mkdir(exist_ok=True)
    SHOTS_DIR.mkdir(exist_ok=True)
    for theme in THEMES:
        if len(argv) == 2:
            card, seconds = argv[0], float(argv[1])
            svg = (REPO / "assets" / f"{card}-{theme}.svg").read_text(encoding="utf-8")
            width, height = (int(float(v)) for v in re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
            page = PAGES_DIR / f"{card}-{theme}.html"
            page.write_text(paused_page(svg, seconds), encoding="utf-8")
            screenshot(page, SHOTS_DIR / f"{card}-{theme}-{seconds:g}s.png", width, height, finished=False)
        else:
            page = PAGES_DIR / f"{theme}.html"
            page.write_text(readme_page(theme), encoding="utf-8")
            screenshot(page, SHOTS_DIR / f"readme-{theme}.png", 900, 2450, finished=True)


if __name__ == "__main__":
    main(sys.argv[1:])
