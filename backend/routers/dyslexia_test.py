"""
Dyslexia Screening Test — medically-aligned DST-style, multi-age-band edition.

The /dyslexia-test/questions endpoint returns the age-appropriate test battery.
The /dyslexia-test/submit endpoint accepts answers and returns a full clinical-style report.

Based on:
- Dyslexia Screening Test (DST) by Fawcett & Nicolson
- Phonological Assessment Battery (PhAB)
- Dyslexia Association of India protocols
- NIMHANS Learning Disability Assessment

CHANGE LOG (v1 -> v2)
----------------------
- Every question now belongs to one of 16 explicit cognitive domains
  (previously ~8 loosely-named sections): Visual Processing, Letter
  Recognition, Letter Orientation, Visual Memory, Phonological Awareness,
  Sound Blending, Segmentation, Rhyming, Working Memory, Rapid Naming,
  Reading Fluency, Reading Accuracy, Orthographic Knowledge, Spelling,
  Reading Comprehension, Visual Attention.
- Visual Processing, Visual Memory, and Visual Attention previously had
  ZERO dedicated items — now each has 2 domain-specific questions per age
  band. Letter Orientation and Reading Accuracy were weak/conflated —
  now isolated and expanded.
- The bank now spans three age bands (6-8, 9-12, 13-16) with wording,
  vocabulary, and difficulty scaled per band, instead of one fixed set.
- Every question carries: id, domain, subdomain, difficulty, weight,
  time_limit, correct_answer, question_type, expected_response_time,
  learning_objective (plus legacy aliases so the existing frontend and
  services/screening_analyzer.py keep working unmodified).
- Duplicate/overlapping items (e.g. two near-identical spelling checks)
  were consolidated; question_type values are drawn only from the set
  services/screening_analyzer.py already scores, so no analyzer changes
  are required for full domain coverage.
- GET /questions gains an optional age/age_band selector (backward
  compatible — omitting it defaults to the 9-12 band, same as before).
"""
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user_optional, get_current_user
from services.screening_analyzer import analyze_screening

router = APIRouter(prefix="/dyslexia-test", tags=["dyslexia-test"])

# ─── Age bands ───────────────────────────────────────────────────────────────

AGE_BANDS: List[str] = ["6-8", "9-12", "13-16"]
DEFAULT_AGE_BAND = "9-12"


def _resolve_age_band(age: Optional[int]) -> str:
    """Map a raw age in years to the nearest supported age band."""
    if age is None:
        return DEFAULT_AGE_BAND
    if age <= 8:
        return "6-8"
    if age <= 12:
        return "9-12"
    return "13-16"


# ─── Question templates: 2 per domain x 16 domains = 32, each with 3 age variants ──
# Each template is the single source of truth for one domain/subdomain pairing;
# `_build_question_bank()` expands it into 3 fully-formed, age-appropriate items.

QUESTION_TEMPLATES: List[Dict[str, Any]] = [
    # === 1. Visual Processing =================================================
    {
        "domain": "Visual Processing", "subdomain": "Visual Discrimination",
        "question_type": "visual_discrimination", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Detect fine visual differences between similar letter/word forms.",
        "variants": {
            "6-8": {"instruction": "Look carefully and find the exact match.",
                     "question": "Which word matches this one exactly: 'saw'?",
                     "options": ["sae", "saw", "sqw", "swa"], "correct_answer": "saw",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 4000},
            "9-12": {"instruction": "Look carefully and find the exact match.",
                      "question": "Which word matches this one exactly: 'friend'?",
                      "options": ["freind", "friend", "fiernd", "frendi"], "correct_answer": "friend",
                      "difficulty": 3, "time_limit": 7, "expected_response_time": 3500},
            "13-16": {"instruction": "Look carefully and find the exact match.",
                       "question": "Which word matches this one exactly: 'necessary'?",
                       "options": ["neccessary", "necesary", "necessary", "neccesary"], "correct_answer": "necessary",
                       "difficulty": 4, "time_limit": 6, "expected_response_time": 3000},
        },
    },
    {
        "domain": "Visual Processing", "subdomain": "Letter-String Recognition",
        "question_type": "visual_wordform", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Recognise familiar letter strings as whole visual units.",
        "variants": {
            "6-8": {"instruction": "Spot the real word.", "question": "Which of these is a real word?",
                     "options": ["gob", "dog", "bod", "gdo"], "correct_answer": "dog",
                     "difficulty": 2, "time_limit": 6, "expected_response_time": 3000},
            "9-12": {"instruction": "Spot the real word.", "question": "Which of these is a real word?",
                      "options": ["siad", "dais", "said", "aids"], "correct_answer": "said",
                      "difficulty": 3, "time_limit": 6, "expected_response_time": 3000},
            "13-16": {"instruction": "Spot the real word.", "question": "Which of these is a real word?",
                       "options": ["quite", "quiet", "qutie", "qiuet"], "correct_answer": "quiet",
                       "difficulty": 4, "time_limit": 5, "expected_response_time": 2500},
        },
    },

    # === 2. Letter Recognition =================================================
    {
        "domain": "Letter Recognition", "subdomain": "Single Letter Identification",
        "question_type": "letter_recognition", "type": "multiple_choice", "weight": 0.8,
        "learning_objective": "Accurately identify individual printed letters.",
        "variants": {
            "6-8": {"instruction": "Which letter is shown correctly?",
                     "question": "Which of these is the letter 'b'?",
                     "options": ["d", "b", "p", "q"], "correct_answer": "b",
                     "difficulty": 1, "time_limit": 5, "expected_response_time": 2000},
            "9-12": {"instruction": "Which letter is shown correctly?",
                      "question": "Which of these is the letter 'g'?",
                      "options": ["p", "q", "g", "y"], "correct_answer": "g",
                      "difficulty": 2, "time_limit": 4, "expected_response_time": 1800},
            "13-16": {"instruction": "Match the uppercase to the lowercase letter.",
                       "question": "Which uppercase letter matches lowercase 'e'?",
                       "options": ["F", "E", "B", "R"], "correct_answer": "E",
                       "difficulty": 2, "time_limit": 3, "expected_response_time": 1500},
        },
    },
    {
        "domain": "Letter Recognition", "subdomain": "Letter-Sound Correspondence",
        "question_type": "letter_recognition", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Match a printed letter or letter pattern to its most common sound.",
        "variants": {
            "6-8": {"instruction": "Which letter makes this sound?",
                     "question": "Which letter makes the /s/ sound?",
                     "options": ["c", "s", "z", "x"], "correct_answer": "s",
                     "difficulty": 1, "time_limit": 6, "expected_response_time": 2500},
            "9-12": {"instruction": "Which letters make this sound?",
                      "question": "Which letter pair makes the /f/ sound in 'photo'?",
                      "options": ["ph", "f", "gh", "th"], "correct_answer": "ph",
                      "difficulty": 3, "time_limit": 6, "expected_response_time": 3000},
            "13-16": {"instruction": "Which letters make this sound?",
                       "question": "Which letter pair makes the /sh/ sound in 'ration'?",
                       "options": ["ti", "sh", "ci", "ssi"], "correct_answer": "ti",
                       "difficulty": 4, "time_limit": 5, "expected_response_time": 2500},
        },
    },

    # === 3. Letter Orientation =================================================
    {
        "domain": "Letter Orientation", "subdomain": "Letter Sequencing / Directionality",
        "question_type": "letter_reversal", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Correctly sequence and orient letters that are commonly reversed.",
        "variants": {
            "6-8": {"instruction": "Select the correct letter.",
                     "question": "Which letter comes right after 'd' in the alphabet?",
                     "options": ["b", "p", "e", "q"], "correct_answer": "e",
                     "difficulty": 2, "time_limit": 6, "expected_response_time": 2500},
            "9-12": {"instruction": "Order the letters alphabetically.",
                      "question": "Put these letters in alphabetical order: 'q d b'",
                      "options": ["b, d, q", "d, b, q", "q, b, d", "b, q, d"], "correct_answer": "b, d, q",
                      "difficulty": 3, "time_limit": 8, "expected_response_time": 3500},
            "13-16": {"instruction": "Order the letters alphabetically.",
                       "question": "Which sequence correctly orders these letters alphabetically: 'p, b, d, q'?",
                       "options": ["b, d, p, q", "p, q, b, d", "b, p, d, q", "d, b, p, q"], "correct_answer": "b, d, p, q",
                       "difficulty": 4, "time_limit": 8, "expected_response_time": 3500},
        },
    },
    {
        "domain": "Letter Orientation", "subdomain": "Mirror-Image Detection",
        "question_type": "mirror_letter", "type": "true_false", "weight": 1.1,
        "learning_objective": "Detect letters that are mirror images of the target letter.",
        "variants": {
            "6-8": {"instruction": "Look at the letter carefully.",
                     "question": "Is this the letter 'p'? (shown: 'q')",
                     "options": ["Yes", "No"], "correct_answer": "No",
                     "difficulty": 2, "time_limit": 5, "expected_response_time": 2000},
            "9-12": {"instruction": "Look at the letter carefully.",
                      "question": "Is this the letter 'b'? (shown: 'd')",
                      "options": ["Yes", "No"], "correct_answer": "No",
                      "difficulty": 3, "time_limit": 4, "expected_response_time": 1800},
            "13-16": {"instruction": "Look at the number carefully.",
                       "question": "Is a mirrored '6' the same as a '9'?",
                       "options": ["Yes", "No"], "correct_answer": "No",
                       "difficulty": 4, "time_limit": 4, "expected_response_time": 1800},
        },
    },

    # === 4. Visual Memory =======================================================
    {
        "domain": "Visual Memory", "subdomain": "Orthographic Visual Memory",
        "question_type": "visual_wordform", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Recall the exact letter sequence of a briefly viewed word.",
        "variants": {
            "6-8": {"instruction": "A word will flash for 2 seconds. Pick the word you saw.",
                     "question": "You saw the word 'cat' for 2 seconds. Which word did you see?",
                     "options": ["cot", "cat", "act", "tac"], "correct_answer": "cat",
                     "difficulty": 2, "time_limit": 6, "expected_response_time": 3000},
            "9-12": {"instruction": "A word will flash for 2 seconds. Pick the word you saw.",
                      "question": "You saw the word 'bread' for 2 seconds. Which word did you see?",
                      "options": ["bread", "beard", "braed", "bared"], "correct_answer": "bread",
                      "difficulty": 3, "time_limit": 6, "expected_response_time": 3000},
            "13-16": {"instruction": "A word will flash for 2 seconds. Pick the word you saw.",
                       "question": "You saw the word 'strength' for 2 seconds. Which word did you see?",
                       "options": ["strength", "strenght", "stregnth", "strentgh"], "correct_answer": "strength",
                       "difficulty": 4, "time_limit": 5, "expected_response_time": 2800},
        },
    },
    {
        "domain": "Visual Memory", "subdomain": "Visual Sequential Memory",
        "question_type": "digit_span", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Hold and recall a brief visual sequence in the correct order.",
        "variants": {
            "6-8": {"instruction": "Remember the order you saw.",
                     "question": "You saw these shapes in order: circle, square, triangle. What was the order?",
                     "options": ["circle, square, triangle", "square, circle, triangle",
                                 "triangle, circle, square", "circle, triangle, square"],
                     "correct_answer": "circle, square, triangle",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Remember the order you saw.",
                      "question": "You saw these numbers in order: 4, 8, 2, 5. What was the order?",
                      "options": ["4, 8, 2, 5", "4, 2, 8, 5", "8, 4, 2, 5", "4, 8, 5, 2"],
                      "correct_answer": "4, 8, 2, 5",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 4000},
            "13-16": {"instruction": "Remember the order you saw.",
                       "question": "You saw these numbers in order: 7, 3, 9, 1, 6. What was the order?",
                       "options": ["7, 3, 9, 1, 6", "7, 9, 3, 1, 6", "3, 7, 9, 1, 6", "7, 3, 1, 9, 6"],
                       "correct_answer": "7, 3, 9, 1, 6",
                       "difficulty": 4, "time_limit": 10, "expected_response_time": 4000},
        },
    },

    # === 5. Phonological Awareness ==============================================
    {
        "domain": "Phonological Awareness", "subdomain": "Phoneme Manipulation (Initial)",
        "question_type": "phoneme_deletion", "type": "multiple_choice", "weight": 1.3,
        "learning_objective": "Manipulate initial phonemes within spoken words.",
        "variants": {
            "6-8": {"instruction": "Remove a sound from the word.",
                     "question": "Say 'CAT' without the /k/ sound. What word do you get?",
                     "options": ["at", "cat", "hat", "ca"], "correct_answer": "at",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Remove a sound from the word.",
                      "question": "Say 'STOP' without the /s/ sound. What word do you get?",
                      "options": ["top", "cop", "hop", "pop"], "correct_answer": "top",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 4000},
            "13-16": {"instruction": "Remove a sound from the word.",
                       "question": "Say 'SPLASH' without the /s/ sound at the start. What word do you get?",
                       "options": ["plash", "lash", "splah", "pash"], "correct_answer": "plash",
                       "difficulty": 5, "time_limit": 10, "expected_response_time": 4000},
        },
    },
    {
        "domain": "Phonological Awareness", "subdomain": "Phoneme Manipulation (Medial/Final)",
        "question_type": "phoneme_deletion", "type": "multiple_choice", "weight": 1.2,
        "learning_objective": "Manipulate phonemes in the middle or end of words.",
        "variants": {
            "6-8": {"instruction": "Remove a sound from the word.",
                     "question": "Say 'SEAT' without the /t/ sound. What word do you get?",
                     "options": ["sea", "eat", "see", "set"], "correct_answer": "sea",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Remove a sound from the word.",
                      "question": "Say 'SMILE' without the /m/ sound. What word do you get?",
                      "options": ["sile", "style", "mile", "isle"], "correct_answer": "sile",
                      "difficulty": 4, "time_limit": 10, "expected_response_time": 4500},
            "13-16": {"instruction": "Remove a sound from the word.",
                       "question": "Say 'FRIEND' without the /r/ sound. What word do you get?",
                       "options": ["fiend", "find", "fend", "fined"], "correct_answer": "fiend",
                       "difficulty": 5, "time_limit": 10, "expected_response_time": 4500},
        },
    },

    # === 6. Sound Blending =======================================================
    {
        "domain": "Sound Blending", "subdomain": "Phoneme Blending",
        "question_type": "phoneme_blending", "type": "multiple_choice", "weight": 1.2,
        "learning_objective": "Blend individually spoken sounds into a whole word.",
        "variants": {
            "6-8": {"instruction": "Blend the sounds together to make a word.",
                     "question": "What word do these sounds make: /s/ /u/ /n/?",
                     "options": ["son", "sun", "sin", "san"], "correct_answer": "sun",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Blend the sounds together to make a word.",
                      "question": "What word do these sounds make: /b/ /r/ /i/ /d/ /g/?",
                      "options": ["bridge", "bright", "brick", "budge"], "correct_answer": "bridge",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 4500},
            "13-16": {"instruction": "Blend the sounds together to make a word.",
                       "question": "What word do these sounds make: /k/ /r/ /i/ /s/ /p/?",
                       "options": ["crisp", "chirp", "crips", "grips"], "correct_answer": "crisp",
                       "difficulty": 4, "time_limit": 8, "expected_response_time": 3500},
        },
    },
    {
        "domain": "Sound Blending", "subdomain": "Syllable Blending",
        "question_type": "phoneme_blending", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Blend spoken syllables into a whole word.",
        "variants": {
            "6-8": {"instruction": "Blend the syllables together.",
                     "question": "What word do these syllables make: 'rain' + 'bow'?",
                     "options": ["rainbow", "rainbown", "raybow", "rainboe"], "correct_answer": "rainbow",
                     "difficulty": 1, "time_limit": 8, "expected_response_time": 3500},
            "9-12": {"instruction": "Blend the syllables together.",
                      "question": "What word do these syllables make: 'com' + 'pu' + 'ter'?",
                      "options": ["computer", "compter", "computter", "comuter"], "correct_answer": "computer",
                      "difficulty": 2, "time_limit": 8, "expected_response_time": 3500},
            "13-16": {"instruction": "Blend the syllables together.",
                       "question": "What word do these syllables make: 'un' + 'be' + 'liev' + 'a' + 'ble'?",
                       "options": ["unbelievable", "unbelieveable", "unbeleivable", "unbelievible"],
                       "correct_answer": "unbelievable",
                       "difficulty": 3, "time_limit": 8, "expected_response_time": 3500},
        },
    },

    # === 7. Segmentation =========================================================
    {
        "domain": "Segmentation", "subdomain": "Phoneme Counting",
        "question_type": "phoneme_segmentation", "type": "multiple_choice", "weight": 1.2,
        "learning_objective": "Count the number of individual sounds in a word.",
        "variants": {
            "6-8": {"instruction": "Count the individual sounds.",
                     "question": "How many sounds are in the word 'CAT'?",
                     "options": ["2", "3", "4", "5"], "correct_answer": "3",
                     "difficulty": 1, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Count the individual sounds.",
                      "question": "How many sounds are in the word 'SHIP'?",
                      "options": ["2", "3", "4", "5"], "correct_answer": "3",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 4000},
            "13-16": {"instruction": "Count the individual sounds.",
                       "question": "How many sounds are in the word 'STRING'?",
                       "options": ["4", "5", "6", "7"], "correct_answer": "5",
                       "difficulty": 4, "time_limit": 10, "expected_response_time": 4500},
        },
    },
    {
        "domain": "Segmentation", "subdomain": "Syllable Counting",
        "question_type": "phoneme_segmentation", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Count the number of syllables in a word.",
        "variants": {
            "6-8": {"instruction": "Count the syllables (beats).",
                     "question": "How many syllables are in 'elephant'?",
                     "options": ["2", "3", "4", "5"], "correct_answer": "3",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 3500},
            "9-12": {"instruction": "Count the syllables (beats).",
                      "question": "How many syllables are in 'basketball'?",
                      "options": ["2", "3", "4", "5"], "correct_answer": "3",
                      "difficulty": 2, "time_limit": 8, "expected_response_time": 3500},
            "13-16": {"instruction": "Count the syllables (beats).",
                       "question": "How many syllables are in 'international'?",
                       "options": ["3", "4", "5", "6"], "correct_answer": "5",
                       "difficulty": 3, "time_limit": 8, "expected_response_time": 3500},
        },
    },

    # === 8. Rhyming ===============================================================
    {
        "domain": "Rhyming", "subdomain": "Rhyme Identification",
        "question_type": "rhyme_detection", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Identify words that share the same ending sound.",
        "variants": {
            "6-8": {"instruction": "Listen to the words and find the rhyme.",
                     "question": "Which word rhymes with 'CAT'?",
                     "options": ["dog", "bat", "cup", "run"], "correct_answer": "bat",
                     "difficulty": 1, "time_limit": 8, "expected_response_time": 3000},
            "9-12": {"instruction": "Listen to the words and find the rhyme.",
                      "question": "Which word rhymes with 'LIGHT'?",
                      "options": ["light", "night", "late", "list"], "correct_answer": "night",
                      "difficulty": 2, "time_limit": 6, "expected_response_time": 2800},
            "13-16": {"instruction": "Listen to the words and find the rhyme.",
                       "question": "Which word rhymes with 'ROUGH'?",
                       "options": ["through", "though", "tough", "dough"], "correct_answer": "tough",
                       "difficulty": 4, "time_limit": 6, "expected_response_time": 2800},
        },
    },
    {
        "domain": "Rhyming", "subdomain": "Rhyme Discrimination",
        "question_type": "rhyme_detection", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Detect which word does NOT rhyme with the others.",
        "variants": {
            "6-8": {"instruction": "Find the word that does not rhyme.",
                     "question": "Which word does NOT rhyme with 'hop, top, mop'?",
                     "options": ["stop", "shop", "step", "pop"], "correct_answer": "step",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 3500},
            "9-12": {"instruction": "Find the word that does not rhyme.",
                      "question": "Which word does NOT rhyme with 'chair, bear, wear'?",
                      "options": ["fair", "stair", "peer", "care"], "correct_answer": "peer",
                      "difficulty": 3, "time_limit": 8, "expected_response_time": 3500},
            "13-16": {"instruction": "Find the word that does not rhyme.",
                       "question": "Which word does NOT rhyme with 'ceiling, dealing, feeling'?",
                       "options": ["healing", "kneeling", "filling", "reeling"], "correct_answer": "filling",
                       "difficulty": 4, "time_limit": 8, "expected_response_time": 3500},
        },
    },

    # === 9. Working Memory =========================================================
    {
        "domain": "Working Memory", "subdomain": "Sentence/Sequence Memory",
        "question_type": "working_memory", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Hold and reorder spoken word sequences in working memory.",
        "variants": {
            "6-8": {"instruction": "Remember and rearrange.",
                     "question": "Rearrange these words into a sentence: 'runs fast dog the'",
                     "options": ["The dog runs fast", "Dog the runs fast", "Fast runs the dog", "The fast dog runs"],
                     "correct_answer": "The dog runs fast",
                     "difficulty": 2, "time_limit": 15, "expected_response_time": 5000},
            "9-12": {"instruction": "Remember and rearrange.",
                      "question": "Rearrange these words into a sentence: 'library the after went she school to'",
                      "options": ["She went to the library after school", "After school she went to the library",
                                  "She the library went after school to", "The library she went to after school"],
                      "correct_answer": "She went to the library after school",
                      "difficulty": 3, "time_limit": 20, "expected_response_time": 6000},
            "13-16": {"instruction": "Remember and rearrange.",
                       "question": ("Rearrange these words into a sentence: 'consequences carefully before "
                                     "decisions their consider should students important making'"),
                       "options": [
                           "Students should carefully consider the consequences before making important decisions",
                           "Students should consider carefully important decisions before the consequences making",
                           "Before making decisions students consequences should consider carefully important",
                           "Important decisions students should carefully making before consider consequences",
                       ],
                       "correct_answer": "Students should carefully consider the consequences before making important decisions",
                       "difficulty": 5, "time_limit": 25, "expected_response_time": 8000},
        },
    },
    {
        "domain": "Working Memory", "subdomain": "Verbal Working Memory (Nonword Recall)",
        "question_type": "nonword_repetition", "type": "multiple_choice", "weight": 1.2,
        "learning_objective": "Hold an unfamiliar sound sequence in memory long enough to reproduce it.",
        "variants": {
            "6-8": {"instruction": "Remember and identify the nonsense word you heard.",
                     "question": "Which nonsense word did you hear: 'PLIMBO'?",
                     "options": ["plimbo", "primbo", "plinbo", "plumbo"], "correct_answer": "plimbo",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 4000},
            "9-12": {"instruction": "Remember and identify the nonsense word you heard.",
                      "question": "Which nonsense word did you hear: 'FENDROPIC'?",
                      "options": ["fendropic", "fendropick", "frendopic", "fendropric"], "correct_answer": "fendropic",
                      "difficulty": 3, "time_limit": 12, "expected_response_time": 4500},
            "13-16": {"instruction": "Remember and identify the nonsense word you heard.",
                       "question": "Which nonsense word did you hear: 'BLONTERSTIP'?",
                       "options": ["blonterstip", "blunterstep", "blontestirp", "blonterstrip"],
                       "correct_answer": "blonterstip",
                       "difficulty": 4, "time_limit": 15, "expected_response_time": 5000},
        },
    },

    # === 10. Rapid Naming ===========================================================
    {
        "domain": "Rapid Naming", "subdomain": "Rapid Letter Naming",
        "question_type": "rapid_letter_naming", "type": "timed_task", "weight": 1.2,
        "learning_objective": "Name a row of familiar letters quickly and accurately.",
        "variants": {
            "6-8": {"instruction": "Name the letters as fast as you can (timed).",
                     "question": "Name these 5 letters as quickly as possible: a, s, m, t, p",
                     "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                     "correct_answer": "All correct fast",
                     "difficulty": 2, "time_limit": 12, "expected_response_time": 6000,
                     "note": "Mark slow_response=true if more than 10 seconds"},
            "9-12": {"instruction": "Name the letters as fast as you can (timed).",
                      "question": "Name these 8 letters as quickly as possible: b, d, p, n, m, q, g, h",
                      "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                      "correct_answer": "All correct fast",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 5000,
                      "note": "Mark slow_response=true if more than 8 seconds"},
            "13-16": {"instruction": "Name the letters as fast as you can (timed).",
                       "question": "Name these 12 letters as quickly as possible: b, d, p, q, n, m, u, w, g, y, i, l",
                       "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                       "correct_answer": "All correct fast",
                       "difficulty": 4, "time_limit": 10, "expected_response_time": 5000,
                       "note": "Mark slow_response=true if more than 8 seconds"},
        },
    },
    {
        "domain": "Rapid Naming", "subdomain": "Rapid Color Naming",
        "question_type": "rapid_color_naming", "type": "timed_task", "weight": 1.0,
        "learning_objective": "Name a row of colors quickly and accurately.",
        "variants": {
            "6-8": {"instruction": "Name the colors as fast as you can (timed).",
                     "question": "Name these colors quickly: Red, Blue, Yellow",
                     "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                     "correct_answer": "All correct fast",
                     "difficulty": 1, "time_limit": 10, "expected_response_time": 5000,
                     "note": "Mark slow_response=true if more than 8 seconds"},
            "9-12": {"instruction": "Name the colors as fast as you can (timed).",
                      "question": "Name these colors quickly: Red, Blue, Green, Yellow, Red",
                      "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                      "correct_answer": "All correct fast",
                      "difficulty": 2, "time_limit": 8, "expected_response_time": 4000,
                      "note": "Mark slow_response=true if more than 7 seconds"},
            "13-16": {"instruction": "Name the colors as fast as you can (timed).",
                       "question": "Name these colors quickly: Red, Blue, Green, Yellow, Purple, Orange, Red, Blue",
                       "options": ["All correct fast", "All correct slow", "Some errors fast", "Some errors slow"],
                       "correct_answer": "All correct fast",
                       "difficulty": 3, "time_limit": 8, "expected_response_time": 4000,
                       "note": "Mark slow_response=true if more than 6 seconds"},
        },
    },

    # === 11. Reading Fluency ==========================================================
    {
        "domain": "Reading Fluency", "subdomain": "Passage Reading Speed",
        "question_type": "reading_speed", "type": "timed_task", "weight": 1.2,
        "learning_objective": "Read connected text at an age-appropriate rate while maintaining accuracy.",
        "variants": {
            "6-8": {"instruction": "Read this short passage and answer. Time is measured.",
                     "question": "Read: 'The big black cat sat on the mat.' — Who sat on the mat?",
                     "options": ["A dog", "A black cat", "A red cat", "A child"], "correct_answer": "A black cat",
                     "difficulty": 2, "time_limit": 15, "expected_response_time": 6000,
                     "note": "Mark slow_response=true if more than 12 seconds"},
            "9-12": {"instruction": "Read this short passage and answer. Time is measured.",
                      "question": ("Read: 'Ravi packed his bag quickly and ran to catch the school bus before it "
                                    "left.' — What did Ravi do?"),
                      "options": ["Ravi missed the bus", "Ravi packed his bag and ran for the bus",
                                  "Ravi walked to school", "Ravi forgot his bag"],
                      "correct_answer": "Ravi packed his bag and ran for the bus",
                      "difficulty": 3, "time_limit": 15, "expected_response_time": 7000,
                      "note": "Mark slow_response=true if more than 12 seconds"},
            "13-16": {"instruction": "Read this short passage and answer. Time is measured.",
                       "question": ("Read: 'Despite the heavy rainfall, the volunteers continued distributing "
                                     "supplies to the flood-affected families.' — What did the volunteers do "
                                     "despite the rain?"),
                       "options": ["They stopped working", "They continued distributing supplies",
                                   "They went home", "They waited for the rain to stop"],
                       "correct_answer": "They continued distributing supplies",
                       "difficulty": 4, "time_limit": 15, "expected_response_time": 7000,
                       "note": "Mark slow_response=true if more than 12 seconds"},
        },
    },
    {
        "domain": "Reading Fluency", "subdomain": "Sight-Word Reading Speed",
        "question_type": "word_reading", "type": "timed_task", "weight": 1.0,
        "learning_objective": "Read high-frequency words quickly and automatically.",
        "variants": {
            "6-8": {"instruction": "Read this word as fast as you can.",
                     "question": "Read this word as fast as you can: 'was'",
                     "options": ["waz", "was", "saw", "wos"], "correct_answer": "was",
                     "difficulty": 1, "time_limit": 5, "expected_response_time": 2000},
            "9-12": {"instruction": "Read this word as fast as you can.",
                      "question": "Read this word as fast as you can: 'through'",
                      "options": ["throught", "through", "thourgh", "trough"], "correct_answer": "through",
                      "difficulty": 3, "time_limit": 5, "expected_response_time": 2000},
            "13-16": {"instruction": "Read this word as fast as you can.",
                       "question": "Read this word as fast as you can: 'conscientious'",
                       "options": ["conscientious", "consciencious", "conscientous", "consciensious"],
                       "correct_answer": "conscientious",
                       "difficulty": 5, "time_limit": 5, "expected_response_time": 2200},
        },
    },

    # === 12. Reading Accuracy ==========================================================
    {
        "domain": "Reading Accuracy", "subdomain": "Regular Word Decoding",
        "question_type": "word_reading", "type": "multiple_choice", "weight": 1.0,
        "learning_objective": "Accurately decode regularly-spelled words.",
        "variants": {
            "6-8": {"instruction": "Read this word correctly.",
                     "question": "What is the correct reading of: 'sit'?",
                     "options": ["sit", "sti", "its", "tis"], "correct_answer": "sit",
                     "difficulty": 1, "time_limit": 8, "expected_response_time": 3000},
            "9-12": {"instruction": "Read this word correctly.",
                      "question": "What is the correct reading of: 'planet'?",
                      "options": ["planet", "plantet", "panlet", "plaent"], "correct_answer": "planet",
                      "difficulty": 2, "time_limit": 7, "expected_response_time": 3000},
            "13-16": {"instruction": "Read this word correctly.",
                       "question": "What is the correct reading of: 'photosynthesis'?",
                       "options": ["photosynthesis", "photosyntheses", "photosinthesis", "photosynthisis"],
                       "correct_answer": "photosynthesis",
                       "difficulty": 4, "time_limit": 7, "expected_response_time": 3200},
        },
    },
    {
        "domain": "Reading Accuracy", "subdomain": "Nonword Decoding",
        "question_type": "pseudoword_reading", "type": "multiple_choice", "weight": 1.2,
        "learning_objective": "Apply phonics rules to decode unfamiliar letter strings.",
        "variants": {
            "6-8": {"instruction": "Read this nonsense word using phonics rules.",
                     "question": "How would you read: 'FLIB'?",
                     "options": ["flib", "bfil", "flub", "flab"], "correct_answer": "flib",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 3500},
            "9-12": {"instruction": "Read this nonsense word using phonics rules.",
                      "question": "How would you read: 'TREMPLE'?",
                      "options": ["tremple", "tremlpe", "tremble", "tempral"], "correct_answer": "tremple",
                      "difficulty": 3, "time_limit": 8, "expected_response_time": 3500},
            "13-16": {"instruction": "Read this nonsense word using phonics rules.",
                       "question": "How would you read: 'PHONTREGATION'?",
                       "options": ["phontregation", "phontrigation", "fontregation", "phontregasion"],
                       "correct_answer": "phontregation",
                       "difficulty": 5, "time_limit": 8, "expected_response_time": 4000},
        },
    },

    # === 13. Orthographic Knowledge ====================================================
    {
        "domain": "Orthographic Knowledge", "subdomain": "Irregular Word Recognition",
        "question_type": "irregular_words", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Recognise the correct spelling of common irregular (non-phonetic) words.",
        "variants": {
            "6-8": {"instruction": "Choose the correctly spelled irregular word.",
                     "question": "Which spelling is correct?",
                     "options": ["thay", "thei", "they", "thaiy"], "correct_answer": "they",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 3000},
            "9-12": {"instruction": "Choose the correctly spelled irregular word.",
                      "question": "Which spelling is correct?",
                      "options": ["wich", "which", "whitch", "whic"], "correct_answer": "which",
                      "difficulty": 3, "time_limit": 7, "expected_response_time": 2800},
            "13-16": {"instruction": "Choose the correctly spelled irregular word.",
                       "question": "Which spelling is correct?",
                       "options": ["rythm", "rhythm", "rhytm", "rhythem"], "correct_answer": "rhythm",
                       "difficulty": 5, "time_limit": 6, "expected_response_time": 2600},
        },
    },
    {
        "domain": "Orthographic Knowledge", "subdomain": "Word-Pattern Recognition",
        "question_type": "visual_wordform", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Spot the correctly formed word among plausible-looking distractors.",
        "variants": {
            "6-8": {"instruction": "Spot the real word.", "question": "Which of these is a real English word?",
                     "options": ["siad", "said", "dais", "dias"], "correct_answer": "said",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 3000},
            "9-12": {"instruction": "Spot the real word.", "question": "Which of these is a real English word?",
                      "options": ["freind", "friend", "fiernd", "frendi"], "correct_answer": "friend",
                      "difficulty": 3, "time_limit": 7, "expected_response_time": 2800},
            "13-16": {"instruction": "Spot the real word.", "question": "Which of these is a real English word?",
                       "options": ["beleive", "believe", "belive", "beleve"], "correct_answer": "believe",
                       "difficulty": 4, "time_limit": 6, "expected_response_time": 2600},
        },
    },

    # === 14. Spelling ====================================================================
    {
        "domain": "Spelling", "subdomain": "Phonetic Spelling",
        "question_type": "spelling", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Spell words that follow regular phonics patterns.",
        "variants": {
            "6-8": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                     "options": ["kat", "cat", "catt", "katt"], "correct_answer": "cat",
                     "difficulty": 1, "time_limit": 8, "expected_response_time": 3500},
            "9-12": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                      "options": ["becaus", "because", "becuase", "becouse"], "correct_answer": "because",
                      "difficulty": 3, "time_limit": 8, "expected_response_time": 4000},
            "13-16": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                       "options": ["definately", "definitely", "definitly", "definetly"], "correct_answer": "definitely",
                       "difficulty": 4, "time_limit": 8, "expected_response_time": 4000},
        },
    },
    {
        "domain": "Spelling", "subdomain": "Irregular/Complex Spelling",
        "question_type": "spelling", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Spell words with irregular or complex letter patterns.",
        "variants": {
            "6-8": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                     "options": ["frend", "friend", "freind", "frind"], "correct_answer": "friend",
                     "difficulty": 2, "time_limit": 8, "expected_response_time": 4000},
            "9-12": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                      "options": ["seperate", "separate", "seprate", "separete"], "correct_answer": "separate",
                      "difficulty": 4, "time_limit": 8, "expected_response_time": 4200},
            "13-16": {"instruction": "Choose the correct spelling.", "question": "Which word is spelled correctly?",
                       "options": ["accomodate", "acommodate", "accommodate", "acomodate"], "correct_answer": "accommodate",
                       "difficulty": 5, "time_limit": 8, "expected_response_time": 4200},
        },
    },

    # === 15. Reading Comprehension =========================================================
    {
        "domain": "Reading Comprehension", "subdomain": "Literal Comprehension",
        "question_type": "reading_comprehension", "type": "multiple_choice", "weight": 1.1,
        "learning_objective": "Answer literal (fact-based) questions about a short passage.",
        "variants": {
            "6-8": {"instruction": "Read and answer.",
                     "question": "Ravi went to school. He forgot his bag. He went back home. What did Ravi forget?",
                     "options": ["His lunch", "His homework", "His bag", "His friend"], "correct_answer": "His bag",
                     "difficulty": 2, "time_limit": 20, "expected_response_time": 7000},
            "9-12": {"instruction": "Read and answer.",
                      "question": ("Priya planted a seed in the garden. She watered it every day. After two weeks, "
                                    "a small plant grew. What did Priya do every day?"),
                      "options": ["She dug the soil", "She watered the seed", "She bought a plant",
                                  "She talked to the seed"],
                      "correct_answer": "She watered the seed",
                      "difficulty": 3, "time_limit": 20, "expected_response_time": 8000},
            "13-16": {"instruction": "Read and answer.",
                       "question": ("The factory reduced its water usage by 40% after installing new recycling "
                                     "equipment, even though production increased. What happened to water usage "
                                     "after the equipment was installed?"),
                       "options": ["It increased", "It stayed the same", "It decreased despite higher production",
                                   "Production stopped"],
                       "correct_answer": "It decreased despite higher production",
                       "difficulty": 5, "time_limit": 20, "expected_response_time": 9000},
        },
    },
    {
        "domain": "Reading Comprehension", "subdomain": "Contextual/Inferential Completion",
        "question_type": "sentence_completion", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Use context and world knowledge to complete a sentence logically.",
        "variants": {
            "6-8": {"instruction": "Complete the sentence correctly.", "question": "The sun rises in the ___.",
                     "options": ["west", "north", "east", "south"], "correct_answer": "east",
                     "difficulty": 1, "time_limit": 10, "expected_response_time": 3500},
            "9-12": {"instruction": "Complete the sentence correctly.",
                      "question": "Because it was raining heavily, the match was ___.",
                      "options": ["postponed", "celebrated", "ignored", "won"], "correct_answer": "postponed",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 4000},
            "13-16": {"instruction": "Complete the sentence correctly.",
                       "question": "Although the evidence was compelling, the jury remained ___ about the verdict.",
                       "options": ["convinced", "undecided", "furious", "absent"], "correct_answer": "undecided",
                       "difficulty": 4, "time_limit": 10, "expected_response_time": 4500},
        },
    },

    # === 16. Visual Attention =================================================================
    {
        "domain": "Visual Attention", "subdomain": "Visual-Motor Copying",
        "question_type": "copying_speed", "type": "multiple_choice", "weight": 0.8,
        "learning_objective": "Accurately and efficiently copy visually presented text.",
        "variants": {
            "6-8": {"instruction": "Copy this exactly, then rate how it went.",
                     "question": "Copy this word exactly: 'sun'. How did you do?",
                     "options": ["Copied correctly, fast", "Copied correctly, slow", "Small errors", "Many errors"],
                     "correct_answer": "Copied correctly, fast",
                     "difficulty": 1, "time_limit": 15, "expected_response_time": 8000},
            "9-12": {"instruction": "Copy this exactly, then rate how it went.",
                      "question": "Copy this sentence exactly: 'The quick fox runs.' How did you do?",
                      "options": ["Copied correctly, fast", "Copied correctly, slow", "Small errors", "Many errors"],
                      "correct_answer": "Copied correctly, fast",
                      "difficulty": 2, "time_limit": 20, "expected_response_time": 10000},
            "13-16": {"instruction": "Copy this exactly, then rate how it went.",
                       "question": ("Copy this sentence exactly: 'Scientific progress relies on careful "
                                     "observation.' How did you do?"),
                       "options": ["Copied correctly, fast", "Copied correctly, slow", "Small errors", "Many errors"],
                       "correct_answer": "Copied correctly, fast",
                       "difficulty": 3, "time_limit": 25, "expected_response_time": 12000},
        },
    },
    {
        "domain": "Visual Attention", "subdomain": "Visual Search / Tracking",
        "question_type": "visual_tracking", "type": "multiple_choice", "weight": 0.9,
        "learning_objective": "Locate a specific target while scanning a line or block of text.",
        "variants": {
            "6-8": {"instruction": "Scan the row and find the target.",
                     "question": "Find the letter 'b' in this row: d p q b p d. How did you do?",
                     "options": ["Found immediately", "Found after some searching", "Found with difficulty",
                                 "Could not find it"],
                     "correct_answer": "Found immediately",
                     "difficulty": 2, "time_limit": 10, "expected_response_time": 5000},
            "9-12": {"instruction": "Scan the row and find the target.",
                      "question": "Find the word 'the' in this row: they, then, the, that, there. How did you do?",
                      "options": ["Found immediately", "Found after some searching", "Found with difficulty",
                                  "Could not find it"],
                      "correct_answer": "Found immediately",
                      "difficulty": 3, "time_limit": 10, "expected_response_time": 5000},
            "13-16": {"instruction": "Scan the row and find the target.",
                       "question": "Find the number '742' in this row: 724, 427, 742, 274, 472. How did you do?",
                       "options": ["Found immediately", "Found after some searching", "Found with difficulty",
                                   "Could not find it"],
                       "correct_answer": "Found immediately",
                       "difficulty": 3, "time_limit": 8, "expected_response_time": 4000},
        },
    },
]


def _build_question_bank() -> Dict[str, List[Dict[str, Any]]]:
    """Expand QUESTION_TEMPLATES into fully-formed, age-banded question objects."""
    bank: Dict[str, List[Dict[str, Any]]] = {band: [] for band in AGE_BANDS}
    for t_index, template in enumerate(QUESTION_TEMPLATES):
        for band in AGE_BANDS:
            variant = template["variants"].get(band)
            if not variant:
                continue
            question: Dict[str, Any] = {
                "id": f"{template['question_type']}_{band.replace('-', '_')}_{t_index}",
                "domain": template["domain"],
                "subdomain": template["subdomain"],
                "section": template["domain"],          # legacy grouping key
                "age_band": band,
                "question_type": template["question_type"],
                "type": template.get("type", "multiple_choice"),
                "instruction": variant["instruction"],
                "question": variant["question"],
                "options": variant["options"],
                "correct_answer": variant["correct_answer"],
                "difficulty": variant["difficulty"],
                "weight": template["weight"],
                "time_limit": variant["time_limit"],
                "time_limit_seconds": variant["time_limit"],   # legacy alias
                "expected_response_time": variant["expected_response_time"],
                "learning_objective": template["learning_objective"],
                "points": variant["difficulty"],                # legacy alias
            }
            if "note" in variant:
                question["note"] = variant["note"]
            bank[band].append(question)
    return bank


SCREENING_QUESTIONS_BY_AGE: Dict[str, List[Dict[str, Any]]] = _build_question_bank()
ALL_QUESTIONS: List[Dict[str, Any]] = [q for band in AGE_BANDS for q in SCREENING_QUESTIONS_BY_AGE[band]]
QUESTIONS_BY_ID: Dict[str, Dict[str, Any]] = {q["id"]: q for q in ALL_QUESTIONS}

# Legacy name kept in case anything else imports SCREENING_QUESTIONS directly.
SCREENING_QUESTIONS: List[Dict[str, Any]] = SCREENING_QUESTIONS_BY_AGE[DEFAULT_AGE_BAND]


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/questions")
async def get_test_questions(age: Optional[int] = None, age_band: Optional[str] = None):
    """Return the age-appropriate standardized dyslexia screening test.

    Backward compatible: calling with no query params returns the 9-12
    band, matching the previous single fixed battery's behaviour.
    """
    band = age_band if age_band in AGE_BANDS else _resolve_age_band(age)
    questions = SCREENING_QUESTIONS_BY_AGE[band]

    sections: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        sec = q["section"]
        sections.setdefault(sec, []).append({k: v for k, v in q.items() if k != "correct_answer"})

    return {
        "age_band": band,
        "available_age_bands": AGE_BANDS,
        "total_questions": len(questions),
        "estimated_time_minutes": max(6, round(len(questions) * 0.4)),
        "sections": sections,
        "instructions": (
            "This is a screening test, not a medical diagnosis. "
            "Answer as best you can. Take your time. "
            "For each question, record if the response was slow (took longer than the time limit)."
        ),
        "disclaimer": "Based on DST (Fawcett & Nicolson) and Dyslexia Association of India protocols.",
    }


class ScreeningAnswer(BaseModel):
    question_id: str
    question_type: str
    given_answer: Optional[str] = None
    correct: Optional[bool] = True
    slow_response: Optional[bool] = False
    time_taken_seconds: Optional[float] = None
    response_time_ms: Optional[int] = None


class ScreeningSubmitReq(BaseModel):
    answers: List[ScreeningAnswer]
    method: Optional[str] = "combined"
    student_age: Optional[int] = None
    age_band: Optional[str] = None
    language: Optional[str] = "english"


@router.post("/submit")
async def submit_screening(req: ScreeningSubmitReq, authorization: Optional[str] = Header(None)):
    """Submit screening answers and get full clinical-style report."""
    if not req.answers:
        raise HTTPException(400, "No answers provided")

    # Auto-grade answers that weren't pre-graded by client. Question ids are
    # unique across all age bands, so this works regardless of which band
    # the client's /questions call returned.
    graded_answers = []
    for a in req.answers:
        qd = QUESTIONS_BY_ID.get(a.question_id, {})
        correct = a.correct
        if a.given_answer is not None and qd.get("correct_answer"):
            correct = a.given_answer.strip().lower() == qd["correct_answer"].strip().lower()

        slow = a.slow_response
        if a.time_taken_seconds and qd.get("time_limit"):
            slow = a.time_taken_seconds > qd["time_limit"]

        graded_answers.append({
            "question_type": a.question_type,
            "correct": correct,
            "slow_response": slow,
            "response_time_ms": a.response_time_ms,
        })

    result = analyze_screening(graded_answers, req.method or "combined")

    # Enhance with ML model prediction if model is trained
    try:
        from ai_model.train_model import predict_from_answers
        ml_result = predict_from_answers(graded_answers)
        if ml_result:
            result["ml_prediction"] = ml_result
            if ml_result["ml_type_confidence"] > 70:
                result["type"] = ml_result["ml_type"]
                result["level"] = ml_result["ml_level"]
                result["source"] = "ml_model"
            else:
                result["source"] = "rule_based"
        else:
            result["source"] = "rule_based"
    except Exception:
        result["source"] = "rule_based"

    # Save result to DB if user is logged in
    user = await get_current_user_optional(authorization)
    if user:
        now = int(time.time())
        band = req.age_band if req.age_band in AGE_BANDS else _resolve_age_band(req.student_age)
        screening_doc = {
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "result": result,
            "studentAge": req.student_age,
            "ageBand": band,
            "language": req.language,
            "answersCount": len(req.answers),
            "createdAt": now,
        }
        await db.screening_results.insert_one({**screening_doc})

        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {
                "readingProfile": {
                    "type": result["type"],
                    "level": result["level"],
                    "score": result["score"],
                    "recommendation": result["recommendation"],
                    "domain_scores": result["domain_scores"],
                    "strengths": result["strengths"],
                    "weaknesses": result["weaknesses"],
                    "screenedAt": now,
                }
            }}
        )

        await db.progress.update_one(
            {"userId": user["id"]},
            {"$set": {"screeningCompleted": True}},
            upsert=True,
        )

        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "title": "Screening Complete!",
            "message": f"Your dyslexia screening is done. Type: {result['type']}. Your AI learning plan is being created.",
            "type": "screening_complete",
            "read": False,
            "createdAt": now,
        })

        # Phase 2: Synthesize and update V2 Learner Intelligence Profile
        try:
            from services.learning.learner_profile_service import recalibrate_from_screening
            await recalibrate_from_screening(user["id"], result, req.student_age)
        except Exception as e:
            # Safe degradation: Never fail the V1 screening submission if V2 synthesis errors
            import logging
            logging.getLogger("dyslexaid.dyslexia_test").error(
                f"Non-blocking error during V2 learner profile synthesis for user {user['id']}: {e}",
                exc_info=True
            )

    return result



@router.get("/history")
async def get_screening_history(authorization: Optional[str] = Header(None)):
    """Get student's past screening results."""
    user = await get_current_user(authorization)
    results = await db.screening_results.find(
        {"userId": user["id"]}, {"_id": 0}
    ).sort("createdAt", -1).to_list(10)
    return results