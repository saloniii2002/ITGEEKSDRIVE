import base64
import json
import logging
from typing import Any, Optional
from groq import AsyncGroq

from backend.app.config import settings
from backend.app.models.schemas import ExtractedBill, LineItem
from backend.app.services.extractor.base import BillExtractor, ExtractionProvenance, ExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert restaurant bill and receipt parser.
Extract all line items, charges, discounts, taxes, and totals from the provided receipt photo(s).

Rules:
1. Return ONLY a valid JSON object matching this exact schema:
{
  "items": [
    {
      "name": "string (item name as printed)",
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
   - Clear printed item with clear price: 0.90 - 1.00
   - Slight glare or minor crease: 0.75 - 0.89
   - Faded thermal print, crumpled paper, steep angle, handwriting, or mixed scripts: 0.40 - 0.74
   - Never guess silently! If a digit is uncertain, provide your best read and assign a low confidence score.
4. If multiple photos of a long receipt are provided, merge them sequentially into a single unified item list.
5. If discount, tax, or service charge are not present, set their value to 0.0.
"""

STRICTER_ADDENDUM = """
ATTENTION - RETRY WITH STRICT RULES:
Your previous extraction had low confidence or arithmetic discrepancy.
- Carefully inspect every price digit and decimal point.
- Ensure that the sum of line items aligns with the subtotal.
- Check for handwritten additions, split taxes (CGST + SGST), or discounts.
- Be especially honest with confidence scores (0.0 to 1.0).
"""


class GroqVisionExtractor(BillExtractor):
    """
    Vision-capable LLM extractor using Groq Vision models (e.g. llama-3.2-11b-vision-preview).
    Extracts structured ExtractedBill directly from receipt images without any classical OCR.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_VISION_MODEL
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

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

        # Format content for vision API (text prompt + base64 image data URLs)
        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": "Please extract all items and totals from the following restaurant bill image(s):"}
        ]

        for idx, img_bytes in enumerate(images):
            # Detect mime type or default to jpeg/png
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
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
            max_tokens=2048,
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
            notes=f"Extracted {len(extracted_bill.items)} items across {len(images)} image(s)"
        )

        return ExtractionResult(bill=extracted_bill, provenance=provenance)
