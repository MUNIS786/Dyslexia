"""
backend/services/learning/tutor_service.py — V2 Personal AI Tutor Core Service.

Coordinates:
1. Dynamic, level-adapted pedagogical prompt construction
2. Gemini AI multi-turn interaction with structured JSON parsing & fallback
3. Robust deterministic offline tutor fallback (Vocabulary, Comprehension, Spelling, Hints, Encouragement)
4. Pedagogical action recommendations (practice_word, read_again, try_question, etc.)
5. Bounded history persistence in MongoDB (db.tutor_conversations)
6. Strict safety boundaries: anti-hallucination, anti-diagnosis, and context minimization
"""
import os
import re
import json
import time
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple

import httpx

from database.database import db
from models.v2_tutor import (
    TutorContext,
    TutorRequest,
    TutorResponse,
    TutorSuggestedAction,
    TutorMessage,
)
from services.learning.tutor_context import build_tutor_context

logger = logging.getLogger("dyslexaid.tutor_service")

# ─── Configuration ───────────────────────────────────────────────────────────

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
TUTOR_TIMEOUT = float(os.environ.get("TUTOR_REQUEST_TIMEOUT", "12.0"))
MAX_HISTORY_MESSAGES = 20

# Common educational vocabulary lookup dictionary for high-quality offline definitions
OFFLINE_DICTIONARY: Dict[str, Dict[str, Any]] = {
    "curious": {
        "definition": "Wanting to learn or know about something exciting.",
        "syllables": "cu · ri · ous",
        "example": "The curious kitten explored every corner of the room.",
        "simple_synonym": "interested",
    },
    "enormous": {
        "definition": "Very, very large in size or amount.",
        "syllables": "e · nor · mous",
        "example": "The friendly elephant was enormous compared to the mouse.",
        "simple_synonym": "huge",
    },
    "beautiful": {
        "definition": "Pleasing to look at or hear; very pretty.",
        "syllables": "beau · ti · ful",
        "example": "A beautiful bright rainbow appeared across the sunny sky.",
        "simple_synonym": "pretty",
    },
    "courageous": {
        "definition": "Brave; doing what is right even when you feel scared.",
        "syllables": "cou · ra · geous",
        "example": "The courageous boy stepped up to help his younger friend.",
        "simple_synonym": "brave",
    },
    "journey": {
        "definition": "Traveling from one place to another.",
        "syllables": "jour · ney",
        "example": "We packed our favorite snacks for the long train journey.",
        "simple_synonym": "trip",
    },
    "whisper": {
        "definition": "To speak in a very quiet, gentle voice.",
        "syllables": "whis · per",
        "example": "She had to whisper in the quiet library.",
        "simple_synonym": "speak softly",
    },
    "discover": {
        "definition": "To see, find, or learn something for the first time.",
        "syllables": "dis · cov · er",
        "example": "We used our magnifying glass to discover tiny insects.",
        "simple_synonym": "find",
    },
    "patient": {
        "definition": "Able to wait calmly without getting upset.",
        "syllables": "pa · tient",
        "example": "The teacher was very patient while we learned the new word.",
        "simple_synonym": "calm",
    },
    "ancient": {
        "definition": "From a very long time ago in history.",
        "syllables": "an · cient",
        "example": "They found an ancient coin buried deep under the sand.",
        "simple_synonym": "very old",
    },
    "rhythm": {
        "definition": "A repeated musical pattern of beats or sounds.",
        "syllables": "rhyth · m",
        "example": "Clap your hands to the steady rhythm of the song.",
        "simple_synonym": "beat",
    },
}


# ─── System Prompt Builder ───────────────────────────────────────────────────

def build_tutor_instruction(context: TutorContext) -> str:
    """
    Constructs a personalized, pedagogical system prompt based on learner level,
    active reading passage, practice areas, and safety guidelines.
    """
    level = context.learningLevel
    level_name = context.learningLevelName
    name = context.displayName or "Student"
    
    # Pedagogical style adaptations per level (Section 14)
    if level == 1:
        pedagogical_style = (
            "FOUNDATION LEVEL: Use very short, simple sentences (6-10 words each). "
            "Explain exactly one concept at a time. Use vivid, child-friendly everyday examples. "
            "Give lots of warm praise and encouragement. Avoid any big or complex words."
        )
    elif level == 2:
        pedagogical_style = (
            "DEVELOPING LEVEL: Use short sentences and simple vocabulary. "
            "Give clear, friendly explanations with one relatable example. "
            "Ask a gentle guiding question at the end to check understanding."
        )
    elif level == 3:
        pedagogical_style = (
            "PROGRESSING LEVEL: Provide clear explanations paired with simple reasoning. "
            "Use illustrative examples and encourage the learner to think about why something works."
        )
    else:
        pedagogical_style = (
            "COMPETENT/MASTERING LEVEL: Offer rich explanations with deeper context, reasoning, "
            "and an engaging comprehension or reflection challenge."
        )

    passage_context_block = "None currently active."
    if context.currentPassage:
        p = context.currentPassage
        vocab_str = ", ".join(p.vocabularyWords) if p.vocabularyWords else "None listed"
        passage_context_block = (
            f"Active Story Title: '{p.title}' (Difficulty Tier {p.difficulty})\n"
            f"Story Excerpt: \"{p.excerpt}\"\n"
            f"Story Vocabulary: {vocab_str}"
        )

    reading_signals_block = "No recent reading sessions recorded."
    if context.recentReading:
        rr = context.recentReading
        reading_signals_block = (
            f"Comprehension: {rr.get('comprehension', 0)}%, "
            f"Words Read: {rr.get('wordsRead', 0)}"
        )

    speech_signals_block = "No speech signals available."
    if context.speechSignals:
        ss = context.speechSignals
        speech_signals_block = f"Reading Accuracy: {ss.get('accuracy', 0)}%, Speed: {ss.get('wpm', 0)} WPM"

    lang = (context.language or "en").lower()
    if lang == "mr":
        language_guidance = (
            "LANGUAGE REQUIREMENT (MARATHI / मराठी):\n"
            "- You MUST write your 'message', 'explanation', 'followUpQuestion', and button 'label' in warm, encouraging, child-friendly Marathi (मराठी) using Devanagari script.\n"
            "- Keep vocabulary accessible, clear, and age-appropriate for primary learners.\n"
            "- If explaining an English word, provide the Marathi meaning and phonics breakdown clearly."
        )
    elif lang == "hi":
        language_guidance = (
            "LANGUAGE REQUIREMENT (HINDI / हिन्दी):\n"
            "- You MUST write your 'message', 'explanation', 'followUpQuestion', and button 'label' in warm, encouraging, child-friendly Hindi (हिन्दी) using Devanagari script.\n"
            "- Keep vocabulary accessible, clear, and age-appropriate for primary learners.\n"
            "- If explaining an English word, provide the Hindi meaning and phonics breakdown clearly."
        )
    else:
        language_guidance = (
            "LANGUAGE REQUIREMENT (ENGLISH):\n"
            "- Respond in clear, supportive, dyslexia-friendly English with simple vocabulary and short sentences."
        )

    prompt = f"""You are the Personal AI Tutor on DyslexAid, a supportive educational companion for learners.
Your learner's name is {name}.
Learner Current Level: Level {level} ({level_name}). Adaptive Tier: Tier {context.adaptiveTier}.
Learner Strengths: {', '.join(context.strengths) if context.strengths else 'Eager learner'}
Growth Practice Areas: {', '.join(context.practiceAreas) if context.practiceAreas else 'Reading fluency & confidence'}

ACTIVE READING STORY:
{passage_context_block}

ACTIVE WORD QUERIED:
{context.activeWord or 'None'}

RECENT PERFORMANCE SIGNALS:
- Reading: {reading_signals_block}
- Speech Practice: {speech_signals_block}

PEDAGOGICAL INSTRUCTION:
{pedagogical_style}

{language_guidance}

STRICT SAFETY & BEHAVIOR RULES (DO NOT VIOLATE):
1. NON-CLINICAL BOUNDARY: You are an educational tutor ONLY. NEVER mention, imply, diagnose, or discuss dyslexia, ADHD, learning disabilities, or medical conditions. Focus purely on reading, phonics, vocabulary, and learning skills.
2. ANTI-HALLUCINATION: Only refer to the story text provided above. If the student asks about a story or question not in the active passage, say politely: "I don't have that story open right now. Could you open it or type the sentence you'd like help with?" NEVER invent story plot details or test scores.
3. PROGRESSIVE HINTS: When a student asks for the answer to a comprehension question or puzzle, DO NOT give the final answer right away. Provide a gentle clue or hint that encourages them to look at the story!
4. RESPONSE LENGTH: Keep replies child-friendly, concise, and structured (2 to 4 short paragraphs or easy-to-read bullet points).
5. TONE: Warm, patient, curious, and celebratory of every effort.

RESPONSE FORMAT:
You MUST respond with a valid JSON object matching this schema:
{{
  "message": "Friendly, encouraging explanation or answer formatted with clear, short lines.",
  "explanation": "Optional simple breakdown or phonics/syllable hint, or null.",
  "suggestedAction": {{
    "type": "practice_word | read_again | try_question | open_reading_coach | start_adaptive_practice | review_hint",
    "label": "Short child-friendly button label (e.g. 'Practice this word')",
    "payload": {{"word": "..."}}
  }},
  "followUpQuestion": "A warm, gentle check question to encourage the learner to reply, or null."
}}
Do NOT output any markdown backticks around the JSON. Output pure raw JSON only.
"""
    return prompt.strip()


# ─── Deterministic Offline Tutor Fallback ─────────────────────────────────────

def generate_offline_fallback(
    request: TutorRequest,
    context: TutorContext,
) -> TutorResponse:
    """
    High-quality, deterministic offline fallback when AI services are unreachable,
    unconfigured, or timing out. Never crashes and provides immediate educational value.
    """
    raw_query = request.message.strip().lower()
    active_word = (request.activeWord or "").strip().lower()
    now = int(time.time())
    lang = (context.language or "en").lower()

    # Multilingual offline fallback for Marathi
    if lang == "mr":
        if any(k in raw_query for k in ["कठीण", "थकलो", "जमणार नाही", "नाही", "अवघड", "hard", "tired", "give up", "sad"]):
            return TutorResponse(
                status="ok",
                message=(
                    f"छान प्रयत्न करत आहात, {context.displayName}! 🌟\n\n"
                    f"वाचताना कधीकधी अडचण येणे अगदी स्वाभाविक आहे. आपण हळूहळू आणि सावकाश शिकूया.\n\n"
                    f"एक दीर्घ श्वास घ्या. आपण एकत्र सराव करूया!"
                ),
                explanation="प्रत्येक लहान प्रयत्नाने वाचनाची शक्ती वाढते.",
                suggestedAction=TutorSuggestedAction(
                    type="start_adaptive_practice",
                    label="सोपा खेळ खेळा",
                    payload={}
                ),
                followUpQuestion="आपण एखादा सोपा शब्द पाहूया का?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "encouragement", "language": "mr"},
                timestamp=now,
            )
        if context.currentPassage and any(k in raw_query for k in ["गोष्ट", "कथा", "hint", "story", "passage"]):
            p = context.currentPassage
            return TutorResponse(
                status="ok",
                message=(
                    f"तुमच्या **\"{p.title}\"** या गोष्टीत:\n\n"
                    f"\"{p.excerpt}\"\n\n"
                    f"**एक छोटी युक्ती:** पात्रांनी आधी काय केले आणि नंतर काय घडले ते सावकाश वाचा!"
                ),
                explanation="चांगले वाचक उत्तरे शोधण्यासाठी पुन्हा मजकूर वाचतात.",
                suggestedAction=TutorSuggestedAction(
                    type="try_question",
                    label="प्रश्नाचे उत्तर पुन्हा शोधा",
                    payload={"passageId": p.passageId}
                ),
                followUpQuestion="कथेतील कोणता भाग तुम्हाला सर्वात जास्त आवडला?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "comprehension_hint", "passageId": p.passageId, "language": "mr"},
                timestamp=now,
            )
        return TutorResponse(
            status="ok",
            message=(
                f"नमस्कार {context.displayName}! मी तुमचा DyslexAid वाचन मित्र आहे. 🌟\n\n"
                f"आपण एकत्र काय करू शकतो:\n"
                f"• **शब्दाचा अर्थ जाणून घेणे**: कोणत्याही शब्दाबद्दल विचारा\n"
                f"• **वाचन कथा समजून घेणे**: गोष्टीतून उत्तरे शोधणे\n"
                f"• **वाचन सराव**: सोपे शब्द आणि वाक्ये वाचणे"
            ),
            explanation="वाचन आणि शब्दांबद्दल मला काहीही विचारा!",
            suggestedAction=TutorSuggestedAction(
                type="open_reading_coach",
                label="वाचन कथा पहा",
                payload={}
            ),
            followUpQuestion="आज आपण कोणता शब्द किंवा गोष्ट शिकायची?",
            source="offline-fallback",
            learningLevel=context.learningLevel,
            contextSummary={"recognizedType": "general_guidance", "language": "mr"},
            timestamp=now,
        )

    # Multilingual offline fallback for Hindi
    if lang == "hi":
        if any(k in raw_query for k in ["कठिन", "थक", "मुश्किल", "नहीं हो रहा", "hard", "tired", "give up", "sad"]):
            return TutorResponse(
                status="ok",
                message=(
                    f"आप बहुत अच्छा प्रयास कर रहे हैं, {context.displayName}! 🌟\n\n"
                    f"पढ़ते समय कभी-कभी मुश्किल लगना बिल्कुल सामान्य है। हम धीरे-धीरे सीखेंगे।\n\n"
                    f"गहरी सांस लें। हम मिलकर अभ्यास करेंगे!"
                ),
                explanation="हर छोटे प्रयास से पढ़ने का आत्मविश्वास बढ़ता है।",
                suggestedAction=TutorSuggestedAction(
                    type="start_adaptive_practice",
                    label="मजेदार खेल खेलें",
                    payload={}
                ),
                followUpQuestion="क्या आप कोई आसान शब्द सीखना चाहेंगे?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "encouragement", "language": "hi"},
                timestamp=now,
            )
        if context.currentPassage and any(k in raw_query for k in ["कहानी", "hint", "story", "passage"]):
            p = context.currentPassage
            return TutorResponse(
                status="ok",
                message=(
                    f"आपकी कहानी **\"{p.title}\"** में:\n\n"
                    f"\"{p.excerpt}\"\n\n"
                    f"**एक आसान संकेत:** ध्यान से देखें कि पात्रों ने पहले क्या किया और उसके बाद क्या हुआ!"
                ),
                explanation="अच्छे पाठक उत्तर खोजने के लिए कहानी दोबारा पढ़ते हैं।",
                suggestedAction=TutorSuggestedAction(
                    type="try_question",
                    label="सवाल दोबारा देखें",
                    payload={"passageId": p.passageId}
                ),
                followUpQuestion="कहानी का कौन सा हिस्सा आपको सबसे अच्छा लगा?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "comprehension_hint", "passageId": p.passageId, "language": "hi"},
                timestamp=now,
            )
        return TutorResponse(
            status="ok",
            message=(
                f"नमस्ते {context.displayName}! मैं आपका DyslexAid पठन मित्र हूँ। 🌟\n\n"
                f"हम मिलकर क्या कर सकते हैं:\n"
                f"• **शब्द का अर्थ जानना**: किसी भी शब्द के बारे में पूछें\n"
                f"• **कहानी समझना**: कहानी से उत्तर खोजना\n"
                f"• **पठन अभ्यास**: आसान शब्द और वाक्य पढ़ना"
            ),
            explanation="शब्दों और कहानियों के बारे में मुझसे कुछ भी पूछें!",
            suggestedAction=TutorSuggestedAction(
                type="open_reading_coach",
                label="कहानियां देखें",
                payload={}
            ),
            followUpQuestion="आज आप क्या पढ़ना या सीखना चाहते हैं?",
            source="offline-fallback",
            learningLevel=context.learningLevel,
            contextSummary={"recognizedType": "general_guidance", "language": "hi"},
            timestamp=now,
        )

    # Detect target word if mentioned
    word_match = re.search(r'\b(?:what does|meaning of|mean|define|word|explain)\s+["\']?([a-zA-Z]{3,20})["\']?', raw_query)
    target_word = active_word or (word_match.group(1).lower() if word_match else None)

    # 1. Vocabulary Query Fallback
    if target_word or any(k in raw_query for k in ["mean", "meaning", "definition", "what is"]):
        w = target_word or "word"
        
        # Check passage vocabulary first
        passage_vocab_entry = None
        if context.currentPassage:
            pass
            
        dict_entry = OFFLINE_DICTIONARY.get(w)
        if dict_entry:
            msg = (
                f"**{w.capitalize()}** ({dict_entry['syllables']})\n\n"
                f"{dict_entry['definition']}\n\n"
                f"**Example:** *\"{dict_entry['example']}\"*"
            )
            return TutorResponse(
                status="ok",
                message=msg,
                explanation=f"You can think of '{w}' as meaning '{dict_entry['simple_synonym']}'.",
                suggestedAction=TutorSuggestedAction(
                    type="practice_word",
                    label=f"Practice '{w}'",
                    payload={"word": w}
                ),
                followUpQuestion=f"Can you try using '{w}' in a short sentence of your own?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "vocabulary", "word": w},
                timestamp=now,
            )
        elif target_word:
            # Word not in small offline dictionary
            msg = (
                f"Great question about the word **'{target_word}'**!\n\n"
                f"Let's break it down into parts and look at how it's used in your story. "
                f"Sound it out slowly: **{target_word[0].upper() + '-' + target_word[1:]}**."
            )
            return TutorResponse(
                status="ok",
                message=msg,
                explanation="Reading each syllable slowly helps our brain recognize new words.",
                suggestedAction=TutorSuggestedAction(
                    type="practice_word",
                    label=f"Practice '{target_word}'",
                    payload={"word": target_word}
                ),
                followUpQuestion="What do you think happens in the sentence around this word?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "vocabulary", "word": target_word},
                timestamp=now,
            )

    # 2. Spelling Query Fallback
    if any(k in raw_query for k in ["how do i spell", "how to spell", "spelling of", "spell"]):
        spell_match = re.search(r'\b(?:spell|spelling of)\s+["\']?([a-zA-Z]+)["\']?', raw_query)
        spell_word = spell_match.group(1).lower() if spell_match else (target_word or "friend")
        dict_entry = OFFLINE_DICTIONARY.get(spell_word)
        syllables = dict_entry["syllables"] if dict_entry else "-".join([spell_word[i:i+2] for i in range(0, len(spell_word), 2)])
        
        msg = (
            f"Here is how you spell **{spell_word.upper()}**:\n\n"
            f"**{spell_word}**\n\n"
            f"Break it into sounds: **{syllables}**."
        )
        return TutorResponse(
            status="ok",
            message=msg,
            explanation=f"Remember the letters: {', '.join(list(spell_word.upper()))}.",
            suggestedAction=TutorSuggestedAction(
                type="practice_word",
                label=f"Practice Spelling '{spell_word}'",
                payload={"word": spell_word}
            ),
            followUpQuestion=f"Can you type '{spell_word}' once to lock it in your memory?",
            source="offline-fallback",
            learningLevel=context.learningLevel,
            contextSummary={"recognizedType": "spelling", "word": spell_word},
            timestamp=now,
        )

    # 3. Reading Comprehension & Hint Fallback
    if any(k in raw_query for k in ["hint", "question", "answer", "story", "passage", "what happened", "don't understand"]):
        if context.currentPassage:
            p = context.currentPassage
            msg = (
                f"In your story **\"{p.title}\"**:\n\n"
                f"\"{p.excerpt}\"\n\n"
                f"**Here's a gentle clue:** Look at what the characters do first, and notice what happens right after!"
            )
            return TutorResponse(
                status="ok",
                message=msg,
                explanation="Good readers look back at the text to find clues.",
                suggestedAction=TutorSuggestedAction(
                    type="try_question",
                    label="Try Question Again",
                    payload={"passageId": p.passageId}
                ),
                followUpQuestion="What did you notice first when you read that part?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "comprehension_hint", "passageId": p.passageId},
                timestamp=now,
            )
        else:
            msg = (
                "I don't have the story you're reading right now!\n\n"
                "To give you the best clue, please open a story in the **Reading Coach** "
                "or paste the sentence you are working on here."
            )
            return TutorResponse(
                status="ok",
                message=msg,
                explanation="Once a story is open, I can give you hints and explain words.",
                suggestedAction=TutorSuggestedAction(
                    type="open_reading_coach",
                    label="Open Reading Coach",
                    payload={}
                ),
                followUpQuestion="Would you like to open a story to read together?",
                source="offline-fallback",
                learningLevel=context.learningLevel,
                contextSummary={"recognizedType": "missing_passage"},
                timestamp=now,
            )

    # 4. Emotional Support / Encouragement Fallback
    if any(k in raw_query for k in ["can't", "hard", "difficult", "tired", "give up", "stupid", "sad", "fail"]):
        msg = (
            f"You are doing wonderful work, {context.displayName}! 🌟\n\n"
            f"Learning to read can feel tricky sometimes, and that is completely normal. "
            f"Even the greatest readers had to take it one word at a time.\n\n"
            f"Take a slow, deep breath. We can go as slowly as you like."
        )
        return TutorResponse(
            status="ok",
            message=msg,
            explanation="Every small step builds your reading power.",
            suggestedAction=TutorSuggestedAction(
                type="start_adaptive_practice",
                label="Try a Fun Short Game",
                payload={}
            ),
            followUpQuestion="Would you like to try an easy word, or take a quick 1-minute stretch break?",
            source="offline-fallback",
            learningLevel=context.learningLevel,
            contextSummary={"recognizedType": "encouragement"},
            timestamp=now,
        )

    # 5. General Friendly Educational Guidance Fallback
    msg = (
        f"Hi {context.displayName}! I'm here to help you read, explore words, and practice.\n\n"
        f"Here are a few fun things we can do together:\n"
        f"• **Explain a word**: \"What does enormous mean?\"\n"
        f"• **Get a hint**: \"Can you give me a clue for question 1?\"\n"
        f"• **Practice spelling**: \"How do I spell beautiful?\"\n"
        f"• **Summarize**: \"Help me understand my reading story.\""
    )
    return TutorResponse(
        status="ok",
        message=msg,
        explanation="Ask me anything about words, stories, or letters!",
        suggestedAction=TutorSuggestedAction(
            type="open_reading_coach",
            label="Explore Reading Stories",
            payload={}
        ),
        followUpQuestion="What would you like to explore today?",
        source="offline-fallback",
        learningLevel=context.learningLevel,
        contextSummary={"recognizedType": "general_guidance"},
        timestamp=now,
    )


# ─── Gemini AI Integration & Response Parser ─────────────────────────────────

def _parse_ai_tutor_response(raw_text: str, context: TutorContext) -> TutorResponse:
    """
    Safely parses JSON or plain text generated by Gemini into a validated TutorResponse.
    Ensures that malformed JSON or markdown never crashes the API.
    """
    cleaned = raw_text.strip()
    # Strip markdown code blocks if the model wrapped output in ```json ... ```
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    now = int(time.time())

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            message = str(data.get("message") or "").strip()
            if not message:
                message = "Here is what I found for you! Let's keep exploring."
            
            explanation = data.get("explanation")
            if explanation and isinstance(explanation, str):
                explanation = explanation.strip()
            else:
                explanation = None

            suggested_action = None
            raw_action = data.get("suggestedAction")
            if isinstance(raw_action, dict) and raw_action.get("type") and raw_action.get("label"):
                suggested_action = TutorSuggestedAction(
                    type=str(raw_action["type"]),
                    label=str(raw_action["label"]),
                    payload=raw_action.get("payload") if isinstance(raw_action.get("payload"), dict) else {},
                )

            follow_up = data.get("followUpQuestion")
            if follow_up and isinstance(follow_up, str):
                follow_up = follow_up.strip()
            else:
                follow_up = None

            return TutorResponse(
                status="ok",
                message=message,
                explanation=explanation,
                suggestedAction=suggested_action,
                followUpQuestion=follow_up,
                source="gemini",
                learningLevel=context.learningLevel,
                contextSummary={
                    "hasPassage": bool(context.currentPassage),
                    "activeWord": context.activeWord,
                },
                timestamp=now,
            )
    except Exception as e:
        logger.warning(f"Could not parse Gemini JSON response ({e}), extracting text content safely.")

    # Plain-text fallback if model responded in free-form text
    return TutorResponse(
        status="ok",
        message=cleaned[:1200] if cleaned else "I am here to help you practice and learn!",
        explanation=None,
        suggestedAction=TutorSuggestedAction(
            type="start_adaptive_practice",
            label="Practice Activities",
            payload={}
        ),
        followUpQuestion="What else would you like to explore together?",
        source="gemini",
        learningLevel=context.learningLevel,
        contextSummary={"parsed": "plain_text"},
        timestamp=now,
    )


async def call_gemini_tutor(
    instruction: str,
    history: List[Dict[str, Any]],
    user_message: str,
) -> Optional[str]:
    """
    Calls the Gemini API with structured system instructions and conversation turns.
    Returns None on any error or timeout to signal that offline fallback should engage.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip() or GEMINI_KEY
    if not key:
        logger.info("GEMINI_API_KEY is not set. Using offline deterministic tutor.")
        return None

    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    # Format multi-turn conversation
    contents: List[Dict[str, Any]] = []
    # Include up to last 4 historical turns
    recent_history = history[-4:] if history else []
    for turn in recent_history:
        role = "user" if turn.get("role") == "user" else "model"
        content_text = turn.get("content") or turn.get("message") or ""
        if content_text.strip():
            contents.append({
                "role": role,
                "parts": [{"text": content_text.strip()}]
            })

    # Add current user prompt
    contents.append({
        "role": "user",
        "parts": [{"text": user_message.strip()}]
    })

    request_body = {
        "systemInstruction": {
            "parts": [{"text": instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.5,  # Moderate temperature for focused, pedagogical answers
            "topP": 0.9,
            "maxOutputTokens": 600,  # Bounded child-friendly length
        }
    }

    try:
        async with httpx.AsyncClient(timeout=TUTOR_TIMEOUT) as client:
            resp = await client.post(
                f"{api_url}?key={key}",
                json=request_body,
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = (candidates[0].get("content") or {}).get("parts") or []
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            else:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")
    except httpx.TimeoutException:
        logger.warning(f"Gemini AI tutor request timed out after {TUTOR_TIMEOUT}s. Engaging fallback.")
    except Exception as e:
        logger.warning(f"Gemini AI tutor call failed: {e}. Engaging fallback.")

    return None


# ─── Bounded History Management ──────────────────────────────────────────────

async def save_tutor_turn(
    learner_id: str,
    user_message: str,
    tutor_response: TutorResponse,
    conversation_id: Optional[str] = None,
) -> str:
    """
    Persists user message and tutor response in db.tutor_conversations.
    Maintains a bounded window of recent messages (max 20) per conversation.
    """
    now = int(time.time())
    conv_id = conversation_id or f"conv_{learner_id}"

    user_entry = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_message.strip(),
        "timestamp": now,
    }

    action_dict = None
    if tutor_response.suggestedAction:
        action_dict = tutor_response.suggestedAction.model_dump()

    assistant_entry = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": tutor_response.message,
        "explanation": tutor_response.explanation,
        "suggestedAction": action_dict,
        "followUpQuestion": tutor_response.followUpQuestion,
        "source": tutor_response.source,
        "timestamp": now,
    }

    try:
        conv = await db.tutor_conversations.find_one({"conversationId": conv_id})
        if conv:
            existing_messages = conv.get("messages", [])
            updated_messages = existing_messages + [user_entry, assistant_entry]
            # Keep bounded history
            if len(updated_messages) > MAX_HISTORY_MESSAGES:
                updated_messages = updated_messages[-MAX_HISTORY_MESSAGES:]
            
            await db.tutor_conversations.update_one(
                {"conversationId": conv_id},
                {
                    "$set": {
                        "messages": updated_messages,
                        "updatedAt": now,
                    }
                }
            )
        else:
            await db.tutor_conversations.insert_one({
                "conversationId": conv_id,
                "learnerId": learner_id,
                "messages": [user_entry, assistant_entry],
                "createdAt": now,
                "updatedAt": now,
            })
    except Exception as e:
        logger.error(f"Error saving tutor conversation turn: {e}")

    return conv_id


async def get_tutor_history(
    learner_id: str,
    conversation_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Retrieves bounded conversational history for a learner.
    Enforces learner ownership to prevent cross-student leakage.
    """
    conv_id = conversation_id or f"conv_{learner_id}"
    try:
        conv = await db.tutor_conversations.find_one(
            {"conversationId": conv_id, "learnerId": learner_id},
            {"_id": 0}
        )
        if conv:
            messages = conv.get("messages", [])
            return messages[-limit:]
    except Exception as e:
        logger.error(f"Error retrieving tutor history: {e}")
    return []


async def clear_tutor_history(
    learner_id: str,
    conversation_id: Optional[str] = None,
) -> bool:
    """
    Clears conversation history for the learner.
    """
    conv_id = conversation_id or f"conv_{learner_id}"
    try:
        res = await db.tutor_conversations.delete_one({"conversationId": conv_id, "learnerId": learner_id})
        return res.deleted_count > 0
    except Exception as e:
        logger.error(f"Error clearing tutor history: {e}")
        return False


# ─── Main Dispatcher ─────────────────────────────────────────────────────────

async def handle_tutor_chat(
    learner_id: str,
    request: TutorRequest,
) -> TutorResponse:
    """
    Primary orchestrator for V2 Personal AI Tutor:
    1. Builds deterministic, compact learner context
    2. Builds level-adapted prompt instructions
    3. Attempts Gemini AI provider call
    4. Automatically falls back to deterministic offline tutor on failure/timeout
    5. Saves interaction turn to bounded history
    6. Returns validated TutorResponse
    """
    # 1. Build compact context
    context = await build_tutor_context(
        learner_id=learner_id,
        active_passage_id=request.activePassageId,
        active_word=request.activeWord,
        language=request.language,
    )

    # 2. Build instructions
    instruction = build_tutor_instruction(context)

    # 3. Call AI provider
    response: Optional[TutorResponse] = None
    ai_raw = await call_gemini_tutor(
        instruction=instruction,
        history=request.history or [],
        user_message=request.message,
    )

    if ai_raw:
        response = _parse_ai_tutor_response(ai_raw, context)

    # 4. Fallback if AI provider unavailable, empty, or timed out
    if not response:
        response = generate_offline_fallback(request, context)

    # 5. Persist turn asynchronously (non-blocking for response)
    try:
        await save_tutor_turn(learner_id, request.message, response)
    except Exception as e:
        logger.warning(f"Could not persist tutor turn: {e}")

    return response
