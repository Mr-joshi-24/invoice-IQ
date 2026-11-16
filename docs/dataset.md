# Invoice IQ — Dataset & Annotation Specifications

## 1. Overview

Invoice IQ utilizes a robust dataset synthesis pipeline combined with real-world Indian GST and international commercial invoice layouts. To maintain scientific rigor and prevent benchmark pollution, data synthesis explicitly prevents data leakage across train, validation, and test splits while simulating layout heterogeneity, spatial jitter, and realistic distractor tokens.

---

## 2. Multi-Layout Template Architecture

To prevent layout memorization, the data generator utilizes 4 distinct commercial invoice layout templates:

1. **Template 1: Modern Corporate Two-Column**:
   - Vendor entity and GSTIN situated in the top-left quadrant.
   - Invoice Number, Date, and PO Number stacked in the top-right quadrant.
   - Itemized table in the center with HSN codes, quantities, and unit rates.
   - Subtotal, Tax, and Grand Total right-aligned at the bottom ($y \approx 0.65 - 0.78$).
2. **Template 2: Minimalist Centered Header**:
   - Centered vendor title and centered GSTIN subtitle.
   - Left-aligned invoice metadata; right-aligned issue dates and payment due dates.
   - Financial totals positioned at $y \approx 0.55 - 0.68$.
3. **Template 3: Boxed Grid Enterprise Invoice**:
   - Vendor information on left with separate "Billed To" box.
   - Stacked right-hand metadata (Tax Invoice, Invoice #, Date, GST Number).
   - Bottom totals with currency prefixing at $y \approx 0.70 - 0.82$.
4. **Template 4: Compact / Retail POS Service Invoice**:
   - Single-column flow with vendor, GSTIN, Bill #, and Date compact header.
   - Financial totals appear early in the vertical document span ($y \approx 0.38 - 0.52$).

### Spatial Jitter & Noise Injection
- **Coordinate Jitter**: Bounding box coordinates receive random uniform noise ($\pm 0.015$ to $\pm 0.03$), preventing fixed-coordinate bin memorization.
- **Distractor Tokens**: Realistic background noise tokens labeled as `O`:
  - Contact details (Phone numbers: `+91 98123 45678`, PIN codes: `560001`, Email)
  - Distractor numbers and dates (Due dates, PO reference codes: `PO-89214`, HSN codes: `HSN-998314`, Unit quantities, Unit rates, Discounts).

---

## 3. Indian GSTIN Specifications

Indian Goods and Services Tax Identification Numbers (GSTIN) adhere to a 15-character alphanumeric format:
- **Digits 1–2**: State code (01 through 38, e.g., 27 for Maharashtra, 29 for Karnataka, 07 for Delhi).
- **Characters 3–12**: Permanent Account Number (PAN) of the business entity (5 uppercase letters, 4 digits, 1 uppercase letter).
- **Character 13**: Entity number of the same PAN holder in the state (1–9 or A–Z).
- **Character 14**: Default alphabet `'Z'`.
- **Character 15**: Checksum digit/letter.

---

## 4. Vendor Isolation & Zero-Leakage Split Strategy

To ensure genuine generalization:
- Synthetic invoice generation strictly isolates vendors across splits:
  - **Training Set (70%)**: Vendors 1–17
  - **Validation Set (15%)**: Vendors 18–20
  - **Test Set (15%)**: Vendors 21–24
- The classifier is tested exclusively on unseen vendor entities, ensuring that the model generalizes to new commercial suppliers without leaking layout styles.

---

## 5. Token Classification Schema

Each token in a document is assigned one of 8 distinct classes:

| Class Label | Description | Example Tokens |
| :--- | :--- | :--- |
| `VENDOR` | Commercial vendor or supplier name | Apex, CyberCore, Logistics, Ltd |
| `INVOICE_NUM` | Unique invoice/bill identifier | INV-2026-401, #BILL/8892 |
| `DATE` | Invoice issuance date | 15/03/2026, 2026-03-15 |
| `GSTIN` | 15-character tax identification | 29ABCDE1234F1Z5 |
| `SUBTOTAL` | Net taxable amount before tax | 5000.00, 12450.00 |
| `TAX` | Applicable GST / VAT amount | 900.00, 180.00 |
| `TOTAL` | Gross total payable amount | 5900.00, 14250.00 |
| `O` | Background text, labels, distractor rates, quantities | Description, Quantity, Rate, Due Date, Phone |
