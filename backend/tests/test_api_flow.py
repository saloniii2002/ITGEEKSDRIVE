import io
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import Base, engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    original_force_mock = settings.FORCE_MOCK_EXTRACTOR
    settings.FORCE_MOCK_EXTRACTOR = True
    Base.metadata.create_all(bind=engine)
    yield
    settings.FORCE_MOCK_EXTRACTOR = original_force_mock
    # Cleanup tables after test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_full_bill_splitter_api_flow(client: TestClient):
    """
    End-to-end test verifying:
    1. Bill image upload & extraction (Stage B)
    2. Retrieve bill with confidence scores (Stage C)
    3. Human review & correction with PATCH (Stage C)
    4. Confirm and lock bill (Stage C)
    5. Add people (Stage D)
    6. Assign items to people using stable item IDs (Stage D)
    7. Attempt calculation with unassigned item -> verify 409 Conflict
    8. Calculate with acknowledge_unassigned=True (Stage E)
    9. Fetch breakdown (Stage E)
    10. Generate WhatsApp share link (Stage F)
    11. Verify secure read-only access via unguessable share_token (Stage F)
    """

    # 1. Upload bill photo(s)
    fake_image_file = io.BytesIO(b"fake_receipt_image_binary_data")
    files = [("files", ("receipt.jpg", fake_image_file, "image/jpeg"))]
    upload_res = client.post("/bills/upload", files=files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    bill_id = upload_data["bill_id"]
    share_token = upload_data["share_token"]
    assert bill_id
    assert share_token
    assert upload_data["status"] == "extracted"
    assert len(upload_data["raw_extraction"]["items"]) > 0

    # 2. GET /bills/{id}
    get_res = client.get(f"/bills/{bill_id}")
    assert get_res.status_code == 200
    bill_detail = get_res.json()
    assert bill_detail["id"] == bill_id
    raw_items = bill_detail["raw_extraction"]["items"]
    assert all("confidence" in itm for itm in raw_items)

    # 3. PATCH /bills/{id} - Human review & correction
    confirmed = bill_detail["confirmed_bill"]
    assert confirmed is not None
    # Let's adjust price of the first item to ₹500 and verify stable ID is preserved
    confirmed["items"][0]["price"] = "500.00"
    confirmed["items"][0]["name"] = "Special Butter Chicken"
    patch_res = client.patch(f"/bills/{bill_id}", json=confirmed)
    assert patch_res.status_code == 200
    updated_confirmed = patch_res.json()["confirmed_bill"]
    assert updated_confirmed["items"][0]["name"] == "Special Butter Chicken"
    assert updated_confirmed["items"][0]["price"] == "500.00"
    
    # Verify calculation fails on unconfirmed bill
    calc_fail = client.post(f"/bills/{bill_id}/calculate", json={"acknowledge_unassigned": False})
    assert calc_fail.status_code == 400

    # 4. POST /bills/{id}/confirm - Lock bill
    confirm_res = client.post(f"/bills/{bill_id}/confirm")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"

    # 5. POST /bills/{id}/people - Add 3 people
    people_payload = [
        {"name": "Alice", "email": "alice@example.com", "phone": "+919876543210"},
        {"name": "Bob", "email": "bob@example.com"},
        {"name": "Charlie"}
    ]
    people_res = client.post(f"/bills/{bill_id}/people", json=people_payload)
    assert people_res.status_code == 201
    people = people_res.json()
    assert len(people) == 3
    alice_id = next(p["id"] for p in people if p["name"] == "Alice")
    bob_id = next(p["id"] for p in people if p["name"] == "Bob")
    charlie_id = next(p["id"] for p in people if p["name"] == "Charlie")

    # 6. POST /bills/{id}/assignments - Assign items using stable item IDs
    all_items = updated_confirmed["items"]
    item_0_id = all_items[0]["id"]
    item_1_id = all_items[1]["id"]
    # Leave item_2, item_3, item_4 UNASSIGNED to test conflict detection!
    assignments_payload = {
        "assignments": {
            item_0_id: [alice_id, bob_id],        # Shared between Alice & Bob
            item_1_id: [alice_id, bob_id, charlie_id]  # Shared among all three
        }
    }
    assign_res = client.post(f"/bills/{bill_id}/assignments", json=assignments_payload)
    assert assign_res.status_code == 200

    # 7. POST /bills/{id}/calculate with acknowledge_unassigned=False -> MUST return 409 Conflict
    conflict_res = client.post(f"/bills/{bill_id}/calculate", json={"acknowledge_unassigned": False})
    assert conflict_res.status_code == 409
    conflict_body = conflict_res.json()["detail"]
    assert conflict_body["error"] == "UNASSIGNED_ITEMS"
    assert len(conflict_body["unassigned_items"]) > 0

    # 8. POST /bills/{id}/calculate with acknowledge_unassigned=True -> Succeeds with warnings
    calc_ok_res = client.post(f"/bills/{bill_id}/calculate", json={"acknowledge_unassigned": True})
    assert calc_ok_res.status_code == 200
    calc_result = calc_ok_res.json()
    assert len(calc_result["persons"]) == 3
    assert len(calc_result["unassigned_items"]) > 0
    assert any("Notice:" in w and "unassigned" in w for w in calc_result["warnings"])

    # 9. GET /bills/{id}/breakdown
    breakdown_res = client.get(f"/bills/{bill_id}/breakdown")
    assert breakdown_res.status_code == 200
    breakdown = breakdown_res.json()
    assert breakdown["bill_id"] == bill_id
    assert len(breakdown["persons"]) == 3

    # 10. GET /bills/{id}/share/whatsapp
    wa_res = client.get(f"/bills/{bill_id}/share/whatsapp?restaurant_name=Punjab+Grill")
    assert wa_res.status_code == 200
    wa_data = wa_res.json()
    assert "https://wa.me/?text=" in wa_data["whatsapp_url"]
    assert "Punjab Grill" in wa_data["message_text"]

    # 11. GET /share/{token} - Read-only view via unguessable share_token
    share_res = client.get(f"/share/{share_token}")
    assert share_res.status_code == 200
    share_data = share_res.json()
    assert share_data["status"] == "success"
    assert share_data["split_result"]["bill_id"] == bill_id

    # Verify invalid share token returns 404
    bad_share = client.get("/share/non-existent-token-12345")
    assert bad_share.status_code == 404
