"""Cut the supplied brand logo into the sizes the app needs.

The source is a screenshot: black letterboxing around a rounded cream tile carrying the
monogram, the wordmark and a tagline. Three jobs:

  1. trim the letterboxing back to the tile,
  2. lift the monogram out on its own — the full lock-up's tagline is illegible below ~200px,
     so a nav bar or a favicon needs the monogram alone,
  3. emit square files at the sizes Next.js and the platforms expect.

Crops are found from the pixels, not hard-coded, so re-running against a cleaner export of the
same artwork still lands correctly.
"""
from PIL import Image

SRC = "/b/source-logo.png"
CREAM = (247, 243, 236)
DARK_MAX = 40          # letterboxing is near-black
CREAM_TOL = 38         # how far from cream counts as "ink"


def bbox_of(im, keep, box=None):
    """Bounding box of pixels satisfying keep(r,g,b), optionally within box."""
    region = im.crop(box) if box else im
    ox, oy = (box[0], box[1]) if box else (0, 0)
    w, h = region.size
    px = region.load()
    xs0, ys0, xs1, ys1 = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if keep(*px[x, y]):
                if x < xs0: xs0 = x
                if x > xs1: xs1 = x
                if y < ys0: ys0 = y
                if y > ys1: ys1 = y
    return (xs0 + ox, ys0 + oy, xs1 + 1 + ox, ys1 + 1 + oy)


def squarify(box, w, h, pad=0.06):
    x0, y0, x1, y1 = box
    side = int(max(x1 - x0, y1 - y0) * (1 + pad * 2))
    side = min(side, w, h)                 # never ask for more canvas than exists
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0 = max(0, min(cx - side // 2, w - side))
    y0 = max(0, min(cy - side // 2, h - side))
    return (x0, y0, x0 + side, y0 + side)


im = Image.open(SRC).convert("RGB")
W, H = im.size

# 1. Trim the screenshot's letterboxing: keep anything that isn't near-black.
tile = im.crop(bbox_of(im, lambda r, g, b: max(r, g, b) > DARK_MAX))
tw, th = tile.size
print(f"tile after trimming letterboxing: {tw}x{th}")

# 2. Lift out the monogram. Measured from this artwork rather than detected: the gold frame
# is ink too, so an ink-bounding-box search returns the whole tile, and the wordmark sits close
# enough beneath the monogram that a generous search box swallows its ascenders.
#   crown tip  y 0.05      monogram feet / window  y 0.71
#   left of R  x 0.21      right of R              x 0.81
MONO = (0.175, 0.045, 0.855, 0.715)
mono_box = tuple(int(v * (tw if i % 2 == 0 else th)) for i, v in enumerate(MONO))
print(f"monogram crop: {mono_box}")
mono = tile.crop(mono_box)

# 3. Square the full lock-up too, so it never letterboxes in a square slot.
side = max(tw, th)
full = Image.new("RGB", (side, side), CREAM)
full.paste(tile, ((side - tw) // 2, (side - th) // 2))

OUT = {
    "/out/logo.png":            (full, 1024),   # full lock-up, hero and share card
    "/out/logo-mark.png":       (mono, 512),    # monogram only, nav and small sizes
    "/app-icons/icon.png":      (mono, 512),    # Next.js App Router favicon
    "/app-icons/apple-icon.png": (mono, 180),   # iOS home screen
}
for path, (img, size) in OUT.items():
    img.resize((size, size), Image.LANCZOS).save(path, optimize=True)
    print("wrote", path, f"{size}x{size}")
