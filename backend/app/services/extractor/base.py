from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel

from backend.app.models.schemas import ExtractedBill


class ExtractionProvenance(BaseModel):
    provider: str
    model: str
    attempt_count: int = 1
    escalated: bool = False
    average_confidence: float = 1.0
    notes: Optional[str] = None


class ExtractionResult(BaseModel):
    bill: ExtractedBill
    provenance: ExtractionProvenance


class BillExtractor(ABC):
    """Abstract interface for all Bill Vision Extractor implementations."""

    @abstractmethod
    async def extract(
        self,
        images: list[bytes],
        stricter_prompt: bool = False,
        **kwargs: Any
    ) -> ExtractionResult:
        """
        Extract line items, tax, service charge, discount, and total from one or more receipt images.
        
        Args:
            images: Raw bytes of bill photo(s).
            stricter_prompt: True if this is a retry attempt requiring stricter parsing and confidence scrutiny.
            
        Returns:
            ExtractionResult containing strictly validated ExtractedBill and metadata provenance.
        """
        pass
