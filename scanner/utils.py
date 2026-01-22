# clean up ", -> ." and spaces
import regex as re
from scanner.config import NON_ITEM_WORDS


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

def is_noise_token(s: str) -> bool:
    low = (s or "").strip().lower()
    return (low in {"t", "f", "t f", "tf", "{f", "iix"}) or (re.fullmatch(r"\d\)", low) is not None)

# Item names are mostly CAPS, but OCR may leak lowercase.
def looks_like_item_name(s: str) -> bool:
    s = (s or "").strip()
    if not s or len(s) <= 2:
        return False
    if s[0].isdigit():
        return False
    if s.upper() in NON_ITEM_WORDS:
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
