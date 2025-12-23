"""
Invoice Extractor — CS50P Final Project
A tool to convert receipt images into structured JSON data.

Simplified structure for CS50P:
1. CLI: Use argparse for image input and output file.
2. OCR: Use pytesseract to get raw text.
3. Parsing: Use Regex templates to extract store, date, and items.
4. Validation: Custom classes to ensure data integrity.
5. Output: Save results to a .jsonl or .json file.
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import date as dt_date

# from PIL import Image
# import pytesseract

# ==========================================
# 1) CONFIGURATION & UTILS
# ==========================================

TEMPLATES = {
    "STARBUCKS": {
        "keywords": ["STARBUCKS", "COFFEE"],
        "date_pattern": r"(\d{4}-\d{2}-\d{2})",
        "item_pattern": r"(?P<product>.+)\s{2,}(?P<price>\d+\.\d{2})"
    }
    # TODO: Add one more store template for a better demo
}

def clean_money_string(value):
    """
    Cleans a string like '$1,200.50' and returns a float.
    This is a perfect function to test with pytest.
    """
    # TODO: Implement cleaning logic (remove currency, handle decimal separator)
    return 0.0

def parse_date_string(date_str):
    """
    Converts various receipt date formats to a datetime.date object.
    Supports: YYYY-MM-DD, DD/MM/YYYY, etc.
    """
    # TODO: Implement robust date parsing
    return dt_date.today()


# ==========================================
# 2) DATA CLASSES (Logic & Validation)
# ==========================================

class Item:
    """Represents a single line item from a receipt."""
    def __init__(self, name, price, quantity=1):
        self.name = name.strip()
        self.price = clean_money_string(price)
        self.quantity = int(quantity)

    def to_dict(self):
        return {
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "total": round(self.price * self.quantity, 2)
        }


class Invoice:
    """Container for the whole receipt data."""
    def __init__(self, store_name, date, items_data):
        self.store_name = store_name.strip().title()
        self.date = parse_date_string(date)
        # items_data should be a list of dicts or Item objects
        self.items = [Item(**item) if isinstance(item, dict) else item for item in items_data]

    def get_total(self):
        return sum(item.price * item.quantity for item in self.items)

    def to_dict(self):
        return {
            "store": self.store_name,
            "date": self.date.isoformat(),
            "items": [item.to_dict() for item in self.items],
            "grand_total": round(self.get_total(), 2)
        }

    def to_flat_list(self):
        """Helper to convert the invoice into a list of rows for CSV/Excel export."""
        rows = []
        for item in self.items:
            # We use normalized names: store_name, date, item.name, item.quantity, item.price
            rows.append([self.store_name, self.date.isoformat(), item.name, item.quantity, item.price])
        return rows


# ==========================================
# 3) CORE FUNCTIONS (To be tested)
# ==========================================

def perform_ocr(image_path):
    """
    Loads image and returns raw string content.
    For local development, ensure tesseract is installed.
    """
    logging.info(f"Extracting text from: {image_path}...")
    # TODO: Implement pytesseract.image_to_string
    return "MOCK OCR TEXT"

def detect_store(text):
    """
    Checks keywords from TEMPLATES against raw text.
    Returns the template key (e.g., 'STARBUCKS') or None.
    """
    logging.info("Analyzing text to identify store...")
    # TODO: Implement keyword search
    return None

def extract_receipt_data(text, template_key):
    """
    Uses regex from the chosen template to find date and line items.
    Returns a dictionary suitable for Invoice constructor.
    """
    logging.info(f"Using template for {template_key}. Extracting fields...")
    # TODO: 1. Find date using date_pattern
    # TODO: 2. Find items using item_pattern (re.finditer)
    return {"store_name": template_key, "date": "2023-01-01", "items_data": []}


# ==========================================
# 4) MAIN & CLI
# ==========================================

def get_args():
    """Defines command line arguments."""
    parser = argparse.ArgumentParser(description="Extract data from receipt images.")
    parser.add_argument("image", help="Path to the receipt image file")
    parser.add_argument("--output", default="invoices.jsonl", help="Output file path (default: invoices.jsonl)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress logs")
    return parser.parse_args()

def main():
    args = get_args()

    # Configure logging based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    logging.info("Starting processing...")

    # 1. Image -> Text
    raw_text = perform_ocr(args.image)
    logging.debug(f"Raw OCR text: {raw_text}")

    # 2. Text -> Template
    store_key = detect_store(raw_text)
    if not store_key:
        logging.error("Could not identify store template. Try a different image.")
        sys.exit(1)

    # 3. Template -> Structured Data
    try:
        data = extract_receipt_data(raw_text, store_key)
        invoice = Invoice(**data)

        # 4. Save to File
        logging.info(f"Writing data to {args.output}...")
        with open(args.output, "a", encoding="utf-8") as f:
            f.write(json.dumps(invoice.to_dict(), ensure_ascii=False) + "\n")

        logging.info("Done! Process complete.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

