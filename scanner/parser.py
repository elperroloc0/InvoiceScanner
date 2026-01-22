import regex as re
from scanner.config import (
    DEAL_RX,
    QTY_AT_RX,
    STOP_HINTS,
    STORE_HINTS,
    WEIGHT_FALLBACK_RX,
    WEIGHT_RX,
)

from .utils import is_noise_token, looks_like_item_name, norm, price_from, prices_in


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

