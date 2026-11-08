#!/usr/bin/env python3
"""Generate a custom-colored GitHub contribution calendar as an SVG.

Usage:
    GITHUB_TOKEN=... python3 scripts/contrib_graph.py ShreyaAjith134 assets/contributions.svg
    python3 scripts/contrib_graph.py --demo assets/demo.svg      # random data, for testing only
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

# ---- palette ---------------------------------------------------------------
BG = "#0e1117"
EMPTY = "#171b22"
LOW = (0xF8, 0xC8, 0xDC)    # baby pink
HIGH = (0xF9, 0x03, 0x7B)   # #f9037b
LABEL = "#8b949e"
LEVELS = 4

CELL, GAP = 12, 4
STEP = CELL + GAP
LEFT, TOP = 40, 30

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def lerp_hex(t):
    r, g, b = (round(LOW[i] + (HIGH[i] - LOW[i]) * t) for i in range(3))
    return f"#{r:02x}{g:02x}{b:02x}"


LEVEL_COLORS = [lerp_hex(i / (LEVELS - 1)) for i in range(LEVELS)]


def fetch(login):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "contrib-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in weeks]


def demo():
    random.seed(7)
    start = date.today() - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks, d = [], start
    while d <= date.today():
        week = []
        for _ in range(7):
            n = random.choice([0, 0, 0, 0, 1, 2, 4, 7, 11]) if d <= date.today() else 0
            week.append((d.isoformat(), n))
            d += timedelta(days=1)
        weeks.append(week)
    return weeks


def level(n, peak):
    if n <= 0:
        return 0
    return min(LEVELS, max(1, math.ceil(LEVELS * n / peak)))


def render(weeks):
    peak = max((n for w in weeks for _, n in w), default=0) or 1
    width = LEFT + len(weeks) * STEP + 16
    height = TOP + 7 * STEP + 14
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contribution graph">',
        f'<rect width="{width}" height="{height}" fill="{BG}"/>',
    ]
    font = 'font-family="Verdana, DejaVu Sans, sans-serif" font-size="10"'

    # weekday labels (Mon / Wed / Fri)
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = TOP + row * STEP + CELL - 2
        out.append(f'<text x="4" y="{y}" fill="{LABEL}" {font}>{name}</text>')

    last_month = None
    for ci, week in enumerate(weeks):
        x = LEFT + ci * STEP
        first = date.fromisoformat(week[0][0])
        if first.month != last_month and first.day <= 14 or (ci == 0):
            if first.month != last_month:
                out.append(f'<text x="{x}" y="{TOP - 10}" fill="{LABEL}" {font}>{first.strftime("%b")}</text>')
                last_month = first.month
        for ri, (d, n) in enumerate(week):
            lv = level(n, peak)
            color = EMPTY if lv == 0 else LEVEL_COLORS[lv - 1]
            y = TOP + ri * STEP
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                f'<title>{n} contributions on {d}</title></rect>'
            )
    out.append("</svg>")
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--demo":
        weeks, dest = demo(), args[1]
    else:
        weeks, dest = fetch(args[0]), args[1]
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w") as f:
        f.write(render(weeks))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()