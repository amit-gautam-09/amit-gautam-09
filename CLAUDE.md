# GitHub profile README

Amit Gautam's GitHub profile page. GitHub shows `README.md` from the repo named exactly after the
username (`amit-gautam-09/amit-gautam-09`) at the top of github.com/amit-gautam-09. Every section is
an SVG card drawn by `scripts/build.py`, in a light and a dark file. The README picks between
them with `<picture><source media="(prefers-color-scheme: dark)">`.

The portfolio site this mirrors is the sibling folder `../Amit Portfolio` (amitgautamwork.com).

## Commands

```bash
python -m pip install --user fonttools             # on this laptop: add --no-binary fonttools (see below)
python scripts/build.py                            # redraw every card into assets/
python scripts/build.py --views                    # refresh only the views pill (the workflow runs this)
python scripts/preview.py                          # screenshot the whole README, light + dark, into .shots/
python scripts/preview.py hero 1.2                 # screenshot one card with its animations paused at 1.2s
```

Windows Application Control on this laptop blocks fontTools' compiled extension ("DLL load failed
... An Application Control policy has blocked this file"). The pure-Python build works:
`python -m pip install --user --force-reinstall --no-deps --no-binary fonttools fonttools`.

The build is deterministic: run it twice and nothing changes. If `git status` shows cards you
didn't mean to touch after a build, something in the build has become non-deterministic. Fix that
rather than committing the noise.

## Rules that are easy to get wrong here

- **Keep the credit.** The last line of `README.md` and the header of `scripts/build.py` credit
  Aahil Khan, matching the portfolio's footer, README and LICENSE. Same wording as the site:
  "Design inspired by aahil-khan.xyz, which drew on yevtam.com (dock, cursor) and ajvadlaseen.com
  (type, borders, shadows)."
- **No code from `aahil-khan/aahil-khan`.** That repo has no licence, so its code is all rights
  reserved. The generator was rewritten from scratch on 2026-10-27 so none of it remains. Don't
  fork it, copy from it, or "port" a piece of it. Ideas are fine; code isn't. (portfolio-canvas,
  the site's upstream, is MIT and is a different repo.)
- **Facts come from the portfolio.** Every number, project and tool here is copied from
  `../Amit Portfolio/content/data/*.json`. Nothing links them automatically. When the site
  changes, update `scripts/build.py` to match and rebuild. Never invent or round a figure the
  site doesn't state.
- **Colours come from the site**: `design/DIRECTION.md` (cream) and `content/themes.ts`
  (tokyo-night) in the portfolio, copied into `PALETTES` in `scripts/svgkit.py`. Accent is a
  highlight, not a surface.
- **Both themes, every time.** Each card is drawn once per palette. Check dark as carefully as
  light; near-black logos need to be in `INK_MARKS` to stay visible there.
- **Reduced motion is one rule.** Each `Card` has a `freeze` time, and reduced motion pauses every
  animation at that moment. Pick a `freeze` after the card has fully arrived. Mark decorative
  loops `deco=True` so they switch off instead.
- **Ticker lines must fit.** `project_card` and `tick` raise if text runs into the ticker column
  or off the card. Shorten the copy; don't remove the check.
- **Fonts are committed** in `fonts/` with their OFL licences, which must stay beside them.
  The build needs no network apart from `--views`.
- **`scripts/views.txt` is owned by the workflow** (`.github/workflows/views.yml`, four times a day).
  Don't hand-edit it except to correct it.

## Checking a change

After any visual change, render it and look at the screenshots before pushing:

```bash
python scripts/build.py && python scripts/preview.py      # then read .shots/readme-light.png and -dark.png
python scripts/preview.py work-shopflo 2.4                # a card mid-animation, both themes
```

The README screenshots force reduced motion, which shows every card in its finished state; that
is also exactly what a reader with reduced motion sees. Card names are the `CARDS` keys in
`scripts/build.py`. Don't use Chrome's `--virtual-time-budget` to catch a moment: it is not
reliable for SVGs inside `<img>`.

## Deploying

Push to `main`; the profile updates within a minute or two. There is no build step on GitHub
except the views workflow. A profile repo only renders from its default branch, so work goes
straight to `main`. Commit only when Amit asks.
