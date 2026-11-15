#!/usr/bin/env python3
"""Neofetch-style animated terminal SVG whose avatar is the dot portrait.

Stage 3 of the Generative Portrait Engine. Where Andrew Grant-style READMEs
put ASCII art in the neofetch "logo" slot, this fills it with ~5k real-color
halftone dots sampled from the background-removed photo. The whole window
animates on a 16 s SMIL loop: the command types itself, the portrait draws in
band by band, the stats appear, the cursor blinks, then it restarts. GitHub
renders SMIL inside markdown image tags (same tech as typing-svg badges).

    python3 dotty_terminal.py matted.png --out ../assets

Input: an RGBA image with the background already removed (see README:
rembg isnet-general-use). Output: terminal-portrait.svg.
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

ACC = "#FFB454"  # amber — matches the gold-lit garage vibe
CH_MONO = "'DejaVu Sans Mono','Courier New',monospace"

# ----------------------------------------------------------------- portrait field
im = Image.open(A.src).convert("RGBA")
W0, H0 = im.size
bx0, by0, bx1, by1 = int(W0 * 0.18), int(H0 * 0.12), int(W0 * 0.88), int(H0 * 0.60)
sub = im.crop((bx0, by0, bx1, by1))
rgb = sub.convert("RGB")
rgb = ImageEnhance.Contrast(rgb).enhance(1.22)
rgb = ImageEnhance.Color(rgb).enhance(1.28)
rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2.2, percent=150, threshold=2))
arr = np.asarray(rgb).astype(np.float32) / 255.0
alpha = np.asarray(sub.split()[-1]).astype(np.float32) / 255.0
H, W = arr.shape[:2]
lum = arr @ np.array([0.2126, 0.7152, 0.0722])

# dot grid (image space), then scale into the panel
CELL = 4.5
cols = int(W / CELL)
rows = int(H / CELL)
xs = np.arange(cols) * CELL + CELL * 0.5
ys = np.arange(rows) * CELL + CELL * 0.5
ix = np.clip(xs.astype(int), 0, W - 1)
iy = np.clip(ys.astype(int), 0, H - 1)
IY, IX = np.meshgrid(iy, ix, indexing="ij")       # rows x cols
L = lum[IY, IX]
Csh = np.clip(arr[IY, IX] ** 0.85 * 1.18 + 0.03, 0, 1)
AL = alpha[IY, IX]
keep = (AL > 0.30)

t = np.clip(L, 0, 1)                      # dark canvas: brightness drives density
rad = 0.42 + CELL * 0.64 * (t ** 0.90)

PANEL_W, PANEL_H = 540.0, 520.0
scale = min(PANEL_W / (cols * CELL), PANEL_H / (rows * CELL))
SX = CELL * scale
PW, PH = cols * CELL * scale, rows * CELL * scale
PX0 = 30 + (560 - PW) / 2
PY0 = 82 + (PANEL_H - PH) / 2

band_n = 24
bands = [[] for _ in range(band_n)]
for r in range(rows):
    bi = min(band_n - 1, int(r * band_n / rows))
    for c in range(cols):
        if not keep[r, c]:
            continue
        col = (np.clip(Csh[r, c] * 255, 0, 255)).astype(int)
        hexv = "#%02x%02x%02x" % tuple(col)
        bands[bi].append((PX0 + c * SX, PY0 + r * SX, rad[r, c] * scale, hexv))
total = sum(len(b) for b in bands)
print(f"dots kept: {total:,}  panel {PW:.0f}x{PH:.0f}")

# ---------------------------------------------------------------------- layout
VW, VH = 1120, 660
CMD = "ms@workstation:~$ rembg selfie.jpg && dotty_terminal.py"
INFO = [
    ("NAME",   "Mohamed Saeed",                 "#e6edf3"),
    ("ROLE",   "Computer Engineer",             "#e6edf3"),
    ("HOME",   "Egypt",                         "#adbac7"),
    ("MODE",   "code by day · cars by weekend", "#adbac7"),
    ("HOBBY",  "luxury cars & engine notes",    "#adbac7"),
    ("FUEL",   "V8 dreams · AMG targets",       "#adbac7"),
    ("ENGINE", "rembg → halftone field → SVG",  "#adbac7"),
    ("RENDER", f"{total:,} colored dots",       ACC),
    ("SIGNAL", "#FFB454 — tank full",           "#ff7b72"),
]

T = 16.0
def anim(begin, end):
    b, e = begin / T, end / T
    return (f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0" keyTimes="0;{b:.4f};{min(e, 0.945):.4f};0.945;1"/>')
def anim1(begin):  # full cycle visible once appeared
    b = begin / T
    return (f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0" keyTimes="0;{b:.4f};{min(b + 0.01, 0.945):.4f};0.945;1"/>')

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}">',
       f'<rect width="{VW}" height="{VH}" rx="16" fill="#010409"/>',
       f'<rect x="8" y="8" width="{VW - 16}" height="{VH - 16}" rx="12" fill="#0D1117" stroke="#1f2937"/>',
       f'<path d="M20 8 h1080 a12 12 0 0 1 12 12 v20 H8 V20 a12 12 0 0 1 12-12 z" fill="#161b22"/>',
       '<circle cx="34" cy="26" r="6" fill="#ff5f57"/><circle cx="56" cy="26" r="6" fill="#febc2e"/>'
       '<circle cx="78" cy="26" r="6" fill="#28c840"/>',
       f'<text x="{VW / 2:.0f}" y="30" text-anchor="middle" font-family="{CH_MONO}" '
       f'font-size="12" fill="#768390">ms@workstation — generative portrait engine</text>']

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# typed command with syntax colors
pre, post = CMD.split("rembg", 1)
tw = len(CMD) * 8.35
svg.append(f'<clipPath id="type"><rect x="28" y="44" height="22" width="{tw:.0f}">'
           f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" '
           f'values="0;0;{tw:.0f};{tw:.0f};0" keyTimes="0;0.03;0.12;0.945;1"/></rect></clipPath>')
svg.append('<g clip-path="url(#type)">'
           f'<text x="30" y="60" xml:space="preserve" font-family="{CH_MONO}" font-size="13">'
           f'<tspan fill="#7ee787">{esc(pre)}</tspan>'
           f'<tspan fill="{ACC}">{esc("rembg" + post[:post.find(" &&")])}</tspan>'
           f'<tspan fill="#c9d1d9">{esc(post[post.find(" &&"):])}</tspan>'
           '</text></g>')
svg.append(f'<rect x="{30 + tw:.0f}" y="48" width="8" height="14" fill="#8b949e">'
           '<animate attributeName="opacity" dur="1s" repeatCount="indefinite" '
           'values="1;1;0;0" keyTimes="0;.5;.5;1"/></rect>')

# dashed divider
svg.append(f'<line x1="600" y1="86" x2="600" y2="{VH - 52}" stroke="#1f2937" stroke-dasharray="2 7">'
           + anim(0.4, 0.8) + '</line>')

# dot portrait: bands fade in top-down
for bi, b in enumerate(bands):
    t0 = 1.1 + bi * 0.10
    parts = [f'<g opacity="1">{anim(t0, t0 + 0.02)}>']
    parts = [f'<g opacity="1">{anim(t0, t0 + 0.02)}']
    for x, y, r, hexv in b:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{hexv}"/>')
    parts.append('</g>')
    svg.append("".join(parts))

# neofetch column
IX, IY = 632, 100
svg.append(f'<g opacity="1">{anim(4.4, 4.7)}<text x="{IX}" y="{IY}" font-family="{CH_MONO}" font-size="14">'
           f'<tspan fill="#7ee787">ms@workstation</tspan><tspan fill="#c9d1d9">:~$ </tspan>'
           '<tspan fill="#e6edf3">neofetch me</tspan></text></g>')
svg.append(f'<g opacity="1">{anim(4.8, 5.1)}<text x="{IX}" y="{IY + 17}" font-family="{CH_MONO}" '
           f'font-size="13" fill="#238636">{"-" * 42}</text></g>')
for i, (k, val, c) in enumerate(INFO):
    yy = IY + 42 + i * 25
    t0 = 5.1 + i * 0.24
    svg.append(f'<g opacity="1">{anim(t0, t0 + 0.2)}'
               f'<text x="{IX}" y="{yy}" font-family="{CH_MONO}" font-size="13">'
               f'<tspan fill="#ffa657">{k}</tspan><tspan fill="#484f58"> : </tspan>'
               f'<tspan fill="{c}">{esc(val)}</tspan></text></g>')

# status line + soft cyan glow behind panel
svg.insert(6, f'<rect x="{PX0 - 8:.0f}" y="{PY0 - 8:.0f}" width="{PW + 16:.0f}" height="{PH + 16:.0f}" '
             f'rx="10" fill="none" stroke="#3a2c16" stroke-width="1" opacity="0.7">' + anim(1.0, 1.3) + '</rect>')
svg.append(f'<g opacity="1">{anim(8.2, 8.6)}<text x="30" y="{VH - 30}" font-family="{CH_MONO}" '
           f'font-size="12" fill="#484f58">rendered by dotty_terminal.py · {total:,} real-color dots · '
           'zero pixels copied — pipeline: rembg isnet-general-use → halftone field → SMIL</text></g>')
svg.append('</svg>')
open(f"{A.out}/terminal-portrait.svg", "w").write("".join(svg))
print("svg:", os.path.getsize(f"{A.out}/terminal-portrait.svg") // 1024, "KiB", f"{VW}x{VH}")
