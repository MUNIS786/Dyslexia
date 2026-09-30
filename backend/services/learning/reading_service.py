"""
backend/services/learning/reading_service.py — Reading Coach Service & Offline Passage Catalog.

Coordinates:
- Deterministic offline catalog of dyslexia-friendly reading passages (Tiers 1-5)
- Session lifecycle: initialization, telemetry tracking, server-side grading, and completion
- Performance computation and integration with the Phase 3 Adaptive Learning Engine
- Learner statistics, reading streak, and domain progression
"""
import time
import uuid
import logging
from typing import List, Dict, Any, Optional

from database.database import db
from models.v2_reading import (
    ReadingPassage,
    ReadingQuestion,
    ReadingVocabularyWord,
    ReadingSession,
    ReadingSessionStartRequest,
    ReadingSessionCompleteRequest,
    ReadingStatsResponse,
)
from services.learning.reading_performance import (
    calculate_comprehension_score,
    calculate_completion_rate,
    calculate_time_efficiency,
    calculate_overall_score,
    grade_comprehension_answers,
    analyze_reading_trend,
)
from services.learning.difficulty_engine import clamp_tier, TIER_CONFIGURATIONS
from services.learning.learner_profile_service import (
    get_learning_state,
    recalibrate_from_activity,
    get_or_create_learner_profile,
)

logger = logging.getLogger("dyslexaid.reading_service")

# ─── Comprehensive Offline Seed Passage Library ──────────────────────────────
# Original educational passages covering Tiers 1 through 5.
# Each includes vocabulary definitions with phonetics/syllables and comprehension questions.
DEFAULT_PASSAGES: List[Dict[str, Any]] = [
    # ══════════════════════════════════════════════════════════════════════════
    # TIER 1: Foundation (Short sentences, phonics, simple CVC / high-frequency words)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "passageId": "pas-t1-001",
        "title": "Sam the Orange Cat",
        "text": (
            "Sam is a fat cat. Sam is bright orange. "
            "He sits on a red mat. The sun is hot. "
            "Sam sees a little bug. The bug hops on the log. "
            "Sam taps the bug with his soft paw. "
            "The bug flies up into the blue sky. "
            "Sam purrs and naps in the warm sun."
        ),
        "difficulty": 1,
        "domain": "reading_comprehension",
        "estimatedMinutes": 2,
        "wordCount": 60,
        "language": "en",
        "gradeBand": "Grade 1",
        "topics": ["animals", "pets"],
        "accessibility": {"recommendedFontSize": 20, "lineHeight": 2.2},
        "active": True,
        "vocabulary": [
            {
                "word": "purrs",
                "definition": "Makes a soft, low vibrating sound when happy.",
                "phonetic": "purz",
                "syllables": ["purrs"],
                "exampleSentence": "The kitten purrs when you gently stroke its back."
            },
            {
                "word": "paw",
                "definition": "The soft foot of an animal like a cat or dog.",
                "phonetic": "paw",
                "syllables": ["paw"],
                "exampleSentence": "The cat waved its front paw at the feather."
            }
        ],
        "questions": [
            {
                "questionId": "q-t1-001-1",
                "question": "What color is Sam the cat?",
                "options": ["Black", "Bright orange", "White", "Grey"],
                "correctAnswer": 1,
                "explanation": "The story tells us right away: 'Sam is bright orange.'",
                "questionType": "detail"
            },
            {
                "questionId": "q-t1-001-2",
                "question": "What does Sam tap with his paw?",
                "options": ["A ball", "A red mat", "A little bug", "A fish"],
                "correctAnswer": 2,
                "explanation": "Sam sees a little bug on the log and taps it with his soft paw.",
                "questionType": "detail"
            },
            {
                "questionId": "q-t1-001-3",
                "question": "Where does the bug go at the end?",
                "options": ["Under the log", "Into the blue sky", "Into the water", "Behind the mat"],
                "correctAnswer": 1,
                "explanation": "The passage says 'The bug flies up into the blue sky.'",
                "questionType": "sequence"
            }
        ]
    },
    {
        "passageId": "pas-t1-002",
        "title": "The Little Red Hen",
        "text": (
            "Hen has a bag of seeds. She drops a seed in the dark mud. "
            "Rain falls down on the soil. The sun shines warm and bright. "
            "A green sprout pops up. The sprout grows tall and strong. "
            "Hen looks at the plant with a big smile. "
            "Good food will grow for all her friends."
        ),
        "difficulty": 1,
        "domain": "reading_comprehension",
        "estimatedMinutes": 2,
        "wordCount": 62,
        "language": "en",
        "gradeBand": "Grade 1",
        "topics": ["nature", "plants"],
        "accessibility": {"recommendedFontSize": 20, "lineHeight": 2.2},
        "active": True,
        "vocabulary": [
            {
                "word": "sprout",
                "definition": "A tiny young shoot or plant starting to grow from a seed.",
                "phonetic": "sprowt",
                "syllables": ["sprout"],
                "exampleSentence": "A tiny green sprout poked out of the flowerpot."
            },
            {
                "word": "soil",
                "definition": "The top layer of earth in which plants grow.",
                "phonetic": "soyl",
                "syllables": ["soil"],
                "exampleSentence": "We put rich black soil around the tomato roots."
            }
        ],
        "questions": [
            {
                "questionId": "q-t1-002-1",
                "question": "What does Hen drop in the dark mud?",
                "options": ["A coin", "A stone", "A seed", "A feather"],
                "correctAnswer": 2,
                "explanation": "The story says Hen 'drops a seed in the dark mud.'",
                "questionType": "detail"
            },
            {
                "questionId": "q-t1-002-2",
                "question": "What helps the sprout grow tall and strong?",
                "options": ["Rain and warm sun", "The cold wind", "A dark box", "Dry sand"],
                "correctAnswer": 0,
                "explanation": "Rain falls and the sun shines warm and bright to help it grow.",
                "questionType": "main_idea"
            }
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 2: Supported (Short paragraphs, simple compound sentences, everyday vocabulary)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "passageId": "pas-t2-001",
        "title": "Leo the Brave Pond Frog",
        "text": (
            "Leo was a small green tree frog who lived by a quiet lotus pond. "
            "All the bigger bullfrogs could leap across the wide water lilies with ease. "
            "Leo's back legs were tiny, so he often hesitated before jumping. "
            "One sunny morning, a buzzing dragonfly landed on a lily pad far from shore. "
            "Leo took a deep breath, gathered his strength, and made a giant leap. "
            "Splash! He landed perfectly in the center of the green pad. "
            "All the pond animals clapped and cheered for the brave little frog."
        ),
        "difficulty": 2,
        "domain": "reading_comprehension",
        "estimatedMinutes": 3,
        "wordCount": 94,
        "language": "en",
        "gradeBand": "Grade 2",
        "topics": ["courage", "animals", "pond life"],
        "accessibility": {"recommendedFontSize": 19, "lineHeight": 2.0},
        "active": True,
        "vocabulary": [
            {
                "word": "hesitated",
                "definition": "Paused for a brief moment before doing something because you feel unsure.",
                "phonetic": "hez-i-tay-tid",
                "syllables": ["hes", "i", "tat", "ed"],
                "exampleSentence": "Rohan hesitated before jumping into the pool water."
            },
            {
                "word": "lotus",
                "definition": "A beautiful water plant with large round leaves and pink or white flowers.",
                "phonetic": "loh-tuhs",
                "syllables": ["lo", "tus"],
                "exampleSentence": "The pink lotus floated gracefully on top of the pond."
            }
        ],
        "questions": [
            {
                "questionId": "q-t2-001-1",
                "question": "Why did Leo hesitate before jumping?",
                "options": [
                    "He was afraid of water",
                    "His back legs were tiny",
                    "He was too sleepy",
                    "He did not like dragonflies"
                ],
                "correctAnswer": 1,
                "explanation": "The text explains: 'Leo's back legs were tiny, so he often hesitated before jumping.'",
                "questionType": "detail"
            },
            {
                "questionId": "q-t2-001-2",
                "question": "What creature landed on the lily pad far from shore?",
                "options": ["A butterfly", "A bullfrog", "A buzzing dragonfly", "A little fish"],
                "correctAnswer": 2,
                "explanation": "A buzzing dragonfly landed on the lily pad, inspiring Leo to jump.",
                "questionType": "detail"
            },
            {
                "questionId": "q-t2-001-3",
                "question": "What is the main lesson of Leo's story?",
                "options": [
                    "Only big animals can leap far",
                    "Dragonflies are noisy",
                    "Trying your best takes courage and brings joy",
                    "Ponds are dangerous places"
                ],
                "correctAnswer": 2,
                "explanation": "Leo overcame his fear and cheered everyone by taking a brave leap.",
                "questionType": "main_idea"
            }
        ]
    },
    {
        "passageId": "pas-t2-002",
        "title": "Asha's Paper Kite",
        "text": (
            "Asha loved windy afternoons in her village. "
            "She spent two whole days making a bright diamond kite out of red paper and thin bamboo sticks. "
            "She tied a long yellow tail made of ribbon scraps to keep it steady. "
            "When Asha ran across the open grassy field, the breeze caught the kite. "
            "It danced high into the clouds, dipping and soaring like a joyful bird. "
            "Her little brother smiled and clapped as they took turns holding the string."
        ),
        "difficulty": 2,
        "domain": "reading_comprehension",
        "estimatedMinutes": 3,
        "wordCount": 85,
        "language": "en",
        "gradeBand": "Grade 2",
        "topics": ["play", "crafts", "family"],
        "accessibility": {"recommendedFontSize": 19, "lineHeight": 2.0},
        "active": True,
        "vocabulary": [
            {
                "word": "bamboo",
                "definition": "A tall, hollow, woody grass that is very strong and lightweight.",
                "phonetic": "bam-boo",
                "syllables": ["bam", "boo"],
                "exampleSentence": "Grandfather used smooth bamboo sticks to build a garden fence."
            },
            {
                "word": "soaring",
                "definition": "Flying high in the air without flapping wings.",
                "phonetic": "sor-ing",
                "syllables": ["soar", "ing"],
                "exampleSentence": "The eagle was soaring peacefully across the blue sky."
            }
        ],
        "questions": [
            {
                "questionId": "q-t2-002-1",
                "question": "What was the kite's yellow tail made of?",
                "options": ["Wool threads", "Ribbon scraps", "Banana leaves", "Plastic tape"],
                "correctAnswer": 1,
                "explanation": "Asha 'tied a long yellow tail made of ribbon scraps to keep it steady.'",
                "questionType": "detail"
            },
            {
                "questionId": "q-t2-002-2",
                "question": "Why did Asha add a tail to the kite?",
                "options": ["To make it heavier", "To keep it steady in the air", "To change its color", "To catch insects"],
                "correctAnswer": 1,
                "explanation": "The text states the tail was added 'to keep it steady.'",
                "questionType": "detail"
            }
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 3: Standard (Multi-paragraph, descriptive vocabulary, simple inferences)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "passageId": "pas-t3-001",
        "title": "The River Otters of the Western Ghats",
        "text": (
            "Along the winding mountain rivers of the Western Ghats, smooth-coated otters play a vital role. "
            "These sleek, web-footed mammals live in tight-knit family groups called holts. "
            "They spend their mornings gliding through clean freshwater streams, hunting for crabs and river fish.\n\n"
            "Otters are extraordinary swimmers with dense, waterproof fur that keeps them warm in chilly currents. "
            "Because otters require undisturbed riverbanks and sparkling clean water to thrive, scientists view them as bioindicators. "
            "When river otters are playful and healthy, it signals that the entire forest watershed is flourishing."
        ),
        "difficulty": 3,
        "domain": "reading_comprehension",
        "estimatedMinutes": 4,
        "wordCount": 97,
        "language": "en",
        "gradeBand": "Grade 3-4",
        "topics": ["nature", "wildlife", "conservation", "science"],
        "accessibility": {"recommendedFontSize": 18, "lineHeight": 1.9},
        "active": True,
        "vocabulary": [
            {
                "word": "bioindicators",
                "definition": "Living creatures whose health shows the overall cleanliness and balance of an environment.",
                "phonetic": "bye-oh-in-di-kay-terz",
                "syllables": ["bi", "o", "in", "di", "ca", "tors"],
                "exampleSentence": "Frogs and otters act as bioindicators because pollution harms them quickly."
            },
            {
                "word": "watershed",
                "definition": "An area of land where all the streams and rainfall drain into a common river or lake.",
                "phonetic": "waw-ter-shed",
                "syllables": ["wa", "ter", "shed"],
                "exampleSentence": "Protecting the mountain watershed keeps drinking water clean for everyone."
            },
            {
                "word": "flourishing",
                "definition": "Growing or developing in a healthy and successful way.",
                "phonetic": "flur-ish-ing",
                "syllables": ["flour", "ish", "ing"],
                "exampleSentence": "With plenty of sunshine and water, the garden flowers were flourishing."
            }
        ],
        "questions": [
            {
                "questionId": "q-t3-001-1",
                "question": "What is a family group of river otters called?",
                "options": ["A pride", "A pack", "A holt", "A school"],
                "correctAnswer": 2,
                "explanation": "The text states: 'These sleek, web-footed mammals live in tight-knit family groups called holts.'",
                "questionType": "detail"
            },
            {
                "questionId": "q-t3-001-2",
                "question": "Why do scientists consider river otters to be bioindicators?",
                "options": [
                    "They can speak to other animals",
                    "Their health reflects whether the river and forest ecosystem is clean",
                    "They migrate across the ocean every winter",
                    "They can change their fur colors"
                ],
                "correctAnswer": 1,
                "explanation": "Because otters need pristine clean water and undisturbed banks, their presence indicates a healthy watershed.",
                "questionType": "simple_inference"
            },
            {
                "questionId": "q-t3-001-3",
                "question": "What helps keep otters warm in cold mountain streams?",
                "options": ["Thick wool coats", "Dense waterproof fur", "Warm mud on their backs", "Big river rocks"],
                "correctAnswer": 1,
                "explanation": "The text notes they have 'dense, waterproof fur that keeps them warm in chilly currents.'",
                "questionType": "detail"
            }
        ]
    },
    {
        "passageId": "pas-t3-002",
        "title": "Maya and the Solar Oven",
        "text": (
            "During the school science fair, Maya wanted to cook without using electricity or firewood. "
            "She lined a cardboard pizza box with shiny aluminum foil to reflect the sun's rays inward. "
            "Next, she placed a sheet of clear plastic wrap across the top lid to trap warmth like a greenhouse.\n\n"
            "Inside the box, Maya placed a small metal tray with two slices of bread topped with cheddar cheese. "
            "She angled the box toward the bright midday sun. "
            "Within twenty minutes, heat was trapped inside, reaching over seventy degrees Celsius. "
            "The cheese melted smoothly into delicious golden toast, proving how renewable clean energy works."
        ),
        "difficulty": 3,
        "domain": "reading_comprehension",
        "estimatedMinutes": 4,
        "wordCount": 110,
        "language": "en",
        "gradeBand": "Grade 3-4",
        "topics": ["science", "clean energy", "inventions"],
        "accessibility": {"recommendedFontSize": 18, "lineHeight": 1.9},
        "active": True,
        "vocabulary": [
            {
                "word": "renewable",
                "definition": "Energy from natural sources that never runs out, like sunlight or wind.",
                "phonetic": "ri-noo-uh-buhl",
                "syllables": ["re", "new", "a", "ble"],
                "exampleSentence": "Solar power is a renewable source of energy that doesn't produce smoke."
            },
            {
                "word": "greenhouse",
                "definition": "A structure that traps heat inside so warmth builds up even when it's cool outside.",
                "phonetic": "green-hows",
                "syllables": ["green", "house"],
                "exampleSentence": "The glass greenhouse kept the delicate tomato seedlings warm all winter."
            }
        ],
        "questions": [
            {
                "questionId": "q-t3-002-1",
                "question": "What material did Maya use to reflect the sunlight into the box?",
                "options": ["Black cloth", "Shiny aluminum foil", "Brown paper", "Thick wood"],
                "correctAnswer": 1,
                "explanation": "Maya lined the pizza box with shiny aluminum foil to reflect the sun's rays inward.",
                "questionType": "detail"
            },
            {
                "questionId": "q-t3-002-2",
                "question": "What was the purpose of the clear plastic wrap?",
                "options": [
                    "To keep rain out of the yard",
                    "To trap heat inside like a greenhouse",
                    "To make the box heavier",
                    "To block all the sunlight"
                ],
                "correctAnswer": 1,
                "explanation": "The plastic wrap let sunlight enter while trapping the warmth inside.",
                "questionType": "detail"
            },
            {
                "questionId": "q-t3-002-3",
                "question": "What big concept did Maya's experiment demonstrate?",
                "options": [
                    "How to build pizza shops",
                    "How renewable solar energy can produce useful heat",
                    "Why metal melts faster than bread",
                    "How to stop the wind"
                ],
                "correctAnswer": 1,
                "explanation": "Her project proved that clean solar energy can cook food effectively without pollution.",
                "questionType": "main_idea"
            }
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 4: Advanced (Complex sentences, richer domain vocabulary, multi-step sequence)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "passageId": "pas-t4-001",
        "title": "The Secrets of Firefly Bioluminescence",
        "text": (
            "On warm summer evenings near meadows and riverbanks, tiny flashes of greenish-yellow light flicker among the tall grass. "
            "These magical sparks belong to fireflies, which are actually beetles capable of producing cold light through a process called bioluminescence.\n\n"
            "Unlike incandescent light bulbs that release over ninety percent of their energy as wasted heat, a firefly's lantern is nearly one hundred percent efficient. "
            "Inside a specialized organ on the underside of their abdomen, an organic molecule called luciferin combines with oxygen, magnesium, and an enzyme named luciferase. "
            "When this chemical reaction occurs, light radiates outward with virtually no warmth.\n\n"
            "Each species of firefly flashes in unique, rhythmic pulses. "
            "Male fireflies fly through the dusk flashing distinctive rhythm codes, while females perched on leaves reply with synchronized counter-signals. "
            "By studying this efficient cold light, biomedical engineers are now designing advanced medical sensors and eco-friendly lighting systems."
        ),
        "difficulty": 4,
        "domain": "reading_comprehension",
        "estimatedMinutes": 5,
        "wordCount": 154,
        "language": "en",
        "gradeBand": "Grade 5-6",
        "topics": ["biology", "bioluminescence", "insects", "biomimicry"],
        "accessibility": {"recommendedFontSize": 17, "lineHeight": 1.8},
        "active": True,
        "vocabulary": [
            {
                "word": "bioluminescence",
                "definition": "The emission of light by living organisms through chemical reactions inside their bodies.",
                "phonetic": "bye-oh-loo-mi-nes-uhns",
                "syllables": ["bi", "o", "lu", "mi", "nes", "cence"],
                "exampleSentence": "Deep sea jellyfish and fireflies both exhibit glowing bioluminescence."
            },
            {
                "word": "luciferase",
                "definition": "A biological enzyme that speeds up the chemical reaction producing light in fireflies.",
                "phonetic": "loo-sif-uh-rays",
                "syllables": ["lu", "cif", "er", "ase"],
                "exampleSentence": "Scientists use luciferase in laboratory research to illuminate microscopic cells."
            },
            {
                "word": "synchronized",
                "definition": "Occurring at the exact same time or in coordinated harmony.",
                "phonetic": "sing-kruh-nyzd",
                "syllables": ["syn", "chro", "nized"],
                "exampleSentence": "The dancers moved in synchronized steps to the beat of the drum."
            }
        ],
        "questions": [
            {
                "questionId": "q-t4-001-1",
                "question": "Why is a firefly's light referred to as 'cold light'?",
                "options": [
                    "Because fireflies only live in freezing climates",
                    "Because nearly one hundred percent of the energy is light with almost no wasted heat",
                    "Because it is cooled by river water",
                    "Because it turns blue during the winter"
                ],
                "correctAnswer": 1,
                "explanation": "Fireflies produce light with nearly 100% efficiency, creating brightness without releasing heat.",
                "questionType": "detail"
            },
            {
                "questionId": "q-t4-001-2",
                "question": "What is the primary purpose of the rhythmic flashing patterns?",
                "options": [
                    "To scare away small mammals",
                    "To communicate and recognize mates of their own species",
                    "To find water in the dark",
                    "To warm up their wings for flight"
                ],
                "correctAnswer": 1,
                "explanation": "Male and female fireflies use distinctive rhythm codes to communicate and find mates.",
                "questionType": "main_idea"
            },
            {
                "questionId": "q-t4-001-3",
                "question": "How are modern engineers using knowledge gained from firefly research?",
                "options": [
                    "To build larger insect traps",
                    "To create energy-efficient lighting and advanced medical sensors",
                    "To manufacture glow-in-the-dark paint for toys only",
                    "To heat homes during winter months"
                ],
                "correctAnswer": 1,
                "explanation": "Biomedical engineers study firefly chemistry to build ultra-efficient lighting and medical diagnostics.",
                "questionType": "detail"
            }
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 5: Mastery (Academic vocabulary, structural synthesis, nuanced inference)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "passageId": "pas-t5-001",
        "title": "Architectural Marvels: The Stepwells of India",
        "text": (
            "Throughout arid regions of western India, ancient architects engineered extraordinary subterranean structures known as 'baolis' or stepwells. "
            "Dating from as early as the sixth century CE, these monuments served far beyond simple cisterns; they were sophisticated hydrologic systems, community sanctuaries, and awe-inspiring architectural masterpieces.\n\n"
            "Constructed deep into the earth to reach natural aquifers, stepwells featured tiers of stone terraces and descending staircases. "
            "As groundwater levels fluctuated with seasonal monsoon rains, villagers could walk downward along intricately carved stone steps to access water regardless of drought severity. "
            "Moreover, the dense subterranean masonry maintained microclimates up to six degrees Celsius cooler than the scorching desert surface above, offering weary travelers a tranquil respite.\n\n"
            "Today, civil engineers and environmentalists re-examine these historical engineering feats for modern water conservation. "
            "By capturing and recharging groundwater through gravity rather than carbon-intensive mechanical pumps, ancient stepwells demonstrate how sustainable resource management can harmonize elegance with ecological resilience."
        ),
        "difficulty": 5,
        "domain": "reading_comprehension",
        "estimatedMinutes": 6,
        "wordCount": 166,
        "language": "en",
        "gradeBand": "Grade 7-8",
        "topics": ["history", "architecture", "water conservation", "engineering"],
        "accessibility": {"recommendedFontSize": 16, "lineHeight": 1.8},
        "active": True,
        "vocabulary": [
            {
                "word": "subterranean",
                "definition": "Existing, situated, or operating below the surface of the earth.",
                "phonetic": "sub-tuh-ray-nee-uhn",
                "syllables": ["sub", "ter", "ra", "ne", "an"],
                "exampleSentence": "The subterranean caverns stayed naturally cool throughout the blazing summer."
            },
            {
                "word": "aquifers",
                "definition": "Underground geological layers of rock or sand that contain and conduct groundwater.",
                "phonetic": "ak-wuh-ferz",
                "syllables": ["aq", "ui", "fers"],
                "exampleSentence": "Wells were drilled deep into the aquifer to supply fresh water to the city."
            },
            {
                "word": "respite",
                "definition": "A short period of rest or relief from something difficult or exhausting.",
                "phonetic": "res-pit",
                "syllables": ["res", "pite"],
                "exampleSentence": "The shaded veranda provided a peaceful respite from the sweltering heat."
            }
        ],
        "questions": [
            {
                "questionId": "q-t5-001-1",
                "question": "What dual advantage did the subterranean design of stepwells provide?",
                "options": [
                    "They stored grain and kept horses warm in winter",
                    "They accessed deep water across seasons and provided a cool community shelter",
                    "They defended cities from invasions and produced electricity",
                    "They were primarily built as religious tombs"
                ],
                "correctAnswer": 1,
                "explanation": "Stepwells provided reliable water access as aquifers fluctuated and kept air several degrees cooler than above ground.",
                "questionType": "main_idea"
            },
            {
                "questionId": "q-t5-001-2",
                "question": "Why are contemporary environmentalists studying ancient stepwells today?",
                "options": [
                    "To reconstruct medieval stone quarries",
                    "To learn how passive, gravity-fed groundwater replenishment can inspire sustainable modern water systems",
                    "To replace all modern piping with stone staircases",
                    "To eliminate the need for rainfall"
                ],
                "correctAnswer": 1,
                "explanation": "Modern environmentalists look to stepwells as models of gravity-based, energy-free groundwater recharging.",
                "questionType": "simple_inference"
            },
            {
                "questionId": "q-t5-001-3",
                "question": "What is the meaning of the word 'aquifer' as used in the passage?",
                "options": [
                    "A high-speed electric motor",
                    "An underground layer of rock or sediment containing groundwater",
                    "A decorative stone archway",
                    "A type of desert wind"
                ],
                "correctAnswer": 1,
                "explanation": "An aquifer is an underground natural water reservoir reached by digging into deep earth layers.",
                "questionType": "vocabulary_in_context"
            }
        ]
    }
]


# ─── Catalog Operations ───────────────────────────────────────────────────────

async def seed_reading_passages() -> int:
    """
    Seeds the reading_passages collection if empty, or ensures default passages exist.
    Called on system startup.
    """
    now = int(time.time())
    seeded = 0
    for p in DEFAULT_PASSAGES:
        doc = dict(p)
        doc["createdAt"] = now
        doc["updatedAt"] = now
        res = await db.reading_passages.update_one(
            {"passageId": doc["passageId"]},
            {"$setOnInsert": doc},
            upsert=True
        )
        if res.upserted_id is not None:
            seeded += 1

    logger.info(f"Seeded {seeded} new reading passages into database.")
    return seeded


async def get_passages(
    tier: Optional[int] = None,
    domain: Optional[str] = None,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves catalog passages matching optional tier, domain, and language filters.
    Falls back to offline in-memory catalog if database is temporarily unavailable.
    """
    query: Dict[str, Any] = {"active": True}
    if tier is not None:
        query["difficulty"] = clamp_tier(tier)
    if domain:
        query["domain"] = domain
    if language:
        query["language"] = language

    try:
        cursor = db.reading_passages.find(query, {"_id": 0}).sort("difficulty", 1)
        passages = await cursor.to_list(length=100)
        if passages:
            return passages
    except Exception as e:
        logger.warning(f"Database query for passages failed: {e}. Falling back to offline catalog.")

    # Offline fallback
    filtered = []
    for p in DEFAULT_PASSAGES:
        if tier is not None and p["difficulty"] != clamp_tier(tier):
            continue
        if domain and p["domain"] != domain:
            continue
        if language and p.get("language") != language:
            continue
        filtered.append(dict(p))
    return filtered


async def get_passage_by_id(passage_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single reading passage by unique passageId.
    """
    try:
        doc = await db.reading_passages.find_one({"passageId": passage_id}, {"_id": 0})
        if doc:
            return doc
    except Exception as e:
        logger.warning(f"Database fetch for passage {passage_id} failed: {e}")

    # Fallback to local catalog
    for p in DEFAULT_PASSAGES:
        if p["passageId"] == passage_id:
            return dict(p)
    return None


# ─── Reading Session Lifecycle ───────────────────────────────────────────────

async def start_reading_session(
    learner_id: str,
    req: ReadingSessionStartRequest
) -> Dict[str, Any]:
    """
    Initializes a new reading session record for a learner.
    Validates passage existence and sets initial session telemetry.
    """
    now = int(time.time())
    session_id = str(uuid.uuid4())

    passage = await get_passage_by_id(req.passageId)
    if not passage:
        raise ValueError(f"Passage '{req.passageId}' not found.")

    words_presented = int(passage.get("wordCount", len(passage.get("text", "").split())))

    session_doc = {
        "sessionId": session_id,
        "learnerId": learner_id,
        "activityId": req.activityId or f"reading-{req.passageId}",
        "passageId": req.passageId,
        "domain": passage.get("domain", "reading_comprehension"),
        "difficulty": int(passage.get("difficulty", 1)),
        "startedAt": now,
        "completedAt": None,
        "readingMode": req.readingMode or "standard",
        "language": req.language or passage.get("language", "en"),
        "wordsPresented": words_presented,
        "wordsRead": 0,
        "wordsCompleted": 0,
        "durationSeconds": 0,
        "comprehensionQuestions": len(passage.get("questions", [])),
        "comprehensionCorrect": 0,
        "comprehensionAccuracy": 0.0,
        "hintsUsed": 0,
        "replaysUsed": 0,
        "difficultWords": [],
        "practicedWords": [],
        "readingScore": 0.0,
        "comprehensionScore": 0.0,
        "overallScore": 0.0,
        "completed": False,
        "skipped": False,
        "adaptation": None,
        "createdAt": now,
        "updatedAt": now,
    }

    try:
        await db.reading_sessions.insert_one(session_doc)
    except Exception as e:
        logger.error(f"Error persisting reading session {session_id}: {e}", exc_info=True)

    # Return safe response without internal MongoDB _id
    safe_session = {k: v for k, v in session_doc.items() if k != "_id"}
    return {
        "status": "ok",
        "session": safe_session,
        "passage": passage,
    }


async def complete_reading_session(
    learner_id: str,
    req: ReadingSessionCompleteRequest
) -> Dict[str, Any]:
    """
    Completes a reading session:
    1. Validates session existence, ownership, and non-duplicate completion.
    2. Performs server-side grading of comprehension answers against passage questions.
    3. Calculates objective reading, comprehension, and overall scores.
    4. Updates session document in MongoDB.
    5. Feeds performance signals into Phase 3 Adaptive Learning Engine & Learner Profile.
    """
    now = int(time.time())

    # 1. Fetch and validate session
    session = await db.reading_sessions.find_one({"sessionId": req.sessionId})
    if not session:
        raise ValueError(f"Reading session '{req.sessionId}' not found.")

    if session.get("learnerId") != learner_id:
        raise PermissionError("Access denied: You do not own this reading session.")

    if session.get("completed") or session.get("completedAt"):
        raise ValueError("This reading session has already been completed.")

    passage_id = session.get("passageId")
    passage = await get_passage_by_id(passage_id)
    if not passage:
        raise ValueError(f"Passage '{passage_id}' could not be located.")

    # 2. Server-side grading of comprehension answers
    questions = passage.get("questions", [])
    correct_count, total_questions, evaluations = grade_comprehension_answers(
        questions=questions,
        user_answers=req.comprehensionAnswers
    )

    comprehension_score = calculate_comprehension_score(correct_count, total_questions)

    # 3. Calculate reading, pacing, and overall scores
    words_presented = session.get("wordsPresented", passage.get("wordCount", 50))
    words_read = req.wordsRead if req.wordsRead is not None else words_presented
    completion_rate = calculate_completion_rate(words_read, words_presented)

    time_efficiency = calculate_time_efficiency(
        duration_seconds=req.durationSeconds,
        word_count=words_presented,
        difficulty_tier=session.get("difficulty", 1)
    )

    practiced_count = len(req.practicedWords or [])
    overall_score = calculate_overall_score(
        comprehension_score=comprehension_score,
        completion_rate=completion_rate,
        time_efficiency=time_efficiency,
        completed=req.completed,
        skipped=req.skipped,
        hints_used=req.hintsUsed,
        words_practiced_count=practiced_count,
    )

    # Reading score: balanced mix of completion rate, pacing, and word practice
    reading_score = round(
        0.50 * completion_rate + 0.35 * time_efficiency + min(15.0, practiced_count * 3.0),
        1
    )

    # Optional speech reading practice blend
    speech_score = session.get("speechPracticeScore")
    if speech_score is not None:
        reading_score = round(0.50 * reading_score + 0.50 * float(speech_score), 1)
        overall_score = round(0.50 * comprehension_score + 0.30 * reading_score + 0.20 * completion_rate, 1)

    # 4. Phase 3 Adaptive Engine Integration
    # Re-evaluate ZPD difficulty progression via Phase 3 adaptation logic
    current_tier = session.get("difficulty", 1)
    state_doc = await get_learning_state(learner_id)
    consecutive_passes = int(state_doc.get("consecutive_passes", 0))
    consecutive_failures = int(state_doc.get("consecutive_failures", 0))
    rolling_scores = list(state_doc.get("rolling_comprehension_scores", []))
    current_streak = int(state_doc.get("current_streak", 0))

    rolling_scores.append(comprehension_score)
    if len(rolling_scores) > 10:
        rolling_scores = rolling_scores[-10:]

    is_pass = overall_score >= 80.0 and comprehension_score >= 70.0
    is_failure = overall_score < 50.0

    if is_pass:
        consecutive_passes += 1
        consecutive_failures = 0
    elif is_failure:
        consecutive_failures += 1
        consecutive_passes = 0

    new_tier = current_tier
    adaptation_triggered = False
    adaptation_reason = None

    if consecutive_passes >= 3 and current_tier < 5:
        new_tier = current_tier + 1
        adaptation_triggered = True
        adaptation_reason = (
            f"Reading mastery demonstrated! 3 consecutive high scores. "
            f"Advancing from Level {current_tier} to Level {new_tier}."
        )
        consecutive_passes = 0
    elif consecutive_failures >= 2 and current_tier > 1:
        new_tier = current_tier - 1
        adaptation_triggered = True
        adaptation_reason = (
            f"Providing gentle reading scaffolding. Adjusting to Level {new_tier} "
            f"for comfortable, joyful practice."
        )
        consecutive_failures = 0

    tier_changed = new_tier != current_tier
    tier_info = TIER_CONFIGURATIONS.get(new_tier, TIER_CONFIGURATIONS[1])

    # 5. Persist completed session record
    adaptation_summary = {
        "adaptationTriggered": adaptation_triggered,
        "previousTier": current_tier,
        "newTier": new_tier,
        "tierChanged": tier_changed,
        "reason": adaptation_reason,
        "evaluations": evaluations,
    }

    updated_session = {
        "completedAt": now,
        "durationSeconds": req.durationSeconds,
        "readingMode": req.readingMode or session.get("readingMode", "standard"),
        "wordsRead": words_read,
        "wordsCompleted": words_read if req.completed else 0,
        "comprehensionQuestions": total_questions,
        "comprehensionCorrect": correct_count,
        "comprehensionAccuracy": comprehension_score,
        "hintsUsed": req.hintsUsed,
        "replaysUsed": req.replaysUsed,
        "difficultWords": req.difficultWords or [],
        "practicedWords": req.practicedWords or [],
        "readingScore": reading_score,
        "comprehensionScore": comprehension_score,
        "overallScore": overall_score,
        "completed": req.completed,
        "skipped": req.skipped,
        "adaptation": adaptation_summary,
        "updatedAt": now,
    }

    await db.reading_sessions.update_one(
        {"sessionId": req.sessionId},
        {"$set": updated_session}
    )

    # 6. Synchronize with Learning State & Profile
    streak_incremented = False
    if current_streak == 0 or (now - int(state_doc.get("last_session_timestamp") or 0)) >= 86400:
        current_streak += 1
        streak_incremented = True

    updated_state = {
        "learnerId": learner_id,
        "activeDifficultyTier": new_tier,
        "active_difficulty_tier": new_tier,
        "tierName": tier_info["name"],
        "consecutivePasses": consecutive_passes,
        "consecutive_passes": consecutive_passes,
        "consecutiveFailures": consecutive_failures,
        "consecutive_failures": consecutive_failures,
        "rollingComprehensionScores": rolling_scores,
        "rolling_comprehension_scores": rolling_scores,
        "currentStreak": current_streak,
        "current_streak": current_streak,
        "lastSessionTimestamp": now,
        "last_session_timestamp": now,
        "lastAdaptationReason": adaptation_reason,
        "updatedAt": now,
        "updated_at": now,
    }
    await db.learning_states.update_one(
        {"learnerId": learner_id},
        {"$set": updated_state},
        upsert=True
    )

    # 7. Recalibrate Learner Profile domains (reading_comprehension & reading_fluency)
    try:
        await recalibrate_from_activity(
            user_id=learner_id,
            activity_data={
                "domain": "reading_comprehension",
                "score": comprehension_score,
                "tier": new_tier,
                "hesitationCount": 0,
                "hintsRequested": req.hintsUsed,
            }
        )
        if reading_score > 0:
            await recalibrate_from_activity(
                user_id=learner_id,
                activity_data={
                    "domain": "reading_fluency",
                    "score": reading_score,
                    "tier": new_tier,
                    "hesitationCount": 0,
                    "hintsRequested": 0,
                }
            )
    except Exception as e:
        logger.warning(f"Learner profile recalibration warning for user {learner_id}: {e}")

    # Also sync V1 progress collection for backward compatibility
    try:
        minutes_spent = round(float(req.durationSeconds) / 60.0, 2)
        await db.progress.update_one(
            {"userId": learner_id},
            {
                "$inc": {
                    "wordsRead": words_read,
                    "hoursReading": round(minutes_spent / 60.0, 3),
                    "totalTimeMinutes": int(minutes_spent),
                    "sessionCount": 1,
                },
                "$set": {
                    "lastActiveDate": now,
                    "streak": current_streak,
                }
            },
            upsert=True
        )
    except Exception as e:
        logger.warning(f"Progress sync error: {e}")

    # 8. Friendly, encouraging child-facing messages
    if tier_changed and new_tier > current_tier:
        next_step_msg = f"Fantastic! You unlocked Level {new_tier} ({tier_info['name']})!"
    elif tier_changed and new_tier < current_tier:
        next_step_msg = f"Great effort! We'll practice another comfortable passage at Level {new_tier}."
    elif overall_score >= 85.0:
        next_step_msg = "Outstanding reading! You're ready for your next exciting story!"
    elif overall_score >= 70.0:
        next_step_msg = "Great reading! Let's practice another passage at this level."
    else:
        next_step_msg = "Good try! We'll give you extra helpful hints on the next passage."

    return {
        "status": "ok",
        "sessionId": req.sessionId,
        "readingScore": reading_score,
        "comprehensionScore": comprehension_score,
        "overallScore": overall_score,
        "correctCount": correct_count,
        "totalQuestions": total_questions,
        "wordsRead": words_read,
        "durationSeconds": req.durationSeconds,
        "practicedWordsCount": practiced_count,
        "adaptation": adaptation_summary,
        "nextStepMessage": next_step_msg,
        "currentTier": new_tier,
        "streak": current_streak,
    }


# ─── Statistics & History ────────────────────────────────────────────────────

async def get_learner_sessions(
    learner_id: str,
    limit: int = 20,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Retrieves history of reading sessions for a specific learner.
    """
    cursor = db.reading_sessions.find(
        {"learnerId": learner_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit)

    return await cursor.to_list(length=limit)


async def get_learner_reading_stats(learner_id: str) -> ReadingStatsResponse:
    """
    Computes reading statistics for the learner:
    - Total & completed sessions
    - Words read & total minutes
    - Rolling comprehension accuracy & overall score
    - Reading trend analysis
    """
    sessions = await db.reading_sessions.find(
        {"learnerId": learner_id, "completed": True},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(length=100)

    state = await get_learning_state(learner_id)
    current_tier = clamp_tier(state.get("active_difficulty_tier", 1))

    total_sessions = len(sessions)
    if total_sessions == 0:
        return ReadingStatsResponse(
            totalSessions=0,
            completedSessions=0,
            totalWordsRead=0,
            totalMinutesRead=0.0,
            avgComprehensionAccuracy=0.0,
            avgOverallScore=0.0,
            currentTier=current_tier,
            wordsPracticedCount=0,
            recentSessions=[],
            domainPerformance={"reading_comprehension": 0.0, "reading_fluency": 0.0},
            trend="steady",
        )

    total_words = sum(s.get("wordsRead", 0) for s in sessions)
    total_seconds = sum(s.get("durationSeconds", 0) for s in sessions)
    total_minutes = round(float(total_seconds) / 60.0, 1)

    comp_scores = [s.get("comprehensionScore", 0.0) for s in sessions]
    overall_scores = [s.get("overallScore", 0.0) for s in sessions]

    avg_comp = round(sum(comp_scores) / float(total_sessions), 1)
    avg_overall = round(sum(overall_scores) / float(total_sessions), 1)

    practiced_count = sum(len(s.get("practicedWords", [])) for s in sessions)
    recent = sessions[:5]

    # Calculate trend (chronological order)
    chronological_scores = list(reversed(comp_scores))
    trend = analyze_reading_trend(chronological_scores)

    return ReadingStatsResponse(
        totalSessions=total_sessions,
        completedSessions=total_sessions,
        totalWordsRead=total_words,
        totalMinutesRead=total_minutes,
        avgComprehensionAccuracy=avg_comp,
        avgOverallScore=avg_overall,
        currentTier=current_tier,
        wordsPracticedCount=practiced_count,
        recentSessions=recent,
        domainPerformance={
            "reading_comprehension": avg_comp,
            "reading_fluency": round(sum(s.get("readingScore", 0.0) for s in sessions) / float(total_sessions), 1),
        },
        trend=trend,
    )
