import logging
import cv2
import easyocr
import numpy as np

# Global reader cache to avoid re-initializing models recursively
_READER_CACHE = {}


def preprocess_receipt(image_path: str) -> np.ndarray:
    logging.info(f"Preprocessing image....")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Cannot read image")

    # 1. Resize (if receipt is small)
    h, w = img.shape[:2]
    if h < 2000:
        scale = 2000 / h
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Mild denoising (careful not to blur characters)
    gray = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=5,  # Reduced from 10 to keep edges sharer
        templateWindowSize=7,
        searchWindowSize=21,
    )

    # 4. Shadow removal — division normalization
    kernel = np.ones((21, 21), np.uint8)
    dilated = cv2.dilate(gray, kernel)
    bg = cv2.medianBlur(dilated, 51)
    norm = cv2.divide(gray, bg, scale=255)

    # 5. CLAHE (moderate)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    norm = clahe.apply(norm)

    # Unused (kept as-is, just not returned)
    result = cv2.adaptiveThreshold(
        norm,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,  # Smaller window helps capture small fonts
        25,  # Higher constant helps suppress gray noise
    )

    return norm



def run_ocr(image, lang=("en",), gpu=False):
    lang_tuple = tuple(sorted(lang))
    if lang_tuple not in _READER_CACHE:
        logging.info("Initializing EasyOCR reader for %s (gpu=%s)", lang_tuple, gpu)
        _READER_CACHE[lang_tuple] = easyocr.Reader(list(lang_tuple), gpu=gpu)

    reader = _READER_CACHE[lang_tuple]
    results = reader.readtext(
        image,
        contrast_ths=0.2, # Lower threshold to capture lighter text
        adjust_contrast=0.5,
        low_text=0.3,
        canvas_size=2560 # Larger canvas for long receipts
    )

    data = []
    for bbox, text, conf in results:
        text = (text or "").strip()
        if text:
            data.append({"text": text, "confidence": round(float(conf), 3)})


    return data
