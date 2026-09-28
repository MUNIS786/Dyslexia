"""Rule-based offline simplifier — fallback when AI is unavailable."""
import re
import os
import json

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "simple_words.json")

try:
    with open(_DATA_PATH, encoding="utf-8") as f:
        SIMPLE_WORDS = json.load(f)
except Exception:
    SIMPLE_WORDS = {
        "approximately": "about", "comprehend": "understand", "demonstrate": "show",
        "sufficient": "enough", "therefore": "so", "however": "but",
        "nevertheless": "still", "significant": "important", "additional": "more",
        "utilize": "use", "assistance": "help", "obtain": "get", "require": "need",
        "facilitate": "help", "implement": "do", "fundamental": "basic",
        "eliminate": "remove", "biochemical": "chemical", "organisms": "living things",
        "predominantly": "mostly", "simultaneously": "at the same time",
        "oxidation": "breakdown", "stomata": "tiny holes in leaves",
        "chlorophyll": "green plant substance", "photosynthesis": "plant food-making",
        "evaporation": "water turning into vapor", "condensation": "vapor turning into water",
        "precipitation": "rain, snow or hail", "atmosphere": "air around Earth",
        "vocabulary": "word list", "comprehension": "understanding", "assessment": "test",
        "intervention": "help", "accommodate": "adjust for", "cognitive": "thinking",
        "neurological": "brain-related", "curriculum": "school subjects",
        "phonological": "sound-based", "orthographic": "spelling-based",
        "acquisition": "learning", "instruction": "teaching", "remediation": "extra help",
    }


def _replace_hard_words(text: str) -> str:
    for hard, easy in SIMPLE_WORDS.items():
        text = re.sub(r"\b" + re.escape(hard) + r"\b", easy, text, flags=re.IGNORECASE)
    return text


def _split_long_sentences(text: str, max_words: int = 12) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for sent in sentences:
        words = sent.split()
        if len(words) <= max_words:
            out.append(sent)
            continue
        parts = re.split(r",\s*|\s+and\s+|\s+but\s+|\s+because\s+|\s+which\s+|\s+however\s+|\s+therefore\s+", sent)
        buf = []
        for part in parts:
            pw = part.split()
            if len(buf) + len(pw) <= max_words:
                buf.extend(pw)
            else:
                if buf:
                    out.append(" ".join(buf) + ".")
                buf = pw
        if buf:
            out.append(" ".join(buf) + ".")
    return " ".join(out)


def simplify_offline(text: str) -> dict:
    easier = _replace_hard_words(text)
    simplified = _split_long_sentences(easier, max_words=12)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", simplified) if s.strip()]
    bullets = sents[:3]
    stop = set("the a an and or but if of to in on at for by with is are was were be been it that this as from into over under".split())
    words = [w.strip(".,!?;:").lower() for w in text.split()]
    freq: dict = {}
    for w in words:
        if len(w) > 5 and w not in stop:
            freq[w] = freq.get(w, 0) + 1
    highlights = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:6]]
    return {
        "text": simplified,
        "bullet_points": bullets,
        "highlights": highlights,
    }
