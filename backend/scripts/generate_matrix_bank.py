"""Generate 80 NVR matrix PNGs (3x3 grids) + manifest.json.

Run once locally:
  cd backend && python scripts/generate_matrix_bank.py

Output: backend/static/matrices/{id}.png + manifest.json
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent.parent / "static" / "matrices"
OUT.mkdir(parents=True, exist_ok=True)

CELL = 100
GRID = 3
PAD = 6
SIZE = CELL * GRID + PAD * 2


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (SIZE, SIZE), "white")
    d = ImageDraw.Draw(img)
    # Grid lines
    for i in range(GRID + 1):
        x = PAD + i * CELL
        d.line([(x, PAD), (x, PAD + GRID * CELL)], fill="black", width=2)
        d.line([(PAD, x), (PAD + GRID * CELL, x)], fill="black", width=2)
    return img, d


def cell_center(row: int, col: int) -> tuple[int, int]:
    return (PAD + col * CELL + CELL // 2, PAD + row * CELL + CELL // 2)


def draw_shape(d: ImageDraw.ImageDraw, shape: str, cx: int, cy: int, r: int, fill: str | None = None, rot: int = 0):
    if shape == "circle":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", fill=fill, width=2)
    elif shape == "square":
        d.rectangle([cx - r, cy - r, cx + r, cy + r], outline="black", fill=fill, width=2)
    elif shape == "triangle":
        pts = _rotate_pts([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], cx, cy, rot)
        d.polygon(pts, outline="black", fill=fill)
    elif shape == "pentagon":
        pts = _polygon_pts(cx, cy, r, 5, rot)
        d.polygon(pts, outline="black", fill=fill)
    elif shape == "hexagon":
        pts = _polygon_pts(cx, cy, r, 6, rot)
        d.polygon(pts, outline="black", fill=fill)
    elif shape == "diamond":
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pts = _rotate_pts(pts, cx, cy, rot)
        d.polygon(pts, outline="black", fill=fill)


def _polygon_pts(cx, cy, r, sides, rot_deg=0):
    rot = math.radians(rot_deg) - math.pi / 2
    return [
        (cx + r * math.cos(rot + 2 * math.pi * i / sides),
         cy + r * math.sin(rot + 2 * math.pi * i / sides))
        for i in range(sides)
    ]


def _rotate_pts(pts, cx, cy, rot_deg):
    rot = math.radians(rot_deg)
    cos, sin = math.cos(rot), math.sin(rot)
    return [(cx + (x - cx) * cos - (y - cy) * sin, cy + (x - cx) * sin + (y - cy) * cos) for x, y in pts]


def mark_missing(d: ImageDraw.ImageDraw, row: int, col: int):
    cx, cy = cell_center(row, col)
    d.text((cx - 8, cy - 16), "?", fill="black")


# ── Pattern generators (each returns list of (row,col,shape,r,fill,rot) plus missing cell) ──

def pattern_shape_progression(seed: int) -> dict:
    shapes = ["circle", "square", "triangle"]
    img, d = new_canvas()
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c)
                continue
            draw_shape(d, shapes[c], cx, cy, 28)
    return {"img": img, "pattern_type": "shape_progression",
            "description": "Shapes progress left-to-right; what completes the last row?"}


def pattern_size_progression(seed: int) -> dict:
    img, d = new_canvas()
    sizes = [16, 24, 32]
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            draw_shape(d, "circle", cx, cy, sizes[c])
    return {"img": img, "pattern_type": "size_progression",
            "description": "Size grows left-to-right; predict the missing size."}


def pattern_rotation(seed: int) -> dict:
    img, d = new_canvas()
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            draw_shape(d, "triangle", cx, cy, 26, rot=c * 90)
    return {"img": img, "pattern_type": "rotation",
            "description": "Triangle rotates 90° each column."}


def pattern_shading(seed: int) -> dict:
    img, d = new_canvas()
    fills = [None, "lightgrey", "black"]
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            draw_shape(d, "circle", cx, cy, 28, fill=fills[c])
    return {"img": img, "pattern_type": "shading",
            "description": "Shading: empty → half → filled."}


def pattern_count(seed: int) -> dict:
    img, d = new_canvas()
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            n = c + 1
            for i in range(n):
                offset = (i - (n - 1) / 2) * 18
                draw_shape(d, "circle", int(cx + offset), cy, 8)
    return {"img": img, "pattern_type": "count_progression",
            "description": "Count of shapes increases 1→2→3 per column."}


def pattern_shape_size_combined(seed: int) -> dict:
    img, d = new_canvas()
    shapes = ["circle", "square", "triangle"]
    sizes = [18, 26, 34]
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            draw_shape(d, shapes[c], cx, cy, sizes[r])
    return {"img": img, "pattern_type": "shape_size_combined",
            "description": "Shape changes by column, size by row."}


def pattern_reflection(seed: int) -> dict:
    img, d = new_canvas()
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            # Right-pointing triangle mirrors to left-pointing each column
            rot = 0 if c % 2 == 0 else 180
            draw_shape(d, "triangle", cx, cy, 26, rot=rot)
    return {"img": img, "pattern_type": "reflection",
            "description": "Triangle reflects each column."}


def pattern_sides_progression(seed: int) -> dict:
    img, d = new_canvas()
    shapes = ["triangle", "square", "pentagon"]
    for r in range(3):
        for c in range(3):
            cx, cy = cell_center(r, c)
            if (r, c) == (2, 2):
                mark_missing(d, r, c); continue
            draw_shape(d, shapes[c], cx, cy, 26)
    return {"img": img, "pattern_type": "sides_progression",
            "description": "Number of sides increases: 3 → 4 → 5."}


PATTERN_FUNCS = [
    pattern_shape_progression,
    pattern_size_progression,
    pattern_rotation,
    pattern_shading,
    pattern_count,
    pattern_shape_size_combined,
    pattern_reflection,
    pattern_sides_progression,
]


def main():
    manifest = []
    idx = 0
    for fn in PATTERN_FUNCS:
        for variant in range(10):
            data = fn(variant)
            mid = f"matrix_{idx:03d}"
            data["img"].save(OUT / f"{mid}.png")
            manifest.append({
                "id": mid,
                "pattern_type": data["pattern_type"],
                "description": data["description"],
            })
            idx += 1
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {idx} matrices to {OUT}")
    print(f"Manifest: {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
