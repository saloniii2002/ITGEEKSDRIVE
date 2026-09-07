import logging
from typing import Any, Optional, TypedDict
from langgraph.graph import END, StateGraph

from backend.app.config import settings
from backend.app.models.schemas import ExtractedBill
from backend.app.services.extractor.base import BillExtractor, ExtractionProvenance, ExtractionResult
from backend.app.services.extractor.groq_vision import GroqVisionExtractor
from backend.app.services.extractor.mock_extractor import MockBillExtractor

logger = logging.getLogger(__name__)


class ExtractorState(TypedDict):
    images: list[bytes]
    attempt: int
    result: Optional[ExtractionResult]
    error: Optional[str]
    is_acceptable: bool


def get_primary_extractor() -> BillExtractor:
    """Factory selecting Groq Vision or Mock based on configuration."""
    if settings.FORCE_MOCK_EXTRACTOR or not settings.GROQ_API_KEY:
        if not settings.GROQ_API_KEY and not settings.FORCE_MOCK_EXTRACTOR:
            logger.warning(
                "GROQ_API_KEY is not set. Defaulting to MockBillExtractor for development/testing."
            )
        return MockBillExtractor()
    return GroqVisionExtractor()


async def extract_node(state: ExtractorState) -> dict[str, Any]:
    """Execute primary vision extraction attempt."""
    attempt = state.get("attempt", 1)
    images = state.get("images", [])
    stricter = (attempt > 1)
    
    extractor = get_primary_extractor()
    logger.info(f"Extraction pipeline node: running attempt {attempt} (stricter={stricter})...")

    try:
        result = await extractor.extract(images=images, stricter_prompt=stricter)
        result.provenance.attempt_count = attempt
        return {
            "result": result,
            "error": None,
            "attempt": attempt,
        }
    except Exception as exc:
        logger.error(f"Extraction attempt {attempt} failed: {exc}")
        return {
            "result": None,
            "error": str(exc),
            "attempt": attempt,
        }


async def validate_node(state: ExtractorState) -> dict[str, Any]:
    """
    Validate extraction quality against confidence threshold and schema requirements.
    If average confidence is below 0.65 or extraction failed, flags for retry.
    """
    result = state.get("result")
    attempt = state.get("attempt", 1)
    error = state.get("error")

    if error or result is None:
        logger.warning(f"Attempt {attempt} produced error: {error}")
        return {"is_acceptable": False}

    items = result.bill.items
    if not items:
        logger.warning(f"Attempt {attempt} returned 0 items. Triggering retry.")
        return {"is_acceptable": False}

    avg_conf = result.provenance.average_confidence
    if avg_conf < 0.65 and attempt < 2:
        logger.warning(f"Average confidence {avg_conf:.2f} is below 0.65. Triggering stricter retry.")
        return {"is_acceptable": False}

    logger.info(f"Extraction passed validation on attempt {attempt} with confidence {avg_conf:.2f}.")
    return {"is_acceptable": True}


def should_retry(state: ExtractorState) -> str:
    """Routing decision: proceed to END or increment attempt for stricter retry."""
    is_acceptable = state.get("is_acceptable", False)
    attempt = state.get("attempt", 1)

    if is_acceptable or attempt >= 2:
        return "end"
    
    # Increment attempt count and retry
    state["attempt"] = attempt + 1
    return "retry"


def build_extraction_graph():
    """Build and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(ExtractorState)

    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)

    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "validate")

    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "retry": "extract",
            "end": END,
        }
    )

    return workflow.compile()


# Compiled singleton graph
extraction_graph = build_extraction_graph()


async def run_extraction_pipeline(images: list[bytes]) -> ExtractionResult:
    """
    Main entry point for Stage B bill extraction orchestrated by LangGraph.
    
    Args:
        images: list of raw image bytes (supports multi-photo long bills)
        
    Returns:
        ExtractionResult containing validated ExtractedBill and complete provenance.
    """
    initial_state: ExtractorState = {
        "images": images,
        "attempt": 1,
        "result": None,
        "error": None,
        "is_acceptable": False,
    }

    final_state = await extraction_graph.ainvoke(initial_state)
    
    result = final_state.get("result")
    if not result:
        error_msg = final_state.get("error") or "Unknown extraction failure"
        raise RuntimeError(f"Bill extraction pipeline failed to produce a valid bill: {error_msg}")

    return result
