import base64
import io
import json
import logging
from typing import Any, Optional
from PIL import Image
from groq import AsyncGroq

from backend.app.config import settings
from backend.app.models.schemas import ExtractedBill, LineItem
from backend.app.services.extractor.base import BillExtractor, ExtractionProvenance, ExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert restaurant receipt and bill parser.
Extract all line items, charges, discounts, taxes, and totals from the provided receipt image(s).

Rules:
1. Return ONLY a valid JSON object matching this schema:
{
  "items": [
    {
      "name": "string (name of item)",
      "quantity": 1,
      "price": 120.50,
      "confidence": 0.95
    }
  ],
  "subtotal": 500.0,
  "tax": 25.0,
  "service_charge": 50.0,
  "discount": 0.0,
  "total": 575.0
}
2. "price" must be the TOTAL line price for that item (quantity * unit price), NOT unit price alone.
3. Assess per-item confidence (0.0 to 1.0):
   - Clear printed line: 0.90 - 1.00
   - Slight glare or minor crease: 0.75 - 0.89
   - Faded print, crumpled, handwriting, or low contrast: 0.40 - 0.74
   - Never guess silently! If a digit is uncertain, assign a lower confidence.
4. If multiple photos of a long receipt are provided, merge them sequentially into a single item list.
5. If discount, tax, or service charge are not present, set their value to 0.0.
"""

STRICTER_ADDENDUM = """
ATTENTION - RETRY WITH STRICT RULES:
Your previous extraction had low confidence or arithmetic discrepancy.
- Carefully inspect every price digit and decimal point.
- Ensure that the sum of line items aligns with the subtotal.
- Check for handwritten additions, split taxes (CGST + SGST), or discounts.
- Be honest with confidence scores (0.0 to 1.0).
"""


def _prepare_image_base64(image_bytes: bytes, max_dim: int = 1024) -> str:
    """Resize large smartphone photos to manageable dimensions and convert to JPEG base64."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Scale down if either dimension exceeds max_dim
        w, h = img.size
        if w > max_dim or h > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as exc:
        logger.warning(f"PIL resize failed, falling back to raw bytes: {exc}")
        return base64.b64encode(image_bytes).decode("utf-8")


class GroqVisionExtractor(BillExtractor):
    """
    Vision LLM extractor using non-LLaMA vision model (qwen/qwen3.8-27b) on Groq.
    Extracts structured ExtractedBill directly from receipt images without any classical OCR.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_VISION_MODEL
        self.client = AsyncGroq(api_key=self.api_key, timeout=45.0) if self.api_key else None

    async def extract(
        self,
        images: list[bytes],
        stricter_prompt: bool = False,
        **kwargs: Any
    ) -> ExtractionResult:
        if not self.client:
            raise ValueError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env or environment."
            )
        if not images:
            raise ValueError("No images provided for extraction.")

        system_instruction = SYSTEM_PROMPT
        if stricter_prompt:
            system_instruction += "\n" + STRICTER_ADDENDUM

        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": "Please extract all items and totals from the following restaurant bill image(s):"}
        ]

        for img_bytes in images:
            b64_img = _prepare_image_base64(img_bytes)
            data_url = f"data:image/jpeg;base64,{b64_img}"
            user_content.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })

        logger.info(f"Calling Groq vision model '{self.model}' with {len(images)} image(s)...")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1 if stricter_prompt else 0.2,
            max_tokens=800,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response received from Groq vision model.")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to decode JSON from Groq vision: {content}")
            raise ValueError(f"Groq vision returned invalid JSON: {exc}")

        # Strict validation against Pydantic ExtractedBill schema
        extracted_bill = ExtractedBill.model_validate(data)

        # Compute average confidence
        if extracted_bill.items:
            avg_conf = sum(item.confidence for item in extracted_bill.items) / len(extracted_bill.items)
        else:
            avg_conf = 0.5

        provenance = ExtractionProvenance(
            provider="groq",
            model=self.model,
            attempt_count=2 if stricter_prompt else 1,
            average_confidence=round(avg_conf, 2),
            notes=f"Extracted {len(extracted_bill.items)} items using non-LLaMA model ({self.model})"
        )

        return ExtractionResult(bill=extracted_bill, provenance=provenance)
