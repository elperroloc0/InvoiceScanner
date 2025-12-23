import argparse
import logging
import os
import re
import sys

STORAGE_FOLDER = "scanned"

ALLOWED_FILE_EXTENTIONS = {
    "..."
}

SAVE_EXTENTIONS = {
    ".jsonl",
    ".csv",
}

def get_args():
    """Defines command line arguments."""
    parser = argparse.ArgumentParser(description="Extract data from receipt images.")
    # first argument
    parser.add_argument("image", help="Path to the receipt image file")
    # optional for csv
    parser.add_argument("-o", "--output", type=str, default="invoices.jsonl", help="Output file path (default: invoices.jsonl) ")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress logs")

    args = parser.parse_args()

    if args.verbose:
        print(f"[LOG] Proccessing image: {args.image}")

    # normalizr extension
    ext = os.path.splitext(args.output)[1].lower()

    # check for accepted extentions
    if not ext in SAVE_EXTENTIONS:
        print(f"extension not supported, use: {', '.join(SAVE_EXTENTIONS)}")
        sys.exit(1)

    # Prepend the directory if needed
    final_path = os.path.join(STORAGE_FOLDER, args.output)
    print(f"Your scan will be stored in: {final_path}")

    # return validated args
    return args

def main():
    args = get_args()

    # log setting
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s"
    )

    # validate image

    # if image is correct
        # send to parser



if __name__ == "__main__":
    main()
