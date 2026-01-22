import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI, api_key

load_dotenv()


def extract_data_with_openai(json_ocr_data: list[dict]) -> dict:

    api_key = os.getenv("OPEN_AI_API")
    prompt = os.getenv("EXTRACT_DATA_PROMPT")

    if not api_key:
        raise ValueError("OPEN_AI_API environment variable not set.")

    if not prompt or not json_ocr_data:
        raise ValueError("Prompt or OCR data is missing.")

    client = OpenAI(api_key=api_key)

    # Дешевле по токенам: компактный JSON
    payload = json.dumps(json_ocr_data, ensure_ascii=False, separators=(",", ":"))


    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": payload},
        ],
        response_format={"type": "json_object"},
    )

    data = json.loads(resp.choices[0].message.content)

    if not isinstance(data, dict):
        raise ValueError("Model response is not a JSON object.")

    # Map store_name to store if necessary
    if "store_name" in data and "store" not in data:
        data["store"] = data.pop("store_name")

    for item in data.get("items", []):
        if "item_name" in item and "name" not in item:
            item["name"] = item.pop("item_name")

    data.setdefault("store", None)
    data.setdefault("items", [])
    data.setdefault("total", None)

    if not isinstance(data.get("items"), list):
        data["items"] = []

    return data
