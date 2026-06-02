"""Year 3 Mental Arithmetic templates — Schofield & Sims MA1 style.

Each template is a deterministic generator. Picks parameters in Year 3 ranges
(numbers ≤ 1000, tables 2-10, simple fractions, money to ~£2), computes the
canonical answer, builds plausible distractors, returns the standard schema.

To add a template:
  1. Write `def t_<name>(rng) -> dict`
  2. Add it to TEMPLATES list at the bottom

The generator picks templates uniformly at random for each question.

Difficulty progression (future work): each template can accept a `difficulty`
arg to scale ranges for Year 4+ when Samihan ages up.
"""
from __future__ import annotations
import random
from typing import Callable

NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}
TENS_WORDS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
              6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}
TEEN_WORDS = {11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
              15: "fifteen", 16: "sixteen", 17: "seventeen",
              18: "eighteen", 19: "nineteen"}
MONTHS_31 = {"January", "March", "May", "July", "August", "October", "December"}
MONTHS_30 = {"April", "June", "September", "November"}
MONTH_LIST = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]


def _num_to_words(n: int) -> str:
    if n in NUMBER_WORDS: return NUMBER_WORDS[n]
    if n in TEEN_WORDS: return TEEN_WORDS[n]
    if n < 100:
        tens = (n // 10) * 10
        ones = n - tens
        return TENS_WORDS[n // 10] + ("" if ones == 0 else "-" + NUMBER_WORDS[ones])
    if n < 1000:
        hundreds = n // 100
        rest = n - hundreds * 100
        if rest == 0:
            return NUMBER_WORDS[hundreds] + " hundred"
        return NUMBER_WORDS[hundreds] + " hundred and " + _num_to_words(rest)
    raise ValueError(n)


def _build_q(answer, distractors, question_text, explanation, rng,
             topic="Mental Arithmetic", answer_str: str | None = None,
             distractor_strs: list[str] | None = None) -> dict:
    """Common builder. `answer_str` / `distractor_strs` override numeric stringification."""
    a_str = answer_str if answer_str is not None else str(answer)
    if distractor_strs is None:
        d_strs = [str(d) for d in distractors]
    else:
        d_strs = distractor_strs
    opts = [a_str] + d_strs
    rng.shuffle(opts)
    return {
        "type": "question",
        "question": question_text,
        "svg_content": None,
        "image_bank_id": None,
        "options": opts,
        "correct_index": opts.index(a_str),
        "explanation": explanation,
        "topic": topic,
        "has_visual": False,
    }


def _near(answer: int, rng: random.Random, count: int = 3, span: int = 10) -> list[int]:
    """Plausible numeric distractors near `answer`."""
    candidates = set()
    for d in (-1, 1, -2, 2, -span, span, -span // 2, span // 2):
        c = answer + d
        if c >= 0 and c != answer:
            candidates.add(c)
    # swapped-digit if multi-digit
    if answer >= 10:
        s = str(answer)
        sw = int(s[::-1])
        if sw != answer and sw > 0:
            candidates.add(sw)
    pool = sorted(candidates)
    rng.shuffle(pool)
    out = pool[:count]
    while len(out) < count:
        x = answer + rng.choice([-5, -3, 3, 5, 7, -7, 11, -11])
        if x > 0 and x != answer and x not in out:
            out.append(x)
    return out


# ════════════════════════ ARITHMETIC ═════════════════════════

def t_addition_3digit_plus_1digit(rng):
    a = rng.randint(100, 900); b = rng.randint(2, 9)
    ans = a + b
    return _build_q(ans, _near(ans, rng), f"{a} + {b} = ?",
                    f"{a} + {b} = {ans}.", rng)


def t_addition_place_value(rng):
    h = rng.randint(1, 9); t = rng.randint(1, 9); o = rng.randint(1, 9)
    ans = h * 100 + t * 10 + o
    return _build_q(ans, _near(ans, rng, span=100),
                    f"{h*100} + {t*10} + {o} = ?",
                    f"{h*100} + {t*10} + {o} = {ans}.", rng)


def t_addition_three_terms(rng):
    a = rng.randint(5, 30); b = rng.randint(5, 30); c = rng.randint(5, 30)
    ans = a + b + c
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Find the total of {a}, {b} and {c}.",
                    f"{a} + {b} + {c} = {ans}.", rng)


def t_subtraction_3digit_minus_tens(rng):
    a = rng.randint(200, 900); b = rng.randint(2, 9) * 10
    ans = a - b
    return _build_q(ans, _near(ans, rng, span=10), f"{a} - {b} = ?",
                    f"{a} - {b} = {ans}.", rng)


def t_subtraction_2digit(rng):
    a = rng.randint(20, 99); b = rng.randint(2, min(20, a - 1))
    ans = a - b
    return _build_q(ans, _near(ans, rng), f"{a} - {b} = ?",
                    f"{a} - {b} = {ans}.", rng)


# ════════════════════════ ORDER OF OPS ═════════════════════════

def t_paren_mul_then_add(rng):
    a = rng.randint(2, 9); b = rng.randint(2, 9); c = rng.randint(1, 9)
    ans = a * b + c
    return _build_q(ans, _near(ans, rng), f"({a} × {b}) + {c} = ?",
                    f"({a} × {b}) + {c} = {a*b} + {c} = {ans}.", rng)


def t_missing_divisor(rng):
    quotient = rng.randint(2, 9); divisor = rng.randint(2, 9)
    dividend = quotient * divisor
    return _build_q(divisor, _near(divisor, rng, span=2),
                    f"{dividend} ÷ ? = {quotient}",
                    f"{dividend} ÷ {divisor} = {quotient}. Check: {divisor} × {quotient} = {dividend}.",
                    rng)


def t_missing_factor(rng):
    a = rng.randint(2, 9); answer = rng.randint(2, 12)
    product = a * answer
    return _build_q(answer, _near(answer, rng, span=2),
                    f"? × {a} = {product}",
                    f"{answer} × {a} = {product}.", rng)


def t_repeated_multiplication_10s(rng):
    n = rng.choice([2, 3])  # 10×10 = 100, 10×10×10 = 1000
    ans = 10 ** n
    expr = " × ".join(["10"] * n)
    return _build_q(ans, [10 ** (n - 1), 10 ** (n + 1), ans + 100][:3],
                    f"{expr} = ?", f"{expr} = {ans}.", rng)


# ════════════════════════ PLACE VALUE ═════════════════════════

def t_place_value_decompose_tens_ones(rng):
    tens = rng.randint(2, 9); ones = rng.randint(1, 9)
    n = tens * 10 + ones
    # answer = "T tens, O ones"  (free-form-ish; we present as choices)
    correct = f"{tens} tens, {ones} ones"
    distractors = [
        f"{ones} tens, {tens} ones",
        f"{tens} tens, {ones-1 if ones > 1 else ones+1} ones",
        f"{tens-1 if tens > 1 else tens+1} tens, {ones} ones",
    ]
    return _build_q(None, None,
                    f"{n} = ___ tens and ___ ones",
                    f"{n} = {tens} tens and {ones} ones.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_place_value_write_digits(rng):
    n = rng.randint(100, 999)
    correct = str(n)
    words = _num_to_words(n)
    distractors = [
        str(n // 10),                    # missing one digit
        str(n + 100 if n + 100 < 1000 else n - 100),
        str(int(str(n)[::-1])),          # swapped
    ]
    return _build_q(None, None,
                    f"Write in digits: {words}",
                    f"{words} = {n}.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_increase_n_times(rng):
    n = rng.randint(2, 9); times = rng.choice([3, 4, 5])
    ans = n * times
    return _build_q(ans, _near(ans, rng),
                    f"Increase {n} {times} times.",
                    f"{n} × {times} = {ans}.", rng)


# ════════════════════════ FRACTIONS ═════════════════════════

def t_fraction_of_money(rng):
    denom = rng.choice([2, 3, 4, 5])
    quotient = rng.randint(2, 9)
    amount = denom * quotient  # ensures clean division
    ans = quotient
    return _build_q(ans, _near(ans, rng, span=2),
                    f"1/{denom} of {amount}p = ?",
                    f"1/{denom} of {amount}p = {amount} ÷ {denom} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=2)])


def t_fraction_reasoning_three_quarters(rng):
    quarter = rng.randint(2, 9)
    three_q = quarter * 3
    return _build_q(quarter, _near(quarter, rng),
                    f"3/4 of Chloe's money is {three_q}p. What is 1/4 of her money?",
                    f"3/4 = {three_q}p, so 1/4 = {three_q} ÷ 3 = {quarter}p.",
                    rng, answer_str=f"{quarter}p",
                    distractor_strs=[f"{d}p" for d in _near(quarter, rng)])


def t_quarters_in_mixed(rng):
    whole = rng.randint(2, 9)
    has_half = rng.choice([True, False])
    if has_half:
        ans = whole * 4 + 2  # extra ½ = 2 quarters
        mixed = f"{whole}½"
    else:
        ans = whole * 4
        mixed = str(whole)
    return _build_q(ans, _near(ans, rng, span=2),
                    f"How many quarters in {mixed}?",
                    f"{mixed} = {ans} quarters (each whole = 4 quarters).",
                    rng)


def t_fraction_tank_remaining(rng):
    capacity = rng.choice([12, 15, 18, 20, 24, 30, 60])
    denom = rng.choice([2, 3, 4]) if capacity % rng.choice([2, 3, 4]) == 0 else 2
    # pick denom that divides capacity
    for d in (2, 3, 4, 5):
        if capacity % d == 0:
            denom = d; break
    full = capacity // denom
    remaining = capacity - full
    return _build_q(remaining, _near(remaining, rng, span=2),
                    f"A tank holds {capacity}L. It is 1/{denom} full. How many more litres to fill it?",
                    f"1/{denom} of {capacity}L = {full}L. To fill: {capacity} - {full} = {remaining}L.",
                    rng, answer_str=f"{remaining}L",
                    distractor_strs=[f"{d}L" for d in _near(remaining, rng, span=2)])


# ════════════════════════ UNITS ═════════════════════════

def t_unit_cm_to_m_cm(rng):
    m = rng.randint(1, 9); cm = rng.randint(0, 99)
    total = m * 100 + cm
    correct = f"{m}m {cm}cm"
    distractors = [
        f"{m}m {cm + 10 if cm < 90 else cm - 10}cm",
        f"{m+1}m {cm}cm",
        f"{m}m {99 - cm}cm",
    ]
    return _build_q(None, None,
                    f"{total}cm = ___ m ___ cm",
                    f"{total}cm = {m}m and {cm}cm (since 1m = 100cm).",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_unit_m_cm_to_cm(rng):
    m = rng.randint(1, 9); cm = rng.randint(1, 99)
    ans = m * 100 + cm
    return _build_q(ans, _near(ans, rng, span=10),
                    f"{m}m {cm}cm = ? cm",
                    f"{m}m = {m*100}cm, plus {cm}cm = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng, span=10)])


def t_unit_m_with_half_to_cm(rng):
    whole = rng.randint(1, 5)
    ans = whole * 100 + 50
    return _build_q(ans, _near(ans, rng, span=50),
                    f"How many cm in {whole}½ m?",
                    f"{whole}½ m = {whole * 100} + 50 = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng, span=50)])


# ════════════════════════ CURRENCY ═════════════════════════

def t_currency_pounds_to_pence(rng):
    pounds = rng.randint(1, 9); pence = rng.randint(1, 99)
    ans = pounds * 100 + pence
    return _build_q(ans, _near(ans, rng, span=10),
                    f"£{pounds}.{pence:02d} = ? p",
                    f"£1 = 100p, so £{pounds}.{pence:02d} = {pounds*100} + {pence} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=10)])


def t_currency_pence_to_pounds(rng):
    pounds = rng.randint(1, 5); pence = rng.choice([5, 10, 15, 20, 25, 50, 75, 80])
    correct = f"£{pounds}.{pence:02d}"
    total_p = pounds * 100 + pence
    distractors = [
        f"£{pounds}.{(pence+10)%100:02d}",
        f"£{pounds + 1}.{pence:02d}",
        f"£0.{(total_p // 10) % 100:02d}",
    ]
    return _build_q(None, None,
                    f"Write as pounds: {pounds} pounds {pence} pence",
                    f"{pounds} pounds {pence} pence = £{pounds}.{pence:02d}.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_money_subtract_from_pound(rng):
    pence = rng.randint(5, 95)
    ans = 100 - pence
    return _build_q(ans, _near(ans, rng, span=10),
                    f"£1.00 - {pence}p = ? p",
                    f"£1.00 = 100p. 100 - {pence} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=10)])


def t_money_add_to_pounds(rng):
    base_p = rng.randint(101, 195)
    add_p = rng.choice([5, 10, 15, 20, 25, 30, 40, 50])
    ans = base_p + add_p
    pounds = base_p // 100; pence = base_p % 100
    return _build_q(ans, _near(ans, rng, span=10),
                    f"To £{pounds}.{pence:02d} add {add_p}p. Total in p?",
                    f"£{pounds}.{pence:02d} = {base_p}p. {base_p} + {add_p} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=10)])


def t_nearest_to_pound(rng):
    # generate 4 close-to-£1 amounts, one closest
    amounts_p = []
    correct = rng.choice([95, 97, 98, 102, 103, 105])  # candidate "closest"
    amounts_p.append(correct)
    while len(amounts_p) < 4:
        c = rng.choice([80, 85, 90, 110, 115, 120, 125])
        if c != correct and c not in amounts_p:
            amounts_p.append(c)
    # Verify correct is genuinely nearest
    correct = min(amounts_p, key=lambda x: abs(x - 100))
    def fmt(p):
        return f"£{p//100}.{p%100:02d}" if p >= 100 else f"{p}p"
    rng.shuffle(amounts_p)
    return {
        "type": "question",
        "question": f"Which of these amounts of money is nearest to £1.00?",
        "svg_content": None, "image_bank_id": None,
        "options": [fmt(p) for p in amounts_p],
        "correct_index": amounts_p.index(correct),
        "explanation": f"|{fmt(correct)} - £1.00| = {abs(correct-100)}p — closest to £1.00.",
        "topic": "Mental Arithmetic", "has_visual": False,
    }


# ════════════════════════ TIME ═════════════════════════

def t_half_hour_plus_min(rng):
    extra = rng.choice([5, 10, 15, 20, 25])
    ans = 30 + extra
    return _build_q(ans, _near(ans, rng, span=5),
                    f"1/2 hour + {extra}min = ? min",
                    f"1/2 hour = 30 min. 30 + {extra} = {ans} min.",
                    rng, answer_str=f"{ans} min",
                    distractor_strs=[f"{d} min" for d in _near(ans, rng, span=5)])


def t_shop_duration(rng):
    start_h = rng.randint(9, 11); start_m = rng.choice([0, 30])
    dur_h = rng.randint(1, 4); dur_m = rng.choice([0, 30])
    end_h = start_h + dur_h + (1 if start_m + dur_m >= 60 else 0)
    end_m = (start_m + dur_m) % 60
    correct = f"{dur_h}h {dur_m}min" if dur_m else f"{dur_h}h"
    distractors = [
        f"{dur_h+1}h {dur_m}min",
        f"{dur_h}h {(dur_m+30)%60}min",
        f"{max(1,dur_h-1)}h {dur_m}min",
    ]
    return _build_q(None, None,
                    f"A shop opens at {start_h}:{start_m:02d} and closes at {end_h}:{end_m:02d}. How long is it open?",
                    f"From {start_h}:{start_m:02d} to {end_h}:{end_m:02d} is {correct}.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_days_in_month(rng):
    month = rng.choice(MONTH_LIST)
    if month == "February":
        ans = 28; distractors_n = [29, 30, 31]
    elif month in MONTHS_31:
        ans = 31; distractors_n = [28, 29, 30]
    else:
        ans = 30; distractors_n = [28, 29, 31]
    return _build_q(ans, distractors_n[:3],
                    f"How many days in {month}?",
                    f"{month} has {ans} days.", rng)


def t_month_offset(rng):
    start_idx = rng.randint(0, 11)
    offset = rng.randint(2, 6)
    ans_idx = (start_idx + offset) % 12
    correct = MONTH_LIST[ans_idx]
    distractors = []
    while len(distractors) < 3:
        i = rng.randint(0, 11)
        if i != ans_idx and MONTH_LIST[i] not in distractors:
            distractors.append(MONTH_LIST[i])
    return _build_q(None, None,
                    f"Name the month that is {offset} months after {MONTH_LIST[start_idx]}.",
                    f"{MONTH_LIST[start_idx]} + {offset} months = {correct}.",
                    rng, answer_str=correct, distractor_strs=distractors)


# ════════════════════════ WORD PROBLEMS ═════════════════════════

def t_money_started_with(rng):
    a = rng.choice([5, 8, 10, 12, 15, 20]); b = rng.choice([5, 8, 10, 12])
    left = rng.choice([20, 30, 40, 50])
    started = a + b + left
    return _build_q(started, _near(started, rng, span=5),
                    f"Kieran spent {a}p and {b}p. He had {left}p left. How much had he at first?",
                    f"{a} + {b} + {left} = {started}p.",
                    rng, answer_str=f"{started}p",
                    distractor_strs=[f"{d}p" for d in _near(started, rng, span=5)])


def t_rows_division(rng):
    rows = rng.randint(3, 9); per_row = rng.choice([5, 10, 12])
    total = rows * per_row
    return _build_q(rows, _near(rows, rng, span=2),
                    f"{total} chairs are arranged in rows of {per_row}. How many rows?",
                    f"{total} ÷ {per_row} = {rows} rows.", rng)


def t_share_equally(rng):
    people = rng.choice([2, 3, 4, 5, 6])
    each = rng.randint(3, 12)
    total = people * each
    return _build_q(each, _near(each, rng),
                    f"Share {total}p equally among {people} friends. How much each?",
                    f"{total} ÷ {people} = {each}p each.",
                    rng, answer_str=f"{each}p",
                    distractor_strs=[f"{d}p" for d in _near(each, rng)])


def t_unit_cost_scaled(rng):
    items_a = rng.choice([5, 10]); cost_a = items_a * rng.choice([5, 10, 6, 8])
    items_b = rng.randint(2, items_a - 1)
    cost_b = (cost_a // items_a) * items_b
    return _build_q(cost_b, _near(cost_b, rng),
                    f"{items_a} biscuits cost {cost_a}p. How much for {items_b} biscuits?",
                    f"{cost_a} ÷ {items_a} = {cost_a//items_a}p each. {items_b} × {cost_a//items_a} = {cost_b}p.",
                    rng, answer_str=f"{cost_b}p",
                    distractor_strs=[f"{d}p" for d in _near(cost_b, rng)])


# ════════════════════════ GEOMETRY ═════════════════════════

def t_square_perimeter_to_side(rng):
    side = rng.randint(4, 15)
    perim = side * 4
    return _build_q(side, _near(side, rng),
                    f"The four sides of a square total {perim}cm. Find the length of one side.",
                    f"{perim} ÷ 4 = {side}cm.",
                    rng, answer_str=f"{side}cm",
                    distractor_strs=[f"{d}cm" for d in _near(side, rng)])


def t_line_segment_difference(rng):
    ab = rng.randint(15, 30); ac = rng.randint(5, ab - 3)
    cb = ab - ac
    return _build_q(cb, _near(cb, rng),
                    f"Line AB is {ab}cm long. Line AC is {ac}cm long. How long is CB?",
                    f"CB = AB - AC = {ab} - {ac} = {cb}cm.",
                    rng, answer_str=f"{cb}cm",
                    distractor_strs=[f"{d}cm" for d in _near(cb, rng)])


# ════════════════════════ SEQUENCES ═════════════════════════

def t_sequence_extend_asc(rng):
    start = rng.randint(50, 200); step = rng.choice([2, 5, 10, 25])
    seq = [start + i * step for i in range(4)]
    ans = start + 4 * step
    return _build_q(ans, _near(ans, rng, span=step),
                    f"Complete this sequence: {', '.join(map(str, seq))}, ?",
                    f"Step = {step}. Next: {seq[-1]} + {step} = {ans}.", rng)


def t_sequence_extend_desc(rng):
    start = rng.randint(300, 500); step = rng.choice([50, 100])
    seq = [start - i * step for i in range(4)]
    ans = start - 4 * step
    return _build_q(ans, _near(ans, rng, span=step),
                    f"Complete this sequence: {', '.join(map(str, seq))}, ?",
                    f"Step = -{step}. Next: {seq[-1]} - {step} = {ans}.", rng)


# ════════════════════════ COMPARISON ═════════════════════════

def t_inequality_fill(rng):
    a = rng.randint(100, 900); b = a + rng.choice([-5, -3, -1, 1, 3, 5])
    correct = "<" if a < b else (">" if a > b else "=")
    return _build_q(None, None,
                    f"Write < or > to make the statement true: {a} ___ {b}",
                    f"{a} {correct} {b}.",
                    rng, answer_str=correct, distractor_strs=["=", "≤", "≥"] if correct != "=" else ["<", ">", "≤"])


def t_difference_known_smaller(rng):
    smaller = rng.randint(10, 50); diff = rng.randint(3, 20)
    larger = smaller + diff
    return _build_q(larger, _near(larger, rng),
                    f"The difference between two numbers is {diff}. The smaller number is {smaller}. What is the larger?",
                    f"larger = smaller + difference = {smaller} + {diff} = {larger}.", rng)


def t_three_numbers_find_third(rng):
    a = rng.choice([9, 18, 25, 50]); b = rng.choice([100, 200, 300, 500, 600])
    third = rng.randint(10, 100)
    total = a + b + third
    return _build_q(third, _near(third, rng),
                    f"Three numbers add up to {total}. One number is {a} and another is {b}. Find the third.",
                    f"{total} - {a} - {b} = {third}.", rng)


# ════════════════════════ EXTENDED SET (Schofield Tests 1-12) ═══════════════

def t_n_less_than(rng):
    """What number is X less than Y?"""
    less_by = rng.randint(5, 50); base = rng.randint(50, 999)
    ans = base - less_by
    return _build_q(ans, _near(ans, rng, span=5),
                    f"What number is {less_by} less than {base}?",
                    f"{base} - {less_by} = {ans}.", rng)


def t_n_more_than(rng):
    """What number is X more than Y?"""
    more_by = rng.choice([5, 10, 20, 50, 100, 200])
    base = rng.randint(50, 800)
    ans = base + more_by
    return _build_q(ans, _near(ans, rng, span=10),
                    f"What number is {more_by} more than {base}?",
                    f"{base} + {more_by} = {ans}.", rng)


def t_increase_money(rng):
    base = rng.randint(50, 150); inc = rng.choice([5, 10, 15, 20, 25, 30])
    ans = base + inc
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Increase {base}p by {inc}p.",
                    f"{base} + {inc} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=5)])


def t_decrease_money(rng):
    base_p = rng.randint(105, 250)
    dec_p = rng.choice([10, 15, 20, 25, 30, 40, 50])
    ans = base_p - dec_p
    pounds = base_p // 100; pence = base_p % 100
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Decrease £{pounds}.{pence:02d} by {dec_p}p. Answer in p.",
                    f"£{pounds}.{pence:02d} = {base_p}p. {base_p} - {dec_p} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=5)])


def t_multi_coin_total(rng):
    """E.g. 'Four 5ps and nine 2ps = ___ p'"""
    a_count = rng.randint(2, 10); a_value = rng.choice([2, 5, 10, 20])
    b_count = rng.randint(2, 10); b_value = rng.choice([1, 2, 5])
    while b_value == a_value:
        b_value = rng.choice([1, 2, 5])
    ans = a_count * a_value + b_count * b_value
    return _build_q(ans, _near(ans, rng),
                    f"{a_count} × {a_value}ps and {b_count} × {b_value}ps = ? p",
                    f"({a_count} × {a_value}) + ({b_count} × {b_value}) = {a_count*a_value} + {b_count*b_value} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng)])


def t_place_value_missing(rng):
    """582 = 500 + ? + 2 — find the missing tens place."""
    h = rng.randint(1, 9); t = rng.randint(1, 9); o = rng.randint(1, 9)
    n = h * 100 + t * 10 + o
    return _build_q(t * 10, _near(t * 10, rng, span=10),
                    f"What is the missing number? {n} = {h*100} + ___ + {o}",
                    f"{h*100} + {t*10} + {o} = {n}, so the missing number is {t*10}.", rng)


def t_change_from(rng):
    spend = rng.randint(5, 45); base = rng.choice([20, 50, 100, 200])
    while spend >= base: spend = rng.randint(5, base - 5)
    ans = base - spend
    return _build_q(ans, _near(ans, rng),
                    f"How much change out of {base}p after spending {spend}p?",
                    f"{base} - {spend} = {ans}p change.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng)])


def t_reverse_change(rng):
    """Spent how much if change is Xp from Yp?"""
    base = rng.choice([50, 100, 200]); change = rng.randint(5, base - 5)
    ans = base - change
    return _build_q(ans, _near(ans, rng),
                    f"How much was spent if the change was {change}p out of {base}p?",
                    f"Spent = {base} - {change} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng)])


def t_multiple_of_n(rng):
    """Which of these is a multiple of N?"""
    n = rng.choice([3, 4, 5, 6, 7, 8])
    correct = n * rng.randint(3, 12)
    # 3 non-multiples nearby
    distractors = []
    while len(distractors) < 3:
        cand = correct + rng.choice([-7, -5, -3, -1, 1, 3, 5, 7])
        if cand > 0 and cand % n != 0 and cand != correct and cand not in distractors:
            distractors.append(cand)
    return _build_q(correct, distractors,
                    f"Which of these is a multiple of {n}?",
                    f"{correct} ÷ {n} = {correct//n} with no remainder, so {correct} is a multiple of {n}.",
                    rng)


def t_coin_equivalence(rng):
    """How many 5ps are worth three 10ps?"""
    target_coin = rng.choice([5, 10, 20, 50])
    source_coin = rng.choice([10, 20, 50])
    while source_coin == target_coin or source_coin < target_coin:
        source_coin = rng.choice([10, 20, 50])
    source_count = rng.randint(2, 6)
    total = source_count * source_coin
    target_count = total // target_coin
    if total % target_coin != 0:
        # fall back to a clean case
        source_count = 3; source_coin = 10; target_coin = 5
        total = 30; target_count = 6
    return _build_q(target_count, _near(target_count, rng, span=2),
                    f"How many {target_coin}ps are worth {source_count} × {source_coin}ps?",
                    f"{source_count} × {source_coin}p = {total}p. {total} ÷ {target_coin} = {target_count} coins.",
                    rng)


def t_mass_subtract_with_units(rng):
    """1kg - 200g = ? g"""
    g = rng.choice([100, 200, 250, 300, 400, 500, 750])
    ans = 1000 - g
    return _build_q(ans, _near(ans, rng, span=50),
                    f"1kg - {g}g = ? g",
                    f"1kg = 1000g. 1000 - {g} = {ans}g.",
                    rng, answer_str=f"{ans}g",
                    distractor_strs=[f"{d}g" for d in _near(ans, rng, span=50)])


def t_mass_kg_g_to_g(rng):
    """1kg 40g = ? g"""
    kg = rng.randint(1, 4); g = rng.choice([40, 50, 100, 150, 200, 250, 400])
    ans = kg * 1000 + g
    return _build_q(ans, _near(ans, rng, span=50),
                    f"{kg}kg {g}g = ? g",
                    f"{kg}kg = {kg*1000}g. {kg*1000} + {g} = {ans}g.",
                    rng, answer_str=f"{ans}g",
                    distractor_strs=[f"{d}g" for d in _near(ans, rng, span=50)])


def t_days_in_months_total(rng):
    """How many days in May, June and July?"""
    starts = [
        ("May, June and July", 31 + 30 + 31),
        ("April and May", 30 + 31),
        ("January and February (non-leap)", 31 + 28),
        ("August and September", 31 + 30),
        ("October, November and December", 31 + 30 + 31),
        ("June, July and August", 30 + 31 + 31),
    ]
    label, ans = rng.choice(starts)
    return _build_q(ans, _near(ans, rng, span=3),
                    f"How many days in {label} in total?",
                    f"Total = {ans} days.", rng)


def t_fraction_of_whole(rng):
    """3/4 of 16"""
    denom = rng.choice([2, 3, 4, 5])
    multiple = rng.randint(2, 9)
    whole = denom * multiple
    numerator = rng.randint(1, denom - 1) if denom > 1 else 1
    ans = (whole // denom) * numerator
    return _build_q(ans, _near(ans, rng),
                    f"What is {numerator}/{denom} of {whole}?",
                    f"{whole} ÷ {denom} = {whole//denom}. {numerator} × {whole//denom} = {ans}.",
                    rng)


def t_value_of_digit(rng):
    """Value of 4 in 648"""
    digits = [rng.randint(1, 9) for _ in range(3)]
    pos = rng.choice([0, 1, 2])  # 0=hundreds, 1=tens, 2=ones
    n = digits[0]*100 + digits[1]*10 + digits[2]
    digit = digits[pos]
    place = [100, 10, 1][pos]
    place_name = ["hundreds", "tens", "ones"][pos]
    ans = digit * place
    return _build_q(ans, _near(ans, rng, span=place),
                    f"What is the value of the digit {digit} in {n}?",
                    f"In {n}, the {digit} is in the {place_name} place. Value = {digit} × {place} = {ans}.",
                    rng)


def t_price_per_kg_fractional(rng):
    """Carrots cost 70p per kg. How much for 1½ kg?"""
    price = rng.choice([20, 30, 40, 50, 60, 70, 80, 100])
    half = rng.choice([True, False])
    whole = rng.randint(1, 3)
    if half:
        ans = price * whole + price // 2
        amount = f"{whole}½ kg"
    else:
        ans = price * (whole + 1)
        amount = f"{whole + 1} kg"
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Carrots cost {price}p per kg. How much for {amount}?",
                    f"Cost = {price}p × {amount} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=5)])


def t_hundreds_tens_ones(rng):
    """239 = ? hundreds ? tens ? ones"""
    h = rng.randint(1, 9); t = rng.randint(0, 9); o = rng.randint(0, 9)
    n = h * 100 + t * 10 + o
    correct = f"{h} hundreds, {t} tens, {o} ones"
    distractors = [
        f"{o} hundreds, {t} tens, {h} ones",
        f"{h} hundreds, {o} tens, {t} ones",
        f"{t} hundreds, {h} tens, {o} ones",
    ]
    return _build_q(None, None,
                    f"{n} = ? hundreds, ? tens, ? ones",
                    f"{n} = {h} hundreds, {t} tens, {o} ones.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_operator_selection(rng):
    """13 - 5 = 8 ? 1 — find the missing operator"""
    a = rng.randint(2, 12); op = rng.choice(['+', '-', '×', '÷'])
    if op == '+':
        b = rng.randint(2, 9); result = a + b
    elif op == '-':
        b = rng.randint(1, a - 1); result = a - b
    elif op == '×':
        b = rng.randint(2, 5); result = a * b
    else:  # ÷
        # ensure clean division
        b = rng.choice([2, 3, 4, 5]); a = b * rng.randint(2, 6); result = a // b
    correct = op
    return _build_q(None, None,
                    f"Write the missing sign +, -, × or ÷: {a} ? {b} = {result}",
                    f"{a} {op} {b} = {result}.",
                    rng, answer_str=correct, distractor_strs=[s for s in ['+','-','×','÷'] if s != op])


def t_repeated_addition_as_mult(rng):
    """8 + 8 + 8 + 8 + 8 = ?"""
    n = rng.randint(2, 9); reps = rng.randint(3, 6)
    ans = n * reps
    plus_chain = " + ".join([str(n)] * reps)
    return _build_q(ans, _near(ans, rng),
                    f"{plus_chain} = ?",
                    f"{n} added {reps} times = {n} × {reps} = {ans}.", rng)


def t_mixed_hour_to_min(rng):
    """1½ hour = ? min"""
    whole = rng.randint(1, 3); has_half = rng.choice([True, False])
    ans = whole * 60 + (30 if has_half else 0)
    text = f"{whole}½" if has_half else str(whole)
    return _build_q(ans, _near(ans, rng, span=15),
                    f"{text} hour{'s' if whole > 1 else ''} = ? minutes",
                    f"1 hour = 60 minutes. {text} h = {ans} minutes.",
                    rng, answer_str=f"{ans} min",
                    distractor_strs=[f"{d} min" for d in _near(ans, rng, span=15)])


def t_three_quarters_of_hour(rng):
    """Three-quarters of 1 hour = ? minutes"""
    fracs = [(1, 4, 15), (1, 3, 20), (1, 2, 30), (2, 3, 40), (3, 4, 45)]
    num, den, ans = rng.choice(fracs)
    return _build_q(ans, _near(ans, rng, span=5),
                    f"{num}/{den} of an hour = ? minutes",
                    f"1 hour = 60 min. {num}/{den} × 60 = {ans} min.",
                    rng, answer_str=f"{ans} min",
                    distractor_strs=[f"{d} min" for d in _near(ans, rng, span=5)])


def t_kg_to_g_fraction(rng):
    """How many grams in 1½ kg?"""
    whole = rng.randint(1, 3); has_half = rng.choice([True, False])
    ans = whole * 1000 + (500 if has_half else 0)
    text = f"{whole}½" if has_half else str(whole)
    return _build_q(ans, _near(ans, rng, span=100),
                    f"How many grams in {text} kg?",
                    f"1 kg = 1000 g. {text} kg = {ans} g.",
                    rng, answer_str=f"{ans}g",
                    distractor_strs=[f"{d}g" for d in _near(ans, rng, span=100)])


def t_subtract_a_product(rng):
    """From 20 take the product of 4 and 5"""
    a = rng.randint(2, 6); b = rng.randint(2, 6)
    base = a * b + rng.randint(5, 25)
    ans = base - a * b
    return _build_q(ans, _near(ans, rng),
                    f"From {base} take the product of {a} and {b}.",
                    f"Product = {a} × {b} = {a*b}. {base} - {a*b} = {ans}.", rng)


def t_rearrange_digits_max(rng):
    """Rearrange the digits 6, 9, 8 to make the largest possible number"""
    digits = rng.sample(range(1, 10), 3)
    sorted_desc = sorted(digits, reverse=True)
    ans = sorted_desc[0]*100 + sorted_desc[1]*10 + sorted_desc[2]
    # plausible wrong arrangements
    distractors = []
    others = [d for d in digits if d != sorted_desc[0]]
    distractors.append(digits[0]*100 + digits[1]*10 + digits[2])  # original order
    asc = sorted(digits); distractors.append(asc[0]*100+asc[1]*10+asc[2])
    distractors.append(sorted_desc[1]*100 + sorted_desc[0]*10 + sorted_desc[2])
    distractors = [d for d in distractors if d != ans][:3]
    while len(distractors) < 3:
        d = rng.randint(100, 999)
        if d != ans and d not in distractors:
            distractors.append(d)
    return _build_q(ans, distractors,
                    f"Rearrange the digits {', '.join(str(d) for d in digits)} to make the largest possible number.",
                    f"Largest is {ans} (digits in descending order).", rng)


def t_change_from_pound(rng):
    spent = rng.randint(11, 95)
    ans = 100 - spent
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Tom bought a toy for {spent}p. How much change did he receive from £1?",
                    f"£1 = 100p. 100 - {spent} = {ans}p change.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=5)])


def t_coin_count_to_total(rng):
    """How many 50p coins make £3?"""
    coin = rng.choice([5, 10, 20, 50])
    pounds = rng.randint(1, 5)
    total_p = pounds * 100
    if total_p % coin != 0:
        return t_coin_count_to_total(rng)
    ans = total_p // coin
    return _build_q(ans, _near(ans, rng, span=2),
                    f"How many {coin}p coins make £{pounds}.00?",
                    f"£{pounds}.00 = {total_p}p. {total_p} ÷ {coin} = {ans} coins.", rng)


def t_equal_notes_total(rng):
    """4 equal notes total £200. Each note = ?"""
    count = rng.choice([2, 4, 5])
    each = rng.choice([5, 10, 20, 50])
    total = count * each
    return _build_q(each, _near(each, rng),
                    f"Grace has {count} bank notes of the same value. They total £{total}. What is the value of each note?",
                    f"£{total} ÷ {count} = £{each} per note.",
                    rng, answer_str=f"£{each}",
                    distractor_strs=[f"£{d}" for d in _near(each, rng)])


def _clock_words(total_min_past_12: int) -> str:
    """Render minutes-past-12-noon as a clock phrase. Only handles clean 15-min increments."""
    hour_words = ["twelve", "one", "two", "three", "four", "five",
                  "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    h = total_min_past_12 // 60
    m = total_min_past_12 % 60
    h_now = h % 12  # 0..11, but we want word for the visible hour
    h_word = hour_words[h_now if h_now != 0 else 12]
    next_h_word = hour_words[(h_now + 1) % 12 if (h_now + 1) % 12 != 0 else 12]
    if m == 0:    return f"{h_word} o'clock"
    if m == 15:   return f"quarter past {h_word}"
    if m == 30:   return f"half past {h_word}"
    if m == 45:   return f"quarter to {next_h_word}"
    return f"{h_word} {m} minutes past"


def t_minutes_between_times(rng):
    """How many minutes from quarter past 12 to 1 o'clock?"""
    start_min = rng.choice([0, 15, 30, 45])
    elapsed = rng.choice([15, 30, 45, 60, 75, 90])
    end_min = start_min + elapsed
    # Ensure end lands on a clean 15-min boundary
    start_words = _clock_words(start_min)
    end_words = _clock_words(end_min)
    ans = elapsed
    return _build_q(ans, _near(ans, rng, span=15),
                    f"How many minutes from {start_words} to {end_words}?",
                    f"{end_words} is {elapsed} minutes after {start_words}.",
                    rng, answer_str=f"{ans} min",
                    distractor_strs=[f"{d} min" for d in _near(ans, rng, span=15)])


def t_hours_between_am_pm(rng):
    """Leaves home 8 a.m., returns 5 p.m. How long?"""
    start_h = rng.randint(7, 11); end_h = rng.randint(2, 7)
    ans = (12 - start_h) + end_h
    return _build_q(ans, _near(ans, rng, span=1),
                    f"Tom leaves home at {start_h} a.m. and returns at {end_h} p.m. For how many hours is he away?",
                    f"{start_h} a.m. to 12 noon = {12-start_h}h. Noon to {end_h} p.m. = {end_h}h. Total = {ans}h.",
                    rng, answer_str=f"{ans} hours",
                    distractor_strs=[f"{d} hours" for d in _near(ans, rng, span=1)])


def t_pile_of_coins(rng):
    """50p + 20p + 5p + 5p + 5p + 1p + 1p"""
    coins = [50, 20, 10, 5, 5, 5, 5, 2, 2, 1, 1]
    selection = rng.sample(coins, rng.randint(4, 7))
    ans = sum(selection)
    pretty = " + ".join(f"{c}p" for c in selection)
    return _build_q(ans, _near(ans, rng, span=5),
                    f"Find the total value of these coins: {pretty}.",
                    f"{pretty} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=5)])


def t_balance_equation(rng):
    """24 + 8 = 12 × ?"""
    target = rng.choice([24, 30, 36, 40, 48, 60])
    a = rng.choice([2, 3, 4, 5, 6])
    b = target - rng.choice([0, 2, 4, 6, 8]) if rng.choice([True, False]) else 0
    # easier: just frame as "X + Y = N × ?"
    n1 = rng.randint(5, 30); n2 = rng.randint(5, 30)
    total = n1 + n2
    factor = rng.choice([f for f in [2, 3, 4, 5, 6] if total % f == 0])
    if total % factor == 0:
        ans = total // factor
        return _build_q(ans, _near(ans, rng),
                        f"{n1} + {n2} = {factor} × ?",
                        f"{n1} + {n2} = {total}. {total} ÷ {factor} = {ans}.", rng)
    # fallback
    return t_balance_equation(rng)


def t_subtract_two_groups_from_total(rng):
    """505 - 200 men - 200 women = children?"""
    total = rng.randint(400, 800); a = rng.choice([100, 150, 200, 250])
    b = rng.choice([100, 150, 200])
    if a + b >= total:
        a = total // 3; b = total // 3
    ans = total - a - b
    return _build_q(ans, _near(ans, rng, span=20),
                    f"A concert has {total} people: {a} men, {b} women, the rest children. How many children?",
                    f"{total} - {a} - {b} = {ans} children.", rng)


def t_two_items_one_known(rng):
    """Notebook + pencil = 70p. Pencil = 11p. Notebook = ?"""
    pencil = rng.randint(5, 30); notebook = rng.randint(30, 80)
    total = pencil + notebook
    ans = notebook
    return _build_q(ans, _near(ans, rng),
                    f"A notebook and pencil cost {total}p in total. The pencil cost {pencil}p. How much did the notebook cost?",
                    f"{total} - {pencil} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng)])


def t_pence_to_pounds_large(rng):
    """309 1ps as £s — large pence to currency"""
    pence = rng.randint(100, 999)
    pounds = pence // 100; rem = pence % 100
    correct = f"£{pounds}.{rem:02d}"
    distractors = [f"£{pounds+1}.{rem:02d}", f"£{pounds}.{(rem+10)%100:02d}", f"£{rem}.{pounds:02d}"]
    return _build_q(None, None,
                    f"In a jar there are {pence} 1p coins. Write this amount in £s.",
                    f"{pence}p = £{pounds}.{rem:02d}.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_doubled_then_added(rng):
    """Double 9 and then add 7"""
    a = rng.randint(2, 15); add = rng.randint(2, 20)
    ans = a * 2 + add
    return _build_q(ans, _near(ans, rng),
                    f"Double {a} and then add {add}.",
                    f"{a} × 2 = {a*2}. {a*2} + {add} = {ans}.", rng)


def t_tens_in_number(rng):
    """How many tens in 380?"""
    n = rng.choice([100, 150, 200, 250, 380, 400, 500, 750, 800, 1000])
    ans = n // 10
    return _build_q(ans, _near(ans, rng, span=2),
                    f"How many tens are there in {n}?",
                    f"{n} ÷ 10 = {ans} tens.", rng)


def t_pair_make_target_money(rng):
    """Which two of these sums make 40p? Options as a set."""
    target = rng.choice([20, 30, 40, 50])
    a = rng.randint(2, target - 2); b = target - a
    # Build a 4-option grid where one pair sums to target
    nums = [a, b]
    while len(nums) < 4:
        c = rng.randint(3, 25)
        if c not in nums and c != target - a and c != target - b:
            nums.append(c)
    rng.shuffle(nums)
    correct = f"{a}p and {b}p"
    distractor_pairs = []
    while len(distractor_pairs) < 3:
        x = rng.sample(nums, 2)
        s = f"{x[0]}p and {x[1]}p"
        if (x[0] + x[1] != target and s not in distractor_pairs
                and {x[0], x[1]} != {a, b}):
            distractor_pairs.append(s)
    return _build_q(None, None,
                    f"Pick the two amounts that add up to {target}p from: " + ", ".join(f"{n}p" for n in nums),
                    f"{a}p + {b}p = {target}p.",
                    rng, answer_str=correct, distractor_strs=distractor_pairs)


def t_per_period_total(rng):
    """Priya saves 20p each month. How much in a year?"""
    rate = rng.choice([5, 10, 15, 20, 25, 30, 50])
    period_name = rng.choice([("month", 12), ("week", 52), ("day", 7)])
    periods = rng.choice([7, 12, 30, 52]) if period_name[0] != "month" else 12
    if period_name[0] == "month": periods = 12
    elif period_name[0] == "week": periods = rng.choice([4, 8, 12])
    elif period_name[0] == "day": periods = rng.choice([5, 7, 10])
    ans = rate * periods
    return _build_q(ans, _near(ans, rng, span=10),
                    f"Priya saves {rate}p each {period_name[0]}. How much does she save in {periods} {period_name[0]}s?",
                    f"{rate} × {periods} = {ans}p.",
                    rng, answer_str=f"{ans}p",
                    distractor_strs=[f"{d}p" for d in _near(ans, rng, span=10)])


def t_half_of_expression(rng):
    """Half of (15 - 7)"""
    a = rng.randint(8, 30); b = rng.randint(2, a // 2)
    expr_val = a - b
    if expr_val % 2 != 0:
        b += 1; expr_val = a - b
    ans = expr_val // 2
    return _build_q(ans, _near(ans, rng),
                    f"Half of ({a} - {b}) = ?",
                    f"{a} - {b} = {expr_val}. Half of {expr_val} = {ans}.", rng)


def t_fraction_of_1(rng):
    """1 - 1/10 = ?  (as fraction or decimal — keep as fraction)"""
    denom = rng.choice([2, 3, 4, 5, 10])
    correct = f"{denom-1}/{denom}"
    distractors = [f"1/{denom}", f"{denom}/{denom-1}", f"{denom-2 if denom > 2 else denom+1}/{denom}"]
    return _build_q(None, None,
                    f"1 - 1/{denom} = ?",
                    f"1 = {denom}/{denom}. {denom}/{denom} - 1/{denom} = {denom-1}/{denom}.",
                    rng, answer_str=correct, distractor_strs=distractors)


def t_cm_to_m_with_complement(rng):
    """85cm + ? cm = 1m"""
    cm = rng.randint(5, 95)
    ans = 100 - cm
    return _build_q(ans, _near(ans, rng, span=5),
                    f"{cm}cm + ? cm = 1m",
                    f"1m = 100cm. 100 - {cm} = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng, span=5)])


def t_difference_lengths_set(rng):
    """Find difference between longest and shortest of 9cm, 26cm, 18cm, 30cm"""
    lengths = sorted(rng.sample(range(5, 50), 4))
    ans = lengths[-1] - lengths[0]
    return _build_q(ans, _near(ans, rng, span=3),
                    f"Find the difference between the longest and shortest of these lengths: {', '.join(f'{l}cm' for l in lengths)}.",
                    f"Longest = {lengths[-1]}cm, shortest = {lengths[0]}cm. Difference = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng, span=3)])


def t_triangle_third_side(rng):
    """Distance round triangle is 25cm. Two sides 9cm each. Find third."""
    two_each = rng.randint(5, 20); perim = rng.randint(2 * two_each + 5, 2 * two_each + 30)
    ans = perim - 2 * two_each
    return _build_q(ans, _near(ans, rng),
                    f"The distance around a triangle is {perim}cm. Two of its sides each measure {two_each}cm. What is the length of the third side?",
                    f"Two sides = {2*two_each}cm. Third = {perim} - {2*two_each} = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng)])


def t_compare_cm_m(rng):
    """405cm is how many cm more than 4m?"""
    m = rng.randint(1, 5); extra = rng.randint(5, 95)
    cm_val = m * 100 + extra
    ans = extra
    return _build_q(ans, _near(ans, rng, span=5),
                    f"By how many cm is {cm_val}cm greater than {m}m?",
                    f"{m}m = {m*100}cm. {cm_val} - {m*100} = {ans}cm.",
                    rng, answer_str=f"{ans}cm",
                    distractor_strs=[f"{d}cm" for d in _near(ans, rng, span=5)])


def t_weeks_to_days(rng):
    """3 weeks = ? days"""
    weeks = rng.randint(2, 8)
    ans = weeks * 7
    return _build_q(ans, _near(ans, rng),
                    f"{weeks} weeks = ? days",
                    f"1 week = 7 days. {weeks} × 7 = {ans} days.",
                    rng, answer_str=f"{ans} days",
                    distractor_strs=[f"{d} days" for d in _near(ans, rng)])


def t_back_calc_pieces(rng):
    """Peaches cut into quarters → 40 pieces. How many peaches?"""
    cut_into = rng.choice([2, 3, 4, 5])
    cut_name = {2: "halves", 3: "thirds", 4: "quarters", 5: "fifths"}[cut_into]
    peaches = rng.randint(5, 20)
    pieces = peaches * cut_into
    return _build_q(peaches, _near(peaches, rng),
                    f"Some peaches were cut into {cut_name}. There were then {pieces} pieces. How many peaches were cut?",
                    f"{pieces} ÷ {cut_into} = {peaches} peaches.", rng)


def t_two_thirds_from_one_third(rng):
    """1/3 of money is 12p. How much is 2/3?"""
    one_third = rng.randint(5, 30)
    two_thirds = one_third * 2
    return _build_q(two_thirds, _near(two_thirds, rng),
                    f"1/3 of a sum of money is {one_third}p. How much is 2/3 of the money?",
                    f"2/3 = 2 × (1/3) = 2 × {one_third} = {two_thirds}p.",
                    rng, answer_str=f"{two_thirds}p",
                    distractor_strs=[f"{d}p" for d in _near(two_thirds, rng)])


# ════════════════════════ REGISTRY ═════════════════════════

TEMPLATES: list[Callable] = [
    # Arithmetic basics
    t_addition_3digit_plus_1digit, t_addition_place_value, t_addition_three_terms,
    t_subtraction_3digit_minus_tens, t_subtraction_2digit,
    t_repeated_addition_as_mult, t_doubled_then_added,
    # Order of ops
    t_paren_mul_then_add, t_missing_divisor, t_missing_factor,
    t_repeated_multiplication_10s, t_subtract_a_product,
    t_balance_equation, t_operator_selection, t_half_of_expression,
    # Place value
    t_place_value_decompose_tens_ones, t_place_value_write_digits,
    t_place_value_missing, t_hundreds_tens_ones, t_increase_n_times,
    t_value_of_digit, t_tens_in_number, t_rearrange_digits_max,
    # Fractions
    t_fraction_of_money, t_fraction_of_whole, t_fraction_reasoning_three_quarters,
    t_quarters_in_mixed, t_fraction_tank_remaining,
    t_two_thirds_from_one_third, t_fraction_of_1,
    # Units & mass
    t_unit_cm_to_m_cm, t_unit_m_cm_to_cm, t_unit_m_with_half_to_cm,
    t_mass_subtract_with_units, t_mass_kg_g_to_g, t_kg_to_g_fraction,
    t_cm_to_m_with_complement, t_compare_cm_m, t_difference_lengths_set,
    # Currency
    t_currency_pounds_to_pence, t_currency_pence_to_pounds,
    t_money_subtract_from_pound, t_money_add_to_pounds, t_nearest_to_pound,
    t_increase_money, t_decrease_money,
    t_multi_coin_total, t_pile_of_coins, t_change_from, t_change_from_pound,
    t_reverse_change, t_coin_equivalence, t_coin_count_to_total,
    t_equal_notes_total, t_pair_make_target_money, t_pence_to_pounds_large,
    # Time / calendar
    t_half_hour_plus_min, t_shop_duration, t_days_in_month, t_month_offset,
    t_days_in_months_total, t_mixed_hour_to_min, t_three_quarters_of_hour,
    t_weeks_to_days, t_minutes_between_times, t_hours_between_am_pm,
    # Multiples
    t_multiple_of_n,
    # Word problems
    t_money_started_with, t_rows_division, t_share_equally, t_unit_cost_scaled,
    t_price_per_kg_fractional, t_subtract_two_groups_from_total,
    t_two_items_one_known, t_per_period_total, t_back_calc_pieces,
    # Geometry
    t_square_perimeter_to_side, t_line_segment_difference, t_triangle_third_side,
    # Sequences
    t_sequence_extend_asc, t_sequence_extend_desc,
    # Comparison
    t_inequality_fill, t_difference_known_smaller, t_three_numbers_find_third,
    t_n_less_than, t_n_more_than,
]


# Templates carrying genuine multi-step / abstract reasoning — gated to higher levels
_OLYMPIAD_ONLY = {
    t_fraction_tank_remaining, t_rearrange_digits_max, t_balance_equation,
    t_half_of_expression, t_fraction_of_1, t_cm_to_m_with_complement,
    t_difference_lengths_set, t_triangle_third_side, t_two_thirds_from_one_third,
    t_subtract_a_product, t_doubled_then_added, t_back_calc_pieces,
}
# Simple one-operation drills — at challenge/olympiad we drop these so the
# bar stays meaningfully higher
_STARTER_ONLY = {
    t_addition_3digit_plus_1digit, t_subtraction_2digit,
    t_repeated_multiplication_10s, t_place_value_decompose_tens_ones,
    t_place_value_write_digits, t_value_of_digit, t_hundreds_tens_ones,
    t_days_in_month, t_share_equally, t_multi_coin_total,
    t_coin_count_to_total, t_n_less_than, t_n_more_than,
    t_sequence_extend_asc, t_sequence_extend_desc,
}


def _templates_for(difficulty: str) -> list:
    if difficulty == "olympiad":
        return [t for t in TEMPLATES if t not in _STARTER_ONLY]
    if difficulty == "challenge":
        return [t for t in TEMPLATES if t not in _STARTER_ONLY and t not in _OLYMPIAD_ONLY]
    # starter — strip the multi-step abstract ones so kids aren't ambushed
    return [t for t in TEMPLATES if t not in _OLYMPIAD_ONLY]


def generate_mental_arithmetic(count: int, seed: int | None = None, difficulty: str = "starter") -> list[dict]:
    """Pick `count` templates and execute each. Template pool scales by
    difficulty so promotion actually feels like harder questions, not just
    a bigger XP number."""
    rng = random.Random(seed)
    pool = _templates_for(difficulty)
    out = []
    seen_templates: list = []  # avoid back-to-back repeats
    for _ in range(count):
        choices = [t for t in pool if t not in seen_templates[-2:]]
        template = rng.choice(choices or pool)
        out.append(template(rng))
        seen_templates.append(template)
    return out
