import urllib.parse
from decimal import Decimal
from typing import Optional

from backend.app.models.schemas import SplitResult


def format_whatsapp_message(
    result: SplitResult,
    share_url: Optional[str] = None,
    restaurant_name: Optional[str] = None
) -> str:
    """
    Format a clean, readable WhatsApp message with itemized breakdown per person.
    """
    header = f"🧾 *Bill Split Breakdown"
    if restaurant_name:
        header += f" — {restaurant_name}"
    header += "*\n━━━━━━━━━━━━━━━━━━━━\n"

    body_lines = []
    for p in result.persons:
        person_line = f"\n👤 *{p.name}* owes: *₹{p.total:.2f}*\n"
        items_desc = []
        for itm in p.items:
            split_note = f" (1/{itm.split_among_count})" if itm.split_among_count > 1 else ""
            items_desc.append(f"  • {itm.item_name}{split_note}: ₹{itm.share_amount:.2f}")
        
        if p.discount_share > Decimal("0.00"):
            items_desc.append(f"  • Discount: -₹{p.discount_share:.2f}")
        if p.tax_share > Decimal("0.00"):
            items_desc.append(f"  • Tax: ₹{p.tax_share:.2f}")
        if p.service_charge_share > Decimal("0.00"):
            items_desc.append(f"  • Service Charge: ₹{p.service_charge_share:.2f}")
            
        body_lines.append(person_line + "\n".join(items_desc))

    footer = f"\n━━━━━━━━━━━━━━━━━━━━\n💰 *Total Paid:* ₹{result.calculated_total:.2f}"
    if result.mismatch:
        footer += f"\n⚠️ *Note:* Bill printed total was ₹{result.printed_total:.2f} (diff: ₹{result.difference:+.2f})"

    if share_url:
        footer += f"\n\n🔗 *Full breakdown link:*\n{share_url}"

    return header + "\n".join(body_lines) + footer


def generate_whatsapp_share_url(message: str, phone: Optional[str] = None) -> str:
    """
    Generate wa.me link with URL-encoded text.
    If phone is provided, target that number, else use https://wa.me/?text=...
    """
    encoded_text = urllib.parse.quote(message)
    if phone:
        # Clean phone number of non-digits
        clean_phone = "".join(filter(str.isdigit, phone))
        return f"https://wa.me/{clean_phone}?text={encoded_text}"
    return f"https://wa.me/?text={encoded_text}"
