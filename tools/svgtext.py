"""turns text into svg paths using the real fonts, so the images look the same on every device
(github shows readme svgs as images, and images cant load web fonts)"""

from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FONTS = Path(__file__).parent / "fonts"
FILES = {"archivo": "Archivo.ttf", "mono": "JetBrainsMono.ttf"}

# same palette as dmonskull.github.io
BG = "#0a0b09"
SURFACE = "#111310"
LINE = "#252a21"
LINE_STRONG = "#353b2f"
TEXT = "#eef1e8"
MUTED = "#a0a797"
FAINT = "#676e5f"
ACCENT = "#a6ff3d"
ACCENT_TEXT = "#b8ff66"


def num(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Face:
    def __init__(self, family, axes):
        path = str(FONTS / FILES[family])
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
        self.hb.set_variations(dict(axes))
        tt = instantiateVariableFont(TTFont(path), dict(axes))
        self.glyphs = tt.getGlyphSet()
        self.order = tt.getGlyphOrder()
        self.upem = tt["head"].unitsPerEm
        self.cap = tt["OS/2"].sCapHeight


@lru_cache(None)
def _face(family, axes):
    return Face(family, axes)


def face(family, **axes):
    return _face(family, tuple(sorted((k, float(v)) for k, v in axes.items())))


def _shape(f, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f.hb, buf, {"kern": True})
    return list(zip(buf.glyph_infos, buf.glyph_positions))


def width(f, text, size, tracking=0):
    """visual width, tracking is in em like css letter-spacing (not added after the last glyph)"""
    glyphs = _shape(f, text)
    if not glyphs:
        return 0
    return sum(p.x_advance for _, p in glyphs) * size / f.upem + tracking * size * (len(glyphs) - 1)


def cap_height(f, size):
    return f.cap * size / f.upem


def path_d(f, text, x, y, size, tracking=0):
    s = size / f.upem
    pen = SVGPathPen(f.glyphs, ntos=num)
    cx = x
    for info, pos in _shape(f, text):
        name = f.order[info.codepoint]
        f.glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, cx + pos.x_offset * s, y - pos.y_offset * s)))
        cx += pos.x_advance * s + tracking * size
    return pen.getCommands()


def text(f, txt, x, y, size, fill, tracking=0, anchor="start", extra=""):
    """one <path> for a line of text. anchor works like svg text-anchor"""
    if anchor != "start":
        w = width(f, txt, size, tracking)
        x -= w if anchor == "end" else w / 2
    d = path_d(f, txt, x, y, size, tracking)
    return f'<path fill="{fill}"{extra} d="{d}"/>' if d else ""


def runs(parts, x, y, size, tracking=0):
    """several pieces on one line, each (face, text, fill). returns (svg, end_x)"""
    out = []
    for f, txt, fill in parts:
        out.append(text(f, txt, x, y, size, fill, tracking))
        x += width(f, txt, size, tracking) + tracking * size
    return "".join(out), x


def backdrop(w, h, glow_x, glow_y, radius=24, uid="b"):
    """the dark card with the faint grid and green glow used on the site"""
    return f"""<defs>
    <clipPath id="{uid}-clip"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath>
    <pattern id="{uid}-grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="#ffffff" stroke-opacity=".035"/></pattern>
    <radialGradient id="{uid}-glow" cx="{glow_x}" cy="{glow_y}" r="{max(w, h) * .6:.0f}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity=".16"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{uid}-fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".2" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <mask id="{uid}-mask"><rect width="{w}" height="{h}" fill="url(#{uid}-fade)"/></mask>
  </defs>
  <g clip-path="url(#{uid}-clip)">
    <rect width="{w}" height="{h}" fill="{BG}"/>
    <rect width="{w}" height="{h}" fill="url(#{uid}-grid)" mask="url(#{uid}-mask)"/>
    <rect class="glow" width="{w}" height="{h}" fill="url(#{uid}-glow)"/>
  </g>
  <rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius - .5}" fill="none" stroke="{LINE}"/>"""


def svg(w, h, body, title, style=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
  <title>{title}</title>
  <style>{style}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  {body}
</svg>
"""
