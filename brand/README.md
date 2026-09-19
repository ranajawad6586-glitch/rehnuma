# RehnumaRent brand assets

The mark is an arch with a single light at its centre — *rehnuma* is the one who guides, and the
light stands in the doorway where a dealer usually does.

## Which file to use

| File | Use it for |
|---|---|
| `rehnumarent-pfp-moss-1024.png` | **Profile picture everywhere** — WhatsApp, Instagram, Facebook, X, YouTube |
| `rehnumarent-pfp-moss-512.png` | Smaller upload limits (some Facebook page fields cap at 1 MB) |
| `rehnumarent-pfp-clay-*.png` | Only where the surrounding feed is already dark green |
| `rehnumarent-pfp-paper-*.png` | Print, letterheads, the stamp-paper agreement footer |
| `rehnumarent-mark.svg` | In code — transparent, scalable, 64-unit viewBox |
| `rehnumarent-pfp-*.svg` | Source for the PNGs; re-render rather than resizing a PNG |

PNG, not SVG, for profile pictures: WhatsApp and Instagram reject SVG uploads outright.

## Why the mark doesn't fill the square

Every platform masks an avatar to a circle. The largest square that fits inside a circle is only
about 70% of it, and platforms zoom slightly on top of that — so a mark sized to fill the square
loses its feet. Here it sits at **58% of the canvas height**, centred and lifted 1% off the
mathematical centre because the two legs make the shape bottom-heavy.

The background runs to the edges of the square. Do **not** draw a circle into the file: services
that don't crop (some WhatsApp group views) would show pale corners around it.

## Re-rendering

`render_pngs.py` draws the PNGs from the same geometry as the SVGs. It needs Pillow, which the
backend image already has:

```bash
docker run --rm -v "$PWD/brand:/out" -v "$PWD/brand/render_pngs.py:/app/render_pngs.py:ro" \
  rehnumarent-api:test python /app/render_pngs.py
```

Colours come from `web/tailwind.config.ts`: moss `#1F5D4C`, clay `#C2703D`, paper `#F4EFE4`,
ink `#2A2722`.
