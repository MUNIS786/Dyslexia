"""
Scan — OCR for images/PDFs. Both students (personal library) and teachers (create assignments).
"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path

from services.ocr_service import ocr_image, preprocess_image

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(tags=["scan"])
ALLOWED = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".pdf"}


@router.post("/scan")
async def scan(
    file: UploadFile = File(...),
    language: str = Form("english"),
):
    if not file.filename:
        raise HTTPException(400, "Empty filename")
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type. Use: {', '.join(ALLOWED)}")

    is_pdf = ext == ".pdf"
    path = str(UPLOAD_DIR / f"scan_{uuid.uuid4().hex}{ext}")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 20MB.")
    with open(path, "wb") as f:
        f.write(content)

    text, method = "", "tesseract"
    try:
        if is_pdf:
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
                method = "pdf-text"
            except ImportError:
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(path)
                    text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
                    method = "pdf-text"
                except Exception:
                    text = ""
            except Exception:
                text = ""

            if not text:
                try:
                    from pdf2image import convert_from_path
                    pages = convert_from_path(path, dpi=200, first_page=1, last_page=5)
                    parts = []
                    for i, pg in enumerate(pages):
                        ip = path.replace(".pdf", f"_p{i}.png")
                        pg.save(ip, "PNG")
                        clean = preprocess_image(ip)
                        parts.append(ocr_image(clean, lang=language))
                        for p in [ip, clean]:
                            if p != ip:
                                try: os.remove(p)
                                except: pass
                        try: os.remove(ip)
                        except: pass
                    text = "\n".join(p for p in parts if p).strip()
                    method = "pdf-ocr"
                except Exception as e:
                    print(f"[scan] pdf-raster: {e}")

            if not text:
                raise HTTPException(400, "Could not extract text from PDF.")
        else:
            clean = preprocess_image(path)
            text = ocr_image(clean, lang=language)
            if clean != path:
                try: os.remove(clean)
                except: pass

        if not text:
            raise HTTPException(400, "Could not extract text. Try a clearer image.")

        return {"text": text, "language": language, "method": method, "wordCount": len(text.split())}
    finally:
        try: os.remove(path)
        except: pass
