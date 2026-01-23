import logging
import cv2
import numpy as np
from typing import Optional

from .ocr import run_ocr
from .openai_service import extract_data_with_openai_vision
from .templates.publix import PublixTemplate

# List of registered templates
AVAILABLE_TEMPLATES = [
    PublixTemplate(),
]

class ScannerManager:
    @staticmethod
    def process(image: np.ndarray) -> dict:
        """
        Orchestrates the scanning process:
        1. Try fast local template matching.
        2. Fallback to OpenAI Vision.
        """
        h, w = image.shape[:2]

        # 1. Header OCR Pass (First 25% of image)
        logging.info("Attempting local template matching (Header Pass)...")
        header_crop = image[0:int(h*0.25), 0:w]
        header_ocr = run_ocr(header_crop)

        matched_template = None
        for temp in AVAILABLE_TEMPLATES:
            if temp.matches(header_ocr):
                matched_template = temp
                break

        if matched_template:
            logging.info(f"Template matched: {matched_template.store_name}. Running local parser.")
            # Run full OCR for local parsing
            full_ocr = run_ocr(image)
            return matched_template.parse(full_ocr)

        # 2. Vision AI Fallback
        logging.info("--> No template matches. Routing to Vision AI for full extraction.")
        result = extract_data_with_openai_vision(image)
        logging.info(f"--> AI Extraction complete. Store detected: {result.get('store')}")
        return result
