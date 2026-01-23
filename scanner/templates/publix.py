from .base import BaseTemplate
from ..parser import parse_receipt

class PublixTemplate(BaseTemplate):
    @property
    def store_name(self) -> str:
        return "Publix"

    @property
    def keywords(self) -> list[str]:
        return ["publix", "where shopping is a pleasure"]

    def parse(self, raw_ocr: list[dict]) -> dict:
        # Reuse existing parsing logic for now
        return parse_receipt(raw_ocr)
