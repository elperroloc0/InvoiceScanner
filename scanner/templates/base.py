from abc import ABC, abstractmethod

class BaseTemplate(ABC):
    @property
    @abstractmethod
    def store_name(self) -> str:
        """Name of the store this template handles."""
        pass

    @property
    @abstractmethod
    def keywords(self) -> list[str]:
        """List of keywords to detect this store in OCR headers."""
        pass

    @abstractmethod
    def parse(self, raw_ocr: list[dict]) -> dict:
        """Logic to extract items and total from full OCR data."""
        pass

    def matches(self, header_ocr: list[dict]) -> bool:
        """Checks if the store name exists in the OCR header."""
        header_text = " ".join([x.get("text", "").lower() for x in header_ocr])
        return any(k.lower() in header_text for k in self.keywords)
