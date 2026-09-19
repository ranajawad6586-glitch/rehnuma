"""Render the RehnumaRent profile-picture PNGs.

Platforms that mask avatars to a circle also reject SVG, so the square PNG is the file that
actually gets uploaded. Drawn at 4x and downsampled, because PIL has no anti-aliasing of its
own and a 104px-wide stroke shows every jagged step at 1x.
"""
from PIL import Image, ImageDraw

CANVAS = 1024
SS = 4                     # supersample factor
BBOX_H = 58.5              # mark height in its own 64-unit space, including cap radius
INSET = 0.58               # fraction of the canvas the mark occupies
OPTICAL_LIFT = 0.01        # the arch is bottom-heavy; lift it off the maths centre

# The mark in its own 64-unit space.
ARCH = [(9, 58), (9, 29.2), (32, 6), (55, 29.2), (55, 58)]
STROKE = 6.5
DOT = (32, 34, 6.4)

VARIANTS = {
    "moss":  ("#1f5d4c", "#f4efe4", "#c2703d"),
    "clay":  ("#c2703d", "#f4efe4", "#1f5d4c"),
    "paper": ("#f4efe4", "#1f5d4c", "#c2703d"),
}


def render(bg: str, stroke: str, dot: str, size: int) -> Image.Image:
    px = size * SS
    scale = (px * INSET) / BBOX_H
    tx = px / 2 - 32 * scale
    ty = px / 2 - 32 * scale - px * OPTICAL_LIFT

    img = Image.new("RGB", (px, px), bg)
    d = ImageDraw.Draw(img)

    pts = [(x * scale + tx, y * scale + ty) for x, y in ARCH]
    w = STROKE * scale
    # joint="curve" rounds the corners; the ends need caps drawn by hand.
    d.line(pts, fill=stroke, width=int(round(w)), joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=stroke)

    cx, cy, cr = DOT
    cx, cy, cr = cx * scale + tx, cy * scale + ty, cr * scale
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=dot)

    return img.resize((size, size), Image.LANCZOS)


for name, (bg, stroke, dot) in VARIANTS.items():
    for size in (1024, 512):
        out = f"/out/rehnumarent-pfp-{name}-{size}.png"
        render(bg, stroke, dot, size).save(out, optimize=True)
        print("wrote", out.split("/")[-1])

# Favicon-scale renders keep the heavier stroke the small variants use.
print("done")
