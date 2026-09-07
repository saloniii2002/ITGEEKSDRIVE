import json
import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.db_models import (
    AssignmentModel,
    BillModel,
    CalculationResultModel,
    PersonModel,
)
from backend.app.models.schemas import (
    AssignmentCreate,
    CalculateRequest,
    ConfirmedBill,
    ConfirmedBillItem,
    ExtractedBill,
    Person,
    PersonCreate,
    SplitResult,
)
from backend.app.services.calculator import UnassignedItemsError, calculate_split
from backend.app.services.extractor.workflow import run_extraction_pipeline
from backend.app.services.share import format_whatsapp_message, generate_whatsapp_share_url

router = APIRouter(tags=["bills"])


# ---------------------------------------------------------------------------
# Stage B: Bill Upload + AI Extraction
# ---------------------------------------------------------------------------

@router.post("/bills/upload", status_code=status.HTTP_201_CREATED)
async def upload_bill(
    files: list[UploadFile] = File(..., description="One or more images of the restaurant bill"),
    db: Session = Depends(get_db)
):
    """
    Accepts one or more photos of a restaurant bill, extracts line items and charges
    using the vision LLM pipeline (orchestrated with LangGraph), and persists the raw extraction.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No bill photos provided.")

    images: list[bytes] = []
    for file in files:
        content = await file.read()
        if content:
            images.append(content)

    if not images:
        raise HTTPException(status_code=400, detail="Uploaded files were empty.")

    try:
        extraction_result = await run_extraction_pipeline(images)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(exc)}"
        )

    # Initialize confirmed bill with stable unique IDs from extraction items
    confirmed_items = []
    for idx, itm in enumerate(extraction_result.bill.items):
        item_slug = itm.name.lower().replace(" ", "_")[:12]
        stable_id = f"item_{idx + 1}_{item_slug}_{uuid.uuid4().hex[:4]}"
        confirmed_items.append(
            ConfirmedBillItem(
                id=stable_id,
                name=itm.name,
                quantity=itm.quantity,
                price=Decimal(str(itm.price))
            )
        )

    initial_confirmed = ConfirmedBill(
        items=confirmed_items,
        subtotal=Decimal(str(extraction_result.bill.subtotal)),
        tax=Decimal(str(extraction_result.bill.tax)),
        service_charge=Decimal(str(extraction_result.bill.service_charge)),
        discount=Decimal(str(extraction_result.bill.discount)),
        total=Decimal(str(extraction_result.bill.total)),
    )

    bill_record = BillModel(
        id=str(uuid.uuid4()),
        share_token=str(uuid.uuid4()),
        status="extracted",
        raw_extraction=json.dumps(extraction_result.bill.model_dump()),
        confirmed_bill=json.dumps(initial_confirmed.model_dump(mode="json")),
        provenance=json.dumps(extraction_result.provenance.model_dump()),
    )
    db.add(bill_record)
    db.commit()
    db.refresh(bill_record)

    return {
        "bill_id": bill_record.id,
        "share_token": bill_record.share_token,
        "status": bill_record.status,
        "raw_extraction": extraction_result.bill,
        "initial_confirmed": initial_confirmed,
        "provenance": extraction_result.provenance,
    }


# ---------------------------------------------------------------------------
# Stage C: Human Review & Correction
# ---------------------------------------------------------------------------

@router.get("/bills/{bill_id}")
def get_bill(bill_id: str, db: Session = Depends(get_db)):
    """Retrieve bill details with raw extraction, confidences, and confirmed version."""
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    return {
        "id": bill.id,
        "status": bill.status,
        "share_token": bill.share_token,
        "raw_extraction": json.loads(bill.raw_extraction) if bill.raw_extraction else None,
        "confirmed_bill": json.loads(bill.confirmed_bill) if bill.confirmed_bill else None,
        "provenance": json.loads(bill.provenance) if bill.provenance else None,
        "created_at": bill.created_at.isoformat() if bill.created_at else None,
    }


@router.patch("/bills/{bill_id}")
def update_confirmed_bill(
    bill_id: str,
    update_data: ConfirmedBill,
    db: Session = Depends(get_db)
):
    """
    Submits human corrections for line items, taxes, discounts, and total.
    Maintains or generates stable unique IDs for all items.
    """
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Ensure all items have non-empty stable IDs
    sanitized_items = []
    for idx, itm in enumerate(update_data.items):
        item_id = itm.id if (itm.id and itm.id.strip()) else f"item_{idx + 1}_{uuid.uuid4().hex[:6]}"
        sanitized_items.append(
            ConfirmedBillItem(
                id=item_id,
                name=itm.name,
                quantity=itm.quantity,
                price=itm.price
            )
        )

    clean_confirmed = ConfirmedBill(
        items=sanitized_items,
        subtotal=update_data.subtotal,
        tax=update_data.tax,
        service_charge=update_data.service_charge,
        discount=update_data.discount,
        total=update_data.total
    )

    bill.confirmed_bill = json.dumps(clean_confirmed.model_dump(mode="json"))
    db.commit()

    return {"message": "Confirmed bill updated successfully", "confirmed_bill": clean_confirmed}


@router.post("/bills/{bill_id}/confirm")
def confirm_bill(bill_id: str, db: Session = Depends(get_db)):
    """Locks the bill as confirmed. Calculations can only be executed on confirmed bills."""
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    if not bill.confirmed_bill:
        raise HTTPException(status_code=400, detail="No confirmed bill items to lock.")

    bill.status = "confirmed"
    db.commit()

    return {
        "message": "Bill confirmed and locked for calculation",
        "bill_id": bill.id,
        "status": bill.status
    }


# ---------------------------------------------------------------------------
# Stage D: People & Assignment
# ---------------------------------------------------------------------------

@router.post("/bills/{bill_id}/people", status_code=status.HTTP_201_CREATED)
def add_people(
    bill_id: str,
    people_in: list[PersonCreate],
    db: Session = Depends(get_db)
):
    """Add participating people to the bill."""
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    if not people_in:
        raise HTTPException(status_code=400, detail="Must provide at least one person.")

    # Remove previous people and add new
    db.query(PersonModel).filter(PersonModel.bill_id == bill_id).delete()
    
    created_people = []
    for p in people_in:
        p_model = PersonModel(
            id=str(uuid.uuid4()),
            bill_id=bill_id,
            name=p.name.strip(),
            email=p.email.strip() if p.email else None,
            phone=p.phone.strip() if p.phone else None,
        )
        db.add(p_model)
        created_people.append(p_model)

    db.commit()

    return [
        Person(id=p.id, name=p.name, email=p.email, phone=p.phone)
        for p in created_people
    ]


@router.get("/bills/{bill_id}/people")
def get_people(bill_id: str, db: Session = Depends(get_db)):
    """Retrieve list of people associated with this bill."""
    people = db.query(PersonModel).filter(PersonModel.bill_id == bill_id).all()
    return [
        Person(id=p.id, name=p.name, email=p.email, phone=p.phone)
        for p in people
    ]


@router.post("/bills/{bill_id}/assignments")
def save_assignments(
    bill_id: str,
    payload: AssignmentCreate,
    db: Session = Depends(get_db)
):
    """
    Map each confirmed item's stable ID to the list of person IDs who shared it.
    """
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Clear prior assignments
    db.query(AssignmentModel).filter(AssignmentModel.bill_id == bill_id).delete()

    assignment_records = []
    for item_id, person_ids in payload.assignments.items():
        for pid in set(person_ids):
            assignment_records.append(
                AssignmentModel(
                    bill_id=bill_id,
                    item_id=item_id,
                    person_id=pid
                )
            )

    db.add_all(assignment_records)
    db.commit()

    return {"message": "Assignments saved", "count": len(assignment_records)}


@router.get("/bills/{bill_id}/assignments")
def get_assignments(bill_id: str, db: Session = Depends(get_db)):
    """Retrieve assignments dictionary keyed by stable item ID."""
    records = db.query(AssignmentModel).filter(AssignmentModel.bill_id == bill_id).all()
    assignments: dict[str, list[str]] = {}
    for r in records:
        assignments.setdefault(r.item_id, []).append(r.person_id)
    return {"assignments": assignments}


# ---------------------------------------------------------------------------
# Stage E: Split + Breakdown
# ---------------------------------------------------------------------------

@router.post("/bills/{bill_id}/calculate")
def calculate_bill_split(
    bill_id: str,
    req: CalculateRequest = CalculateRequest(),
    db: Session = Depends(get_db)
):
    """
    Runs the Stage A deterministic calculation engine against confirmed items + assignments.
    If unassigned items exist and acknowledge_unassigned is False, raises HTTP 409 Conflict.
    """
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    if bill.status not in ("confirmed", "calculated"):
        raise HTTPException(
            status_code=400,
            detail="Bill must be confirmed by the user before running calculation."
        )

    if not bill.confirmed_bill:
        raise HTTPException(status_code=400, detail="Confirmed bill data is missing.")

    confirmed_dict = json.loads(bill.confirmed_bill)
    confirmed_bill = ConfirmedBill.model_validate(confirmed_dict)

    people_records = db.query(PersonModel).filter(PersonModel.bill_id == bill_id).all()
    if not people_records:
        raise HTTPException(status_code=400, detail="Please add at least one person before calculating.")

    people = [
        Person(id=p.id, name=p.name, email=p.email, phone=p.phone)
        for p in people_records
    ]

    # Gather assignments
    assignment_records = db.query(AssignmentModel).filter(AssignmentModel.bill_id == bill_id).all()
    assignments: dict[str, list[str]] = {}
    for r in assignment_records:
        assignments.setdefault(r.item_id, []).append(r.person_id)

    try:
        result = calculate_split(
            confirmed_bill=confirmed_bill,
            people=people,
            assignments=assignments,
            acknowledge_unassigned=req.acknowledge_unassigned,
            bill_id=bill_id
        )
    except UnassignedItemsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "UNASSIGNED_ITEMS",
                "message": str(exc),
                "unassigned_items": [item.model_dump(mode="json") for item in exc.unassigned_items]
            }
        )

    # Persist calculation result
    existing_res = db.query(CalculationResultModel).filter(CalculationResultModel.bill_id == bill_id).first()
    result_json = json.dumps(result.model_dump(mode="json"))

    if existing_res:
        existing_res.result_data = result_json
    else:
        db.add(CalculationResultModel(bill_id=bill_id, result_data=result_json))

    bill.status = "calculated"
    db.commit()

    return result


@router.get("/bills/{bill_id}/breakdown")
def get_breakdown(bill_id: str, db: Session = Depends(get_db)):
    """Retrieve full per-person breakdown and validation alerts."""
    res_record = db.query(CalculationResultModel).filter(CalculationResultModel.bill_id == bill_id).first()
    if not res_record:
        raise HTTPException(
            status_code=404,
            detail="Breakdown not found. Please run calculation first."
        )

    data = json.loads(res_record.result_data)
    return SplitResult.model_validate(data)


# ---------------------------------------------------------------------------
# Stage F: Sharing
# ---------------------------------------------------------------------------

@router.get("/bills/{bill_id}/share/whatsapp")
def get_whatsapp_share_url_endpoint(
    bill_id: str,
    phone: Optional[str] = Query(None, description="Optional recipient phone number"),
    restaurant_name: Optional[str] = Query(None, description="Restaurant name for message header"),
    db: Session = Depends(get_db)
):
    """
    Generate formatted WhatsApp share text and wa.me URL for the bill's calculation.
    """
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    res_record = db.query(CalculationResultModel).filter(CalculationResultModel.bill_id == bill_id).first()
    if not res_record:
        raise HTTPException(status_code=400, detail="Bill has not been calculated yet.")

    data = json.loads(res_record.result_data)
    result = SplitResult.model_validate(data)

    share_url = f"{settings.FRONTEND_URL}/share/{bill.share_token}"
    message = format_whatsapp_message(result, share_url=share_url, restaurant_name=restaurant_name)
    wa_url = generate_whatsapp_share_url(message, phone=phone)

    return {
        "whatsapp_url": wa_url,
        "message_text": message,
        "share_url": share_url
    }


@router.get("/share/{token}")
def get_shareable_breakdown(token: str, db: Session = Depends(get_db)):
    """
    Secure, read-only breakdown view accessible via unguessable UUID4 token.
    Never exposes internal sequential IDs or editing capabilities.
    """
    bill = db.query(BillModel).filter(BillModel.share_token == token).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Shared bill breakdown not found or expired.")

    res_record = db.query(CalculationResultModel).filter(CalculationResultModel.bill_id == bill.id).first()
    if not res_record:
        raise HTTPException(status_code=404, detail="Breakdown has not been generated for this bill.")

    data = json.loads(res_record.result_data)
    split_result = SplitResult.model_validate(data)

    return {
        "status": "success",
        "share_token": token,
        "split_result": split_result,
        "created_at": bill.created_at.isoformat() if bill.created_at else None,
    }
