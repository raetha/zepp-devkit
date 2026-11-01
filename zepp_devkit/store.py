"""Zepp store images: 360x360 screenshots and a 240x240 icon, as the Zepp Console asks.

Round screens: the screenshot centred with no margin, transparent outside the circle.
Square screens: centred with equal side margins and no top or bottom margin.
"""
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 360


def _round_mask(size):
    big = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(big).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    return big.resize((size, size), Image.LANCZOS)  # antialiased edge


def screenshot(src, dest, shape="round"):
    shot = Image.open(src).convert("RGBA")
    if shape == "round":
        shot = shot.resize((SIZE, SIZE), Image.LANCZOS)
        shot.putalpha(_round_mask(SIZE))
    else:
        w = round(shot.width * SIZE / shot.height)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.alpha_composite(shot.resize((w, SIZE), Image.LANCZOS), ((SIZE - w) // 2, 0))
        shot = canvas
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shot.save(dest, optimize=True)
    return dest


def icon(src, dest, size=240):
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS).save(dest, optimize=True)
    return dest


def screenshots(raw_dir, out_dir, shape="round"):
    """raw_dir/<n>-<name>.png (480x480 emulator shots) -> out_dir/screenshot-<name>.png."""
    out = []
    for raw in sorted(Path(raw_dir).glob("*.png")):
        name = raw.stem.split("-", 1)[-1]
        out.append(screenshot(raw, Path(out_dir) / f"screenshot-{name}.png", shape))
    return out
