"""Deterministic Non-Verbal Reasoning generators.

Why deterministic? v1 tried AI-generated NVR and shipped visual-vs-logic
mismatches (the SVG shown didn't match the stated answer). Here, Python
builds BOTH the SVG and the correct answer in the same code path so they
can never drift apart.

Pattern families covered (~13 templates):
  NVR Sequences   — polygon-sides, rotation, count, size sequences
  NVR Odd One Out — color/shape/orientation odd-one-out
  NVR Rotations   — rotation-match, mirror-vs-rotation
  NVR Matrices    — 3×3 grids with row/column patterns
  NVR Analogies   — A:B :: C:?

Each generator returns the schema used elsewhere:
    {type, question, svg_content, image_bank_id, options, correct_index,
     explanation, topic, has_visual}
Options are SVG strings — QuestionCard renders them via SVGOption.
"""
from __future__ import annotations
import math
import random
from typing import Callable

# ── SVG primitives ──────────────────────────────────────────────

CELL = 80  # one cell is 80×80 svg units


def _polygon_points(sides: int, cx: float, cy: float, r: float, rotation_deg: float = 0) -> str:
    pts = []
    for i in range(sides):
        a = math.radians(rotation_deg - 90 + (360 / sides) * i)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def _star_points(cx: float, cy: float, outer_r: float, inner_r: float, rotation_deg: float = 0) -> str:
    pts = []
    for i in range(10):
        a = math.radians(rotation_deg - 90 + 36 * i)
        r = outer_r if i % 2 == 0 else inner_r
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


SHAPE_SIDES = {
    "triangle": 3, "square": 4, "pentagon": 5,
    "hexagon": 6, "heptagon": 7, "octagon": 8,
}


def shape(name: str, color: str = "black", fill: bool = True,
          rotation: float = 0, size: float = 26,
          cx: float = 40, cy: float = 40) -> str:
    """Return an SVG fragment (no <svg> wrapper) for one primitive shape."""
    fill_attr = color if fill else "none"
    sw = 3  # stroke width
    if name == "circle":
        return f'<circle cx="{cx}" cy="{cy}" r="{size}" fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'
    if name in SHAPE_SIDES:
        pts = _polygon_points(SHAPE_SIDES[name], cx, cy, size, rotation)
        return f'<polygon points="{pts}" fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'
    if name == "star":
        pts = _star_points(cx, cy, size, size * 0.42, rotation)
        return f'<polygon points="{pts}" fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'
    if name == "arrow":
        # arrow pointing right at rotation=0 (degrees clockwise)
        # built as a triangle + rectangle composed
        body = (
            f'<g transform="rotate({rotation} {cx} {cy})">'
            f'<rect x="{cx - size}" y="{cy - size*0.15}" width="{size * 1.3}" height="{size * 0.3}" '
            f'fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'
            f'<polygon points="{cx + size*0.3},{cy - size*0.55} {cx + size},{cy} {cx + size*0.3},{cy + size*0.55}" '
            f'fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'
            f'</g>'
        )
        return body
    # fallback — a square
    pts = _polygon_points(4, cx, cy, size, rotation)
    return f'<polygon points="{pts}" fill="{fill_attr}" stroke="{color}" stroke-width="{sw}"/>'


def cell_svg(content: str, bg: str = "#fff", border: bool = True) -> str:
    """Standalone 80×80 cell SVG — used for option buttons. Each option button
    sanitises its SVG independently via SVGOption (svg-only profile)."""
    border_attr = (
        f' style="border:1px solid #94a3b8; background:{bg}; border-radius:4px;"'
        if border else f' style="background:{bg}"'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELL} {CELL}" '
        f'width="80" height="80"{border_attr}>{content}</svg>'
    )


def _frag_from_cell(cell: str) -> str:
    """Strip the outer <svg> wrapper from a cell_svg() string so we can
    embed its drawing inside a composite SVG via <g transform>."""
    if cell.startswith("<svg"):
        inner_start = cell.index(">") + 1
        inner_end = cell.rindex("</svg>")
        return cell[inner_start:inner_end]
    return cell


def _cell_bg_frag(qmark: bool = False) -> str:
    """Background rect that goes behind a cell's drawing. The question-mark
    cell uses a violet-tinted background to flag 'find this'."""
    bg = "#faf5ff" if qmark else "#fff"
    stroke = "#a855f7" if qmark else "#94a3b8"
    return (
        f'<rect x="0" y="0" width="{CELL}" height="{CELL}" fill="{bg}" '
        f'stroke="{stroke}" stroke-width="1" rx="4"/>'
    )


def row_svg(cells: list[str], spacing: int = 12) -> str:
    """Lay cells side by side as a SINGLE SVG using <g transform="translate()">
    — DOMPurify-safe (no nested <svg>) and renders cleanly in every browser."""
    n = len(cells)
    width = n * CELL + (n - 1) * spacing
    parts = []
    for i, cell in enumerate(cells):
        x = i * (CELL + spacing)
        is_q = cell == question_mark_cell()
        parts.append(
            f'<g transform="translate({x},0)">'
            f'{_cell_bg_frag(is_q)}'
            f'{_frag_from_cell(cell)}'
            f'</g>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {CELL}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:380px;display:block;margin:0 auto;">'
        + "".join(parts)
        + "</svg>"
    )


def grid_svg(cells: list[str], cols: int = 3, spacing: int = 8) -> str:
    rows = (len(cells) + cols - 1) // cols
    width = cols * CELL + (cols - 1) * spacing
    height = rows * CELL + (rows - 1) * spacing
    parts = []
    for i, cell in enumerate(cells):
        r, c = divmod(i, cols)
        x, y = c * (CELL + spacing), r * (CELL + spacing)
        is_q = cell == question_mark_cell()
        parts.append(
            f'<g transform="translate({x},{y})">'
            f'{_cell_bg_frag(is_q)}'
            f'{_frag_from_cell(cell)}'
            f'</g>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:300px;display:block;margin:0 auto;">'
        + "".join(parts)
        + "</svg>"
    )


def question_mark_cell() -> str:
    """A cell showing a big violet '?' — marks the slot the child must fill."""
    return cell_svg(
        '<text x="40" y="55" text-anchor="middle" font-size="48" font-weight="bold" '
        'fill="#a855f7" font-family="sans-serif">?</text>',
        bg="#faf5ff",
    )


# ── Distractor helpers ─────────────────────────────────────────

PALETTE = ["#0f172a", "#dc2626", "#2563eb", "#16a34a", "#a855f7", "#f59e0b"]


def _shuffled_options(correct_svg: str, distractor_svgs: list[str], rng: random.Random) -> tuple[list[str], int]:
    """Pick 3 unique distractors, shuffle with correct, return (options, correct_idx)."""
    seen = {correct_svg}
    uniq_distractors = []
    for d in distractor_svgs:
        if d not in seen and len(uniq_distractors) < 3:
            seen.add(d)
            uniq_distractors.append(d)
    while len(uniq_distractors) < 3:
        # pad with random palette variants so we always have 4 options
        filler = cell_svg(shape(rng.choice(list(SHAPE_SIDES.keys()) + ["circle", "star"]),
                                color=rng.choice(PALETTE)))
        if filler not in seen:
            seen.add(filler)
            uniq_distractors.append(filler)
    options = [correct_svg] + uniq_distractors[:3]
    rng.shuffle(options)
    return options, options.index(correct_svg)


def _q(question_text: str, svg_content: str, options: list[str], correct_index: int,
       explanation: str, topic: str) -> dict:
    return {
        "type": "question",
        "question": question_text,
        "svg_content": svg_content,
        "image_bank_id": None,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
        "topic": topic,
        "has_visual": True,
    }


# ── NVR Sequences templates ────────────────────────────────────

POLY_SEQ = ["triangle", "square", "pentagon", "hexagon", "heptagon", "octagon"]


def t_seq_polygon_sides(rng: random.Random) -> dict:
    """3 → 4 → 5 → ? Or 6 → 5 → 4 → ?"""
    direction = rng.choice([1, -1])
    if direction == 1:
        start_idx = rng.randint(0, len(POLY_SEQ) - 4)
    else:
        start_idx = rng.randint(3, len(POLY_SEQ) - 1)
    indices = [start_idx + direction * i for i in range(4)]
    seq_shapes = [POLY_SEQ[i] for i in indices]
    color = rng.choice(PALETTE[:4])
    cells_q = [cell_svg(shape(s, color=color, fill=False, size=24)) for s in seq_shapes[:3]] + [question_mark_cell()]
    svg_content = row_svg(cells_q)
    correct = cell_svg(shape(seq_shapes[3], color=color, fill=False, size=24))
    # Distractors: same shape one step off; random shape from sequence
    distractors = []
    for off in [-1, 1, 2]:
        i = indices[3] + off
        if 0 <= i < len(POLY_SEQ) and i != indices[3]:
            distractors.append(cell_svg(shape(POLY_SEQ[i], color=color, fill=False, size=24)))
    rng.shuffle(distractors)
    options, idx = _shuffled_options(correct, distractors, rng)
    expl = (
        "Each shape adds one more side than the previous."
        if direction == 1
        else "Each shape has one fewer side than the previous."
    )
    return _q("Which shape comes next?", svg_content, options, idx, expl, "NVR Sequences")


def t_seq_rotation(rng: random.Random) -> dict:
    """Same shape, rotating by 45° or 90° each step."""
    step = rng.choice([45, 90])
    name = rng.choice(["arrow", "triangle", "pentagon", "star"])
    start = rng.choice([0, 30, 45, 60])
    color = rng.choice(PALETTE[:4])
    rots = [start + step * i for i in range(4)]
    cells_q = [cell_svg(shape(name, color=color, fill=True, rotation=r, size=24)) for r in rots[:3]] + [question_mark_cell()]
    svg_content = row_svg(cells_q)
    correct = cell_svg(shape(name, color=color, fill=True, rotation=rots[3], size=24))
    # Distractors: rotation off by ±step or by step//2, or wrong shape
    distractors = [
        cell_svg(shape(name, color=color, fill=True, rotation=rots[3] - step, size=24)),
        cell_svg(shape(name, color=color, fill=True, rotation=rots[3] + step, size=24)),
        cell_svg(shape(name, color=color, fill=True, rotation=rots[3] + step // 2, size=24)),
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    return _q(
        "Which shape continues the rotation?",
        svg_content, options, idx,
        f"The shape turns {step}° clockwise each step.",
        "NVR Sequences",
    )


def t_seq_count(rng: random.Random) -> dict:
    """1 dot, 2 dots, 3 dots, ?"""
    direction = rng.choice([1, -1])
    if direction == 1:
        start = rng.randint(1, 3)
    else:
        start = rng.randint(4, 5)
    counts = [start + direction * i for i in range(4)]
    if not all(1 <= c <= 6 for c in counts):
        # safety: clamp + flip
        counts = list(range(1, 5)) if direction == 1 else list(range(5, 1, -1))
    color = rng.choice(PALETTE[:4])
    def dots_cell(n: int) -> str:
        # arrange n small dots in a tidy pattern
        coords = [(20, 40), (40, 40), (60, 40), (20, 20), (60, 20), (40, 60)][:n]
        frags = "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/>' for x, y in coords)
        return cell_svg(frags)

    cells_q = [dots_cell(c) for c in counts[:3]] + [question_mark_cell()]
    svg_content = row_svg(cells_q)
    correct = dots_cell(counts[3])
    distractors = [dots_cell(c) for c in (counts[3] - 1, counts[3] + 1, counts[3] + 2) if 1 <= c <= 6 and c != counts[3]]
    options, idx = _shuffled_options(correct, distractors, rng)
    expl = "Each box has one more dot than the previous." if direction == 1 else "Each box has one fewer dot than the previous."
    return _q("Which comes next?", svg_content, options, idx, expl, "NVR Sequences")


def t_seq_size(rng: random.Random) -> dict:
    """Same shape getting bigger or smaller."""
    direction = rng.choice([1, -1])
    name = rng.choice(list(SHAPE_SIDES.keys()) + ["circle", "star"])
    if direction == 1:
        sizes = [10, 16, 22, 28]
    else:
        sizes = [28, 22, 16, 10]
    color = rng.choice(PALETTE[:4])
    cells_q = [cell_svg(shape(name, color=color, fill=False, size=s)) for s in sizes[:3]] + [question_mark_cell()]
    svg_content = row_svg(cells_q)
    correct = cell_svg(shape(name, color=color, fill=False, size=sizes[3]))
    distractors = [
        cell_svg(shape(name, color=color, fill=False, size=sizes[3] - 6)),
        cell_svg(shape(name, color=color, fill=False, size=sizes[3] + 6)),
        cell_svg(shape(name, color=color, fill=True, size=sizes[3])),  # fill flipped — wrong
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    expl = "Each shape is bigger than the previous." if direction == 1 else "Each shape is smaller than the previous."
    return _q("Which size comes next?", svg_content, options, idx, expl, "NVR Sequences")


# ── NVR Odd One Out templates ──────────────────────────────────

def t_odd_color(rng: random.Random) -> dict:
    """Four same shape, three the same colour, one different."""
    name = rng.choice(list(SHAPE_SIDES.keys()) + ["circle", "star"])
    common = rng.choice(PALETTE[:4])
    others = [c for c in PALETTE if c != common]
    odd_color = rng.choice(others)
    cells = [
        cell_svg(shape(name, color=common, size=24)),
        cell_svg(shape(name, color=common, size=24)),
        cell_svg(shape(name, color=common, size=24)),
        cell_svg(shape(name, color=odd_color, size=24)),
    ]
    # Cells are themselves the options — none is the "question SVG"
    rng.shuffle(cells)
    correct_svg = cell_svg(shape(name, color=odd_color, size=24))
    correct_index = cells.index(correct_svg)
    return _q(
        "Which one is the odd one out?",
        "",  # no separate question image; options are the cells
        cells, correct_index,
        f"Three are the same colour; this one is different.",
        "NVR Odd One Out",
    )


def t_odd_shape(rng: random.Random) -> dict:
    """Four cells: three same shape, one different."""
    common = rng.choice(list(SHAPE_SIDES.keys()) + ["circle", "star"])
    odd = rng.choice([s for s in list(SHAPE_SIDES.keys()) + ["circle", "star"] if s != common])
    color = rng.choice(PALETTE[:4])
    cells = [
        cell_svg(shape(common, color=color, size=24)),
        cell_svg(shape(common, color=color, size=24)),
        cell_svg(shape(common, color=color, size=24)),
        cell_svg(shape(odd, color=color, size=24)),
    ]
    rng.shuffle(cells)
    correct_svg = cell_svg(shape(odd, color=color, size=24))
    correct_index = cells.index(correct_svg)
    return _q(
        "Which one is the odd one out?",
        "",
        cells, correct_index,
        "Three are the same shape; one is different.",
        "NVR Odd One Out",
    )


def t_odd_fill(rng: random.Random) -> dict:
    """Three filled shapes, one outline-only (or vice versa)."""
    name = rng.choice(list(SHAPE_SIDES.keys()) + ["circle", "star"])
    color = rng.choice(PALETTE[:4])
    odd_filled = rng.choice([True, False])
    cells = [
        cell_svg(shape(name, color=color, fill=not odd_filled, size=24)),
        cell_svg(shape(name, color=color, fill=not odd_filled, size=24)),
        cell_svg(shape(name, color=color, fill=not odd_filled, size=24)),
        cell_svg(shape(name, color=color, fill=odd_filled, size=24)),
    ]
    rng.shuffle(cells)
    correct_svg = cell_svg(shape(name, color=color, fill=odd_filled, size=24))
    correct_index = cells.index(correct_svg)
    return _q(
        "Which one is the odd one out?",
        "",
        cells, correct_index,
        "Three are filled in the same way; one is different.",
        "NVR Odd One Out",
    )


# ── NVR Rotations templates ────────────────────────────────────

def t_rotation_match(rng: random.Random) -> dict:
    """Given a base shape, find the option that is the base rotated by X°.
    Text instructions live in question_text since the svg_content is sanitised
    to SVG-only at render time."""
    name = rng.choice(["arrow", "triangle", "pentagon", "star"])
    base_rot = rng.choice([0, 30, 60])
    rotate_by = rng.choice([90, 180, -90, 45])
    color = rng.choice(PALETTE[:4])
    svg_content = cell_svg(shape(name, color=color, rotation=base_rot, size=28))
    correct = cell_svg(shape(name, color=color, rotation=base_rot + rotate_by, size=28))
    distractors = [
        cell_svg(shape(name, color=color, rotation=base_rot - rotate_by, size=28)),
        cell_svg(shape(name, color=color, rotation=base_rot + rotate_by // 2, size=28)),
        cell_svg(shape(name, color=color, rotation=base_rot + rotate_by + 90, size=28)),
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    direction_word = "clockwise" if rotate_by > 0 else "anti-clockwise"
    return _q(
        f"Take this shape and turn it {abs(rotate_by)}° {direction_word}. Which one matches?",
        svg_content, options, idx,
        f"Rotate the shape {abs(rotate_by)}° {direction_word}.",
        "NVR Rotations",
    )


def _analogy_svg(a: str, b: str, c: str) -> str:
    """Pure-SVG layout for 'A → B  |  C → ?', using <g transform> for cell
    placement so DOMPurify can't strip the layout structure."""
    aw = CELL
    arrow_w = 30
    sep_w = 20
    width = aw * 3 + arrow_w * 2 + sep_w + 30

    def at(x: int, cell: str) -> str:
        return (
            f'<g transform="translate({x},0)">'
            f'{_cell_bg_frag()}'
            f'{_frag_from_cell(cell)}'
            f'</g>'
        )

    x_a = 0
    x_arrow1 = x_a + aw
    x_b = x_arrow1 + arrow_w
    x_sep = x_b + aw
    x_c = x_sep + sep_w
    x_arrow2 = x_c + aw
    x_q = x_arrow2 + arrow_w
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {CELL}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:420px;display:block;margin:0 auto;">'
        + at(x_a, a)
        + f'<text x="{x_arrow1 + arrow_w//2}" y="48" text-anchor="middle" font-size="28" font-weight="bold">→</text>'
        + at(x_b, b)
        + f'<text x="{x_sep + sep_w//2}" y="50" text-anchor="middle" font-size="32" fill="#94a3b8">|</text>'
        + at(x_c, c)
        + f'<text x="{x_arrow2 + arrow_w//2}" y="48" text-anchor="middle" font-size="28" font-weight="bold">→</text>'
        + f'<text x="{x_q + 15}" y="55" text-anchor="middle" font-size="40" font-weight="bold" fill="#a855f7">?</text>'
        + '</svg>'
    )


# ── NVR Matrices templates ─────────────────────────────────────

def t_matrix_row_rotation(rng: random.Random) -> dict:
    """3×3 grid; each row rotates a shape by a fixed step. Find the missing cell."""
    name = rng.choice(["arrow", "triangle", "pentagon"])
    step = rng.choice([45, 90])
    color = rng.choice(PALETTE[:4])
    # row r starts at some base, columns rotate by step
    starts = [rng.randint(0, 3) * 30 for _ in range(3)]
    cells: list[str] = []
    missing_idx = rng.randint(0, 8)
    correct_rot = None
    for i in range(9):
        r, c = divmod(i, 3)
        rot = starts[r] + step * c
        if i == missing_idx:
            cells.append(question_mark_cell())
            correct_rot = rot
        else:
            cells.append(cell_svg(shape(name, color=color, rotation=rot, size=22)))
    svg_content = grid_svg(cells, cols=3)
    correct = cell_svg(shape(name, color=color, rotation=correct_rot, size=22))
    distractors = [
        cell_svg(shape(name, color=color, rotation=correct_rot + step, size=22)),
        cell_svg(shape(name, color=color, rotation=correct_rot - step, size=22)),
        cell_svg(shape(name, color=color, rotation=correct_rot + step * 2, size=22)),
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    return _q(
        "Find the missing piece.",
        svg_content, options, idx,
        f"Each row rotates the shape {step}° at each step.",
        "NVR Matrices",
    )


def t_matrix_color_diagonal(rng: random.Random) -> dict:
    """3×3 grid; cells on the same diagonal share a colour. Find missing."""
    name = rng.choice(["circle", "square", "triangle"])
    colors = rng.sample(PALETTE[:5], 3)
    # diagonal mapping: cell (r, c) → colors[(r + c) % 3]
    cells: list[str] = []
    missing_idx = rng.randint(0, 8)
    correct_color = None
    for i in range(9):
        r, c = divmod(i, 3)
        col = colors[(r + c) % 3]
        if i == missing_idx:
            cells.append(question_mark_cell())
            correct_color = col
        else:
            cells.append(cell_svg(shape(name, color=col, size=22)))
    svg_content = grid_svg(cells, cols=3)
    correct = cell_svg(shape(name, color=correct_color, size=22))
    other_colors = [c for c in colors if c != correct_color]
    distractors = [cell_svg(shape(name, color=c, size=22)) for c in other_colors[:2]]
    distractors.append(cell_svg(shape(name, color=rng.choice([c for c in PALETTE if c not in colors]), size=22)))
    options, idx = _shuffled_options(correct, distractors, rng)
    return _q(
        "Find the missing piece.",
        svg_content, options, idx,
        "Look at the diagonals — each shares the same colour.",
        "NVR Matrices",
    )


# ── NVR Analogies templates ────────────────────────────────────

def t_analogy_rotation(rng: random.Random) -> dict:
    """A:B as C:?, where A→B is a rotation."""
    name1 = rng.choice(["arrow", "triangle"])
    name2 = rng.choice(["pentagon", "star", "hexagon"])
    rot_step = rng.choice([90, 45, 180])
    color1 = rng.choice(PALETTE[:4])
    color2 = rng.choice([c for c in PALETTE[:4] if c != color1])
    a = cell_svg(shape(name1, color=color1, rotation=0, size=26))
    b = cell_svg(shape(name1, color=color1, rotation=rot_step, size=26))
    c = cell_svg(shape(name2, color=color2, rotation=0, size=26))
    correct = cell_svg(shape(name2, color=color2, rotation=rot_step, size=26))
    svg_content = _analogy_svg(a, b, c)
    distractors = [
        cell_svg(shape(name2, color=color2, rotation=-rot_step, size=26)),
        cell_svg(shape(name2, color=color2, rotation=rot_step // 2, size=26)),
        cell_svg(shape(name2, color=color1, rotation=rot_step, size=26)),  # wrong colour
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    return _q(
        "Pick the option that fits the pattern.",
        svg_content, options, idx,
        f"The first pair rotates by {rot_step}°. Apply the same rotation to the second.",
        "NVR Analogies",
    )


def t_analogy_fill(rng: random.Random) -> dict:
    """A:B as C:?, where A→B flips fill."""
    name1 = rng.choice(list(SHAPE_SIDES.keys()) + ["circle"])
    name2 = rng.choice([s for s in list(SHAPE_SIDES.keys()) + ["circle", "star"] if s != name1])
    color = rng.choice(PALETTE[:4])
    a = cell_svg(shape(name1, color=color, fill=False, size=26))
    b = cell_svg(shape(name1, color=color, fill=True, size=26))
    c = cell_svg(shape(name2, color=color, fill=False, size=26))
    correct = cell_svg(shape(name2, color=color, fill=True, size=26))
    svg_content = _analogy_svg(a, b, c)
    distractors = [
        cell_svg(shape(name2, color=color, fill=False, size=26)),
        cell_svg(shape(name2, color=rng.choice([cc for cc in PALETTE if cc != color]), fill=True, size=26)),
        cell_svg(shape(name1, color=color, fill=True, size=26)),  # wrong shape
    ]
    options, idx = _shuffled_options(correct, distractors, rng)
    return _q(
        "Pick the option that fits the pattern.",
        svg_content, options, idx,
        "The first pair fills the shape in. Apply the same change to the second.",
        "NVR Analogies",
    )


# ── Template registry per NVR topic ────────────────────────────

TEMPLATES_BY_TOPIC: dict[str, list[Callable]] = {
    "NVR Sequences": [t_seq_polygon_sides, t_seq_rotation, t_seq_count, t_seq_size],
    "NVR Odd One Out": [t_odd_color, t_odd_shape, t_odd_fill],
    "NVR Rotations": [t_rotation_match],
    "NVR Matrices": [t_matrix_row_rotation, t_matrix_color_diagonal],
    "NVR Analogies": [t_analogy_rotation, t_analogy_fill],
}


def generate_nvr(topic: str, count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """Pick `count` templates from the topic's pool and execute each.
    difficulty is currently advisory — patterns are visually consistent across
    levels; harder content can be added by extending the per-template generator."""
    rng = random.Random(seed)
    pool = TEMPLATES_BY_TOPIC.get(topic, [])
    if not pool:
        return []
    out: list[dict] = []
    seen_recent: list = []
    for _ in range(count):
        choices = [t for t in pool if t not in seen_recent[-2:]] or pool
        tpl = rng.choice(choices)
        try:
            out.append(tpl(rng))
            seen_recent.append(tpl)
        except Exception:
            # never let one template tank the whole quest — skip and retry
            continue
    return out
