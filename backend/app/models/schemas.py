from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Extraction Models (Stage B: AI Extraction Contract)
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    name: str = Field(..., description="Name of the bill item")
    quantity: int = Field(default=1, description="Quantity of item ordered")
    price: float = Field(..., description="Total line price for this item (not unit price)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")


class ExtractedBill(BaseModel):
    items: list[LineItem] = Field(default_factory=list, description="List of line items on the bill")
    subtotal: float = Field(default=0.0, description="Stated or calculated food subtotal")
    tax: float = Field(default=0.0, description="Total tax amount (e.g. GST/VAT)")
    service_charge: float = Field(default=0.0, description="Service charge or tip amount")
    discount: float = Field(default=0.0, description="Discount amount applied")
    total: float = Field(default=0.0, description="Printed final grand total on bill")


# ---------------------------------------------------------------------------
# Confirmed Models (Stage C: Clean, human-reviewed input to calculator)
# ---------------------------------------------------------------------------

class ConfirmedBillItem(BaseModel):
    id: str = Field(..., description="Stable unique identifier for the confirmed item")
    name: str
    quantity: int = 1
    price: Decimal = Field(..., description="Confirmed total price in Decimal")


class ConfirmedBill(BaseModel):
    items: list[ConfirmedBillItem]
    subtotal: Decimal = Field(default=Decimal("0.00"))
    tax: Decimal = Field(default=Decimal("0.00"))
    service_charge: Decimal = Field(default=Decimal("0.00"))
    discount: Decimal = Field(default=Decimal("0.00"))
    total: Decimal = Field(..., description="Printed grand total from the physical receipt")


# ---------------------------------------------------------------------------
# People & Assignment Models (Stage D)
# ---------------------------------------------------------------------------

class PersonCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class Person(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class AssignmentCreate(BaseModel):
    # Keyed against confirmed item's stable ID, NOT raw array index
    assignments: dict[str, list[str]] = Field(
        ...,
        description="Map of confirmed item ID -> list of person IDs who shared it"
    )


# ---------------------------------------------------------------------------
# Split & Breakdown Models (Stage A & E: Pure Deterministic Output)
# ---------------------------------------------------------------------------

class PersonItemShare(BaseModel):
    item_id: str
    item_name: str
    share_amount: Decimal
    split_among_count: int


class PersonBreakdown(BaseModel):
    person_id: str
    name: str
    items: list[PersonItemShare]
    food_subtotal: Decimal
    tax_share: Decimal
    service_charge_share: Decimal
    discount_share: Decimal
    total: Decimal


class UnassignedItemInfo(BaseModel):
    item_id: str
    name: str
    price: Decimal


class CalculateRequest(BaseModel):
    acknowledge_unassigned: bool = Field(
        default=False,
        description="If true, allows calculation to proceed even if some items have 0 consumers"
    )


class SplitResult(BaseModel):
    bill_id: str
    persons: list[PersonBreakdown]
    assigned_food_total: Decimal
    subtotal: Decimal
    tax: Decimal
    service_charge: Decimal
    discount: Decimal
    calculated_total: Decimal
    printed_total: Decimal
    mismatch: bool
    difference: Decimal
    unassigned_items: list[UnassignedItemInfo]
    warnings: list[str]
