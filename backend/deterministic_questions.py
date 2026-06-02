"""Deterministic (non-AI) question generators.

Use these for topics where exact arithmetic correctness matters more than
variety — e.g. division drills, number patterns. AI generation is reserved for
topics where natural-language variety is the point.

Each generator returns a list[dict] matching the schema used by AI generation:
    {
        "type": "question",
        "question": str,
        "svg_content": None,
        "image_bank_id": None,
        "options": [str, str, str, str],
        "correct_index": int,  # 0-3
        "explanation": str,
        "topic": str,
        "has_visual": False,
    }
"""
from __future__ import annotations
import random
from typing import Callable


def _shuffle_options(answer: int, distractors: list[int], topic: str,
                     explanation_template: Callable[[int], str],
                     question_text: str, rng: random.Random) -> dict:
    """Build a question dict with answer + distractors shuffled, correct_index pointing at the truth."""
    opts = [answer] + list(distractors)
    rng.shuffle(opts)
    correct_index = opts.index(answer)
    return {
        "type": "question",
        "question": question_text,
        "svg_content": None,
        "image_bank_id": None,
        "options": [str(o) for o in opts],
        "correct_index": correct_index,
        "explanation": explanation_template(answer),
        "topic": topic,
        "has_visual": False,
    }


def _division_distractors(answer: int, divisor: int, dividend: int, rng: random.Random) -> list[int]:
    """Plausible wrong answers near the true answer."""
    candidates = set()
    # off-by-one type errors
    candidates.add(max(1, answer - 1))
    candidates.add(answer + 1)
    # swapped digits if multi-digit
    if answer >= 10:
        s = str(answer)
        swapped = int(s[::-1])
        if swapped != answer and swapped > 0:
            candidates.add(swapped)
    # off-by-divisor (forgot a step)
    if answer - divisor > 0:
        candidates.add(answer - divisor)
    candidates.add(answer + divisor)
    # near-divides (one off from clean)
    near = (dividend + 1) // divisor
    if near != answer and near > 0:
        candidates.add(near)
    near = (dividend - 1) // divisor
    if near != answer and near > 0:
        candidates.add(near)
    # drop the true answer if it leaked in
    candidates.discard(answer)
    pool = sorted(candidates)
    rng.shuffle(pool)
    return pool[:3]


def _division_question(dividend: int, divisor: int, topic: str, rng: random.Random) -> dict:
    """One division question with the standard schema."""
    assert dividend % divisor == 0, f"{dividend} is not divisible by {divisor}"
    answer = dividend // divisor
    distractors = _division_distractors(answer, divisor, dividend, rng)
    # Pad if not enough plausible distractors
    pad_candidates = [answer + k for k in (2, 3, 4, 5, -2, -3, 10, -10)]
    for p in pad_candidates:
        if len(distractors) >= 3: break
        if p > 0 and p != answer and p not in distractors:
            distractors.append(p)

    flavours = [
        f"What is {dividend} ÷ {divisor}?",
        f"{dividend} ÷ {divisor} = ?",
        f"Calculate {dividend} divided by {divisor}.",
        f"Solve: {dividend} ÷ {divisor}",
    ]
    q_text = rng.choice(flavours)

    def explain(ans: int) -> str:
        return (
            f"{dividend} ÷ {divisor} = {ans}. "
            f"Check: {divisor} × {ans} = {divisor * ans}. ✓"
        )

    return _shuffle_options(answer, distractors[:3], topic, explain, q_text, rng)


# ── Public generators ────────────────────────────────────────────────────────

def generate_division_2by1(count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """2-digit ÷ 1-digit divisions, fully divisible. Range scales with difficulty:
      starter:   divisor 2-5,  quotient 2-9  (dividends 4-45)
      challenge: divisor 2-9,  quotient 2-12 (dividends 10-108)
      olympiad:  divisor 2-12, quotient 5-15 (dividends 10-180, sometimes 3-digit)"""
    rng = random.Random(seed)
    dv_lo, dv_hi, q_lo, q_hi = {
        "starter":   (2, 5,  2, 9),
        "challenge": (2, 9,  2, 12),
        "olympiad":  (2, 12, 5, 15),
    }.get(difficulty, (2, 5, 2, 9))
    out = []
    for _ in range(count):
        for _attempt in range(40):
            divisor = rng.randint(dv_lo, dv_hi)
            quotient = rng.randint(q_lo, q_hi)
            dividend = divisor * quotient
            if 10 <= dividend <= 999:
                out.append(_division_question(dividend, divisor, "Division 2÷1", rng))
                break
    return out


def _times_fact_question(rng: random.Random, hi: int = 12) -> dict:
    """One multiplication fact, range scales with difficulty (hi)."""
    a = rng.randint(2, hi)
    b = rng.randint(2, hi)
    answer = a * b
    # plausible distractors
    candidates = set()
    candidates.add(answer + a); candidates.add(answer - a)
    candidates.add(answer + b); candidates.add(answer - b)
    candidates.add(a * (b + 1)); candidates.add(a * (b - 1))
    candidates.discard(answer); candidates = {c for c in candidates if c > 0}
    distractors = sorted(candidates)
    rng.shuffle(distractors)
    distractors = distractors[:3]
    while len(distractors) < 3:
        d = answer + rng.choice([-2, -1, 1, 2, 5, -5, 10, -10])
        if d > 0 and d != answer and d not in distractors:
            distractors.append(d)
    flavours = [
        f"What is {a} × {b}?",
        f"{a} × {b} = ?",
        f"Calculate {a} × {b}.",
        f"Work out {a} times {b}.",
    ]
    q_text = rng.choice(flavours)
    def explain(ans: int) -> str:
        return f"{a} × {b} = {ans}. (Check: {b} × {a} also gives {ans}.)"
    return _shuffle_options(answer, distractors, "Times & Division Mix", explain, q_text, rng)


def generate_division_3by1(count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """3-digit ÷ 1-digit (or 2-digit at olympiad), fully divisible.
      starter:   3-digit ÷ 1-digit, divisor 2-9
      challenge: 3-digit ÷ 1-digit, divisor 2-12, sometimes 4-digit
      olympiad:  3 or 4-digit ÷ 2-digit divisor"""
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        for _attempt in range(80):
            if difficulty == "olympiad":
                divisor = rng.randint(11, 25)
                lo, hi = 200, 9999
            elif difficulty == "challenge":
                divisor = rng.randint(2, 12)
                lo, hi = 100, 9999
            else:  # starter
                divisor = rng.randint(2, 9)
                lo, hi = 100, 999
            min_q = (lo + divisor - 1) // divisor
            max_q = hi // divisor
            if max_q < min_q:
                continue
            quotient = rng.randint(min_q, max_q)
            dividend = divisor * quotient
            if lo <= dividend <= hi:
                out.append(_division_question(dividend, divisor, "Division 3÷1", rng))
                break
    return out


def generate_times_division_mix(count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """Mixed × / ÷ drill, range scales with difficulty:
      starter:   tables 2-9
      challenge: tables 2-12
      olympiad:  tables 2-15
    """
    rng = random.Random(seed)
    times_hi = {"starter": 9, "challenge": 12, "olympiad": 15}.get(difficulty, 9)
    out = []
    for _ in range(count):
        kind = rng.choice(["times", "div2", "div3"])
        if kind == "times":
            out.append(_times_fact_question(rng, hi=times_hi))
        elif kind == "div2":
            # Inline the 2÷1 logic with this rng so seed stays consistent
            for _attempt in range(20):
                divisor = rng.randint(2, 9)
                quotient = rng.randint(2, 9)
                dividend = divisor * quotient
                if 10 <= dividend <= 99:
                    q = _division_question(dividend, divisor, "Times & Division Mix", rng)
                    out.append(q); break
        else:  # div3
            for _attempt in range(50):
                divisor = rng.randint(2, 9)
                min_q = (100 + divisor - 1) // divisor
                max_q = 999 // divisor
                quotient = rng.randint(min_q, max_q)
                dividend = divisor * quotient
                if 100 <= dividend <= 999:
                    q = _division_question(dividend, divisor, "Times & Division Mix", rng)
                    out.append(q); break
    return out


# ── Topic registry — used by _materialise_questions to bypass AI ─────────────

def generate_mental_arithmetic_wrapper(count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """Wrapper delegating to the Schofield-style template library."""
    from mental_arithmetic_templates import generate_mental_arithmetic
    return generate_mental_arithmetic(count, seed=seed, difficulty=difficulty)


DETERMINISTIC_GENERATORS: dict[str, Callable[..., list[dict]]] = {
    "Mental Arithmetic":   generate_mental_arithmetic_wrapper,  # 60+ Schofield-style templates
    "Times & Division Mix": generate_times_division_mix,
    "Division 2÷1":         generate_division_2by1,
    "Division 3÷1":         generate_division_3by1,
}


def generate(topic: str, count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict] | None:
    """Return deterministic questions for `topic`, or None if no generator exists."""
    gen = DETERMINISTIC_GENERATORS.get(topic)
    if gen is None:
        return None
    return gen(count, seed=seed, difficulty=difficulty)
