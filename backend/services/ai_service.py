"""AI service — single source of truth for all Gemini/Claude/Emergent calls.

Used by every router (chat, simplify, ai_plan, teacher, daily_tasks, etc).
The Chat Assistant path (`chat_reply`) always calls Gemini directly and only
falls back to the offline FAQ when CHAT_OFFLINE_MODE=true is explicitly set
in the environment. Any other failure surfaces as an AIServiceError so the
router can return a proper HTTP error instead of silently degrading.
"""
import os
import json
import re
import time
import uuid
import logging
import httpx
from typing import Optional

# ─── Logging ────────────────────────────────────────────────────────────────

logger = logging.getLogger("dyslexaid.ai_service")
if not logger.handlers:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

# ─── Config ─────────────────────────────────────────────────────────────────
# Every tunable lives in the environment. Nothing below should ever be
# hardcoded again — if a new knob is needed, add an env var for it here.

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
EMERGENT_MODEL = os.environ.get("EMERGENT_MODEL", GEMINI_MODEL)
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Generation defaults. Individual calls can override max_tokens; everything
# else is shared so behavior stays consistent across providers.
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "800"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
TOP_P = float(os.environ.get("TOP_P", "0.95"))
TOP_K = int(os.environ.get("TOP_K", "40"))
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "20"))

# If a Gemini reply is cut off by the token budget, retry once at this
# multiplier before giving up and returning the truncated text.
TRUNCATION_RETRY_MULTIPLIER = float(os.environ.get("TRUNCATION_RETRY_MULTIPLIER", "1.75"))
TRUNCATION_RETRY_MAX_TOKENS = int(os.environ.get("TRUNCATION_RETRY_MAX_TOKENS", "2000"))

# Explicit, config-driven offline switch. Defaults to OFF — real Gemini
# responses are always used unless this is deliberately turned on.
CHAT_OFFLINE_MODE = os.environ.get("CHAT_OFFLINE_MODE", "false").strip().lower() == "true"

if not GEMINI_KEY:
    logger.warning(
        "GEMINI_API_KEY is not set. Set it in your .env file (and make sure "
        "load_dotenv() runs before this module is imported) or every chat "
        "request will fail loudly with a 500 instead of silently degrading."
    )
else:
    logger.info(
        "Gemini configured | model=%s | max_output_tokens=%d | key_loaded=%s",
        GEMINI_MODEL, MAX_OUTPUT_TOKENS, bool(GEMINI_KEY),
    )


class AIServiceError(Exception):
    """Raised when Gemini cannot fulfil a request and no offline mode is configured.

    The router layer catches this and converts it into a proper HTTPException —
    it must never be silently swallowed into a fallback answer.
    """

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def get_gemini_key() -> str:
    """Centralized API key access. Raises a clear, loud error if missing."""
    if not GEMINI_KEY:
        logger.error("GEMINI_API_KEY missing at request time.")
        raise AIServiceError(
            "GEMINI_API_KEY is missing or empty. Set it in the backend .env "
            "file and restart the server — the AI Assistant cannot function "
            "without it.",
            status_code=500,
        )
    return GEMINI_KEY


def _generation_config(max_tokens: Optional[int] = None) -> dict:
    """Single place that builds Gemini's generationConfig, so every call
    path (chat, simplify, lesson plan, AI plan, ...) shares the same
    temperature/top_p/top_k and none of them can drift out of sync."""
    return {
        "temperature": TEMPERATURE,
        "topP": TOP_P,
        "topK": TOP_K,
        "maxOutputTokens": max_tokens or MAX_OUTPUT_TOKENS,
    }


# ─── Prompts ────────────────────────────────────────────────────────────────

SIMPLIFY_PROMPT = """You are a reading assistant for children with dyslexia in India.

Rules (follow ALL without exception):
1. Every sentence must be 12 words or fewer.
2. Use only simple everyday words — no jargon.
3. NEVER remove facts, names, numbers, or important information.
4. Reply in the SAME language as the input (English / Hindi / Tamil / Marathi).
5. Return ONLY a JSON object of this exact shape and nothing else:
{
  "text": "The full simplified paragraph as one string.",
  "bullet_points": ["Short key point 1", "Short key point 2", "Short key point 3"],
  "highlights": ["word1", "word2", "word3"]
}
Do not add markdown fences or extra commentary."""

LESSON_PLAN_PROMPT = """You are an expert special education teacher in India specialising in dyslexia.
Generate a structured 30-minute lesson plan with timestamps for each activity.
Keep language simple and practical for Indian government school teachers.
Use plain text with sections like:
0-5 min: Warm-up ...
5-15 min: Main activity ...
15-25 min: Practice ...
25-30 min: Review ...
Accommodations: ..."""

CHATBOT_SYSTEM = """You are a warm, helpful assistant for DyslexAid — a free reading app
for dyslexic students in India. Help students, parents, and teachers.
Rules:
- Be warm, simple, and encouraging.
- Answer in the SAME language the user writes in (English, Hindi, Tamil, or Marathi).
- Keep answers focused and easy to read — a short paragraph or a few bullet points is plenty.
- Always finish your sentence and your thought; do not stop mid-sentence.
- Never use complex jargon.
- If asked about dyslexia symptoms, always recommend consulting a specialist at dyslexiaindia.org.in."""

AI_PLAN_PROMPT = """You are an expert in dyslexia education for Indian school students.
Based on the student's dyslexia screening results and usage data, generate a personalized learning plan.

Return ONLY a JSON object:
{
  "summary": "One paragraph describing the student's profile and approach.",
  "weeklyGoals": ["Goal 1", "Goal 2", "Goal 3"],
  "plan": [
    {"week": 1, "focus": "Focus area", "activities": ["Activity 1", "Activity 2"], "goal": "Measurable goal"},
    {"week": 2, "focus": "Focus area", "activities": ["Activity 1", "Activity 2"], "goal": "Measurable goal"},
    {"week": 3, "focus": "Focus area", "activities": ["Activity 1", "Activity 2"], "goal": "Measurable goal"},
    {"week": 4, "focus": "Focus area", "activities": ["Activity 1", "Activity 2"], "goal": "Measurable goal"}
  ],
  "accommodations": ["Accommodation 1", "Accommodation 2"],
  "parentTips": ["Tip 1", "Tip 2"],
  "teacherTips": ["Tip 1", "Tip 2"]
}
Do not add markdown fences or extra commentary."""

PROGRESS_SUGGESTION_PROMPT = """You are a dyslexia specialist AI for DyslexAid India.
Analyze this student's progress data and give adaptive suggestions to update their learning plan.

Return ONLY a JSON object:
{
  "suggestion": "One clear, encouraging suggestion for the student.",
  "planUpdate": "What to change in the plan this week.",
  "encouragement": "Short motivational message.",
  "nextGoal": "Specific measurable goal for next week."
}
Do not add markdown fences or extra commentary."""

OFFLINE_CONVERTER_PROMPT = """You are helping convert student notes into dyslexia-friendly format.
Rules:
1. Break all sentences to 12 words or fewer.
2. Use simple words. Replace hard words with easy ones.
3. Add clear bullet points for key ideas.
4. Keep all facts, dates, names, and numbers.
5. Return ONLY JSON:
{
  "text": "Simplified version of the notes.",
  "bullet_points": ["Key point 1", "Key point 2", "Key point 3"],
  "highlights": ["important_word1", "important_word2"]
}"""

DAILY_TASKS_PROMPT = """You are a dyslexia education specialist for Indian school students.
Generate 3-5 daily learning tasks for a student based on their dyslexia type and current progress.

Return ONLY a JSON array:
[
  {"title": "Short task name", "description": "Clear 1-2 sentence instructions.", "type": "reading|phonics|vocabulary|quiz|exercise", "durationMinutes": 10},
  ...
]
Tasks should be practical, achievable, and specific to the dyslexia type.
No markdown fences, just the JSON array."""


# ─── Helpers ────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


async def _call_claude(system: str, user_msg: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """Call Anthropic Claude API directly. Best-effort — returns None on any
    failure so callers can fall through to the next provider."""
    if not ANTHROPIC_KEY:
        return None
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": max_tokens or MAX_OUTPUT_TOKENS,
                    "system": system,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
        latency_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code == 429:
            logger.warning("Claude rate limited (429) | latency_ms=%d", latency_ms)
            return None
        if resp.status_code != 200:
            logger.warning(
                "Claude HTTP %s | latency_ms=%d | body=%s",
                resp.status_code, latency_ms, resp.text[:300],
            )
            return None
        data = resp.json()
        if data.get("content"):
            text = data["content"][0]["text"]
            logger.info(
                "Claude response | model=%s | latency_ms=%d | chars=%d",
                CLAUDE_MODEL, latency_ms, len(text),
            )
            return text
    except httpx.TimeoutException:
        logger.warning("Claude request timed out after %.0fs", REQUEST_TIMEOUT)
    except Exception as e:
        logger.warning("Claude call failed: %s", e)
    return None


async def _call_gemini(system: str, user_msg: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """Call Gemini directly. Used by the multi-provider fallback chain
    (_call_ai) for simplify / lesson-plan / AI-plan / daily-tasks — the
    interactive chat path uses _call_gemini_chat instead, which needs
    multi-turn history and stricter error surfacing.

    Best-effort — returns None on any failure so callers can fall through
    to the next provider. Shares GEMINI_MODEL / GEMINI_API_URL / generation
    config with the chat path so behavior never drifts between the two.
    """
    if not GEMINI_KEY:
        return None
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_KEY}",
                json={
                    "contents": [{"parts": [{"text": f"{system}\n\n{user_msg}"}]}],
                    "generationConfig": _generation_config(max_tokens),
                },
            )
        latency_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code == 429:
            logger.warning("Gemini rate limited (429) | latency_ms=%d", latency_ms)
            return None
        if resp.status_code != 200:
            logger.warning(
                "Gemini HTTP %s | latency_ms=%d | body=%s",
                resp.status_code, latency_ms, resp.text[:300],
            )
            return None
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
            logger.warning("Gemini returned no candidates | blockReason=%s", block_reason)
            return None
        finish_reason = candidates[0].get("finishReason")
        if finish_reason == "MAX_TOKENS":
            logger.warning("Gemini reply hit MAX_TOKENS | latency_ms=%d", latency_ms)
        text = candidates[0]["content"]["parts"][0]["text"]
        logger.info(
            "Gemini response | model=%s | latency_ms=%d | chars=%d | finish_reason=%s",
            GEMINI_MODEL, latency_ms, len(text), finish_reason,
        )
        return text
    except httpx.TimeoutException:
        logger.warning("Gemini request timed out after %.0fs", REQUEST_TIMEOUT)
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
    return None


async def _call_emergent(system: str, user_msg: str, model: str = None) -> Optional[str]:
    """Call via emergentintegrations if key is present. Last-resort fallback."""
    if not EMERGENT_KEY:
        return None
    start = time.monotonic()
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"dyslexaid-{uuid.uuid4()}",
            system_message=system,
        ).with_model("gemini", model or EMERGENT_MODEL)
        text = await chat.send_message(UserMessage(text=user_msg))
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("Emergent response | model=%s | latency_ms=%d", model or EMERGENT_MODEL, latency_ms)
        return text
    except Exception as e:
        logger.warning("Emergent call failed: %s", e)
    return None


async def _call_ai(system: str, user_msg: str, max_tokens: Optional[int] = None) -> tuple[Optional[str], str]:
    """Try Claude → Gemini → Emergent, return (response, source).

    max_tokens is optional and forwarded to every provider that supports it —
    callers like generate_ai_plan rely on being able to request a larger
    budget for long structured JSON output.
    """
    r = await _call_claude(system, user_msg, max_tokens)
    if r:
        return r, "claude"
    r = await _call_gemini(system, user_msg, max_tokens)
    if r:
        return r, "gemini"
    r = await _call_emergent(system, user_msg)
    if r:
        return r, "emergent"
    logger.warning("All AI providers failed or unconfigured — falling back to offline path.")
    return None, "offline"


# ─── Public API ─────────────────────────────────────────────────────────────

async def simplify_with_ai(text: str, language: str = "english") -> tuple[Optional[dict], str]:
    """Returns (structured_dict, method)."""
    raw, source = await _call_ai(SIMPLIFY_PROMPT, f"Language: {language}\n\nRewrite this:\n\n{text}")
    if not raw:
        return None, "offline"
    try:
        data = _extract_json(raw)
        return {
            "text": data.get("text", "").strip(),
            "bullet_points": data.get("bullet_points", [])[:5],
            "highlights": data.get("highlights", [])[:8],
        }, source
    except Exception as e:
        logger.warning("Simplify response failed to parse as JSON: %s | raw=%s", e, raw[:200])
        return None, "offline"


async def generate_lesson_plan(student_name: str, profile: str, subject: str, language: str) -> str:
    prompt = (
        f"Student: {student_name}\n"
        f"Reading Profile: {profile}\n"
        f"Subject: {subject}\n"
        f"Language: {language}\n\n"
        f"Generate a 30-minute lesson plan with specific activities for this profile."
    )
    raw, _ = await _call_ai(LESSON_PLAN_PROMPT, prompt)
    if raw:
        return raw.strip()
    return _fallback_lesson_plan(student_name, profile, subject)


async def _call_gemini_chat(system: str, turns: list, max_tokens: Optional[int] = None) -> str:
    """Call Gemini for one AI Assistant chat turn using proper multi-turn format.

    Raises AIServiceError (never returns None) so failures are never silently
    swallowed into a fallback answer. If the reply is cut off by the token
    budget (finishReason == MAX_TOKENS), retries once at a larger budget
    instead of returning a truncated sentence to the user.
    """
    key = get_gemini_key()

    contents = [
        {"role": "user" if t["role"] == "user" else "model", "parts": [{"text": t["content"]}]}
        for t in turns
    ]

    budget = max_tokens or MAX_OUTPUT_TOKENS
    logger.info("Gemini chat request | model=%s | turns=%d | max_output_tokens=%d", GEMINI_MODEL, len(contents), budget)

    async def _request(token_budget: int):
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(
                    f"{GEMINI_API_URL}?key={key}",
                    json={
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": contents,
                        "generationConfig": _generation_config(token_budget),
                    },
                )
        except httpx.TimeoutException as e:
            logger.error("Gemini chat timed out after %.0fs", REQUEST_TIMEOUT)
            raise AIServiceError(f"Gemini API timed out after {REQUEST_TIMEOUT:.0f}s.", status_code=504) from e
        except httpx.RequestError as e:
            logger.error("Gemini chat network error: %s", e)
            raise AIServiceError(f"Could not reach the Gemini API: {e}") from e

        latency_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code == 429:
            logger.error("Gemini chat rate limited (429) | latency_ms=%d", latency_ms)
            raise AIServiceError("Gemini API rate limit exceeded. Please try again shortly.", status_code=429)
        if resp.status_code == 401 or resp.status_code == 403:
            logger.error("Gemini chat auth error (%s) | latency_ms=%d", resp.status_code, latency_ms)
            raise AIServiceError("Gemini API rejected the request — check GEMINI_API_KEY.", status_code=500)
        if resp.status_code != 200:
            logger.error("Gemini chat HTTP %s | latency_ms=%d | body=%s", resp.status_code, latency_ms, resp.text[:500])
            raise AIServiceError(f"Gemini API returned HTTP {resp.status_code}: {resp.text[:300]}", status_code=502)

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
            logger.error("Gemini chat returned no candidates | blockReason=%s | raw=%s", block_reason, str(data)[:500])
            raise AIServiceError(f"Gemini API returned no candidates (blockReason={block_reason}).")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        try:
            text = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error("Gemini chat unexpected response shape | raw=%s", str(data)[:500])
            raise AIServiceError("Gemini API returned an unexpected response shape.") from e

        usage = data.get("usageMetadata", {})
        logger.info(
            "Gemini chat response | latency_ms=%d | chars=%d | finish_reason=%s | prompt_tokens=%s | output_tokens=%s",
            latency_ms, len(text), finish_reason,
            usage.get("promptTokenCount"), usage.get("candidatesTokenCount"),
        )
        return text.strip(), finish_reason

    text, finish_reason = await _request(budget)

    if finish_reason == "MAX_TOKENS" and budget < TRUNCATION_RETRY_MAX_TOKENS:
        retry_budget = min(int(budget * TRUNCATION_RETRY_MULTIPLIER), TRUNCATION_RETRY_MAX_TOKENS)
        logger.warning(
            "Chat reply truncated at %d tokens — retrying once at %d tokens.", budget, retry_budget,
        )
        text, finish_reason = await _request(retry_budget)
        if finish_reason == "MAX_TOKENS":
            logger.warning("Chat reply still truncated after retry at %d tokens — returning as-is.", retry_budget)

    return text


async def chat_reply(message: str, history: list, user_context: dict = None) -> tuple[str, str]:
    """Single production entry point for the AI Assistant chat.

    Returns (reply_text, source_tag) where source_tag is "gemini" on success.
    Raises AIServiceError on failure unless CHAT_OFFLINE_MODE=true, in which
    case it returns the offline FAQ answer with source_tag "offline-faq".
    """
    system = CHATBOT_SYSTEM
    if user_context:
        profile = user_context.get("readingProfile") or {}
        name = user_context.get("name", "Student")
        d_type = profile.get("type", "")
        lang = (user_context.get("languages") or ["english"])[0]
        if d_type:
            system += (
                f"\n\nStudent context: Name={name}, Dyslexia type={d_type}, "
                f"Language={lang}. Tailor all advice to {d_type}."
            )

    turns = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in (history or [])[-6:]]
    turns.append({"role": "user", "content": message})

    logger.info("Chat request received | msg_len=%d | history_turns=%d", len(message), len(turns) - 1)

    try:
        reply = await _call_gemini_chat(system, turns)
        return reply, "gemini"
    except AIServiceError as e:
        logger.error("Gemini chat failed: %s", e)
        if CHAT_OFFLINE_MODE:
            logger.warning("CHAT_OFFLINE_MODE=true — serving offline FAQ. reason=%s", e)
            return _faq_fallback(message), "offline-faq"
        # No silent fallback: propagate so the router returns a real HTTP error.
        raise


async def generate_ai_plan(screening_result: dict, progress: dict, user: dict) -> Optional[dict]:
    """Generate personalized learning plan from screening + progress data."""
    prompt = (
        f"Student: {user.get('name', 'Student')}, Age group: school-age\n"
        f"Dyslexia Type: {screening_result.get('type', 'Unknown')}\n"
        f"Severity Level: {screening_result.get('level', 'moderate')}\n"
        f"Screening Score: {screening_result.get('score', 0)}/100\n"
        f"Flags detected: {', '.join(screening_result.get('flags', []))}\n"
        f"Language preference: {(user.get('languages') or ['english'])[0]}\n"
        f"Current comprehension: {progress.get('avgComprehension', 0)}%\n"
        f"Docs scanned so far: {progress.get('docsScanned', 0)}\n"
        f"School context: Indian government/private school\n\n"
        f"Generate a 4-week adaptive learning plan."
    )
    raw, source = await _call_ai(AI_PLAN_PROMPT, prompt, max_tokens=1500)
    if not raw:
        return None
    try:
        return _extract_json(raw)
    except Exception as e:
        logger.warning("AI plan response failed to parse as JSON: %s", e)
        return None


async def generate_progress_suggestion(progress: dict, plan: dict, user: dict) -> Optional[dict]:
    """Analyze progress and suggest plan adaptations."""
    prompt = (
        f"Student: {user.get('name', 'Student')}\n"
        f"Dyslexia type: {(user.get('readingProfile') or {}).get('type', 'Unknown')}\n"
        f"Current avg comprehension: {progress.get('avgComprehension', 0)}%\n"
        f"Docs scanned this week: {progress.get('docsScanned', 0)}\n"
        f"Streak: {progress.get('streak', 0)} days\n"
        f"Words mastered: {progress.get('wordsMastered', 0)}\n"
        f"Recent comprehension scores: {progress.get('comprehensionScores', [])[-5:]}\n"
        f"Current plan summary: {plan.get('summary', 'Not available')}\n\n"
        f"Analyze this data and suggest plan adaptations."
    )
    raw, source = await _call_ai(PROGRESS_SUGGESTION_PROMPT, prompt)
    if not raw:
        return None
    try:
        return _extract_json(raw)
    except Exception as e:
        logger.warning("Progress suggestion response failed to parse as JSON: %s", e)
        return None


async def convert_notes_offline(text: str, language: str = "english") -> tuple[dict, str]:
    """Convert student notes to dyslexia-friendly format — AI with offline fallback."""
    raw, source = await _call_ai(OFFLINE_CONVERTER_PROMPT, f"Language: {language}\n\nNotes:\n\n{text}")
    if raw:
        try:
            data = _extract_json(raw)
            return data, source
        except Exception as e:
            logger.warning("Notes conversion response failed to parse as JSON: %s", e)
    # Offline fallback
    from services.offline_simplifier import simplify_offline
    return simplify_offline(text), "offline"


async def generate_daily_tasks(d_type: str, level: str, comp: int, user: dict) -> Optional[list]:
    """Generate AI daily tasks. Returns list or None."""
    lang = (user.get("languages") or ["english"])[0]
    prompt = (
        f"Student dyslexia type: {d_type}\n"
        f"Severity: {level}\n"
        f"Current comprehension: {comp}%\n"
        f"Language: {lang}\n\n"
        f"Generate 4 daily tasks appropriate for this student."
    )
    raw, _ = await _call_ai(DAILY_TASKS_PROMPT, prompt)
    if not raw:
        return None
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        tasks = json.loads(raw.strip())
        if isinstance(tasks, list):
            return tasks
    except Exception as e:
        logger.warning("Daily tasks response failed to parse as JSON: %s", e)
    return None


# ─── Fallbacks ──────────────────────────────────────────────────────────────

def _fallback_lesson_plan(name: str, profile: str, subject: str) -> str:
    return (
        f"Lesson Plan for {name} — {profile}\n\n"
        f"0-5 min:   Warm-up — Letter Detective game (identify target letters on flash cards)\n"
        f"5-15 min:  Scan today's {subject} chapter using DyslexAid Scan & Read\n"
        f"15-25 min: Listen to simplified version at 0.75x speed with word highlighting\n"
        f"25-30 min: Comprehension check — 3 multiple-choice questions\n\n"
        f"Accommodations: OpenDyslexic font on, cream background, 24px text minimum.\n"
        f"Homework: 10-minute re-read of the simplified version with a parent/sibling."
    )


FAQ = [
    ("dyslexia what is condition disorder",
     "Dyslexia is a reading difficulty where the brain struggles to connect letters to sounds. It is NOT related to intelligence. With the right tools, dyslexic children can thrive!"),
    ("scan camera photo upload pdf",
     "To scan text, tap 'Scan with Camera' or 'Upload PDF/Image'. The app will extract and simplify the text automatically."),
    ("language hindi tamil marathi english",
     "DyslexAid supports English, Hindi, Tamil, and Marathi. Select your language on the Scan & Read screen."),
    ("offline internet wifi network",
     "DyslexAid works offline. OCR, reading, and note conversion all work without internet after first setup."),
    ("free cost price subscription",
     "DyslexAid is 100% free — forever. No subscription, no charges."),
    ("font opendyslexic letters",
     "DyslexAid uses OpenDyslexic font — weighted bottoms on letters prevent b/d/p/q confusion."),
    ("tts read aloud speech voice listen play",
     "Tap Play to hear text read aloud. Each word highlights as spoken. Adjust speed from 0.75x to 1.5x."),
    ("screening test type detect",
     "Go to Dyslexia Screening for our medically-aligned test. It identifies the dyslexia type and the app adapts. It is a screening tool, not a medical diagnosis."),
    ("teacher dashboard class students",
     "Teachers get a full dashboard to monitor student progress and assign documents to the class."),
    ("plan learning schedule week",
     "After your screening test, our AI creates a personalized 4-week learning plan just for you. It updates as you progress!"),
    ("specialist doctor help consult",
     "For formal assessment, visit dyslexiaindia.org.in — the Dyslexia Association of India."),
    ("progress score comprehension improvement",
     "Check your Progress tab to see your comprehension scores, words mastered, reading streak, and weekly activity chart."),
]


def _faq_fallback(message: str) -> str:
    msg = message.lower()
    best = None
    best_score = 0
    for kws, ans in FAQ:
        score = sum(1 for kw in kws.split() if kw in msg)
        if score > best_score:
            best_score, best = score, ans
    if best and best_score > 0:
        return best
    return "Hi! I'm DyslexAid's assistant. I can help with dyslexia info, app usage, and reading tips. What would you like to know?"