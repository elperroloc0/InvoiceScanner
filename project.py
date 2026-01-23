import argparse
import logging
import os
import cv2

from scanner.config import ALLOWED_IMAGE_EXTENSIONS, SAVE_EXTENSIONS, STORAGE_FOLDER
from scanner.ocr import preprocess_receipt
from scanner.manager import ScannerManager
from scanner.storage import dict_to_table, save_to_file

def get_args():
    """Parse and validate command lines arguments."""
    parser = argparse.ArgumentParser(description="Extract data from receipt images.")
    parser.add_argument("image", help="Path to the receipt image file", nargs="?")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="invoices.jsonl",
        help="Output file path(default: invoices.jsonl)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed logs")

    args = parser.parse_args()

    # If no image path provided, we'll launch GUI in main()
    if not args.image:
        return args

    # --- Validate ---
    image_path = os.path.abspath(args.image)
    if not os.path.isfile(args.image):
        parser.error(f"Image file not found: {args.image}")

    img_ext = os.path.splitext(args.image)[1].lower()
    if img_ext not in ALLOWED_IMAGE_EXTENSIONS:
        parser.error(
            f"Image extension not supported. Use: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    out_ext = os.path.splitext(args.output)[1].lower()
    if out_ext not in SAVE_EXTENSIONS:
        parser.error(f"Unsupported output format. Use: {', '.join(sorted(SAVE_EXTENSIONS))}")

    os.makedirs(STORAGE_FOLDER, exist_ok=True)

    args.image = image_path
    args.output = os.path.abspath(args.output)

    return args


def main():
    args = get_args()

    # Launch GUI if no image path provided
    if not args.image:
        try:
            from gui import App
            app = App()
            app.mainloop()
        except ImportError:
            print("To use the GUI, install customtkinter: pip install customtkinter")
        return

    # CLI Mode
    verbose = args.verbose
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Silence libraries
    logging.getLogger("easyocr").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    logging.info("++++++++++ PROCESSING IMAGE +++++++++++")
    try:
        # 1. Preprocess
        preprocessed_img = preprocess_receipt(args.image)

        # 2. Smart Routing (Template or Vision)
        result = ScannerManager.process(preprocessed_img)

        # 3. Display Results
        dict_to_table(result)

        # 4. Save Options
        choice = input("\nSave extracted data to file? (Y/n): ").strip().lower()
        if choice not in ['n', 'no']:
            save_to_file(result, args.output)
            logging.info("Data saved to %s", args.output)
        else:
            logging.info("Save cancelled by user.")

    except Exception as e:
        logging.error(f"Failed to process image: {e}")

if __name__ == "__main__":
    main()
