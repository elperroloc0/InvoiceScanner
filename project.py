import argparse
import logging
import os

from scanner.config import ALLOWED_IMAGE_EXTENSIONS, SAVE_EXTENSIONS, STORAGE_FOLDER
from scanner.ocr import preprocess_receipt, run_ocr
from scanner.openai_service import extract_data_with_openai
from scanner.parser import parse_receipt
from scanner.storage import dict_to_table, save_to_file


def get_args():
    """Parse and validate command lines arguments."""
    parser = argparse.ArgumentParser(description="Extract data from receipt images.")
    parser.add_argument("image", help="Path to the receipt image file")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="invoices.jsonl",
        help="Output file path(default: invouces.jsonl)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed logs")

    args = parser.parse_args()

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
    image = args.image
    verbose = args.verbose

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Silence libraries
    logging.getLogger("easyocr").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    logging.info("++++++++++ PROPROCESSING IMAGE +++++++++++")
    try:
        preprocessed_img = preprocess_receipt(image)
    except Exception as e:
        logging.error(f"Failed to preprocess image: {e}")
        return

    logging.info("++++++++++     OCR READING     +++++++++++")
    try:
        raw = run_ocr(preprocessed_img, gpu=True)
    except Exception as e:
        logging.error(f"OCR failed: {e}")
        return

    if not raw:
        logging.error("No text detected.")
        return

    is_publix = str(input("Is this a Publix receipt? (y/N): ")).strip().lower() in ['y', 'yes']

    # ---------------------------
    # NON-PUBLIX -> OpenAI branch
    # ---------------------------

    if  not is_publix:
        logging.info("Applying AI adjustments...")

        try:
            result = extract_data_with_openai(raw)
        except Exception as e:
            logging.error(f"OpenAI data extraction failed: {e}")
            return

        dict_to_table(result)

        save_data = True
        choice = input("Save extracted data to file? (Y/n): ").strip().lower()
        if choice in ['n', 'no']:
            save_data = False

        if save_data:
            save_to_file(result, args.output)
            logging.info("Data saved to %s", args.output)
        else:
            logging.info("Save cancelled by user.")
        return

    # ---------------------------
    # PUBLIX
    # ---------------------------

    logging.info("Applying Publix-specific OCR adjustments...")
    # Calculate average confidence
    avg_conf = sum(x["confidence"] for x in raw) / len(raw)
    logging.debug("Average confidence: %.2f%%", avg_conf * 100)

    receipt = parse_receipt(raw)
    dict_to_table(receipt)

    save_data = True

    if avg_conf < 0.90:
        if 0.85 < avg_conf:
            logging.info("OCR EXTRACTED INFORMATION MAY HAVE ERRORS!")
        else:
            logging.warning("⚠️ OCR EXTRACTED INFORMATION HIGHLY INACCURATE! ⚠️")

        # Single while loop for both conditions
        while True:
            choice = input("Confidence is low. Save to file anyway? (y/N): ").strip().lower()
            if choice in ["y", "yes"]:
                save_data = True
                break
            elif choice in ['n', 'no', '']:
                save_data = False
                break
            print("Please type 'y' or 'n'")

    if save_data:
        save_to_file(receipt, args.output)
        logging.info("Data saved to %s", args.output)
    else:
        logging.info("Save cancelled by user.")


    # For developing:
    # print(raw)
    # import matplotlib.pyplot as plt
    # plt.imshow(preprocessed_img, cmap="gray")
    # plt.title("OCR input")
    # plt.axis("off")
    # plt.show()


if __name__ == "__main__":
    main()
