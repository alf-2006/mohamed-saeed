#!/usr/bin/env python3
"""Stage 0 of the Generative Portrait Engine: AI background removal.

Segmentation is what turns a cluttered snapshot into readable dot art — the
mural behind the subject contributed ~40 % of the noise in early renders, so
the first learned model in the pipeline is an saliency/matting network
(`isnet-general-use` via rembg). Everything downstream samples this matte, so
dots only ever land on the subject.

    pip install "rembg[cpu]" pillow numpy
    python matting.py photo.jpg --out ../assets

Writes portrait-matted.png (RGBA). Alpha = the subject; background = removed.
Letterbox bars in the source screenshot are detected and cropped first.
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out", default=".")
ap.add_argument("--model", default="isnet-general-use",
                help="rembg model (isnet-general-use, u2net, birefnet-general …)")
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)

from rembg import remove, new_session  # noqa: E402  (heavy import, run only here)

im = Image.open(A.src).convert("RGB")
a = np.asarray(im).astype(np.float32) / 255.0

# ------------------------------------------------- letterbox bar detection
lum = a @ np.array([0.2126, 0.7152, 0.0722])
row_std = a.std(axis=(1, 2))
row_max = a.max(axis=(1, 2))
# A bar row is grainy-dark: low spread and low peak brightness. The photo is
# the longest contiguous run of the *other* rows — this survives watermark
# text sitting inside the bottom bar and JPEG noise everywhere.
is_bar = (row_std < 0.055) & (row_max < 0.26)
content = ~is_bar
H0, W0 = a.shape[:2]
run_len, best = 0, (0, 0)
for i, c in enumerate(content):
    run_len = run_len + 1 if c else 0
    if run_len > best[1] - best[0]:
        best = (i - run_len + 1, i)
if best[1] - best[0] < H0 * 0.4:
    best = (0, H0 - 1)                    # nothing convincing → full frame
    print("no letterbox detected, using full frame")
else:
    print(f"content rows {best[0]}-{best[1]} ({best[1] - best[0] + 1}px of {H0})")
y0, y1 = best
crop = im.crop((0, y0, W0, y1 + 1))

# ----------------------------------------------------------------- matting
sess = new_session(A.model)
matted = remove(crop, session=sess, alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=15,
                alpha_matting_erode_size=8)

# feather the matte edge a touch so dot radii near the silhouette stay smooth
alpha = matted.split()[-1].filter(ImageFilter.GaussianBlur(0.8))
matted.putalpha(alpha)

out = os.path.join(A.out, "portrait-matted.png")
matted.save(out, optimize=True)
frac = np.asarray(alpha).mean() / 255.0
print(f"{out}: {matted.size[0]}x{matted.size[1]}, subject covers {frac:.0%}")
