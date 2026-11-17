"""turns text into svg paths using the real fonts, so the images look the same on every device
(github shows readme svgs as images, and images cant load web fonts).
also holds the look shared with the dmon site: colors, the violet glow, the orbits and the grain"""

from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FONTS = Path(__file__).parent / "fonts"
FILES = {"outfit": "Outfit.ttf", "mono": "JetBrainsMono.ttf"}

# same palette as the dmon site
BG = "#08070b"
INK = "#f3eeff"
ACCENT = "#bca9fb"
GLASS = "#0d0b14"
SHADE = "#120c24"  # orbit ink on top of the bright core
GLOW_STOPS = [(0, "#f3eeff"), (.15, "#bca9fb"), (.32, "#7d5fe0"), (.5, "#3a2785"), (.7, "#150f2b"), (.9, BG)]
CHART = ["#f3eeff", "#bca9fb", "#9b84f2", "#7d5fe0", "#5a42b4", "#3a2785"]  # brightest first


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


def text(f, txt, x, y, size, fill, tracking=0, anchor="start", opacity=None):
    """one <path> for a line of text. anchor works like svg text-anchor"""
    if anchor != "start":
        w = width(f, txt, size, tracking)
        x -= w if anchor == "end" else w / 2
    d = path_d(f, txt, x, y, size, tracking)
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return f'<path fill="{fill}"{op} d="{d}"/>' if d else ""


def name_gradient(uid):
    """the light violet to white fill the site uses on DMON (css linear-gradient 105deg)"""
    return (f'<linearGradient id="{uid}" x1="0" y1=".37" x2="1" y2=".63">'
            '<stop offset="0" stop-color="#c9b9ff"/><stop offset=".48" stop-color="#f3eeff"/>'
            '<stop offset="1" stop-color="#fff"/></linearGradient>')


def _ellipse_gradient(gid, cx, cy, rx, ry, stops):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return (f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{rx}" gradientUnits="userSpaceOnUse" '
            f'gradientTransform="translate({cx} {cy}) scale(1 {ry / rx:.4f}) translate({-cx} {-cy})">{s}</radialGradient>')


def glow(uid, w, h, cx, cy, rx, ry, breathe=True):
    """the violet glow, bent by noise so it isnt a perfect ellipse. returns (defs, body).
    also defines masks {uid}-in and {uid}-out for the bright core, so orbits can switch ink there like the site does"""
    big = f'x="-200" y="-200" width="{w + 400}" height="{h + 400}"'
    defs = "".join([
        _ellipse_gradient(f"{uid}-g", cx, cy, rx, ry, GLOW_STOPS),
        _ellipse_gradient(f"{uid}-c", cx, cy, rx, ry, [(.26, "#fff"), (.3, "#000")]),
        _ellipse_gradient(f"{uid}-ci", cx, cy, rx, ry, [(.26, "#000"), (.3, "#fff")]),
        f'<filter id="{uid}-warp" filterUnits="userSpaceOnUse" {big}>'
        '<feTurbulence type="fractalNoise" baseFrequency=".0032" numOctaves="2" seed="11"/>'
        '<feDisplacementMap in="SourceGraphic" scale="80" xChannelSelector="R" yChannelSelector="G"/></filter>',
        f'<mask id="{uid}-in" maskUnits="userSpaceOnUse" {big}><rect {big} fill="url(#{uid}-c)" filter="url(#{uid}-warp)"/></mask>',
        f'<mask id="{uid}-out" maskUnits="userSpaceOnUse" {big}><rect {big} fill="url(#{uid}-ci)" filter="url(#{uid}-warp)"/></mask>',
    ])
    cls = ' class="breathe"' if breathe else ""
    body = f'<g{cls}><rect {big} fill="url(#{uid}-g)" filter="url(#{uid}-warp)"/></g>'
    return defs, body


def grain(uid, w, h):
    """film grain like the site, it also hides banding in the dark gradient. returns (defs, body)"""
    defs = (f'<filter id="{uid}" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch" seed="5"/>'
            '<feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  .12 0 0 0 -.04"/></filter>')
    return defs, f'<rect width="{w}" height="{h}" filter="url(#{uid})"/>'


def orbit(cx, cy, rx, ry, rot, period, phase, mask_out=None, mask_in=None, opacity=.24):
    """one hairline orbit with a node going round it and a short comet tail behind the node.
    light ink on the dark, and dark ink inside mask_in (the bright core) like the site"""
    d = f"M{rx} 0A{rx} {ry} 0 1 1 {-rx} 0A{rx} {ry} 0 1 1 {rx} 0"
    begin = f"-{phase * period:.2f}s"
    timing = f'dur="{period}s" begin="{begin}" repeatCount="indefinite"'

    def layer(ink, line_op, halo):
        tail = ""
        for length, op in ((150, .14), (70, .28), (28, .5)):
            tail += (f'<path d="{d}" fill="none" stroke="{ink}" stroke-opacity="{op}" stroke-width="1.6" stroke-linecap="round" '
                     f'pathLength="1000" stroke-dasharray="{length} {1000 - length}">'
                     f'<animate attributeName="stroke-dashoffset" values="{length};{length - 1000}" {timing}/></path>')
        node = f'<circle r="3.4" fill="{ink}"><animateMotion path="{d}" {timing}/></circle>'
        if halo:
            node = f'<circle r="18" fill="url(#halo)"><animateMotion path="{d}" {timing}/></circle>' + node
        return (f'<g transform="translate({cx} {cy}) rotate({rot})">'
                f'<path d="{d}" fill="none" stroke="{ink}" stroke-opacity="{line_op}" stroke-width="1.2"/>{tail}{node}</g>')

    out = layer(INK, opacity, True)
    if mask_out:
        out = f'<g mask="url(#{mask_out})">{out}</g>'
    if mask_in:
        out += f'<g mask="url(#{mask_in})">{layer(SHADE, .5, False)}</g>'
    return out


HALO = ('<radialGradient id="halo"><stop offset="0" stop-color="#b9a3ff" stop-opacity=".6"/>'
        '<stop offset="1" stop-color="#b9a3ff" stop-opacity="0"/></radialGradient>')


def svg(w, h, body, title, style=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
  <title>{title}</title>
  <style>
    .breathe {{ transform-box: view-box; transform-origin: 50% 80%; animation: breathe 11s ease-in-out infinite alternate; }}
    @keyframes breathe {{ from {{ transform: scale(1); }} to {{ transform: scale(1.06) translateY(-6px); }} }}{style}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  {body}
</svg>
"""
