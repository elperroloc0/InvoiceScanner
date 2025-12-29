# test_project.py
import pytest
from project import norm, parse_receipt, price_from


def test_promotion():
    raw = [
        {"text": "BREAD", "confidence": 0.99},
        {"text": "2.00", "confidence": 0.99},
        {"text": "Promotion", "confidence": 0.99},
        {"text": "0.50", "confidence": 0.99},
    ]
    out = parse_receipt(raw)
    assert any(item["name"] == "PROMOTION" and item["price"] == -0.50 for item in out["items"])


def test_norm():
    assert norm("  HeLlo   World!  ") == "HeLlo World!"


def test_noise():
    # "F" is treated as noise token by the parser's cleaning step
    out = parse_receipt([{"text": "F", "confidence": 0.99}])
    assert out["items"] == []
    assert out["total"] is None

    # "You Saved ..." lines are ignored outright
    out = parse_receipt(
        [
            {"text": "You Saved", "confidence": 0.99},
            {"text": "MILK", "confidence": 0.99},
            {"text": "3.50", "confidence": 0.99},
        ]
    )
    assert len(out["items"]) == 1
    assert out["items"][0]["name"] == "MILK"
    assert out["items"][0]["price"] == 3.50


def test_price_from_publix_spacing_and_comma():
    assert price_from("3,39") == 3.39
    assert price_from("3, 39") == 3.39
    assert price_from("46 , 17") == 46.17
    assert price_from("0,99 T") == 0.99
    assert price_from("~0,55") == 0.55


def test_split_price():
    # This verifies the internal merge_split_prices behavior via observable output.
    raw = [
        {"text": "Publix", "confidence": 0.98},
        {"text": "MILK", "confidence": 0.95},
        {"text": "3", "confidence": 0.95},
        {"text": "39", "confidence": 0.95},
    ]
    out = parse_receipt(raw)
    assert len(out["items"]) == 1
    assert out["items"][0]["name"] == "MILK"
    assert out["items"][0]["price"] == 3.39


def test_parse_split_deal():
    # Current parser does NOT build deal when "N FOR" is on its own line without prices.
    raw = [
        {"text": "Publix", "confidence": 0.98},
        {"text": "FRNDSHP SOUR CREAM", "confidence": 0.58},
        {"text": "@", "confidence": 0.91},
        {"text": "4 FOR", "confidence": 0.99},
        {"text": "5,00", "confidence": 0.93},  # total
        {"text": "1,25", "confidence": 0.99},  # unit (won't be attached as deal)
        {"text": "Grand Total", "confidence": 0.52},
        {"text": "5,00", "confidence": 0.76},
    ]
    out = parse_receipt(raw)
    item = out["items"][0]
    assert item["name"] == "FRNDSHP SOUR CREAM"
    assert item["price"] == 5.00
    assert "deal" not in item
    assert out["total"] == 5.00


def test_parse_weight_item():
    raw = [
        {"text": "Publix", "confidence": 0.98},
        {"text": "BANANAS", "confidence": 0.90},
        {"text": "1,25 lb @ 0,79 0,99", "confidence": 0.92},
        {"text": "Grand Total", "confidence": 0.60},
        {"text": "0,99", "confidence": 0.95},
    ]

    out = parse_receipt(raw)
    assert out["store"] == "Publix"

    assert len(out["items"]) == 1
    item = out["items"][0]

    assert item["name"] == "BANANAS"
    assert item["unit"] == "lb"
    assert item["qty"] == 1.25
    assert item["unit_price"] == 0.79
    assert item["price"] == 0.99
    assert out["total"] == 0.99


def test_price_correction():
    # Typical OCR error fixes
    assert price_from("12.Og") == 12.09
    assert price_from("12.0g") == 12.09
    assert price_from("12.0S") == 12.05
    assert price_from("3 O9") == None
    assert price_from("3 . 50") == 3.50
    assert price_from("Total: -5.99") == -5.99


def test_looks_like_item_name():
    from project import looks_like_item_name
    assert looks_like_item_name("MILK") is True
    assert looks_like_item_name("APpLe") is True  # > 60% upper
    assert looks_like_item_name("apple") is False # all lower
    assert looks_like_item_name("123") is False
    assert looks_like_item_name("TOTAL") is False # in NON_ITEM_WORDS_LOCAL
    assert looks_like_item_name("TO") is False    # too short


def test_is_stop_line():
    from project import is_stop_line
    assert is_stop_line("TOTAL") is True
    assert is_stop_line("Grand Total") is True
    assert is_stop_line("Subtotal") is True
    assert is_stop_line("MILK") is False


def test_parse_receipt_standard():
    raw_ocr = [
        {"text": "Publix", "confidence": 0.9},
        {'text': 'Sea Ranch', 'confidence': 0.9},
        {"text": "APPLE JUICE", "confidence": 0.9},
        {"text": "4.50", "confidence": 0.99},
        {"text": "TOTAL", "confidence": 0.9},
        {"text": "4.50", "confidence": 0.99},
    ]
    result = parse_receipt(raw_ocr)

    assert result["store"] == "Publix"
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "APPLE JUICE"
    assert result["items"][0]["price"] == 4.50
    assert result["total"] == 4.50


def test_voided_item():
    raw_ocr = [
        {"text": "VOIDED ITEM", "confidence": 0.9},
        {"text": "BAD MILK", "confidence": 0.9},
        {"text": "3.00", "confidence": 0.9},
    ]
    result = parse_receipt(raw_ocr)
    assert result["items"][0]["price"] == -3.00
    assert result["items"][0]["voided"] is True
