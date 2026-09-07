"""
Stage A: Pure Python Deterministic Calculation Engine for Bill Splitter.

This module contains the core mathematical logic for splitting restaurant bills:
- Currency arithmetic strictly uses Decimal to eliminate floating-point imprecision.
- Per-item splitting divides line prices equally among consumers with deterministic remainder cents distribution.
- Proportional pools (tax, service charge, discount) are allocated using the Largest Remainder Method
  (Hare-Niemeyer) with a deterministic tie-break rule (person_id ascending).
- Discount vs. Tax Ordering:
    * In standard restaurant accounting (especially under Indian GST regulations), discounts (promotions,
      vouchers, happy-hour markdowns) are deducted directly from the food subtotal before GST and service charges
      are computed.
    * Proportional discount is deducted from each consumer's food total (reducing their taxable base).
    * Total for person i: person_food_subtotal - person_discount_share + person_tax_share + person_service_charge_share.
- Validation:
    * Sum of person breakdowns must equal (assigned_food_total - discount + tax + service_charge).
    * Calculated total is compared against the bill's printed total. If abs(calculated - printed) > 0.01,
      mismatch is flagged with exact signed difference.
    * Unassigned items are identified and excluded; calculate_split raises UnassignedItemsError unless
      explicitly acknowledged via acknowledge_unassigned=True.
"""

from decimal import Decimal, ROUND_FLOOR
import math
from typing import Optional

from backend.app.models.schemas import (
    ConfirmedBill,
    Person,
    PersonBreakdown,
    PersonItemShare,
    SplitResult,
    UnassignedItemInfo,
)


class UnassignedItemsError(ValueError):
    """Raised when one or more items have zero assigned consumers and calculation is attempted without acknowledgement."""
    def __init__(self, unassigned_items: list[UnassignedItemInfo]):
        self.unassigned_items = unassigned_items
        item_names = ", ".join([f"'{item.name}' (₹{item.price:.2f})" for item in unassigned_items])
        super().__init__(
            f"Cannot calculate split: {len(unassigned_items)} item(s) have no consumers assigned: {item_names}. "
            "Please assign consumers or set acknowledge_unassigned=True to exclude them."
        )


def _to_cents(amount: Decimal) -> int:
    """Convert a Decimal currency amount to integer cents/paisa."""
    return int((amount * Decimal(100)).quantize(Decimal("1")))


def _to_decimal(cents: int) -> Decimal:
    """Convert integer cents/paisa back to Decimal currency with 2 decimal places."""
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def allocate_item_price_cents(item_price: Decimal, consumer_ids: list[str]) -> dict[str, int]:
    """
    Split an item's price in cents among consumers.
    
    If total cents cannot be divided evenly, remainder cents (1 cent each) are assigned
    to consumers ordered by person_id ascending for deterministic, repeatable allocation.
    """
    if not consumer_ids:
        return {}
    
    total_cents = _to_cents(item_price)
    num_consumers = len(consumer_ids)
    
    base_cents = total_cents // num_consumers
    remainder_cents = total_cents % num_consumers
    
    # Deterministic order: sort consumers by person_id ascending
    sorted_consumers = sorted(consumer_ids)
    
    result = {}
    for idx, pid in enumerate(sorted_consumers):
        extra = 1 if idx < remainder_cents else 0
        result[pid] = base_cents + extra
        
    return result


def allocate_pool_largest_remainder(
    pool_amount: Decimal,
    weights: dict[str, Decimal]
) -> dict[str, Decimal]:
    """
    Distribute a currency pool (tax, service charge, discount) proportionally according
    to weights using the Largest Remainder Method (Hare-Niemeyer).
    
    Deterministic Tie-Break Rule:
    When remainder fractions are identical, tie-breaking prioritizes person_id ascending.
    This guarantees that identical remainders resolve identically across runs with zero drift.
    
    Guarantees:
    sum(result.values()) == pool_amount exactly.
    """
    pool_cents = _to_cents(pool_amount)
    total_weight = sum(weights.values(), Decimal("0.00"))
    
    if pool_cents == 0 or total_weight == Decimal("0.00"):
        # If total weight is 0 or pool is 0, give 0 to everyone
        if pool_cents == 0 or not weights:
            return {pid: Decimal("0.00") for pid in weights}
        # If pool > 0 but total_weight == 0, distribute pool evenly among all people
        num_people = len(weights)
        sorted_pids = sorted(weights.keys())
        base = pool_cents // num_people
        rem = pool_cents % num_people
        return {
            pid: _to_decimal(base + (1 if idx < rem else 0))
            for idx, pid in enumerate(sorted_pids)
        }
    
    # Calculate exact quotas and floor cents for each person
    quotas: dict[str, Decimal] = {}
    floored_cents: dict[str, int] = {}
    remainders: dict[str, Decimal] = {}
    
    for pid, weight in weights.items():
        # Exact quota in cents = pool_cents * (weight / total_weight)
        exact_quota = (Decimal(pool_cents) * weight) / total_weight
        floor_val = int(exact_quota.to_integral_value(rounding=ROUND_FLOOR))
        quotas[pid] = exact_quota
        floored_cents[pid] = floor_val
        remainders[pid] = exact_quota - Decimal(floor_val)
        
    allocated_cents_sum = sum(floored_cents.values())
    surplus_cents = pool_cents - allocated_cents_sum
    
    # Sort by:
    # 1. Remainder fraction descending (-remainder)
    # 2. person_id ascending (deterministic tie-break)
    sorted_by_remainder = sorted(
        weights.keys(),
        key=lambda pid: (-remainders[pid], pid)
    )
    
    final_cents = dict(floored_cents)
    for i in range(surplus_cents):
        recipient = sorted_by_remainder[i]
        final_cents[recipient] += 1
        
    return {pid: _to_decimal(cents) for pid, cents in final_cents.items()}


def calculate_split(
    confirmed_bill: ConfirmedBill,
    people: list[Person],
    assignments: dict[str, list[str]],
    acknowledge_unassigned: bool = False,
    bill_id: str = ""
) -> SplitResult:
    """
    Deterministic calculation engine executing Stage A specification.
    
    Args:
        confirmed_bill: The validated ConfirmedBill with Decimal line items and charges.
        people: List of participating Person records.
        assignments: Mapping of confirmed item ID -> list of person IDs who shared it.
        acknowledge_unassigned: If False, raises UnassignedItemsError if any item has 0 consumers.
        bill_id: Identifier for the bill.
        
    Returns:
        SplitResult containing detailed per-person breakdowns, validation totals, and mismatch alerts.
    """
    people_by_id = {p.id: p for p in people}
    person_shares: dict[str, list[PersonItemShare]] = {p.id: [] for p in people}
    person_food_cents: dict[str, int] = {p.id: 0 for p in people}
    
    unassigned_items: list[UnassignedItemInfo] = []
    
    # 1. Process each confirmed item
    for item in confirmed_bill.items:
        raw_consumers = assignments.get(item.id, [])
        # Filter to valid known people and deduplicate while keeping deterministic order
        valid_consumers = [pid for pid in sorted(set(raw_consumers)) if pid in people_by_id]
        
        if not valid_consumers:
            unassigned_items.append(
                UnassignedItemInfo(
                    item_id=item.id,
                    name=item.name,
                    price=item.price
                )
            )
            continue
            
        # Split item price among consumers with deterministic remainder cents allocation
        cents_per_consumer = allocate_item_price_cents(item.price, valid_consumers)
        
        for pid, share_cents in cents_per_consumer.items():
            share_decimal = _to_decimal(share_cents)
            person_shares[pid].append(
                PersonItemShare(
                    item_id=item.id,
                    item_name=item.name,
                    share_amount=share_decimal,
                    split_among_count=len(valid_consumers)
                )
            )
            person_food_cents[pid] += share_cents

    # Check for unassigned items blocking
    if unassigned_items and not acknowledge_unassigned:
        raise UnassignedItemsError(unassigned_items)
        
    warnings: list[str] = []
    if unassigned_items:
        unassigned_total = sum((item.price for item in unassigned_items), Decimal("0.00"))
        item_names = ", ".join([f"'{item.name}' (₹{item.price:.2f})" for item in unassigned_items])
        warnings.append(
            f"Notice: {len(unassigned_items)} unassigned item(s) totaling ₹{unassigned_total:.2f} "
            f"excluded from calculation: {item_names}."
        )

    # 2. Food subtotals per person and total assigned food
    person_food_subtotals: dict[str, Decimal] = {
        pid: _to_decimal(cents) for pid, cents in person_food_cents.items()
    }
    assigned_food_total = sum(person_food_subtotals.values(), Decimal("0.00"))
    
    # 3. Proportional allocations using Largest Remainder Method with person_id ascending tie-break
    # Note: Discount is calculated on food share to proportionally reduce food expenditure.
    discount_shares = allocate_pool_largest_remainder(
        confirmed_bill.discount,
        person_food_subtotals
    )
    
    # Tax and service charge are allocated proportionally to each person's food share
    tax_shares = allocate_pool_largest_remainder(
        confirmed_bill.tax,
        person_food_subtotals
    )
    
    service_charge_shares = allocate_pool_largest_remainder(
        confirmed_bill.service_charge,
        person_food_subtotals
    )
    
    # 4. Assemble PersonBreakdown per person
    breakdowns: list[PersonBreakdown] = []
    for p in sorted(people, key=lambda person: person.id):
        pid = p.id
        f_sub = person_food_subtotals[pid]
        d_share = discount_shares[pid]
        t_share = tax_shares[pid]
        sc_share = service_charge_shares[pid]
        
        # Person total = Food Subtotal - Discount + Tax + Service Charge
        p_total = (f_sub - d_share + t_share + sc_share).quantize(Decimal("0.01"))
        
        breakdowns.append(
            PersonBreakdown(
                person_id=pid,
                name=p.name,
                items=person_shares[pid],
                food_subtotal=f_sub,
                tax_share=t_share,
                service_charge_share=sc_share,
                discount_share=d_share,
                total=p_total
            )
        )
        
    # 5. Validation against printed total
    # Calculated total = assigned_food_total + tax + service_charge - discount
    calculated_total = (
        assigned_food_total + confirmed_bill.tax + confirmed_bill.service_charge - confirmed_bill.discount
    ).quantize(Decimal("0.01"))
    
    difference = (calculated_total - confirmed_bill.total).quantize(Decimal("0.01"))
    mismatch = abs(difference) > Decimal("0.01")
    
    if mismatch:
        warnings.append(
            f"Bill total mismatch: calculated total (₹{calculated_total:.2f}) differs from printed "
            f"total (₹{confirmed_bill.total:.2f}) by ₹{difference:+.2f}."
        )

    return SplitResult(
        bill_id=bill_id,
        persons=breakdowns,
        assigned_food_total=assigned_food_total,
        subtotal=confirmed_bill.subtotal,
        tax=confirmed_bill.tax,
        service_charge=confirmed_bill.service_charge,
        discount=confirmed_bill.discount,
        calculated_total=calculated_total,
        printed_total=confirmed_bill.total,
        mismatch=mismatch,
        difference=difference,
        unassigned_items=unassigned_items,
        warnings=warnings
    )
