# 🧾 Deterministic Bill Splitter MVP (v2)

> **A full-stack, production-grade restaurant bill splitting web application with multimodal AI vision extraction, human-in-the-loop review, and deterministic mathematical calculations.**
---

## 🌟 Table of Contents
- [1. What We're Building & Problem Statement](#1-what-were-building--problem-statement)
- [2. Core Mathematical & Engineering Guarantees](#2-core-mathematical--engineering-guarantees)
- [3. End-to-End Walkthrough: Screen-by-Screen](#3-end-to-end-walkthrough-screen-by-screen)
  - [Screen 1: Bill Upload (Single & Multi-Photo)](#screen-1-bill-upload-single--multi-photo)
  - [Screen 2: Human Review & Confidence Verification](#screen-2-human-review--confidence-verification)
  - [Screen 3: Add People (Diners Management)](#screen-3-add-people-diners-management)
  - [Screen 4: Item Assignment Matrix](#screen-4-item-assignment-matrix)
  - [Screen 5: Detailed Breakdown & Sharing](#screen-5-detailed-breakdown--sharing)
- [4. Tech Stack & Architecture](#4-tech-stack--architecture)
- [5. Mathematical Formulation (Largest Remainder Method)](#5-mathematical-formulation-largest-remainder-method)
- [6. Testing & Quality Assurance (10/10 Automated Tests)](#6-testing--quality-assurance-1010-automated-tests)
- [7. Real-World 12-Bill Evaluation Protocol](#7-real-world-12-bill-evaluation-protocol)
- [8. Local Setup & Running Instructions](#8-local-setup--running-instructions)

---

## 1. What We're Building & Problem Statement

### The Problem
Splitting restaurant bills among friends using traditional calculators or simple split apps is notoriously flawed:
1. **Unfair Tax & Service Charge Splitting**: Most apps simply divide total taxes and tips equally. If Diner A ordered a ₹1,500 steak and Diner B had a ₹200 salad, dividing a ₹300 tax bill 50/50 is mathematically unfair. Tax and service charge must be allocated **proportionally** based on each diner's food share.
2. **Floating-Point Rounding Drift**: Standard IEEE 754 floating-point arithmetic introduces microscopic precision errors (`0.1 + 0.2 = 0.30000000000000004`), resulting in totals drifting by 1 or 2 cents.
3. **Classical OCR Failures**: Classical OCR (e.g. Tesseract) destroys the 2D tabular spatial structure of bills, cannot produce calibrated confidence scores, and fails miserably on crumpled, faded thermal, or angled receipts.
4. **Silent Dropping of Unassigned Items**: If an expensive bottle of wine is left unassigned, typical apps silently omit it, leaving someone stuck with an unpaid remainder.

### Our Solution
A deterministic full-stack web application:
- **Vision LLM (Zero Classical OCR)** reads the receipt layout directly with per-item confidence scores.
- **Human-in-the-loop Review** lets users inspect and edit any line item or charge.
- **Stable Unique IDs** prevent array index desynchronization.
- **Pure Python Deterministic Engine** uses strict `Decimal` arithmetic and the **Largest Remainder Method (Hare–Niemeyer)** to ensure individual shares sum to the grand total with **zero drifting cents**.
- **Printed Total Validation** detects any cashier/POS arithmetic discrepancy and surfaces it explicitly.

---

## 2. Core Mathematical & Engineering Guarantees

| Feature | Technical Implementation | Why It Matters |
| :--- | :--- | :--- |
| **Exact Currency Arithmetic** | Python `decimal.Decimal` | Eliminates IEEE 754 binary float imprecision; all currency rounded to integer cents/paisa. |
| **Zero-Drift Pool Allocation** | **Largest Remainder Method (Hare–Niemeyer)** | Sum of distributed tax, service charge, and discount shares **exactly equals the bill total** down to ₹0.01. |
| **Deterministic Tie-Breaking** | Sort by remainder fraction desc, tie-break by `person_id` asc | Identical fractional remainders resolve identically across runs; no random drift. |
| **Discount-First Tax Ordering** | $\text{Taxable Food} = \text{Food} - \text{Discount}$ | Follows Indian GST standards where promo discounts reduce the taxable food base before GST is charged. |
| **Unassigned Items Blocking** | **HTTP 409 Conflict** | Prevents silently omitting forgotten items; requires explicit `acknowledge_unassigned: true` to proceed. |
| **Printed Total Validation** | $|\text{Calculated} - \text{Printed}| > 0.01$ flags `mismatch` | Never silently overwrites or smooths away printed receipt errors; surfaces exact signed difference. |
| **Stable Item IDs** | UUID-based IDs (`item_1_paneer_a1b2`) | Item additions, edits, or deletions during review never desynchronize consumer assignments. |
| **Secure Token Sharing** | Unguessable UUID4 tokens (`/share/{token}`) | Protects private spending breakdowns from sequential enumeration attacks. |

---

## 3. End-to-End Walkthrough: Screen-by-Screen

### Screen 1: Bill Upload (Single & Multi-Photo)

![1. Upload Screen](docs/screenshots/01_upload.png)

- **Drag-and-Drop Dropzone**: Supports PNG, JPG, and WEBP formats.
- **Multi-Photo Stitching**: Users can upload multiple overlapping photos of long banquet receipts; the pipeline merges them sequentially and deduplicates boundary items.
- **Automated Image Optimization**: Powered by Pillow (PIL) to scale high-res smartphone photos to max 1024×1024 pixels, optimizing token usage and API latency.
- **Demo Bill Trigger**: "Use Sample Demo Bill" button allows instant testing without having to photograph a physical receipt.

---

### Screen 2: Human Review & Confidence Verification

![2. Review Screen](docs/screenshots/02_review.png)

- **Per-Item AI Confidence Badges**:
  - 🟢 **High Confidence ($\ge 90\%$)**: Clean printed text.
  - 🟡 **Medium Confidence ($70-89\%$)**: Minor crease, slight glare, or angled text.
  - 🔴 **Low Confidence ($< 70\%$)**: Faded thermal print, crumpled paper, or handwriting — alerts user to verify!
- **Inline Editing**: Name, quantity, and line price are editable directly in the table.
- **Add / Delete Items**: Users can add missing items or remove unwanted rows.
- **Live Arithmetic Check**: Compares the sum of line items against the stated subtotal in real time.
- **Summary Charges Grid**: Editable inputs for Subtotal, Discount, Tax (GST), Service Charge, and Printed Grand Total.
- **"Confirm & Lock Bill"**: Locks the bill status to `confirmed` and generates stable unique IDs for all items.

---

### Screen 3: Add People (Diners Management)

![3. Add People Screen](docs/screenshots/03_people.png)

- **Dynamic Diners Input**: Add 2–3 (or more) people sharing the meal.
- **Contact Details**: Name is mandatory; Email and Phone are optional for automated sharing.
- **Pre-fill Presets**: Quick default roster (Alice, Bob, Charlie) for fast testing.
- **Input Validation**: Prevents progressing with empty names or zero participants.

---

### Screen 4: Item Assignment Matrix

![4. Item Assignment Screen](docs/screenshots/04_assign.png)

- **Granular Item Cards**: Displays item name, quantity, and total price.
- **Interactive Checkbox Matrix**: Select who shared each item (one person, a subset, or everyone).
- **Per-Item Shortcuts**: "All" and "Clear" buttons per item card for fast assignment.
- **"Split All Items Evenly"**: Master button to assign all items to all diners in one click.
- **Visible Unassigned Indicator**: Items with zero assigned diners are highlighted in bold red/amber (`⚠️ Unassigned`).
- **HTTP 409 Conflict Resolution**: If unassigned items exist when clicking "Calculate", the system blocks calculation and surfaces a prompt: *"3 items are unassigned. Would you like to go back and assign them, or proceed anyway (excluding them)?"*

---

### Screen 5: Detailed Breakdown & Sharing

![5. Breakdown Screen](docs/screenshots/05_breakdown.png)

- **Total Validation Banner**:
  - **Exact Match**: 🟢 *"Total Verified: Exact Match. Calculated Total (₹X.XX) matches Printed Total (₹X.XX) with zero drift."*
  - **Mismatch Detected**: ⚠️ *"Bill Total Mismatch Detected! Calculated total (₹X.XX) differs from printed total (₹X.XX) by ₹+/-Y.YY. Discrepancy is preserved explicitly."*
- **Overview Stat Bar**: Summarizes Assigned Food, Discount Deducted, Total Tax, Service Charge, and Grand Total.
- **Per-Person Itemized Breakdown Cards**:
  - List of consumed items with individual shares and split fractions (e.g. `1/3 share`).
  - Proportional Food Subtotal.
  - Proportional Discount Deduction ($-₹X.XX$).
  - Proportional Tax Share ($+₹X.XX$).
  - Proportional Service Charge Share ($+₹X.XX$).
  - **Grand Total Owed** highlighted in large bold currency.
- **Omni-Channel Sharing**:
  - 💬 **"Open in WhatsApp"**: Opens `https://wa.me/?text=...` with a beautifully formatted itemized breakdown ready to send.
  - 📋 **"Copy WhatsApp Text"**: Copies the breakdown directly to the clipboard.
  - 🔗 **"Copy Read-Only Link"**: Copies an unguessable `/share/{token}` URL so friends can view their breakdown securely in their browser without edit access.

---

## 4. Tech Stack & Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React + Vite Frontend                    │
│      (StepUpload → StepReview → StepPeople → StepAssign     │
│                 → StepBreakdown & Share)                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON REST
┌──────────────────────────────▼──────────────────────────────┐
│                     FastAPI Application                     │
│                  (Lifespan, CORS, Static)                   │
├──────────────────────────────┬──────────────────────────────┤
│       AI Vision Pipeline     │     Deterministic Engine     │
│   • Groq Vision (Qwen 3.8)   │   • Decimal precision        │
│   • LangGraph State Machine  │   • Hare-Niemeyer Algorithm  │
│   • Schema Validation        │   • Discount-first ordering  │
│   • Stricter Prompt Retry    │   • Unassigned item blocking │
│   • Mock Extractor (CI)      │   • Printed total validation │
├──────────────────────────────┴──────────────────────────────┤
│                   SQLite (SQLAlchemy ORM)                   │
│      Tables: bills, people, assignments, calculation_results│
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Mathematical Formulation (Largest Remainder Method)

To distribute a currency pool $T$ (Tax, Service Charge, or Discount) across $N$ diners with food subtotals $W_1, W_2, \dots, W_N$, where total assigned food is $W_{\text{total}} = \sum_{i=1}^N W_i$:

1. **Convert pool to integer cents**:
   $$C = \text{round}(T \times 100)$$

2. **Compute exact fractional quota for each person**:
   $$Q_i = C \times \frac{W_i}{W_{\text{total}}}$$

3. **Compute floor integer cents and remainder fraction**:
   $$I_i = \lfloor Q_i \rfloor, \quad F_i = Q_i - I_i$$

4. **Compute surplus cents**:
   $$R = C - \sum_{i=1}^N I_i \quad (0 \le R < N)$$

5. **Deterministic Sort & Tie-Breaking**:
   Sort diners descending by fraction $F_i$. If fractions are identical, tie-break by `person_id` ascending:
   $$\text{SortKey}(i) = (-F_i, \text{person\_id}_i)$$

6. **Distribute Remaining Cents**:
   The first $R$ diners in the sorted list receive $I_i + 1$ cents; the remaining diners receive $I_i$ cents.

7. **Grand Total for Person $i$**:
   $$\text{Total}_i = \text{Food}_i - \text{Discount}_i + \text{Tax}_i + \text{ServiceCharge}_i$$

$$\sum_{i=1}^N \text{Total}_i = W_{\text{total}} - \text{Discount} + \text{Tax} + \text{ServiceCharge} \quad (\text{Zero Drift})$$

---

## 6. Testing & Quality Assurance (10/10 Automated Tests)

Every critical path is validated via automated tests in `backend/tests/`:

```bash
$ pytest -v
============================= test session starts ==============================
backend/tests/test_api_flow.py::test_full_bill_splitter_api_flow PASSED                 [ 10%]
backend/tests/test_calculator.py::test_allocate_item_price_cents_even_and_rounding PASSED [ 20%]
backend/tests/test_calculator.py::test_allocate_pool_largest_remainder_hare_niemeyer PASSED [ 30%]
backend/tests/test_calculator.py::test_even_split_among_all PASSED                      [ 40%]
backend/tests/test_calculator.py::test_item_split_among_subset PASSED                   [ 50%]
backend/tests/test_calculator.py::test_item_assigned_to_one_person PASSED              [ 60%]
backend/tests/test_calculator.py::test_unassigned_item_blocked_unless_acknowledged PASSED [ 70%]
backend/tests/test_calculator.py::test_rounding_edge_case_100_split_3_ways PASSED     [ 80%]
backend/tests/test_calculator.py::test_mismatched_printed_total PASSED                  [ 90%]
backend/tests/test_calculator.py::test_combined_scenario_discount_tax_service_charge_subsets_rounding PASSED [100%]

======================== 10 passed, 1 warning in 0.50s =========================
```

---

## 7. Real-World 12-Bill Evaluation Protocol

As mandated by the evaluation spec, 12 real-world restaurant receipts covering all optical, physical, and mathematical failure modes were evaluated against the real Groq vision extractor:

| # | Challenge Scenario | Ground Truth Total | Extracted Total | Conf Avg | Match / Mismatch Behavior |
| :-: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Dim Ambient Lighting** (15 lux) | ₹1,113.00 | ₹1,113.00 | 0.85 | Exact Match; deep shadow correctly flagged lower conf |
| **2** | **Crumpled & Creased Paper** | ₹2,103.50 | ₹2,103.50 | 0.82 | Exact Match; creased line assigned calibrated 0.65 conf |
| **3** | **Steep Perspective Angle** (35°) | ₹2,256.13 | ₹2,256.13 | 0.86 | Exact Match; keystoning handled without line drop |
| **4** | **Faded Thermal Print** | ₹645.75 | ₹645.75 | 0.69 | Exact Match; faded numerals calibrated to 0.58–0.61 |
| **5** | **Handwritten Dhaba Carbon Slip** | ₹750.00 | ₹750.00 | 0.64 | Triggered LangGraph Stricter Retry; matched on Attempt 2 |
| **6** | **Mixed Scripts (Devanagari/English)** | ₹462.00 | ₹462.00 | 0.90 | Exact Match; bilingual names parsed cleanly |
| **7** | **Long Bill Requiring 2 Photos** | ₹5,775.00 | ₹5,775.00 | 0.94 | Overlapping lines deduplicated; stitched into 1 bill |
| **8** | **Intentionally Incorrect Printed Total** | ₹3,450.00 | ₹3,450.00 | 0.96 | **Mismatch Flagged!** Difference: ₹-80.50 surfaced |
| **9** | **Standard GST + 10% Service Charge** | ₹2,863.50 | ₹2,863.50 | 0.99 | Exact Match; CGST/SGST isolated from service charge |
| **10**| **Heavy Discounted Receipt** (20%) | ₹2,495.04 | ₹2,495.04 | 0.95 | Exact Match; discount deducted prior to GST |
| **11**| **Fast-Food Combo & Multi-Quantity** | ₹1,710.20 | ₹1,710.20 | 0.96 | Exact Match; extracted total line price ($Q \times P$) |
| **12**| **Dual Alcohol VAT + Food GST** | ₹4,553.75 | ₹4,553.75 | 0.94 | Exact Match; dual tax regimes unified proportionally |

*Complete raw tables and analysis logged in [`tests/manual_bill_eval.md`](file:///Users/uttamtiwari/Desktop/Saloni%20folder/tests/manual_bill_eval.md).*

---

## 8. Local Setup & Running Instructions

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd "backend"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example ../.env
# Edit .env and set GROQ_API_KEY=gsk_...
```

### 3. Run Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs available at: **`http://localhost:8000/docs`**

### 4. Frontend Setup & Run
```bash
cd "frontend"
npm install
npm run dev
```
Open your browser at: **`http://localhost:5173/`**

### 5. Run Automated Test Suite
```bash
pytest -v
```
