"""builds the static readme images in assets/ (banner and the two buttons). run it again after changing text here"""

from pathlib import Path

from svgtext import (ACCENT, ACCENT_TEXT, BG, LINE_STRONG, MUTED, TEXT, backdrop, cap_height, face, runs, svg, text,
                     width)

OUT = Path(__file__).resolve().parent.parent / "assets"

TAGLINE = [("i do reverse engineering. i come from ", 0), ("xbox 360", 1), (" RE.", 0)]
DISCORD = ("M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z")


def banner():
    w, h, pad = 1200, 400, 64
    mono = face("mono", wght=500)
    black = face("archivo", wght=900, wdth=125)
    body_f = [face("archivo", wght=400, wdth=100), face("archivo", wght=600, wdth=100)]

    # status line
    status = text(mono, "REVERSE ENGINEER", pad + 24, 95, 17, MUTED, tracking=.08)

    # wordmark fills the width
    track = -.035
    size = (w - 2 * pad) / (width(black, "DMONSKULL", 100, track) / 100)
    base = 132 + cap_height(black, size)
    word, _ = runs([(black, "DMON", TEXT), (black, "SKULL", ACCENT_TEXT)], pad - size * .01, base, size, track)

    # tagline under the wordmark
    tsize = 30
    pieces = [(body_f[b], t, TEXT if b else MUTED) for t, b in TAGLINE]
    assert sum(width(f, t, tsize) for f, t, _ in pieces) <= w - 2 * pad, "tagline too long for one line"
    tag, _ = runs(pieces, pad, base + 62, tsize)

    # site link bottom right
    link = text(mono, "dmonskull.github.io ↗", w - pad, h - 44, 18, ACCENT_TEXT, anchor="end")

    body = backdrop(w, h, 170, -60) + f"""
  <circle class="ring" cx="{pad + 6}" cy="89" r="5" fill="{ACCENT}"/>
  <circle cx="{pad + 6}" cy="89" r="5" fill="{ACCENT}"/>
  {status}
  {word}
  {tag}
  {link}"""
    style = f"""
    .ring {{ transform-box: fill-box; transform-origin: center; animation: ring 2.4s ease-out infinite; }}
    @keyframes ring {{ 0% {{ transform: scale(1); opacity: .7; }} 100% {{ transform: scale(3.2); opacity: 0; }} }}
    .glow {{ animation: drift 14s ease-in-out infinite alternate; }}
    @keyframes drift {{ from {{ transform: translate(0, 0); }} to {{ transform: translate(80px, 30px); }} }}"""
    title = "DMONSKULL. i do reverse engineering. i come from xbox 360 RE."
    (OUT / "banner.svg").write_text(svg(w, h, body, title, style))


def button(name, label, fill, ink, stroke=None, icon=None):
    mono = face("mono", wght=500)
    size, h, padx = 19, 60, 30
    icon_w = 26 + 12 if icon else 0
    w = round(padx * 2 + icon_w + width(mono, label, size))
    y = h / 2 + cap_height(mono, size) / 2
    parts = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{(h - 2) / 2}" fill="{fill}"' + \
            (f' stroke="{stroke}" stroke-width="2"' if stroke else "") + "/>"
    if icon:
        parts += f'<path fill="#5865F2" transform="translate({padx} {(h - 26) / 2}) scale({26 / 24})" d="{icon}"/>'
    parts += text(mono, label, padx + icon_w, y, size, ink)
    (OUT / f"button-{name}.svg").write_text(svg(w, h, parts, label))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    banner()
    button("site", "dmonskull.github.io ↗", ACCENT, BG)
    button("discord", "join my discord ↗", BG, TEXT, stroke=LINE_STRONG, icon=DISCORD)
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.name:22} {p.stat().st_size / 1024:.1f} KB")
