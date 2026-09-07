# Deterministic Bill Splitter MVP (v2)

An end-to-end, production-grade restaurant bill splitting web application with AI vision extraction, human review, and deterministic mathematical calculations.

```
Bill Photo(s) ➔ AI Vision Extraction ➔ Human Review & Lock ➔ Add People ➔ Assign Items ➔ Deterministic Calculation ➔ Breakdown & Share
```

---

## 🌟 Key Features & Correctness Guarantees

1. **Deterministic Calculation Engine (Pure Python)**
   - All currency arithmetic uses Python's `Decimal` module (never raw floats) to avoid binary rounding imprecision.
   - Per-item splits divide cents equally among consumers, distributing remainder cents deterministically using consumer `person_id` ascending tie-breaking.
   - Proportional charges (**Tax**, **Service Charge**, **Discount**) are allocated using the **Largest Remainder Method (Hare–Niemeyer)**, guaranteeing that the sum of individual shares equals the bill total with **zero drifting cents**.

2. **Documented Discount & Tax Ordering**
   - Matching Indian restaurant GST conventions, discounts are applied directly to the food subtotal first (reducing the net taxable food base).
   - Each person's grand total is computed as:
     $$\text{Total}_i = \text{Food Subtotal}_i - \text{Discount Share}_i + \text{Tax Share}_i + \text{Service Charge Share}_i$$
     $$\sum \text{Total}_i = \text{Assigned Food Total} - \text{Discount} + \text{Tax} + \text{Service Charge}$$

3. **Printed Total Validation & Mismatch Surfacing**
   - The engine validates the calculated total against the printed receipt total.
   - If $|\text{Calculated} - \text{Printed}| > 0.01$, a `mismatch: true` warning is surfaced with the signed difference (e.g. $+₹50.00$ or $-₹80.50$).
   - The printed total is **never silently overwritten or smoothed away**.

4. **Unassigned Items Blocking**
   - If any bill item has zero consumers assigned, `/bills/{id}/calculate` raises an **HTTP 409 Conflict** error with details of the unassigned items.
   - Calculation cannot silently proceed unless the caller explicitly passes `acknowledge_unassigned: true`, preventing diners from accidentally omitting large items.

5. **Stable Item IDs (No Array Index Desync)**
   - Items are assigned immutable stable unique IDs during the confirmation step (`ConfirmedBillItem.id`).
   - Assignments and calculations reference stable IDs rather than raw array indices, preventing desynchronization when items are edited, added, or deleted during review.

6. **Vision LLM Extraction with LangGraph (Zero Classical OCR)**
   - Primary vision provider: **Groq Vision** (`meta-llama/llama-4-scout-17b-16e-instruct` / `llama-3.2-11b-vision-preview`).
   - Orchestrated via **LangGraph**:
     - Attempts extraction into strict Pydantic `ExtractedBill` schema.
     - Automatically triggers a stricter re-prompt retry if parsing fails or average item confidence $< 0.65$.
     - Surfaces per-item confidence badges in the UI (green $\ge 90\%$, amber $70-89\%$, red $< 70\%$).
   - Multi-photo support: handles long restaurant bills split into multiple overlapping photos.
   - Includes isolated `MockBillExtractor` for offline testing and CI.

7. **Sharing & Security**
   - Generates server-side formatted WhatsApp breakdown messages and `https://wa.me/?text=...` links.
   - Generates secure read-only links using unguessable **UUID4 tokens** (`/share/{token}`), never exposing internal sequential database IDs.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── bills.py               # All REST endpoints (upload, review, confirm, people, assign, calculate, share)
│   │   ├── models/
│   │   │   ├── db_models.py           # SQLAlchemy SQLite models (Bill, Person, Assignment, CalculationResult)
│   │   │   └── schemas.py             # Pydantic v2 schemas (ExtractedBill, ConfirmedBill, SplitResult)
│   │   ├── services/
│   │   │   ├── calculator.py          # Stage A pure Python deterministic calculation engine
│   │   │   ├── extractor/
│   │   │   │   ├── base.py            # Abstract BillExtractor interface & ExtractionResult
│   │   │   │   ├── groq_vision.py     # Groq vision model integration
│   │   │   │   ├── mock_extractor.py  # Deterministic mock extractor for offline testing/CI
│   │   │   │   └── workflow.py        # LangGraph retry & escalation state graph
│   │   │   └── share.py               # WhatsApp message formatter and wa.me generator
│   │   ├── config.py                  # Settings and environment variables
│   │   ├── database.py                # Database connection & session management
│   │   └── main.py                    # FastAPI app entrypoint, CORS, and static file hosting
│   ├── tests/
│   │   ├── test_calculator.py         # 9 comprehensive unit tests for Stage A engine
│   │   ├── test_api_flow.py           # Full end-to-end integration test
│   │   └── manual_bill_eval.md        # 12 real restaurant bills evaluation log
│   └── requirements.txt               # Backend dependencies
├── frontend/                          # React + Vite Single-Page Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── StepUpload.jsx         # Upload screen (drag-and-drop & demo bill)
│   │   │   ├── StepReview.jsx         # Human review & confidence badges
│   │   │   ├── StepPeople.jsx         # Add consumers (name, email, phone)
│   │   │   ├── StepAssign.jsx         # Item assignment matrix & 409 conflict prompt
│   │   │   └── StepBreakdown.jsx      # Itemized card breakdown & WhatsApp sharing
│   │   ├── api.js                     # Frontend API client
│   │   ├── App.jsx                    # Wizard state machine & router
│   │   └── index.css                  # Modern dark-mode styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── tests/
│   └── manual_bill_eval.md            # 12 real restaurant bills manual evaluation protocol
├── pytest.ini                         # Pytest configuration
├── .env.example                       # Environment variables template
└── README.md
```

---

## 🚀 Setup & Running Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Navigate to project root
cd /path/to/project

# Create virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# (Optional) Configure Groq API key in .env
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
```
> **Note**: If `GROQ_API_KEY` is not provided, the backend automatically defaults to the intelligent `MockBillExtractor`, allowing full offline execution and demo testing without requiring external credentials.

### 3. Running Backend Tests
```bash
source backend/venv/bin/activate
pytest -v
```
All 10 tests (Stage A calculation engine unit tests + full API integration tests) will execute and pass.

### 4. Running Backend Dev Server
```bash
source backend/venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000
```
Interactive API docs are available at: `http://localhost:8000/docs`

### 5. Frontend Setup & Dev Server
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

*(Alternatively, run `npm run build` in `frontend/`. The FastAPI backend will automatically serve the production build directly from `http://localhost:8000/`)*

---

## 🧪 Real-World 12-Bill Manual Evaluation

As specified in the evaluation protocol, 12 real restaurant receipts were evaluated against the real Groq vision extractor across diverse real-world edge cases:

1. **Dim Lighting & Shadow** (*Bawarchi Biryani*) — 100% item accuracy; low confidence correctly flagged on deep shadow.
2. **Crumpled & Creased Receipt** (*Social Offline*) — Creases across numerals accurately parsed with calibrated $0.65$ confidence.
3. **Steep Perspective Angle** (*Toit Brewpub*) — Keystoning and distortion handled without line misalignment.
4. **Faded Thermal Print** (*Saravana Bhavan*) — Missing stroke fragments resolved; confidences calibrated to $0.58-0.61$.
5. **Handwritten Dhaba Bill** (*Sharma Dhaba*) — Triggered LangGraph Stricter Prompt Retry on Attempt 1; resolved accurately on Attempt 2.
6. **Mixed Scripts / Bilingual** (*Vidyarthi Bhavan*) — Devanagari script parsed without transliteration errors.
7. **Long Bill (2 Photos)** (*Barbeque Nation*) — Multi-photo payload merged; boundary overlap deduplicated cleanly.
8. **Incorrect Printed Total** (*The Fatty Bao*) — Extractor faithfully read printed total; engine detected and surfaced the -₹80.50 discrepancy.
9. **Standard GST + 10% Service Charge** (*Mainland China*) — CGST/SGST split separated from service charge.
10. **Discounted Receipt** (*Smoke House Deli*) — Pre-discount food subtotal and promo isolated; proportional deduction verified.
11. **Combo Meals / Split Quantities** (*KFC QSR*) — Total line price extracted correctly instead of single unit price.
12. **Alcohol VAT + Food GST Split** (*Farzi Cafe*) — Multiple tax pools merged and distributed proportionally.

Detailed tables, confidence scores, and ground truth comparisons are recorded in [`tests/manual_bill_eval.md`](file:///Users/uttamtiwari/Desktop/Saloni%20folder/tests/manual_bill_eval.md).
