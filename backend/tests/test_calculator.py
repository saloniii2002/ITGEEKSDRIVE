from decimal import Decimal
import pytest

from backend.app.models.schemas import (
    ConfirmedBill,
    ConfirmedBillItem,
    Person,
)
from backend.app.services.calculator import (
    UnassignedItemsError,
    allocate_item_price_cents,
    allocate_pool_largest_remainder,
    calculate_split,
)


def make_person(pid: str, name: str) -> Person:
    return Person(id=pid, name=name)


def make_item(item_id: str, name: str, price: str, qty: int = 1) -> ConfirmedBillItem:
    return ConfirmedBillItem(id=item_id, name=name, price=Decimal(price), quantity=qty)


# ---------------------------------------------------------------------------
# Stage A Test Suite: Calculation Engine
# ---------------------------------------------------------------------------

def test_allocate_item_price_cents_even_and_rounding():
    """Verify that item splitting divides cents and distributes remainders deterministically."""
    # 100.00 / 3 = 33.33 each with 1 cent remainder
    # Consumers: ["p3", "p1", "p2"] -> sorted ascending: ["p1", "p2", "p3"]
    # p1 gets 33.34, p2 and p3 get 33.33
    result = allocate_item_price_cents(Decimal("100.00"), ["p3", "p1", "p2"])
    assert result == {"p1": 3334, "p2": 3333, "p3": 3333}
    assert sum(result.values()) == 10000


def test_allocate_pool_largest_remainder_hare_niemeyer():
    """Verify Largest Remainder Method with deterministic person_id tie-breaking."""
    # Pool = 10.01 (1001 cents) across 3 equal weights of 100.00
    # Exact quotas: 333.666... cents each
    # Floor: 333 cents each (sum = 999). Remainder = 2 cents.
    # Fractions: 0.666... each (identical!)
    # Deterministic tie-break by person_id ascending: p1 and p2 get +1 cent.
    weights = {
        "p3": Decimal("100.00"),
        "p1": Decimal("100.00"),
        "p2": Decimal("100.00"),
    }
    allocated = allocate_pool_largest_remainder(Decimal("10.01"), weights)
    assert allocated["p1"] == Decimal("3.34")
    assert allocated["p2"] == Decimal("3.34")
    assert allocated["p3"] == Decimal("3.33")
    assert sum(allocated.values()) == Decimal("10.01")


def test_even_split_among_all():
    """Test standard even split among all people with tax and service charge."""
    people = [make_person("p1", "Alice"), make_person("p2", "Bob"), make_person("p3", "Charlie")]
    items = [
        make_item("i1", "Pizza Margherita", "600.00"),
        make_item("i2", "Pasta Carbonara", "450.00"),
    ]
    # Total food: 1050.00. Tax: 52.50. Service: 105.00. Total = 1207.50
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("1050.00"),
        tax=Decimal("52.50"),
        service_charge=Decimal("105.00"),
        discount=Decimal("0.00"),
        total=Decimal("1207.50"),
    )
    assignments = {
        "i1": ["p1", "p2", "p3"],
        "i2": ["p1", "p2", "p3"],
    }
    
    result = calculate_split(bill, people, assignments, bill_id="bill_1")
    
    assert not result.mismatch
    assert result.difference == Decimal("0.00")
    assert result.calculated_total == Decimal("1207.50")
    assert len(result.persons) == 3
    
    # Each person food = 1050 / 3 = 350.00
    for p in result.persons:
        assert p.food_subtotal == Decimal("350.00")
        assert p.tax_share == Decimal("17.50")
        assert p.service_charge_share == Decimal("35.00")
        assert p.total == Decimal("402.50")
        
    assert sum(p.total for p in result.persons) == Decimal("1207.50")


def test_item_split_among_subset():
    """Test where items are split among different subsets of people."""
    p_alice = make_person("p1", "Alice")
    p_bob = make_person("p2", "Bob")
    p_charlie = make_person("p3", "Charlie")
    people = [p_alice, p_bob, p_charlie]
    
    items = [
        make_item("i1", "Paneer Tikka", "300.00"),      # Alice & Bob (150 each)
        make_item("i2", "Chicken Biryani", "400.00"),    # Bob & Charlie (200 each)
        make_item("i3", "Garlic Naan", "100.00"),        # All three (33.34, 33.33, 33.33)
    ]
    # Total food = 800.00
    # Alice food: 150 + 33.34 = 183.34
    # Bob food: 150 + 200 + 33.33 = 383.33
    # Charlie food: 200 + 33.33 = 233.33
    # Sum food = 800.00
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("800.00"),
        tax=Decimal("40.00"),            # 5% GST
        service_charge=Decimal("80.00"), # 10% Service charge
        discount=Decimal("0.00"),
        total=Decimal("920.00"),
    )
    assignments = {
        "i1": ["p1", "p2"],
        "i2": ["p2", "p3"],
        "i3": ["p1", "p2", "p3"],
    }
    
    result = calculate_split(bill, people, assignments)
    
    assert not result.mismatch
    assert result.calculated_total == Decimal("920.00")
    
    p_map = {p.person_id: p for p in result.persons}
    assert p_map["p1"].food_subtotal == Decimal("183.34")
    assert p_map["p2"].food_subtotal == Decimal("383.33")
    assert p_map["p3"].food_subtotal == Decimal("233.33")
    
    # Proportional tax sum = 40.00 exactly
    assert sum(p.tax_share for p in result.persons) == Decimal("40.00")
    # Proportional service charge sum = 80.00 exactly
    assert sum(p.service_charge_share for p in result.persons) == Decimal("80.00")
    # Person totals sum to 920.00 exactly
    assert sum(p.total for p in result.persons) == Decimal("920.00")


def test_item_assigned_to_one_person():
    """Test where an item is assigned to exclusively one person."""
    p_alice = make_person("p1", "Alice")
    p_bob = make_person("p2", "Bob")
    people = [p_alice, p_bob]
    
    items = [
        make_item("i1", "Steak", "750.00"),   # Alice only
        make_item("i2", "Salad", "250.00"),   # Bob only
    ]
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("1000.00"),
        tax=Decimal("50.00"),
        service_charge=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("1050.00"),
    )
    assignments = {
        "i1": ["p1"],
        "i2": ["p2"],
    }
    
    result = calculate_split(bill, people, assignments)
    p_map = {p.person_id: p for p in result.persons}
    
    assert p_map["p1"].food_subtotal == Decimal("750.00")
    assert p_map["p1"].tax_share == Decimal("37.50")
    assert p_map["p1"].total == Decimal("787.50")
    
    assert p_map["p2"].food_subtotal == Decimal("250.00")
    assert p_map["p2"].tax_share == Decimal("12.50")
    assert p_map["p2"].total == Decimal("262.50")
    
    assert sum(p.total for p in result.persons) == Decimal("1050.00")


def test_unassigned_item_blocked_unless_acknowledged():
    """Verify that unassigned items raise UnassignedItemsError unless acknowledged."""
    people = [make_person("p1", "Alice"), make_person("p2", "Bob")]
    items = [
        make_item("i1", "Burger", "300.00"),
        make_item("i2", "Expensive Wine", "2500.00"),  # Nobody assigned!
    ]
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("2800.00"),
        tax=Decimal("140.00"),
        service_charge=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("2940.00"),
    )
    # Wine is not assigned
    assignments = {
        "i1": ["p1", "p2"],
    }
    
    # 1. Blocked when acknowledge_unassigned is False
    with pytest.raises(UnassignedItemsError) as exc_info:
        calculate_split(bill, people, assignments, acknowledge_unassigned=False)
    assert "Expensive Wine" in str(exc_info.value)
    assert len(exc_info.value.unassigned_items) == 1
    
    # 2. Allowed when acknowledge_unassigned is True
    result = calculate_split(bill, people, assignments, acknowledge_unassigned=True)
    assert len(result.unassigned_items) == 1
    assert result.unassigned_items[0].name == "Expensive Wine"
    assert any("Notice:" in w and "unassigned" in w for w in result.warnings)
    # Only burger (300) is split, so calculated total differs from printed total (2940)
    assert result.mismatch is True
    assert result.calculated_total == Decimal("300.00") + Decimal("140.00")  # 440.00
    assert result.difference == Decimal("440.00") - Decimal("2940.00")       # -2500.00


def test_rounding_edge_case_100_split_3_ways():
    """Verify ₹100 split 3 ways yields 33.34, 33.33, 33.33 with deterministic tie-break."""
    people = [make_person("p1", "Alice"), make_person("p2", "Bob"), make_person("p3", "Charlie")]
    items = [make_item("i1", "Shared Dish", "100.00")]
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("100.00"),
        tax=Decimal("0.00"),
        service_charge=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("100.00"),
    )
    assignments = {"i1": ["p1", "p2", "p3"]}
    
    result = calculate_split(bill, people, assignments)
    p_map = {p.person_id: p for p in result.persons}
    
    assert p_map["p1"].total == Decimal("33.34")
    assert p_map["p2"].total == Decimal("33.33")
    assert p_map["p3"].total == Decimal("33.33")
    assert sum(p.total for p in result.persons) == Decimal("100.00")


def test_mismatched_printed_total():
    """Verify that a difference between calculated and printed total is surfaced explicitly."""
    people = [make_person("p1", "Alice"), make_person("p2", "Bob")]
    items = [make_item("i1", "Meal", "500.00")]
    # Printed total has an error: says 580.00 instead of 550.00 (500 + 50 tax)
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("500.00"),
        tax=Decimal("50.00"),
        service_charge=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("580.00"),  # Intentionally incorrect printed receipt total
    )
    assignments = {"i1": ["p1", "p2"]}
    
    result = calculate_split(bill, people, assignments)
    
    assert result.mismatch is True
    assert result.calculated_total == Decimal("550.00")
    assert result.printed_total == Decimal("580.00")
    # difference = calculated - printed = 550.00 - 580.00 = -30.00
    assert result.difference == Decimal("-30.00")
    assert any("Bill total mismatch" in w for w in result.warnings)


def test_combined_scenario_discount_tax_service_charge_subsets_rounding():
    """
    Complex test combining:
    - 3 people: Alice (p1), Bob (p2), Charlie (p3)
    - 4 items with subsets and single-consumer items
    - Proportional discount applied to food
    - Proportional tax & service charge
    - Rounding edge cases on all pools
    - Exact sum validation
    """
    people = [
        make_person("p1", "Alice"),
        make_person("p2", "Bob"),
        make_person("p3", "Charlie"),
    ]
    items = [
        make_item("i1", "Crispy Calamari", "385.00"),     # Alice, Bob, Charlie (128.34, 128.33, 128.33)
        make_item("i2", "Mutton Rogan Josh", "650.00"),   # Alice, Bob (325.00 each)
        make_item("i3", "Craft Beer Flight", "490.00"),   # Charlie only (490.00)
        make_item("i4", "Tiramisu", "275.00"),            # Bob, Charlie (137.50 each)
    ]
    # Food Total = 385 + 650 + 490 + 275 = 1800.00
    # Food shares:
    # Alice: 128.34 + 325.00 = 453.34
    # Bob: 128.33 + 325.00 + 137.50 = 590.83
    # Charlie: 128.33 + 490.00 + 137.50 = 755.83
    # Sum food = 453.34 + 590.83 + 755.83 = 1800.00
    
    # Discount: 180.00 (10% promo)
    # Tax (GST): 81.00 (5% on 1800 - 180 = 1620)
    # Service charge: 162.00 (10% on 1620)
    # Calculated Total = 1800 - 180 + 81 + 162 = 1863.00
    bill = ConfirmedBill(
        items=items,
        subtotal=Decimal("1800.00"),
        tax=Decimal("81.00"),
        service_charge=Decimal("162.00"),
        discount=Decimal("180.00"),
        total=Decimal("1863.00"),
    )
    assignments = {
        "i1": ["p1", "p2", "p3"],
        "i2": ["p1", "p2"],
        "i3": ["p3"],
        "i4": ["p2", "p3"],
    }
    
    result = calculate_split(bill, people, assignments, bill_id="complex_bill_1")
    
    assert not result.mismatch
    assert result.difference == Decimal("0.00")
    assert result.calculated_total == Decimal("1863.00")
    
    # Check exact pool distributions
    assert sum(p.discount_share for p in result.persons) == Decimal("180.00")
    assert sum(p.tax_share for p in result.persons) == Decimal("81.00")
    assert sum(p.service_charge_share for p in result.persons) == Decimal("162.00")
    assert sum(p.total for p in result.persons) == Decimal("1863.00")
    
    # Verify each person's total formula: food - discount + tax + service_charge
    for p in result.persons:
        expected = p.food_subtotal - p.discount_share + p.tax_share + p.service_charge_share
        assert p.total == expected
        
    # Re-run and check bitwise determinism
    result_second_run = calculate_split(bill, people, assignments, bill_id="complex_bill_1")
    assert result.model_dump() == result_second_run.model_dump()
