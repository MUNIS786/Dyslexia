# DyslexAid Machine Learning Engine

This module contains the machine learning pipelines used by DyslexAid for automated offline dyslexia classification and severity estimation.

## Clinical Assessment Dimensions
The model extracts 20 normalized features based on standardized Dyslexia Screening Test (DST) domains:
1. **Phonological Awareness**: Sound-symbol mapping, phoneme deletion, and rhyme detection.
2. **Phonological Memory**: Digit span and non-word repetition.
3. **Rapid Naming (RAN)**: Rapid automatized naming of colors, numbers, and objects.
4. **Letter Reversal**: Mirroring tendencies (e.g. b/d, p/q).
5. **Reading Fluency**: Reading speed and hesitation rates.
6. **Orthographic / Spelling**: Irregular word recognition and phonetic spelling approximations.
7. **Comprehension**: Question answering and inference capabilities.
8. **Motor / Writing**: Speed and motor-coordination proxies.

## Model Architecture
- **Type Classifier** (`dyslexia_type_model.pkl`):
  - Predicts subtype: *No significant indicators*, *Phonological Dyslexia*, *RAN Deficit*, *Surface Dyslexia*, or *Double Deficit*.
  - Uses a Scikit-Learn pipeline with feature scaling, interaction terms, and calibrated ensemble classification.
- **Severity Classifier** (`dyslexia_level_model.pkl`):
  - Predicts severity: *low*, *moderate*, or *high*.
- **Offline Reliability**:
  - The models are pre-trained and serialized via `joblib`, allowing instant, zero-latency inference on low-power devices without an active internet connection or external cloud API dependency.

## Training & Retraining
To retrain the models:
```bash
python train_model.py
```
The resulting model artifacts will be saved as `.pkl` files and synced with the backend inference engine.
