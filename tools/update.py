"""daily job: draws the stats card"""

import argparse
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from svgtext import (BG, CHART, GLASS, HALO, INK, cap_height, face, glow, grain, name_gradient, orbit, svg, text,
                     width)

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


def stats_card(user, now):
    """the stats in the dmon site style: dark card, violet haze from below, one orbit, glass label"""
    repos = own_projects(user)
    w, h, pad = 1200, 380, 64
    mono = face("mono", wght=500)
    sans = face("outfit", wght=500)

    releases = [(r["latestRelease"], r["name"]) for r in repos if r["latestRelease"]]
    latest = max(releases, key=lambda x: x[0]["publishedAt"], default=None)
    stats = [
        (f"{user['contributionsCollection']['contributionCalendar']['totalContributions']:,}", "CONTRIBUTIONS, PAST YEAR"),
        (f"{sum(r['stargazerCount'] for r in repos):,}", "STARS"),
        (f"{user['everything']['totalCount']:,}", "PUBLIC REPOS"),
        (latest[0]["tagName"], f"LATEST: {latest[1].upper()}") if latest else ("none", "LATEST RELEASE"),
    ]

    gdefs, gbody = glow("g", w, h, w / 2, h + 230, 780, 420)
    ndefs, nbody = grain("grain", w, h)
    out = [f'<defs>{gdefs}{ndefs}{name_gradient("num")}{HALO}<clipPath id="clip"><rect width="{w}" height="{h}" rx="22"/></clipPath></defs>',
           '<g clip-path="url(#clip)">', f'<rect width="{w}" height="{h}" fill="{BG}"/>', gbody,
           orbit(w / 2 + 60, h + 150, 760, 250, -5, 74, .3, opacity=.14), nbody]

    # glass label like the site's PINNED pill, and the date across from it
    label, size, track = "GITHUB STATS", 13, .14
    lw = width(mono, label, size, track)
    out.append(f'<rect x="{pad}" y="40" width="{lw + 30:.0f}" height="34" rx="17" fill="{GLASS}" fill-opacity=".8" stroke="{INK}" stroke-opacity=".12"/>')
    out.append(text(mono, label, pad + 15, 57 + cap_height(mono, size) / 2, size, INK, tracking=track, opacity=.88))
    out.append(text(mono, f"UPDATED {now:%b} {now.day}, {now.year}".upper(), w - pad, 57 + cap_height(mono, 13) / 2, 13, INK,
                    tracking=.09, anchor="end", opacity=.5))

    col = (w - 2 * pad) / len(stats)
    for i, (value, label) in enumerate(stats):
        x = pad + i * col
        size = 66
        while width(sans, value, size, -.04) > col - 28 and size > 24:
            size -= 2
        out.append(text(sans, value, x, 182, size, "url(#num)", tracking=-.04))
        out.append(text(mono, label, x, 214, 13, INK, tracking=.09, opacity=.7))
        if i:
            out.append(f'<path d="M{x - 22:.0f} 126V218" stroke="{INK}" stroke-opacity=".1"/>')

    # top languages by code size, shaded in the site violets instead of github colors
    sizes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in ranked) or 1
    top = [(name, v / total) for name, v in ranked[:5]]
    rest = 1 - sum(p for _, p in top)
    if rest > .005:
        top.append(("Other", rest))
    top = [(name, p, CHART[i]) for i, (name, p) in enumerate(top)]

    out.append(f'<path d="M{pad} 252H{w - pad}" stroke="{INK}" stroke-opacity=".1"/>')
    out.append(text(mono, "TOP LANGUAGES", pad, 290, 13, INK, tracking=.09, opacity=.7))
    bar_w, x = w - 2 * pad, pad
    out.append(f'<clipPath id="bar"><rect x="{pad}" y="304" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    out.append(f'<rect x="{pad}" y="304" width="{bar_w}" height="8" fill="{INK}" fill-opacity=".08"/>')
    for name, p, color in top:
        seg = bar_w * p
        out.append(f'<rect x="{x:.1f}" y="304" width="{seg + .5:.1f}" height="8" fill="{color}"/>')
        x += seg
    out.append("</g>")
    x = pad
    for name, p, color in top:
        label = (f"{name} {p * 100:.0f}%" if p >= .01 else f"{name} <1%").upper()
        out.append(f'<circle cx="{x + 4}" cy="341" r="4" fill="{color}"/>')
        out.append(text(mono, label, x + 16, 341 + cap_height(mono, 14) / 2, 14, INK, tracking=.08, opacity=.85))
        x += 16 + width(mono, label, 14, .08) + 30

    out.append("</g>")
    out.append(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="21.5" fill="none" stroke="{INK}" stroke-opacity=".1"/>')
    summary = ", ".join(f"{v} {l.lower()}" for v, l in stats)
    return svg(w, h, "\n  ".join(out), f"github stats: {summary}")


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
