"""
DyslexAid AI Model — Multi-Label Dyslexia Profile Classifier
==============================================================
Connects to:
  - services/screening_analyzer.py  (QUESTION_TYPES_TO_DOMAIN, lazy-imported)
  - ai_model/__init__.py            (imports predict_from_answers,
                                      screening_answers_to_features,
                                      TYPE_LABELS, LEVEL_LABELS, FEATURE_NAMES)
  - routers/dyslexia_test.py        (calls predict_from_answers(answers, student_meta))
"""

import os
import json
import numpy as np
import pandas as pd

# ─── Domains / Labels ────────────────────────────────────────────────────────

DOMAINS = [
    "phonological_awareness", "phonological_memory", "rapid_naming",
    "letter_reversal", "reading_fluency", "orthographic_spelling",
    "comprehension", "motor_writing",
]

LANGUAGES = ["english", "hindi", "tamil", "marathi", "telugu", "kannada", "other"]

MISTAKE_PATTERNS = [
    "letter_reversal", "letter_omission", "letter_substitution",
    "word_omission", "sequencing_error", "phonetic_substitution", "none",
]

PROFILE_LABELS = [
    "No Significant Indicators",
    "Phonological Dyslexia",
    "RAN Deficit (Rapid Naming)",
    "Surface Dyslexia",
    "Double Deficit",
    "Visual-Perceptual Dyslexia",
    "Working Memory Deficit",
    "Attention-Related Reading Difficulty",
]

# Backward-compatible alias (old single-label name still importable elsewhere)
TYPE_LABELS = PROFILE_LABELS

LEVEL_LABELS = ["low", "moderate", "high"]

QUESTION_TYPE_TO_MISTAKE_PATTERN = {
    "rhyme_detection": "phonetic_substitution",
    "phoneme_blending": "phonetic_substitution",
    "phoneme_segmentation": "phonetic_substitution",
    "phoneme_deletion": "phonetic_substitution",
    "working_memory": "sequencing_error",
    "digit_span": "sequencing_error",
    "nonword_repetition": "phonetic_substitution",
    "rapid_naming": "word_omission",
    "rapid_letter_naming": "letter_omission",
    "rapid_color_naming": "word_omission",
    "letter_recognition": "letter_substitution",
    "letter_reversal": "letter_reversal",
    "mirror_letter": "letter_reversal",
    "reading_speed": "sequencing_error",
    "word_reading": "word_omission",
    "pseudoword_reading": "phonetic_substitution",
    "irregular_words": "letter_substitution",
    "spelling": "letter_omission",
    "visual_wordform": "sequencing_error",
    "reading_comprehension": "sequencing_error",
}

LABEL_TO_MISTAKE_PATTERN = {
    "No Significant Indicators": "none",
    "Phonological Dyslexia": "phonetic_substitution",
    "RAN Deficit (Rapid Naming)": "word_omission",
    "Surface Dyslexia": "letter_substitution",
    "Double Deficit": "sequencing_error",
    "Visual-Perceptual Dyslexia": "letter_reversal",
    "Working Memory Deficit": "sequencing_error",
    "Attention-Related Reading Difficulty": "word_omission",
}

# ─── Feature Schema ──────────────────────────────────────────────────────────

NUMERIC_FEATURES = (
    [f"{d}_accuracy" for d in DOMAINS]
    + [f"{d}_response_time" for d in DOMAINS]
    + [
        "age",
        "reading_speed_wpm",
        "working_memory_score",
        "total_error_rate",
        "total_slow_rate",
        "phono_ran_interaction",
        "surface_score",
    ]
)

CATEGORICAL_FEATURES = ["language", "mistake_pattern"]

FEATURE_NAMES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# ─── Feature Engineering: raw answers -> profile -> feature frame ───────────

def screening_answers_to_profile(answers: list, student_meta: dict = None) -> dict:
    """Convert raw screening answers + optional student metadata into a
    domain-level profile dict used to build the model feature frame."""
    from services.screening_analyzer import QUESTION_TYPES_TO_DOMAIN

    student_meta = student_meta or {}

    domain_errors, domain_slow, domain_total = {}, {}, {}
    mistake_counter = {}

    for a in answers:
        qt = a.get("question_type", "")
        domain = QUESTION_TYPES_TO_DOMAIN.get(qt)
        if not domain:
            continue
        domain_total[domain] = domain_total.get(domain, 0) + 1
        if not a.get("correct", True):
            domain_errors[domain] = domain_errors.get(domain, 0) + 1
            pattern = QUESTION_TYPE_TO_MISTAKE_PATTERN.get(qt, "none")
            mistake_counter[pattern] = mistake_counter.get(pattern, 0) + 1
        if a.get("slow_response", False):
            domain_slow[domain] = domain_slow.get(domain, 0) + 1

    error_rates, slow_rates = [], []
    for d in DOMAINS:
        total = max(domain_total.get(d, 1), 1)
        error_rates.append(domain_errors.get(d, 0) / total)
        slow_rates.append(domain_slow.get(d, 0) / total)

    total_error = float(np.mean(error_rates))
    total_slow = float(np.mean(slow_rates))
    phono_ran_interaction = error_rates[0] * slow_rates[2]
    surface_score = error_rates[5] * (1 - error_rates[0])

    dominant_mistake_pattern = "none"
    if mistake_counter:
        dominant_mistake_pattern = max(mistake_counter, key=mistake_counter.get)

    reading_speed_wpm = student_meta.get("reading_speed_wpm")
    if reading_speed_wpm is None:
        base_wpm = 60 + float(student_meta.get("age", 9)) * 6
        reading_speed_wpm = max(
            15.0, base_wpm - total_error * 40 - total_slow * 30
        )

    working_memory_score = student_meta.get("working_memory_score")
    if working_memory_score is None:
        working_memory_score = float(np.clip(
            1 - error_rates[1] - 0.1 * slow_rates[1], 0, 1
        ))

    profile = {"language": student_meta.get("language", "english")}
    for i, d in enumerate(DOMAINS):
        profile[f"{d}_accuracy"] = 1 - error_rates[i]
        profile[f"{d}_response_time"] = slow_rates[i]
    profile.update({
        "age": float(student_meta.get("age", 9)),
        "reading_speed_wpm": float(reading_speed_wpm),
        "working_memory_score": float(working_memory_score),
        "total_error_rate": total_error,
        "total_slow_rate": total_slow,
        "phono_ran_interaction": float(phono_ran_interaction),
        "surface_score": float(surface_score),
        "mistake_pattern": dominant_mistake_pattern,
    })
    return profile


def build_feature_frame(profile: dict) -> pd.DataFrame:
    """Build a single-row DataFrame in FEATURE_NAMES order from a profile dict."""
    row = {name: profile.get(name, np.nan) for name in NUMERIC_FEATURES}
    row["language"] = profile.get("language", "english")
    row["mistake_pattern"] = profile.get("mistake_pattern", "none")
    return pd.DataFrame([row], columns=FEATURE_NAMES)


def screening_answers_to_features(answers: list, student_meta: dict = None) -> pd.DataFrame:
    """Backward-compatible entry point: answers -> model-ready feature frame."""
    profile = screening_answers_to_profile(answers, student_meta)
    return build_feature_frame(profile)


# ─── Preprocessing ────────────────────────────────────────────────────────────

def build_preprocessor():
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder

    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("num", numeric_pipe, NUMERIC_FEATURES),
        ("cat", categorical_pipe, CATEGORICAL_FEATURES),
    ])


# ─── Synthetic Multi-Label Data Generation ───────────────────────────────────

COMBOS = [
    ("No Significant Indicators",),
    ("Phonological Dyslexia",),
    ("RAN Deficit (Rapid Naming)",),
    ("Surface Dyslexia",),
    ("Double Deficit", "Phonological Dyslexia", "RAN Deficit (Rapid Naming)"),
    ("Visual-Perceptual Dyslexia",),
    ("Working Memory Deficit",),
    ("Attention-Related Reading Difficulty",),
    ("Phonological Dyslexia", "Working Memory Deficit"),
    ("Surface Dyslexia", "Visual-Perceptual Dyslexia"),
    ("Phonological Dyslexia", "Attention-Related Reading Difficulty"),
    ("RAN Deficit (Rapid Naming)", "Attention-Related Reading Difficulty"),
]


def _apply_label_pattern(label, base_error, base_slow, noise):
    if label == "Phonological Dyslexia":
        base_error[0] = 0.70 + noise()
        base_error[1] = 0.55 + noise()
        base_error[3] = 0.50 + noise()
        base_slow[0] = 0.40 + noise()
    elif label == "RAN Deficit (Rapid Naming)":
        base_slow[2] = 0.75 + noise()
        base_slow[4] = 0.60 + noise()
        base_error[2] = 0.35 + noise()
        base_error[4] = 0.30 + noise()
    elif label == "Surface Dyslexia":
        base_error[5] = 0.75 + noise()
        base_error[4] = 0.40 + noise()
        base_error[0] = max(0.05, 0.15 + noise())
    elif label == "Double Deficit":
        base_error[0] = max(base_error[0], 0.75 + noise())
        base_error[1] = max(base_error[1], 0.65 + noise())
        base_error[3] = max(base_error[3], 0.60 + noise())
        base_slow[2] = max(base_slow[2], 0.80 + noise())
        base_slow[4] = max(base_slow[4], 0.65 + noise())
    elif label == "Visual-Perceptual Dyslexia":
        base_error[3] = 0.65 + noise()
        base_error[5] = 0.45 + noise()
        base_slow[3] = 0.35 + noise()
    elif label == "Working Memory Deficit":
        base_error[1] = 0.70 + noise()
        base_slow[1] = 0.55 + noise()
        base_error[6] = 0.35 + noise()
    elif label == "Attention-Related Reading Difficulty":
        for i in range(8):
            base_slow[i] = max(base_slow[i], 0.35 + noise())
        base_error[6] = 0.40 + noise()
        base_error[7] = 0.35 + noise()
    else:  # No Significant Indicators
        for i in range(8):
            base_error[i] = 0.10 + abs(noise())
            base_slow[i] = 0.10 + abs(noise())


def _generate_profile_sample(active_labels: tuple) -> dict:
    noise = lambda: np.random.normal(0, 0.08)
    base_error = [0.10] * 8
    base_slow = [0.10] * 8

    for label in active_labels:
        _apply_label_pattern(label, base_error, base_slow, noise)

    base_error = np.clip(base_error, 0, 1).tolist()
    base_slow = np.clip(base_slow, 0, 1).tolist()

    total_error = float(np.mean(base_error))
    total_slow = float(np.mean(base_slow))
    phono_ran_interaction = base_error[0] * base_slow[2]
    surface_score = base_error[5] * (1 - base_error[0])

    if total_error < 0.25:
        level = 0
    elif total_error < 0.55:
        level = 1
    else:
        level = 2

    age = float(np.clip(np.random.normal(9, 2), 6, 14))
    language = np.random.choice(LANGUAGES, p=[0.35, 0.25, 0.1, 0.1, 0.08, 0.07, 0.05])
    primary_label = active_labels[0]
    mistake_pattern = LABEL_TO_MISTAKE_PATTERN.get(primary_label, "none")
    if np.random.rand() < 0.15:
        mistake_pattern = np.random.choice(MISTAKE_PATTERNS)

    reading_speed_wpm = max(
        15.0, (60 + age * 6) - total_error * 40 - total_slow * 30 + np.random.normal(0, 5)
    )
    working_memory_score = float(np.clip(
        1 - base_error[1] - 0.1 * base_slow[1] + noise(), 0, 1
    ))

    row = {}
    for i, d in enumerate(DOMAINS):
        row[f"{d}_accuracy"] = 1 - base_error[i]
        row[f"{d}_response_time"] = base_slow[i]
    row.update({
        "age": age,
        "reading_speed_wpm": float(reading_speed_wpm),
        "working_memory_score": working_memory_score,
        "total_error_rate": total_error,
        "total_slow_rate": total_slow,
        "phono_ran_interaction": float(phono_ran_interaction),
        "surface_score": float(surface_score),
        "language": language,
        "mistake_pattern": mistake_pattern,
    })
    return row, list(active_labels), level


def generate_synthetic_dataset(n_samples: int = 3000):
    np.random.seed(42)
    samples_per_combo = max(1, n_samples // len(COMBOS))

    rows, label_lists, levels, combo_keys = [], [], [], []
    for combo in COMBOS:
        for _ in range(samples_per_combo):
            row, labels, level = _generate_profile_sample(combo)
            rows.append(row)
            label_lists.append(labels)
            levels.append(level)
            combo_keys.append("|".join(sorted(labels)))

    X_df = pd.DataFrame(rows, columns=FEATURE_NAMES)

    from sklearn.preprocessing import MultiLabelBinarizer
    mlb = MultiLabelBinarizer(classes=PROFILE_LABELS)
    Y_bin = mlb.fit_transform(label_lists)
    y_level = np.array(levels)

    return X_df, Y_bin, y_level, combo_keys, mlb


# ─── Training ─────────────────────────────────────────────────────────────────

def train_model():
    try:
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.multiclass import OneVsRestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import train_test_split, KFold
        from sklearn.metrics import (
            classification_report, accuracy_score, hamming_loss,
            roc_auc_score, f1_score,
        )
        from sklearn.base import clone
        import joblib
    except ImportError:
        print("Install: pip install scikit-learn pandas numpy joblib")
        return

    print("Generating synthetic multi-label training data...")
    X_df, Y_bin, y_level, combo_keys, mlb = generate_synthetic_dataset(n_samples=3000)
    print(f"Dataset: {X_df.shape[0]} samples, {X_df.shape[1]} raw features, "
          f"{len(PROFILE_LABELS)} profile labels")

    X_train, X_test, Y_train, Y_test, yl_train, yl_test = train_test_split(
        X_df, Y_bin, y_level, test_size=0.2, random_state=42, stratify=combo_keys
    )

    # ─── Multi-label profile classifier ──────────────────────────────────
    print("\nTraining multi-label PROFILE classifier...")
    profile_pipeline = Pipeline([
        ("preprocess", build_preprocessor()),
        ("clf", OneVsRestClassifier(RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_split=4,
            class_weight="balanced", random_state=42,
        ))),
    ])
    profile_pipeline.fit(X_train, Y_train)

    Y_pred = profile_pipeline.predict(X_test)
    Y_proba = profile_pipeline.predict_proba(X_test)

    subset_accuracy = accuracy_score(Y_test, Y_pred)
    h_loss = hamming_loss(Y_test, Y_pred)
    try:
        macro_auc = roc_auc_score(Y_test, Y_proba, average="macro")
    except ValueError:
        macro_auc = None

    print(f"Subset (exact-match) accuracy: {subset_accuracy:.3f}")
    print(f"Hamming loss: {h_loss:.3f}")
    if macro_auc is not None:
        print(f"Macro ROC-AUC: {macro_auc:.3f}")
    print(classification_report(Y_test, Y_pred, target_names=PROFILE_LABELS, zero_division=0))

    # ─── 5-fold cross-validation ──────────────────────────────────────────
    print("Running 5-fold cross-validation on training set...")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    X_train_r = X_train.reset_index(drop=True)
    cv_subset, cv_hamming, cv_f1 = [], [], []
    for tr_idx, val_idx in kf.split(X_train_r):
        Xtr, Xval = X_train_r.iloc[tr_idx], X_train_r.iloc[val_idx]
        Ytr, Yval = Y_train[tr_idx], Y_train[val_idx]
        fold_model = clone(profile_pipeline)
        fold_model.fit(Xtr, Ytr)
        Yp = fold_model.predict(Xval)
        cv_subset.append(accuracy_score(Yval, Yp))
        cv_hamming.append(hamming_loss(Yval, Yp))
        cv_f1.append(f1_score(Yval, Yp, average="macro", zero_division=0))
    cv_subset_mean = float(np.mean(cv_subset))
    cv_hamming_mean = float(np.mean(cv_hamming))
    cv_f1_mean = float(np.mean(cv_f1))
    print(f"CV subset accuracy: {cv_subset_mean:.3f} | "
          f"CV hamming loss: {cv_hamming_mean:.3f} | CV macro-F1: {cv_f1_mean:.3f}")

    # ─── Severity level classifier ────────────────────────────────────────
    print("\nTraining severity LEVEL classifier...")
    level_pipeline = Pipeline([
        ("preprocess", build_preprocessor()),
        ("clf", GradientBoostingClassifier(n_estimators=150, max_depth=4, random_state=42)),
    ])
    level_pipeline.fit(X_train, yl_train)
    yl_pred = level_pipeline.predict(X_test)
    level_accuracy = accuracy_score(yl_test, yl_pred)
    print(f"Level Accuracy: {level_accuracy:.3f}")
    print(classification_report(yl_test, yl_pred, target_names=LEVEL_LABELS, zero_division=0))

    # ─── Save artifacts ────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "..", "ai_model") \
        if "ai_model" not in os.path.basename(os.path.dirname(__file__)) else os.path.dirname(__file__)
    os.makedirs("ai_model", exist_ok=True)

    joblib.dump(profile_pipeline, "ai_model/dyslexia_profile_model.pkl")
    joblib.dump(level_pipeline, "ai_model/dyslexia_level_model.pkl")
    joblib.dump(mlb, "ai_model/dyslexia_label_binarizer.pkl")

    with open("ai_model/model_info.json", "w") as f:
        json.dump({
            "feature_names": FEATURE_NAMES,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "profile_labels": PROFILE_LABELS,
            "level_labels": LEVEL_LABELS,
            "languages": LANGUAGES,
            "mistake_patterns": MISTAKE_PATTERNS,
            "metrics": {
                "subset_accuracy": float(subset_accuracy),
                "hamming_loss": float(h_loss),
                "macro_roc_auc": macro_auc,
                "cv_subset_accuracy_mean": cv_subset_mean,
                "cv_hamming_loss_mean": cv_hamming_mean,
                "cv_f1_macro_mean": cv_f1_mean,
            },
            "level_accuracy": float(level_accuracy),
            "training_samples": int(X_df.shape[0]),
        }, f, indent=2)

    print("\nModels saved:")
    print("  - ai_model/dyslexia_profile_model.pkl")
    print("  - ai_model/dyslexia_level_model.pkl")
    print("  - ai_model/dyslexia_label_binarizer.pkl")
    print("  - ai_model/model_info.json")

    return profile_pipeline, level_pipeline, mlb


# ─── Inference ────────────────────────────────────────────────────────────────

def predict_from_answers(answers: list, student_meta: dict = None, threshold: float = 0.35) -> dict:
    """
    Run multi-label ML prediction on screening answers.
    Returns a probability for EVERY dyslexia profile.
    Falls back to None (caller uses rule-based path) if models aren't trained.
    """
    import joblib

    base_dir = os.path.dirname(__file__)
    profile_path = os.path.join(base_dir, "dyslexia_profile_model.pkl")
    level_path = os.path.join(base_dir, "dyslexia_level_model.pkl")
    mlb_path = os.path.join(base_dir, "dyslexia_label_binarizer.pkl")

    if not (os.path.exists(profile_path) and os.path.exists(level_path)):
        return None

    try:
        profile_pipeline = joblib.load(profile_path)
        level_pipeline = joblib.load(level_path)
        labels = PROFILE_LABELS
        if os.path.exists(mlb_path):
            mlb = joblib.load(mlb_path)
            labels = list(mlb.classes_)

        X_row = screening_answers_to_features(answers, student_meta)

        proba = profile_pipeline.predict_proba(X_row)[0]
        profile_probabilities = {
            labels[i]: round(float(p) * 100, 1) for i, p in enumerate(proba)
        }
        active_profiles = [lbl for lbl, p in zip(labels, proba) if p >= threshold]
        top_idx = int(np.argmax(proba))
        primary_profile = labels[top_idx]
        if not active_profiles:
            active_profiles = [primary_profile]

        level_pred = level_pipeline.predict(X_row)[0]
        level_proba = level_pipeline.predict_proba(X_row)[0]

        return {
            "profile_probabilities": profile_probabilities,
            "active_profiles": active_profiles,
            "primary_profile": primary_profile,
            # Backward-compatible single-label keys
            "ml_type": primary_profile,
            "ml_type_confidence": round(float(max(proba)) * 100, 1),
            "ml_type_probabilities": profile_probabilities,
            "ml_level": LEVEL_LABELS[level_pred],
            "ml_level_confidence": round(float(max(level_proba)) * 100, 1),
            "source": "ml_model",
        }
    except Exception as e:
        print(f"[ml] prediction error: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("DyslexAid AI Model Trainer — Multi-Label Profile Classifier")
    print("=" * 60)
    train_model()
    print("\nDone! Run the backend and the model will be loaded automatically.")