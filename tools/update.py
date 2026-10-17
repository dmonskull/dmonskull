"""daily job: draws the stats card"""

import argparse
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from svgtext import (ACCENT, FAINT, LINE, LINE_STRONG, MUTED, TEXT, backdrop, face, svg, text, width)

QUERY = """
query ($login: String!) {
  user(login: $login) {
    login
    contributionsCollection { contributionCalendar { totalContributions } }
    everything: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name description url pushedAt isArchived stargazerCount
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
        latestRelease { tagName publishedAt }
      }
    }
  }
}
"""


def token():
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    return t or subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def fetch(login):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token()}", "Content-Type": "application/json", "User-Agent": f"{login}-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise SystemExit(f"github said no: {out['errors']}")
    return out["data"]["user"]


def own_projects(user):
    """public repos that are actual projects (not this profile repo or the site repo)"""
    skip = {user["login"].lower(), f"{user['login'].lower()}.github.io"}
    return [r for r in user["repositories"]["nodes"] if r["name"].lower() not in skip]


def visible(color):
    """some language colors (lua is navy) vanish on the dark card, so lift the darkest ones toward white"""
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lum = .2126 * r + .7152 * g + .0722 * b
    if lum >= .25:
        return color
    k = .55 * (1 - lum / .25)
    return "#" + "".join(f"{round((c + (1 - c) * k) * 255):02x}" for c in (r, g, b))


def stats_card(user, now):
    repos = own_projects(user)
    w, h, pad = 1200, 360, 64
    mono = face("mono", wght=500)
    big = face("archivo", wght=800, wdth=112)

    releases = [(r["latestRelease"], r["name"]) for r in repos if r["latestRelease"]]
    latest = max(releases, key=lambda x: x[0]["publishedAt"], default=None)
    stats = [
        (f"{user['contributionsCollection']['contributionCalendar']['totalContributions']:,}", "CONTRIBUTIONS, PAST YEAR"),
        (f"{sum(r['stargazerCount'] for r in repos):,}", "STARS"),
        (f"{user['everything']['totalCount']:,}", "PUBLIC REPOS"),
        (latest[0]["tagName"], f"LATEST: {latest[1].upper()}") if latest else ("none", "LATEST RELEASE"),
    ]

    out = [backdrop(w, h, w - 120, h + 80, uid="s")]
    out.append(f'<circle class="ring" cx="{pad + 6}" cy="77" r="5" fill="{ACCENT}"/><circle cx="{pad + 6}" cy="77" r="5" fill="{ACCENT}"/>')
    out.append(text(mono, "GITHUB STATS", pad + 22, 83, 16, MUTED, tracking=.08))
    out.append(text(mono, f"UPDATED {now:%b} {now.day}, {now.year}".upper(), w - pad, 83, 15, FAINT, tracking=.08, anchor="end"))

    col = (w - 2 * pad) / len(stats)
    for i, (value, label) in enumerate(stats):
        x = pad + i * col
        size = 62
        while width(big, value, size, -.02) > col - 24 and size > 24:
            size -= 2
        out.append(text(big, value, x, 172, size, TEXT, tracking=-.02))
        out.append(text(mono, label, x, 206, 14, MUTED, tracking=.06))
        if i:
            out.append(f'<path d="M{x - 20:.0f} 118V208" stroke="{LINE}"/>')

    # top languages by code size
    sizes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]
            sizes.setdefault(n["name"], [0, visible(n["color"]) if n["color"] else FAINT])[0] += e["size"]
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1][0])
    total = sum(v[0] for _, v in ranked) or 1
    top = [(name, v[0] / total, v[1]) for name, v in ranked[:5]]
    rest = 1 - sum(p for _, p, _ in top)
    if rest > .005:
        top.append(("Other", rest, LINE_STRONG))

    out.append(f'<path d="M{pad} 240H{w - pad}" stroke="{LINE}" stroke-dasharray="4 5"/>')
    out.append(text(mono, "TOP LANGUAGES", pad, 277, 14, MUTED, tracking=.08))
    bar_w, x = w - 2 * pad, pad
    out.append(f'<clipPath id="bar"><rect x="{pad}" y="290" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    for name, p, color in top:
        seg = bar_w * p
        out.append(f'<rect x="{x:.1f}" y="290" width="{seg + .5:.1f}" height="10" fill="{color}"/>')
        x += seg
    out.append("</g>")
    x = pad
    for name, p, color in top:
        label = f"{name} {p * 100:.0f}%" if p >= .01 else f"{name} <1%"
        out.append(f'<circle cx="{x + 6}" cy="327" r="6" fill="{color}"/>')
        out.append(text(mono, label, x + 20, 333, 16, TEXT))
        x += 20 + width(mono, label, 16) + 32

    style = """
    .ring { transform-box: fill-box; transform-origin: center; animation: ring 2.4s ease-out infinite; }
    @keyframes ring { 0% { transform: scale(1); opacity: .7; } 100% { transform: scale(3.2); opacity: 0; } }"""
    summary = ", ".join(f"{v} {l.lower()}" for v, l in stats)
    return svg(w, h, "\n  ".join(out), f"github stats: {summary}", style)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("LOGIN", "dmonskull"))
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    user = fetch(args.login)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.svg").write_text(stats_card(user, now))
    print("stats card written")
