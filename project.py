import argparse
import logging
import os

import cv2
import numpy as np

STORAGE_FOLDER = "samples"

SAVE_EXTENSIONS = {".jsonl", ".json", ".csv"}
ALLOWED_IMAGE_EXTENSIONS = {".npg", ".jpg", ".jpeg"}


def get_args():
    """Parse and validate command lines arguments."""
    parser = argparse. ArgumentParser(description="Extract data from receipt images.")
    parser.add_argument("image", help="Path to the receipt image file")
    parser.add_argument("-o", "--output", type=str, default="invoices.jsonl", help="Output file path(default: invouces.jsonl)",)
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed logs")

    args = parser.parse_args()

    """ --- Validate  --- """
    # input image
    image_path = os.path.abspath(args.image)
    if not os.path.isfile(args.image):
        parser.error(f"Image file not found: {args.image}")

    # input extension
    img_ext = os.path.splitext(args.image)[1].lower()
    if img_ext not in ALLOWED_IMAGE_EXTENSIONS:
        parser.error(f"Image extension not supported. Use: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}")

    # output extension
    out_ext = os.path.splitext(args.output)[1].lower()
    if out_ext not in SAVE_EXTENSIONS:
        parser.error(f"Unsupported output format. Use: {', '.join(sorted(SAVE_EXTENSIONS))}")

    # output default check if exist
    os.makedirs(STORAGE_FOLDER, exist_ok=True)

    args.image = image_path
    args.output = os.path.abspath(args.output)

    return args




