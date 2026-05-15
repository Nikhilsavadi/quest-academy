"""Anthropic question + vision generation. Synchronous wrappers."""
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from config import settings

log = logging.getLogger("ai")

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


MATRIX_MANIFEST_PATH = Path(__file__).parent / "static" / "matrices" / "manifest.json"


def load_matrix_manifest() -> list[dict]:
    if not MATRIX_MANIFEST_PATH.exists():
        return []
    try:
        return json.loads(MATRIX_MANIFEST_PATH.read_text())
    except Exception:
        return []


# ── Visual mode selection ────────────────────────────────────────
def pick_visual_mode(subject: str, topic: str) -> str:
    s = subject.lower()
    if s == "nvr":
        if "matrices" in topic.lower():
            return "matrix"
        return "svg"
    if s == "maths":
        if any(k in topic.lower() for k in ("shape", "area", "perimeter", "angle")):
            return "svg"
        return "text"
    return "text"


# ── Standard generation ──────────────────────────────────────────
SYSTEM = (
    "You generate UK 11+ exam preparation questions for a child training for "
    "Ripon Grammar School entrance. You always return valid JSON only — no "
    "markdown, no preamble, no trailing prose."
)


def build_prompt(
    count: int,
    subject: str,
    topic: str,
    difficulty: str,
    visual_mode: str,
    mastery_context: str,
    learn_mode: bool,
    matrix_manifest: list[dict],
) -> str:
    matrix_block = ""
    if visual_mode == "matrix":
        items = [f'- {m["id"]}: {m["description"]}' for m in matrix_manifest[:30]]
        matrix_block = "\nMATRIX BANK (set image_bank_id to one of these):\n" + "\n".join(items) + "\n"

    learn_block = ""
    if learn_mode:
        learn_block = """
LEARN MODE: First object in the array MUST be:
{
  "type": "worked_example",
  "question": "Here's how to solve this type of question...",
  "walkthrough": "Step by step explanation",
  "example_question": "A full example question",
  "example_answer": "Answer with reasoning"
}
Then follow with normal questions.
"""

    return f"""You are generating {count} {subject} questions at {difficulty} difficulty for an 8-year-old UK student preparing for the 11+ exam at Ripon Grammar School.

TOPIC FOCUS: {topic}

CHILD'S MASTERY CONTEXT:
{mastery_context}

VISUAL MODE: {visual_mode}

DIFFICULTY GUIDE:
- starter: straightforward Year 3-4, single step
- challenge: Year 4-5, multi-step, olympiad intro
- olympiad: Junior Maths Challenge style, genuinely hard for age 8-10

PATTERN SPOTTING NOTE:
This child's key development area is spotting patterns quickly. Include pattern-recognition elements wherever natural for the topic.
{learn_block}
SVG RULES (when visual_mode=svg):
- Self-contained SVG, viewBox="0 0 400 100" for sequences
- viewBox="0 0 200 200" for single shapes
- Shapes: circles, rects, polygons using SVG primitives only
- No external fonts, no images within SVG
- Clean strokes, minimal fills
- Sequences: 4 shapes shown, ? for 5th position
- Option SVGs: viewBox="0 0 80 80" each (each option string is a complete <svg>...</svg>)
- Geometry diagrams: labelled with <text> elements, viewBox="0 0 300 200"
{matrix_block}
Return ONLY a valid JSON array. No markdown. No preamble.
Schema per question:
{{
  "type": "question",
  "question": "string",
  "svg_content": "string | null",
  "image_bank_id": "string | null",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "string (friendly, encouraging)",
  "topic": "{topic}",
  "has_visual": boolean
}}
"""


def _extract_json_array(text: str) -> list[dict]:
    """Pull a JSON array out of the response, tolerating accidental fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found")
    return json.loads(text[start : end + 1])


def generate_questions(
    *,
    count: int,
    subject: str,
    topic: str,
    difficulty: str,
    mastery_context: str,
    learn_mode: bool = False,
) -> list[dict]:
    """Returns a list of question dicts. Worked-example dict prepended when learn_mode."""
    visual_mode = pick_visual_mode(subject, topic)
    manifest = load_matrix_manifest()
    prompt = build_prompt(
        count=count,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        visual_mode=visual_mode,
        mastery_context=mastery_context,
        learn_mode=learn_mode,
        matrix_manifest=manifest,
    )

    # If API key is a placeholder, return offline stub questions so the app still works
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("sk-ant-PLACEHOLDER"):
        return _offline_stub(count, subject, topic, difficulty, learn_mode)

    last_err = None
    for attempt in range(2):
        try:
            resp = client().messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=4096,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            arr = _extract_json_array(text)
            return _validate_and_clean(arr, topic, learn_mode)
        except Exception as e:
            log.exception("AI generation failed (attempt %s)", attempt + 1)
            last_err = e
    log.warning("Falling back to offline stub after AI failure: %s", last_err)
    return _offline_stub(count, subject, topic, difficulty, learn_mode)


def _validate_and_clean(arr: list[dict], topic: str, learn_mode: bool) -> list[dict]:
    cleaned: list[dict] = []
    for q in arr:
        if q.get("type") == "worked_example":
            cleaned.append({
                "type": "worked_example",
                "question": q.get("question", "Worked example"),
                "walkthrough": q.get("walkthrough", ""),
                "example_question": q.get("example_question", ""),
                "example_answer": q.get("example_answer", ""),
                "topic": topic,
            })
            continue
        opts = q.get("options") or []
        if not isinstance(opts, list) or len(opts) != 4:
            continue
        ci = q.get("correct_index", 0)
        if not isinstance(ci, int) or not 0 <= ci <= 3:
            continue
        cleaned.append({
            "type": "question",
            "question": q.get("question", ""),
            "svg_content": q.get("svg_content"),
            "image_bank_id": q.get("image_bank_id"),
            "options": [str(o) for o in opts],
            "correct_index": ci,
            "explanation": q.get("explanation", "Nice work."),
            "topic": q.get("topic") or topic,
            "has_visual": bool(q.get("has_visual")),
        })
    if learn_mode and (not cleaned or cleaned[0].get("type") != "worked_example"):
        cleaned.insert(0, {
            "type": "worked_example",
            "question": f"Here's how to approach {topic} questions.",
            "walkthrough": "Read carefully, spot the pattern, eliminate impossible options.",
            "example_question": "Example coming up.",
            "example_answer": "Walk through step by step.",
            "topic": topic,
        })
    return cleaned


# ── Vision: Bond Book scan ──────────────────────────────────────
SCAN_PROMPT = """Analyse this UK 11+ preparation workbook page and extract:

1. SUBJECT: Maths | NVR | VR
2. DIFFICULTY: starter | challenge | olympiad
3. YEAR_GROUP: Age X-Y
4. QUESTION_TYPES: List every distinct question format
5. FORMAT_NOTES: Structure, visual elements, answer format, timing instructions, questions per page
6. SAMPLE_QUESTIONS: 2-3 verbatim questions as style anchors
7. VISUAL_PATTERNS: NVR visual logic if applicable, otherwise null
8. TOPIC_TAGS: Map to taxonomy (Maths/NVR/VR topic list)

Return ONLY valid JSON:
{
  "subject": "Maths|NVR|VR",
  "difficulty": "starter|challenge|olympiad",
  "year_group": "Age X-Y",
  "question_types": ["type1", "type2"],
  "format_notes": "string",
  "sample_questions": ["q1", "q2", "q3"],
  "visual_patterns": "string | null",
  "topic_tags": ["tag1", "tag2"]
}
"""


def scan_workbook_image(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("sk-ant-PLACEHOLDER"):
        return {
            "subject": "Maths",
            "difficulty": "challenge",
            "year_group": "Age 8-10",
            "question_types": ["multiple choice"],
            "format_notes": "Offline stub — provide API key to scan.",
            "sample_questions": ["What is 7 × 8?"],
            "visual_patterns": None,
            "topic_tags": ["Mental Arithmetic"],
        }
    b64 = base64.standard_b64encode(image_bytes).decode()
    for attempt in range(2):
        try:
            resp = client().messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": SCAN_PROMPT},
                    ],
                }],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text[text.find("{"): text.rfind("}") + 1])
        except Exception:
            log.exception("Scan attempt %s failed", attempt + 1)
    raise ValueError("Could not parse workbook")


def build_template_prompt(template: dict, count: int) -> str:
    return f"""Generate {count} questions in the EXACT style of this UK 11+ workbook page.

STYLE PROFILE:
Subject: {template['subject']}
Difficulty: {template['difficulty']}
Year group: {template['year_group']}
Question types: {template['question_types']}
Format notes: {template['format_notes']}
Visual patterns: {template.get('visual_patterns')}

ANCHOR EXAMPLES (match this style exactly):
{json.dumps(template['sample_questions'], indent=2)}

Rules:
- Match difficulty and format of anchors precisely
- Do not repeat the anchor examples themselves
- Maintain same question structure and vocabulary level
- For NVR: generate SVG visuals matching described patterns
- Return strict JSON array matching standard question schema
"""


def generate_from_template(template: dict, count: int) -> list[dict]:
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("sk-ant-PLACEHOLDER"):
        return _offline_stub(count, template["subject"], template.get("topic_tags", ["General"])[0], template["difficulty"], False)
    prompt = build_template_prompt(template, count)
    for _ in range(2):
        try:
            resp = client().messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=4096,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            arr = _extract_json_array(resp.content[0].text)
            topic = template.get("topic_tags", ["General"])[0]
            return _validate_and_clean(arr, topic, False)
        except Exception:
            log.exception("Template generation failed")
    return _offline_stub(count, template["subject"], "General", template["difficulty"], False)


# ── Offline stub (used when API key absent or generation fails) ─
def _offline_stub(count: int, subject: str, topic: str, difficulty: str, learn_mode: bool) -> list[dict]:
    base = []
    if learn_mode:
        base.append({
            "type": "worked_example",
            "question": f"How to tackle {topic}",
            "walkthrough": "Read the question, identify the pattern, eliminate wrong options, double-check.",
            "example_question": "If 3, 5, 7, 9, what comes next?",
            "example_answer": "11 — the pattern adds 2 each time.",
            "topic": topic,
        })
    samples = [
        ("What number comes next: 2, 4, 6, 8, ?", ["9", "10", "11", "12"], 1, "Each number goes up by 2."),
        ("What is 7 × 8?", ["54", "56", "58", "64"], 1, "7 eights are 56."),
        ("Half of 48 is?", ["12", "16", "22", "24"], 3, "48 ÷ 2 = 24."),
        ("Which is a factor of 24?", ["5", "7", "8", "9"], 2, "24 ÷ 8 = 3, so 8 is a factor."),
        ("Find the odd one out: 4, 9, 16, 20, 25", ["9", "16", "20", "25"], 2, "All others are square numbers."),
        ("If today is Monday, what day is in 10 days?", ["Tuesday", "Wednesday", "Thursday", "Friday"], 2, "10 days later = Thursday."),
        ("A square has perimeter 20cm. Its side is?", ["4cm", "5cm", "6cm", "10cm"], 1, "20 ÷ 4 = 5cm."),
        ("Round 47 to the nearest 10.", ["40", "45", "50", "47"], 2, "47 is closer to 50 than 40."),
        ("What is 1/2 + 1/4?", ["1/6", "2/6", "3/4", "1"], 2, "1/2 = 2/4, so 2/4 + 1/4 = 3/4."),
        ("Pattern: 1, 4, 9, 16, ?", ["20", "23", "25", "32"], 2, "Square numbers — 5² = 25."),
    ]
    for i in range(count):
        q, opts, ci, exp = samples[i % len(samples)]
        base.append({
            "type": "question",
            "question": q,
            "svg_content": None,
            "image_bank_id": None,
            "options": opts,
            "correct_index": ci,
            "explanation": exp,
            "topic": topic,
            "has_visual": False,
        })
    return base
