from decimal import Decimal
from typing import Any
import json

from backend.app.models.schemas import ExtractedBill, LineItem
from backend.app.services.extractor.base import BillExtractor, ExtractionProvenance, ExtractionResult


class MockBillExtractor(BillExtractor):
    """
    Deterministic mock extractor for unit tests, integration tests, and offline CI.
    Provides realistic receipt data with individual field confidences.
    """

    def __init__(self, default_scenario: str = "standard"):
        self.default_scenario = default_scenario

    async def extract(
        self,
        images: list[bytes],
        stricter_prompt: bool = False,
        **kwargs: Any
    ) -> ExtractionResult:
        # Check if caller specified a custom scenario in kwargs or image bytes
        scenario = kwargs.get("scenario", self.default_scenario)
        
        # If multi-image bill is passed, simulate merged items
        if len(images) > 1 or scenario == "multi_page":
            items = [
                LineItem(name="Truffle Fries (Page 1)", quantity=1, price=320.0, confidence=0.96),
                LineItem(name="Wild Mushroom Risotto (Page 1)", quantity=1, price=580.0, confidence=0.94),
                LineItem(name="Grilled Sea Bass (Page 2)", quantity=1, price=850.0, confidence=0.91),
                LineItem(name="Sparkling Water (Page 2)", quantity=2, price=240.0, confidence=0.97),
                LineItem(name="Tiramisu (Page 2)", quantity=1, price=350.0, confidence=0.89),
            ]
            subtotal = sum(item.price for item in items)  # 2340.0
            tax = round(subtotal * 0.05, 2)              # 117.0
            service_charge = round(subtotal * 0.10, 2)   # 234.0
            discount = 200.0
            total = round(subtotal + tax + service_charge - discount, 2)  # 2491.0
            
            bill = ExtractedBill(
                items=items,
                subtotal=subtotal,
                tax=tax,
                service_charge=service_charge,
                discount=discount,
                total=total
            )
            provenance = ExtractionProvenance(
                provider="mock",
                model="mock-multi-page-v1",
                attempt_count=1,
                average_confidence=round(sum(i.confidence for i in items) / len(items), 2),
                notes=f"Merged {len(images)} receipt photos"
            )
            return ExtractionResult(bill=bill, provenance=provenance)

        # Standard realistic restaurant bill scenario
        items = [
            LineItem(name="Butter Chicken", quantity=1, price=480.0, confidence=0.98),
            LineItem(name="Garlic Naan", quantity=3, price=210.0, confidence=0.95),
            LineItem(name="Dal Makhani", quantity=1, price=340.0, confidence=0.92),
            LineItem(name="Jeera Rice", quantity=1, price=220.0, confidence=0.94),
            LineItem(name="Gulab Jamun (2 pcs)", quantity=1, price=160.0, confidence=0.85),
        ]
        
        # If stricter prompt was requested, simulate refined confidence
        if stricter_prompt:
            for item in items:
                item.confidence = min(1.0, item.confidence + 0.05)

        subtotal = 1410.0
        tax = 70.50             # 5% GST
        service_charge = 141.00 # 10% Service charge
        discount = 150.00       # Promotional coupon
        total = 1471.50         # 1410 - 150 + 70.5 + 141 = 1471.50

        bill = ExtractedBill(
            items=items,
            subtotal=subtotal,
            tax=tax,
            service_charge=service_charge,
            discount=discount,
            total=total
        )
        
        avg_conf = sum(i.confidence for i in items) / len(items)
        provenance = ExtractionProvenance(
            provider="mock",
            model="mock-extractor-v1",
            attempt_count=2 if stricter_prompt else 1,
            average_confidence=round(avg_conf, 2),
            notes="Deterministic synthetic bill"
        )
        return ExtractionResult(bill=bill, provenance=provenance)
