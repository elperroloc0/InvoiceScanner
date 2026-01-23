import regex as re

STORAGE_FOLDER = "samples"

SAVE_EXTENSIONS = {".jsonl", ".json", ".csv"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

# price tags (-) 12.34/12,34
PRICE_RX = re.compile(r"-?\d+[.,]\d{2}\b")
STOP_WORDS = ("total", "subtotal", "grand total", "payment", "tax")

# ---------- helpers ----------
NON_ITEM_WORDS = {
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
