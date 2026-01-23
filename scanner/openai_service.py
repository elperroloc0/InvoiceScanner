import json
import logging
import os
import base64
import cv2
import numpy as np

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def extract_data_with_openai_vision(image_array: np.ndarray) -> dict:
    """
    Sends the preprocessed image directly to OpenAI Vision (GPT-4o)
    for high-accuracy data extraction.
    """
    api_key = os.getenv("OPEN_AI_API")
    prompt = os.getenv("EXTRACT_DATA_PROMPT")

    if not api_key:
        raise ValueError("OPEN_AI_API environment variable not set.")

    if prompt is None:
        # Fallback prompt if .env is missing it
        prompt = (
            "Respond strictly in JSON format. Do not group or omit repeating items. "
            "Schema: {\"store\": string|null, \"items\": [{\"name\": string, \"price\": number}], \"total\": number|null}. "
            "Calculate 'total' as the final grand total paid (including taxes). "
            "Do not list Tax or Shipping as items. Return ONLY JSON."
        )

    # 1. Convert OpenCV image (NumPy array) to Base64
    _, buffer = cv2.imencode(".jpg", image_array, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    base64_image = base64.b64encode(buffer).decode("utf-8")

    client = OpenAI(api_key=api_key)

    try:
        logging.info("Sending image to OpenAI Vision model...")
        resp = client.chat.completions.create(
            model="gpt-4o-mini", # or gpt-4o for maximum power
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content
        data = json.loads(content)

        # Standardize structure
        if "store_name" in data and "store" not in data:
            data["store"] = data.pop("store_name")

        for item in data.get("items", []):
            if "item_name" in item and "name" not in item:
                item["name"] = item.pop("item_name")

        data.setdefault("store", "Unknown Store")
        data.setdefault("items", [])
        data.setdefault("total", 0.0)

        return data

    except Exception as e:
        logging.error(f"OpenAI Vision error: {e}")
        raise e
