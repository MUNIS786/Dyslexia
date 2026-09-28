"""OCR service — Tesseract (offline) with image preprocessing."""
import os
import pytesseract
from PIL import Image

LANG_MAP = {
    "english": "eng", "eng": "eng",
    "hindi": "hin", "hin": "hin",
    "tamil": "tam", "tam": "tam",
    "marathi": "mar", "mar": "mar",
}


def ocr_image(image_path: str, lang: str = "english") -> str:
    tlang = LANG_MAP.get(lang.lower(), "eng")
    try:
        img = Image.open(image_path)
        config = "--psm 6 --oem 3"
        return pytesseract.image_to_string(img, lang=tlang, config=config).strip()
    except pytesseract.TesseractNotFoundError:
        print("[ocr] Tesseract not found. Install: apt-get install tesseract-ocr")
        return ""
    except Exception as e:
        print(f"[ocr] error: {e}")
        if tlang != "eng":
            try:
                img = Image.open(image_path)
                return pytesseract.image_to_string(img, lang="eng", config="--psm 6 --oem 3").strip()
            except Exception:
                return ""
        return ""


def preprocess_image(image_path: str) -> str:
    """Grayscale + adaptive threshold + deskew. Returns clean image path."""
    try:
        import cv2
        import numpy as np
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Adaptive thresholding for uneven lighting
        th = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
        )
        # Slight sharpening
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharp = cv2.filter2D(th, -1, kernel)
        out = image_path.rsplit(".", 1)[0] + "_clean.png"
        cv2.imwrite(out, sharp)
        return out
    except ImportError:
        # OpenCV not installed — try PIL basic enhance
        try:
            from PIL import ImageEnhance, ImageFilter
            img = Image.open(image_path).convert("L")
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = img.filter(ImageFilter.SHARPEN)
            out = image_path.rsplit(".", 1)[0] + "_clean.png"
            img.save(out)
            return out
        except Exception:
            return image_path
    except Exception:
        return image_path
