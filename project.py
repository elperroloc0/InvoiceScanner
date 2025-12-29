import argparse
import csv
import json
import logging
import os

import cv2
import easyocr
import numpy as np
import regex as re

STORAGE_FOLDER = "samples"

SAVE_EXTENSIONS = {".jsonl", ".json", ".csv"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

# price tags (-) 12.34/12,34
PRICE_RX = re.compile(r"-?\d+[.,]\d{2}\b")
STOP_WORDS = ("total", "subtotal", "grand total", "payment", "tax")

# ---------- helpers ----------
NON_ITEM_WORDS_LOCAL = {
    "FOR","TOTAL","SUBTOTAL","TAX","SALES","ORDER","GRAND","CREDIT",
    "PAYMENT","CHANGE","BALANCE","SAVED","SAVE","YOU","RECEIPT",
}

STOP_HINTS = (
    "grand total","order total","sub total","subtotal","amount due","balance due",
    "total","payment","change","credit","debit",
)

STORE_HINTS = {
    "Publix": ("publix",),
}

WEIGHT_RX = re.compile(
    r"(?P<qty>\d+[.,]\d+)\s*(?:lb|lbs|ib|1b)\s*(?:@|at|a)?\s*" #1.23 lb @
    r"(?P<unit>\d+[.,]\d+)\s*(?:/?\s*(?:lb|lbs|ib|1b))?\s*" #3.99/lb
    r"(?P<total>\-?\d+[.,]\d{2})\b",  #4.91
    re.I,
)
WEIGHT_FALLBACK_RX = re.compile(
    r"(?P<qty>\d+[.,]\d+)\s*(?:@|at|a)?\s*(?P<unit>\d+[.,]\d+)\s*/\s*(?:lb|lbs|ib|1b).*?(?P<total>\-?\d+[.,]\d{2})\b",
    re.I, #	1.23 @ 3.99 / lb .... 4.91
)

DEAL_RX = re.compile(r"\b(?P<buy>\d+)\s*FOR\b", re.I) # 2 FOR 5.00
QTY_AT_RX = re.compile(r"\b(?P<qty>\d+)\s*@\s*(?P<unit>\d+[.,]\d{2})\b", re.I) 	# 3 @ 1.29


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


# clean up ", -> ." and spaces
def norm(s: str) -> str:
    s = (s or "").strip().replace(",", ".")
    s = re.sub(r"\s+", " ", s) # replace multiple spaces with one
    return s

# normalize numeric data
def price_from(s: str):
    s = (s or "").strip()

    # Basic normalization
    s = s.replace(",", ".")
    s = re.sub(r"\s+", " ", s)

    # OCR fixes: g/q -> 9, O/o -> 0 (only in numeric context)
    # Order matters!!
    s = re.sub(r"(?<=\d\.)[oO]", "0", s)                   # 12.Og -> 12.0g
    s = re.sub(r"(?<=[\d\.])[gq]", "9", s, flags=re.I)     # 12.0g -> 12.09
    s = re.sub(r"(?<=\d)[sS](?=\b|\d)", "5", s)            # 12.0S -> 12.05

    # Merge "16 . 76" -> "16.76"
    s = re.sub(r"(\d)\s*\.\s*(\d{2})\b", r"\1.\2", s)

    m = re.search(r"-?\d+\.\d{2}\b", s)
    return float(m.group()) if m else None


# find all valid prices and return them in float
def prices_in(s: str) -> list[float]:
    s = norm(s)
    s = re.sub(r"(\d)\s*\.\s*(\d{2})\b", r"\1.\2", s)
    out = []
    for m in re.finditer(r"-?\d+\.\d{2}\b", s):
        out.append(float(m.group()))
    return out


# helpers for unnecessary parts of the check
def is_you_saved(s: str) -> bool:
    s = norm(s).lower()
    return "you saved" in s or bool(re.search(r"\byou\s*sav", s))


def is_promotion(s: str) -> bool:
    return "promotion" in norm(s).lower()


def is_voided(s: str) -> bool:
    return "voided item" in norm(s).lower() or "void item" in norm(s).lower()


def is_stop_line(s: str) -> bool:
    low = norm(s).lower()
    return any(h in low for h in STOP_HINTS)


# Item names are mostly CAPS, but OCR may leak lowercase.
def looks_like_item_name(s: str) -> bool:
    s = (s or "").strip()
    if not s or len(s) <= 2:
        return False
    if s[0].isdigit():
        return False
    if s.upper() in NON_ITEM_WORDS_LOCAL:
        return False
    if re.fullmatch(r"\d+", s):
        return False
    if price_from(s) is not None:
        return False

    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False

    upper = sum(1 for c in letters if c.isupper())
    ratio = upper / len(letters)

    # Allow "APpLe" still passes
    return ratio >= 0.60


def merge_split_prices(lines: list[str]) -> list[str]:
    out = []
    i = 0
    while i < len(lines):
        a = norm(lines[i])

        # If "3" and next "49" -> "3.49"
        if a.isdigit() and 1 <= len(a) <= 3 and i + 1 < len(lines):
            b = norm(lines[i + 1])
            if b.isdigit() and len(b) == 2:
                # Avoid cases like 9951 + 30 etc. (addresses/phones)
                if len(a) <= 2:  # most often prices: 2..9 dollars
                    out.append(f"{int(a)}.{b}")
                    i += 2
                    continue

        out.append(a)
        i += 1
    return out

    # ---------- clean lines ----------
def is_noise_token(s: str) -> bool:
    low = (s or "").strip().lower()
    return (low in {"t", "f", "t f", "tf", "{f", "iix"}) or (re.fullmatch(r"\d\)", low) is not None)







def parse_receipt(raw_ocr: list[dict], min_conf: float = 0.30) -> dict:
    lines: list[str] = []
    for x in raw_ocr:
        text = norm(x.get("text") or "")
        if not text:
            continue

        # Delete trash tokens
        if is_noise_token(text):
            continue
        # Ignore "You Saved ..." noise lines outright
        if is_you_saved(text):
            continue

        conf = float(x.get("confidence") or 0)

        # Keep prices always, names by threshold/shape
        if price_from(text) is not None or conf >= min_conf or (conf >= 0.12 and looks_like_item_name(text)):
            lines.append(text)

    lines = merge_split_prices(lines)
    print(f"HUIIIIIIIIIIII{lines}")


    # ---------- detect store ----------
    # i implemented it this way bcs i would like to expant
    # this propram to work with other receipt type
    # in the future
    joined = " ".join(lines).lower()
    store = "Unknown"
    for name, hints in STORE_HINTS.items():
        if any(h in joined for h in hints):
            store = name
            break

    # ---------- extract items ----------
    items: list[dict] = []
    name_parts: list[str] = []

    def current_name() -> str | None:
        nm = " ".join(name_parts).strip()
        return nm if nm else None

    def reset_name():
        name_parts.clear()

    # pointer for
    i = 0
    while i < len(lines):
        line = lines[i]

        # Pattern 6: Voided item -> next line is name, then -(price) (same or next line)
        if is_voided(line):
            i += 1

            # Collect voided item name (1..3 lines)
            void_name_parts = []
            while i < len(lines) and len(void_name_parts) < 3:
                s = lines[i].strip()

                # Stop/totals
                if is_stop_line(s):
                    break

                # Price -> name ended
                if price_from(s) is not None:
                    break

                # Skip trash tokens
                if is_noise_token(s) or is_you_saved(s) or is_promotion(s):
                    i += 1
                    continue

                # Take only what looks like an item
                if looks_like_item_name(s):
                    void_name_parts.append(s)

                i += 1

            # Price for voided (this line or next)
            void_price = None
            if i < len(lines):
                void_price = price_from(lines[i])
                if void_price is None and i + 1 < len(lines):
                    void_price = price_from(lines[i + 1])
                    if void_price is not None:
                        i += 1

            if void_price is not None:
                # Voided item should be negative
                if void_price > 0:
                    void_price = -void_price

                nm = " ".join(void_name_parts).strip() or "VOIDED ITEM"
                items.append({"name": nm, "price": void_price, "voided": True})

            reset_name()
            i += 1
            continue

        # Stop near totals (but allow to continue if it's a stray "TOTAL" without a price)
        if is_stop_line(line):
            # If next line has a price, assume we're in totals section
            if i + 1 < len(lines) and price_from(lines[i + 1]) is not None:
                break

        # Collect item name parts
        if price_from(line) is None and looks_like_item_name(line) and not name_parts:
            name_parts.append(line)
            i += 1
            continue
        if price_from(line) is None and looks_like_item_name(line) and name_parts:
            # Sometimes name spans multiple lines
            name_parts.append(line)
            i += 1
            continue

        # connects name parts in 'name_parts' if there are any
        nm = current_name()

        # Base pattern: Name + (price) on some line (could be current line)
        # If current line is just a price and we have a name -> close item
        if nm and price_from(line) is not None and len(prices_in(line)) == 1 and re.fullmatch(r"-?\d+\.\d{2}", norm(line)):
            base_price = price_from(line)
            items.append({"name": nm, "price": base_price})
            reset_name()
            i += 1
            continue

        # If line contains price and we have a name and line isn't a deal/qty/weight -> treat as base item price
        if nm and price_from(line) is not None:
            # Pattern 1: deal "1 @ 2 FOR (unit) (final)"
            mdeal = DEAL_RX.search(line)
            if mdeal:
                deal_qty = int(mdeal.group("buy"))
                ps = prices_in(line)
                unit = None
                final = None
                # Typical: "... 2 FOR 1.99 3.98" -> unit=1.99, final=3.98
                if len(ps) >= 2:
                    unit = ps[-2]
                    final = ps[-1]
                elif len(ps) == 1:
                    final = ps[0]
                if final is not None:
                    items.append({"name": nm, "price": final, "deal": {"qty": deal_qty, "unit_price": unit}})
                    reset_name()
                    i += 1
                    continue

            # Pattern 2: quantity "3 @ (unit) (final)"
            mqty = QTY_AT_RX.search(line)
            if mqty:
                qty = int(mqty.group("qty"))
                unit = float(mqty.group("unit").replace(",", "."))
                ps = prices_in(line)
                final = ps[-1] if ps else None
                if final is not None:
                    items.append({"name": nm, "price": final, "qty": qty, "unit_price": unit})
                    reset_name()
                    i += 1
                    continue

            # Pattern 3: by weight
            w = None
            mw = WEIGHT_RX.search(line) or WEIGHT_FALLBACK_RX.search(line)
            if mw:
                qty = float(mw.group("qty").replace(",", "."))
                unit = float(mw.group("unit").replace(",", "."))
                total = float(mw.group("total").replace(",", "."))
                w = {"qty": qty, "unit_price": unit, "price": total, "unit": "lb"}

            if w is not None:
                items.append({"name": nm, **w})
                reset_name()
                i += 1
                continue

            # Otherwise treat as normal: Name + price on same line
            base_price = price_from(line)
            items.append({"name": nm, "price": base_price})
            reset_name()
            i += 1
            continue

        # Pattern 4: after base item, Promotion line then negative discount next
        # (Handled by scanning when we see "Promotion" while no name_parts)
        if is_promotion(line):
            # Discount amount might be on same or next line
            disc = price_from(line)
            if disc is None and i + 1 < len(lines):
                disc = price_from(lines[i + 1])
                if disc is not None:
                    i += 1
            if disc is not None and disc > 0:
                disc = -disc
            if disc is not None:
                items.append({"name": "PROMOTION", "price": disc})
            i += 1
            reset_name()
            continue

        # Pattern 5: "You saved" lines are removed in cleaning step
        i += 1

    # ---------- extract total ----------
    total = None
    for idx, line in enumerate(lines):
        low = norm(line).lower()

        if any(k in low for k in ("grand total", "amount due", "balance due", "order total", "total")):
            # Same line first
            total = price_from(line)
            if total is None and idx + 1 < len(lines):
                total = price_from(lines[idx + 1])
            if total is not None:
                break

    if total is None:
        # Fallback: max positive price in tail of receipt
        all_prices = []
        for l in lines:
            p = price_from(l)
            if p is not None:
                all_prices.append(p)
        positives = [p for p in all_prices if p >= 0]
        total = max(positives) if positives else (max(all_prices) if all_prices else None)

    return {"store": store, "items": items, "total": total}



def preprocess_receipt(image_path: str) -> np.ndarray:
    logging.info(f"Preprocessing image: {image_path}")

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

    # 3. Mild denoising (highly recommended)
    gray = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=10,  # 6–10
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
    logging.debug("Initializing EasyOCR reader (gpu=%s, lang=%s)", gpu, lang)

    reader = easyocr.Reader(list(lang), gpu=gpu)
    results = reader.readtext(
        image,
        contrast_ths=0.5,
        adjust_contrast=0.4,
        low_text=0.4,
    )

    data = []
    for bbox, text, conf in results:
        text = (text or "").strip()
        if text:
            data.append({"text": text, "confidence": round(float(conf), 3)})

    return data


def dict_to_table(data):
    print(f"Store: {data['store']}")
    print("-" * 46)

    print(f"{'Item Name':<35} | {'Price':>8}")
    print("-" * 46)

    for item in data["items"]:
        name = item.get("name", "")
        price = item.get("price", None)

        if price is None:
            print(f"{name:<35} | {'':>8}")
        else:
            print(f"{name:<35} | {price:>8.2f}")

    print("-" * 46)

    total = data.get("total")
    if total is None:
        print(f"{'Total':<35} | {'':>8}")
    else:
        print(f"{'Total':<35} | {total:>8.2f}")




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


def save_to_file(data: dict, path: str):
    """Save receipt data to JSON, JSONL, or CSV."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    elif ext == ".jsonl":
        with open(path, "a") as f:
            f.write(json.dumps(data) + "\n")
    elif ext == ".csv":
        file_exists = os.path.isfile(path)
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["store", "item_name", "price", "total"])
            if not file_exists:
                writer.writeheader()

            # If no items, write at least the total
            if not data["items"]:
                 writer.writerow({"store": data["store"], "item_name": "N/A", "price": 0.0, "total": data["total"]})
            else:
                for item in data["items"]:
                    writer.writerow({
                        "store": data["store"],
                        "item_name": item.get("name"),
                        "price": item.get("price"),
                        "total": data["total"]
                    })
    logging.info(f"Result saved to {path}")




if __name__ == "__main__":
    main()
