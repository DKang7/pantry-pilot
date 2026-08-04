from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass
class ExtractedReceiptItem:
    raw_text: str
    normalized_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None

@dataclass
class ReceiptExtractionResult:
    store_name: Optional[str]
    purchase_date: Optional[str]
    currency: Optional[str]
    total: Optional[float]
    items: list[ExtractedReceiptItem]
    warnings: list[str]

class ReceiptExtractor(Protocol):
    def extract_receipt(
        self,
        file_path: str
    ) -> ReceiptExtractionResult:
        ...