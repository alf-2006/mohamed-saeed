#!/usr/bin/env python3
"""Animated terminal that paints the AI-generated car as a dot field.

Same engine family as dotty_terminal.py (neofetch-style SMIL loop) but in
full-bleed mode: the halftone dot field occupies the entire window below the
typed command, revealed band by band left-to-right — a garage-door sweep.
Dark studio pixels are skipped (radius would be invisible anyway), so only
the car and its rim light become dots.

    python3 dotty_car.py assets/car-hero.jpg --out assets

Output: terminal-car.svg
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out", default=".")
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)

ACC = "#FFB454"
CH_MONO = "'DejaVu Sans Mono','Courier New',monospace"

# ----------------------------------------------------------------- image field
im = Image.open(A.src).convert("RGB")
W0, H0 = im.size
sub = im.crop((int(W0 * 0.02), int(H0 * 0.02), int(W0 * 0.98), int(H0 * 0.92)))
rgb = ImageEnhance.Contrast(sub).enhance(1.32)
rgb = ImageEnhance.Color(rgb).enhance(1.18)
rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2.2, percent=260, threshold=2))
arr = np.asarray(rgb).astype(np.float32) / 255.0
H, W = arr.shape[:2]
lum = arr @ np.array([0.2126, 0.7152, 0.0722])

# dot grid
CELL = 7.5
cols = int(W / CELL)
rows = int(H / CELL)
xs = np.arange(cols) * CELL + CELL * 0.5
ys = np.arange(rows) * CELL + CELL * 0.5
ix = np.clip(xs.astype(int), 0, W - 1)
iy = np.clip(ys.astype(int), 0, H - 1)
IY, IX = np.meshgrid(iy, ix, indexing="ij")       # rows x cols
L = lum[IY, IX]
Csh = np.clip(arr[IY, IX] ** 0.85 * 1.18 + 0.03, 0, 1)

t = np.clip(L, 0, 1)
keep = t > 0.045                       # near-black studio background → no dots
rad = 0.32 + CELL * 0.55 * (t ** 1.05)

PANEL_W, PANEL_H = 1064.0, 420.0
scale = min(PANEL_W / (cols * CELL), PANEL_H / (rows * CELL))
SX = CELL * scale
PW, PH = cols * CELL * scale, rows * CELL * scale
PX0 = (1120 - PW) / 2
PY0 = 95 + (PANEL_H - PH) / 2

band_n = 26
bands = [[] for _ in range(band_n)]
for c in range(cols):
    bi = min(band_n - 1, int(c * band_n / cols))
    for r in range(rows):
        if not keep[r, c]:
            continue
        col = (np.clip(Csh[r, c] * 255, 0, 255)).astype(int)
        hexv = "#%02x%02x%02x" % tuple(col)
        bands[bi].append((PX0 + c * SX, PY0 + r * SX, rad[r, c] * scale, hexv))
total = sum(len(b) for b in bands)
print(f"dots kept: {total:,}  panel {PW:.0f}x{PH:.0f}")

# ---------------------------------------------------------------------- layout
VW, VH = 1120, 660
CMD_PRE = "ms@garage:~$ "
CMD_BIN = "dotty_car.py"
CMD_ARG = " car-hero.jpg --paint"
FULLCMD = CMD_PRE + CMD_BIN + CMD_ARG

T = 16.0
def anim(begin, end):
    b, e = begin / T, end / T
    return (f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0" keyTimes="0;{b:.4f};{min(e, 0.945):.4f};0.945;1"/>')

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}">',
       f'<rect width="{VW}" height="{VH}" rx="16" fill="#010409"/>',
       f'<rect x="8" y="8" width="{VW - 16}" height="{VH - 16}" rx="12" fill="#0D1117" stroke="#1f2937"/>',
       f'<path d="M20 8 h1080 a12 12 0 0 1 12 12 v20 H8 V20 a12 12 0 0 1 12-12 z" fill="#161b22"/>',
       '<circle cx="34" cy="26" r="6" fill="#ff5f57"/><circle cx="56" cy="26" r="6" fill="#febc2e"/>'
       '<circle cx="78" cy="26" r="6" fill="#28c840"/>',
       f'<text x="{VW / 2:.0f}" y="30" text-anchor="middle" font-family="{CH_MONO}" '
       f'font-size="12" fill="#768390">ms@garage — generative garage engine</text>']

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# typed command with syntax colors
tw = len(FULLCMD) * 8.35
svg.append(f'<clipPath id="type"><rect x="28" y="44" height="22" width="{tw:.0f}">'
           f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" '
           f'values="0;0;{tw:.0f};{tw:.0f};0" keyTimes="0;0.03;0.12;0.945;1"/></rect></clipPath>')
svg.append('<g clip-path="url(#type)">'
           f'<text x="30" y="60" xml:space="preserve" font-family="{CH_MONO}" font-size="13">'
           f'<tspan fill="#7ee787">{esc(CMD_PRE)}</tspan>'
           f'<tspan fill="{ACC}">{esc(CMD_BIN)}</tspan>'
           f'<tspan fill="#c9d1d9">{esc(CMD_ARG)}</tspan>'
           '</text></g>')
svg.append(f'<rect x="{30 + tw:.0f}" y="48" width="8" height="14" fill="#8b949e">'
           '<animate attributeName="opacity" dur="1s" repeatCount="indefinite" '
           'values="1;1;0;0" keyTimes="0;.5;.5;1"/></rect>')

# soft amber glow behind the panel
svg.insert(6, f'<rect x="{PX0 - 8:.0f}" y="{PY0 - 8:.0f}" width="{PW + 16:.0f}" height="{PH + 16:.0f}" '
             f'rx="10" fill="none" stroke="#3a2c16" stroke-width="1" opacity="0.7">' + anim(1.0, 1.3) + '</rect>')

# dot field: bands sweep in left-to-right (garage door)
for bi, b in enumerate(bands):
    t0 = 1.1 + bi * 0.09
    parts = [f'<g opacity="1">{anim(t0, t0 + 0.02)}']
    for x, y, r, hexv in b:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{hexv}"/>')
    parts.append('</g>')
    svg.append("".join(parts))

# status segments under the panel (explicit x positions)
segs = [("GARAGE : ", "#ffa657", "door open", "#e6edf3", 300),
        ("SOURCE : ", "#ffa657", "AI-generated render", "#adbac7", 545),
        ("DOTS : ", "#ffa657", f"{total:,} real-color", ACC, 830)]
for lab, lc, val, vc, xx in segs:
    svg.append(f'<g opacity="1">{anim(4.4, 4.9)}<text x="{xx}" y="552" font-family="{CH_MONO}" font-size="13">'
               f'<tspan x="{xx}" fill="{lc}">{lab}</tspan><tspan x="{xx + len(lab) * 7.8:.0f}" fill="{vc}">{esc(val)}</tspan></text></g>')

svg.append(f'<g opacity="1">{anim(8.2, 8.6)}<text x="30" y="{VH - 30}" font-family="{CH_MONO}" '
           f'font-size="12" fill="#484f58">rendered by dotty_car.py · same halftone field as the portrait terminal · '
           'zero pixels copied — pipeline: AI render → luminance dots → SMIL</text></g>')
svg.append('</svg>')
open(f"{A.out}/terminal-car.svg", "w").write("".join(svg))
print("svg:", os.path.getsize(f"{A.out}/terminal-car.svg") // 1024, "KiB", f"{VW}x{VH}")
