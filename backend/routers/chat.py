"""
Chat — directly connected to Gemini Flash.
Personalizes responses based on student's dyslexia profile + settings.
"""
import os
import httpx
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from deps.deps import get_current_user_optional

router = APIRouter(tags=["chat"])

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are DyslexAid's AI assistant — warm, simple, and encouraging.
You help students with dyslexia, their parents, and teachers in India.

Rules:
- ALWAYS respond in the SAME language the user writes in (English, Hindi, Tamil, or Marathi).
- Keep responses SHORT (3-5 sentences max). Use simple words.
- Be warm and encouraging. Never make the student feel bad.
- If the student has a specific dyslexia type, tailor advice to that type.
- For medical questions about dyslexia, recommend dyslexiaindia.org.in or NIMHANS.
- Format with line breaks between sentences so it's easy to read.
- Never use complex jargon or long paragraphs.
"""

# ─── Profile-level teaching guidance ────────────────────────────────────────
# Keyed by the "type"/"primary_profile" value stored on the student's
# readingProfile. Covers both legacy and current analyzer profile names.

PROFILE_GUIDANCE: Dict[str, str] = {
    "Visual Dyslexia": "This student is a VISUAL learner. Use diagrams, describe things spatially "
                        "(left/right, top/bottom, shapes, colors), and avoid dense unbroken text.",
    "Phonological Dyslexia": "This student is a PHONOLOGICAL learner. Always include a pronunciation / "
                              "sound-it-out guide for any new or tricky word (e.g. 'cat = /k/ /a/ /t/').",
    "Surface Dyslexia": "This student has surface dyslexia. Emphasize sight-word and whole-word "
                         "recognition — show the whole word shape rather than leading with phonics rules.",
    "Working Memory Deficit": "This student has working memory challenges. Keep explanations SHORT — "
                               "one idea per sentence, one step at a time. Never stack multiple instructions.",
    "Double Deficit Dyslexia": "This student has both phonological and rapid-naming challenges. Include "
                                "pronunciation guidance AND keep explanations short with extra response time.",
    "RAN Deficit (Rapid Naming)": "This student names things slowly. Be patient, keep pace relaxed, and "
                                   "don't rush follow-up questions.",
    "Reading Fluency Deficit": "This student reads slowly. Use short sentences, repeat key terms, and "
                                "keep a relaxed, patient pace.",
    "Mixed Profile": "This student shows challenges across several areas. Combine short explanations, "
                      "simple vocabulary, and visual or pronunciation support as needed below.",
    "No significant indicators": "No specific dyslexia adaptations are required — use clear, friendly "
                                  "general explanations.",
}

# ─── Domain-level teaching guidance ─────────────────────────────────────────
# Keyed by domain name. Covers both the current 12-domain analyzer taxonomy
# and the older 8-domain names, so this works regardless of which analyzer
# version produced the stored profile.

DOMAIN_GUIDANCE: Dict[str, str] = {
    "visual_processing": "Use simple diagrams, visual descriptions, and spatial analogies instead of dense text.",
    "visual_attention": "Highlight or bold the single key word/phrase to focus on; avoid cluttered explanations.",
    "phonological_processing": "Include a pronunciation guide (sound it out) for new or tricky words.",
    "phonological_awareness": "Include a pronunciation guide (sound it out) for new or tricky words.",
    "orthographic_processing": "Emphasize whole-word/sight-word recognition rather than letter-by-letter rules.",
    "orthographic_spelling": "Emphasize whole-word/sight-word recognition rather than letter-by-letter rules.",
    "spelling_ability": "When spelling comes up, show the word as a whole shape/pattern to memorize.",
    "reading_fluency": "Keep sentences short and paced naturally; avoid long unbroken text.",
    "reading_accuracy": "Show tricky words clearly and offer to break them down step by step if asked.",
    "working_memory": "Keep explanations SHORT — one idea per sentence, one step at a time.",
    "phonological_memory": "Keep explanations SHORT — one idea per sentence, one step at a time.",
    "rapid_naming": "Give the student extra time to respond; don't rush follow-up questions.",
    "reading_comprehension": "Summarize the main idea in one simple sentence before adding detail.",
    "comprehension": "Summarize the main idea in one simple sentence before adding detail.",
    "processing_speed": "Be patient and concise; avoid overwhelming with too much information at once.",
    "language_processing": "Use simple, everyday vocabulary and short sentences; avoid idioms.",
}


def _domain_score(entry: Any) -> Optional[float]:
    """Domain score entries may be a dict ({'score': 62, ...}) or a bare number."""
    if isinstance(entry, dict):
        return entry.get("score")
    if isinstance(entry, (int, float)):
        return entry
    return None


def _weak_domains(domain_scores: Dict[str, Any], threshold: int = 50) -> List[str]:
    weak = []
    for domain, entry in (domain_scores or {}).items():
        score = _domain_score(entry)
        if score is not None and score >= threshold:
            weak.append(domain)
    return weak


def _adaptive_settings(profile_type: str, weak_domains: List[str]) -> Dict[str, bool]:
    """Derive a compact adaptive-settings checklist the model can act on."""
    weak_set = set(weak_domains)
    return {
        "short_explanations": (
            profile_type in ("Working Memory Deficit", "Double Deficit Dyslexia", "Mixed Profile")
            or bool(weak_set & {"working_memory", "phonological_memory", "processing_speed"})
        ),
        "use_diagrams": (
            profile_type == "Visual Dyslexia"
            or bool(weak_set & {"visual_processing", "visual_attention"})
        ),
        "pronunciation_guides": (
            profile_type in ("Phonological Dyslexia", "Double Deficit Dyslexia")
            or bool(weak_set & {"phonological_processing", "phonological_awareness"})
        ),
        "sight_word_emphasis": (
            profile_type == "Surface Dyslexia"
            or bool(weak_set & {"orthographic_processing", "orthographic_spelling", "spelling_ability"})
        ),
        "extra_response_time": (
            profile_type in ("RAN Deficit (Rapid Naming)", "Reading Fluency Deficit", "Double Deficit Dyslexia")
            or bool(weak_set & {"rapid_naming", "processing_speed"})
        ),
        "simple_vocabulary": bool(weak_set & {"language_processing", "reading_comprehension", "comprehension"}),
    }


def _build_personalization(user: dict) -> str:
    """Build the student-context block appended to the base system prompt."""
    rp = (user or {}).get("readingProfile") or {}
    if not rp:
        return ""

    name = user.get("name", "Student")
    lang = (user.get("languages") or ["english"])[0]
    d_type = rp.get("type", "")
    level = rp.get("level", "")
    score = rp.get("score", "")
    strengths = rp.get("strengths") or []
    weaknesses = rp.get("weaknesses") or []
    domain_scores = rp.get("domain_scores") or {}

    weak_domains = _weak_domains(domain_scores)
    adaptive = _adaptive_settings(d_type, weak_domains)

    lines = [
        "\n\n--- STUDENT PROFILE ---",
        f"Name: {name} | Language: {lang}",
    ]
    if d_type:
        lines.append(f"Dyslexia profile: {d_type} (risk level: {level}, score: {score}/100)")
    if strengths:
        lines.append(f"Strengths: {', '.join(strengths)}")
    if weaknesses:
        lines.append(f"Weaknesses: {', '.join(weaknesses)}")

    adaptations = []
    if d_type and d_type in PROFILE_GUIDANCE:
        adaptations.append(PROFILE_GUIDANCE[d_type])
    for domain in weak_domains:
        if domain in DOMAIN_GUIDANCE:
            adaptations.append(DOMAIN_GUIDANCE[domain])

    if adaptations:
        lines.append("\nTEACHING ADAPTATIONS (apply these to every response):")
        # De-duplicate while preserving order
        seen = set()
        for a in adaptations:
            if a not in seen:
                lines.append(f"- {a}")
                seen.add(a)

    active_settings = [k for k, v in adaptive.items() if v]
    if active_settings:
        lines.append(f"\nAdaptive settings active: {', '.join(active_settings)}")

    lines.append(f"Always tailor explanations to a {d_type or 'general'} learner." if d_type else "")
    return "\n".join(l for l in lines if l)


async def _call_gemini(messages: list, system: str) -> str:
    if not GEMINI_KEY:
        return None
    try:
        # Build Gemini conversation format
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_KEY}",
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300},
                }
            )
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[gemini-chat] error: {e}")
    return None


FAQ = [
    (["dyslexia", "what is", "condition", "disorder"],
     "Dyslexia is a reading difficulty where the brain finds it hard to connect letters to sounds. It is NOT related to intelligence. With the right help, dyslexic children can do very well! 🌟"),
    (["scan", "camera", "upload", "photo", "pdf"],
     "To scan text, go to the Scan tab. You can upload a photo or PDF. The app will extract the text and convert it to dyslexia-friendly format automatically."),
    (["offline", "internet", "wifi", "network"],
     "DyslexAid works offline! OCR scanning, reading, and note conversion all work without internet. Your progress is always saved."),
    (["free", "cost", "price", "pay", "subscription"],
     "DyslexAid is 100% free — forever. No subscription, no charges. It is built specially for Indian schools! 🇮🇳"),
    (["plan", "learning", "schedule"],
     "After your screening test, our AI creates a personal 4-week plan just for you. The plan updates automatically as you learn!"),
    (["progress", "score", "result", "comprehension"],
     "Check your Progress tab to see your scores, streak, words you learned, and weekly activity chart."),
    (["font", "size", "color", "setting", "background"],
     "You can change your font, text size, background color, and reading speed in Settings. These are made specially for dyslexia readers!"),
    (["teacher", "classroom", "code", "join"],
     "Ask your teacher for their classroom code. Then go to Settings > Join Classroom and enter the code to join."),
]


def _faq_fallback(message: str) -> str:
    msg = message.lower()
    best, best_score = None, 0
    for kws, ans in FAQ:
        score = sum(1 for kw in kws if kw in msg)
        if score > best_score:
            best_score, best = score, ans
    if best and best_score > 0:
        return best
    return "Hi! I'm DyslexAid's assistant. I can help with dyslexia info, app features, and reading tips. What would you like to know?"


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatReq(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


@router.post("/chat")
async def chat(req: ChatReq, authorization: Optional[str] = Header(None)):
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(400, "No message")

    # Build personalized system prompt with full student context
    user = await get_current_user_optional(authorization)
    system = SYSTEM_PROMPT
    if user:
        system += _build_personalization(user)

    # Build conversation history
    history = [{"role": m.role if m.role == "user" else "assistant", "content": m.content}
               for m in (req.history or [])[-6:]]
    history.append({"role": "user", "content": msg})

    # Try Gemini first
    reply = await _call_gemini(history, system)
    if reply:
        return {"reply": reply.strip(), "source": "gemini-flash"}

    # Offline FAQ fallback
    return {"reply": _faq_fallback(msg), "source": "faq"}