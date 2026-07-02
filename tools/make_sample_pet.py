"""Generate assets/sample_pet.gif.

A small animated GIF suitable for testing the desktop pet overlay:
64x64 canvas, fully transparent background, a coloured circle that
moves around so the alpha channel is easy to verify visually.

Not part of the runtime; invoked once to produce the bundled asset.
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw

SIZE = 64
FRAMES = 24
DURATION_MS = 80  # 12.5 fps — slow enough to see the path clearly
CIRCLE_RADIUS = 10


def make_frame(t: int) -> Image.Image:
    """One frame of the animation: a circle tracing a small figure-8."""
    # Fully transparent background, RGBA.
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Parametric figure-8 (Lissajous with a=2, b=2, phase shift).
    cx = SIZE / 2 + 18 * math.sin(2 * math.pi * t / FRAMES)
    cy = SIZE / 2 + 12 * math.sin(2 * math.pi * t / FRAMES + math.pi / 2)

    draw.ellipse(
        (
            cx - CIRCLE_RADIUS,
            cy - CIRCLE_RADIUS,
            cx + CIRCLE_RADIUS,
            cy + CIRCLE_RADIUS,
        ),
        fill=(220, 110, 180, 230),  # pink, slightly transparent
        outline=(40, 20, 30, 255),
        width=1,
    )
    return img


def main(out_path: str) -> int:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    frames = [make_frame(t) for t in range(FRAMES)]

    # Pillow's GIF writer does not preserve per-frame alpha; the first
    # frame's transparent pixels become the GIF's transparent index.
    # Our first frame is fully transparent, so the whole canvas is.
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,  # infinite loop
        disposal=2,  # restore to background — required for moving shapes
        transparency=0,
    )
    print(f"wrote {out_path} ({os.path.getsize(out_path)} bytes)")
    return 0


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(project_root, "assets", "sample_pet.gif")
    )
    sys.exit(main(target))
