import random
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

# Diverse pool of realistic vendors across industries
VENDORS = [
    # Technology & Cloud
    "Apex Cloud Solutions Pvt Ltd",
    "Nexus Digital Systems Inc",
    "Quantum Dynamics Infotech",
    "CyberCore Networks LLP",
    "Virtue Soft Technologies",
    "InfraTech Solutions Private Limited",
    # Logistics & Freight
    "TransGlobal Logistics Solutions",
    "RapidFreight Cargo Express",
    "BlueWave Maritime & Shipping",
    "Horizon Supply Chain Logistics",
    "MetroFleet Transport Carriers",
    # Industrial & Hardware
    "Titan Industrial Equipment Ltd",
    "Precision Tools & Dies Works",
    "Vortex Heavy Machinery Corp",
    "OmniTech Electrical Components",
    "Bharat Forgings & Engineering",
    # Professional & Business Services
    "Starlight Corporate Consulting",
    "Sterling Legal & Advisory LLP",
    "Catalyst Financial Advisory",
    "Summit Strategy Management Group",
    "Beacon Strategic Auditing Group",
    # Supplies & Retail
    "Prime Wholesale Stationery Supplies",
    "Modern Office Interiors Ltd",
    "EverGreen Paper & Packaging",
    "Pinnacle Commercial Supplies"
]

# Indian State Codes for GSTIN generation
STATE_CODES = [
    "01", "02", "03", "04", "06", "07", "08", "09", "10",  # North
    "19", "20", "21", "22", "23", "24",                     # East & Central
    "27", "29", "32", "33", "36", "37"                      # West & South
]

INVOICE_PREFIXES = ["INV", "BILL", "TAX-INV", "DOC", "REC", "INVOICE", "SI"]
CURRENCY_SYMBOLS = ["INR", "Rs.", "₹", "USD", "$", "EUR", "€"]

LINE_ITEMS_POOL = [
    ("Software Development Retainer", 15000.0, "HSN-998314", 1, 15000.0),
    ("Cloud Infrastructure Hosting", 8500.0, "HSN-998315", 2, 4250.0),
    ("Technical Support & Maintenance", 4200.0, "HSN-998712", 1, 4200.0),
    ("Industrial Fasteners Pack", 1850.0, "HSN-731815", 5, 370.0),
    ("Office Supplies & Printing Paper", 950.0, "HSN-480255", 10, 95.0),
    ("Management Advisory Fee", 22000.0, "HSN-998311", 1, 22000.0),
    ("Network Security Audit", 12500.0, "HSN-998313", 1, 12500.0),
    ("Hardware Maintenance Service", 3400.0, "HSN-998719", 2, 1700.0),
    ("Supply Chain Consulting", 17500.0, "HSN-998312", 1, 17500.0),
    ("Freight & Handling Charges", 2800.0, "HSN-996511", 1, 2800.0)
]


def generate_valid_gstin(state_code: str = None) -> str:
    """Generates a syntactically valid 15-character Indian GSTIN."""
    state = state_code or random.choice(STATE_CODES)
    pan_chars = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
    pan_digits = "".join(random.choices("0123456789", k=4))
    pan_last = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    entity_num = str(random.randint(1, 9))
    z_char = "Z"
    checksum_char = random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{state}{pan_chars}{pan_digits}{pan_last}{entity_num}{z_char}{checksum_char}"


def generate_invoice_number() -> str:
    """Generates varied realistic invoice numbers."""
    prefix = random.choice(INVOICE_PREFIXES)
    year = random.choice([2024, 2025, 2026])
    seq = random.randint(100, 99999)
    style = random.choice([
        f"{prefix}-{year}-{seq}",
        f"{prefix}/{year}/{seq}",
        f"{prefix}-{seq}",
        f"#{prefix}{seq}",
        f"{year}/{seq}",
        f"{prefix}/{seq}"
    ])
    return style


def generate_invoice_date() -> str:
    """Generates dates in varied common commercial formats."""
    base_date = datetime(2025, 1, 1)
    random_days = random.randint(0, 450)
    dt = base_date + timedelta(days=random_days)
    fmt = random.choice([
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%m/%d/%Y"
    ])
    return dt.strftime(fmt)


def generate_financial_amounts() -> Tuple[float, float, float]:
    """Generates consistent Subtotal, Tax Amount, and Total Amount."""
    subtotal = round(random.uniform(500.0, 50000.0), 2)
    tax_rate = random.choice([0.05, 0.12, 0.18, 0.28])
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total


def jitter(val: float, delta: float = 0.015, min_val: float = 0.01, max_val: float = 0.99) -> float:
    """Adds small random noise to bounding box coordinates to simulate OCR variance."""
    j = val + random.uniform(-delta, delta)
    return round(min(max_val, max(min_val, j)), 3)


def make_token(text: str, label: str, x1: float, y1: float, x2: float, y2: float) -> Dict[str, Any]:
    """Creates a normalized token dictionary with coordinate safety checks."""
    x1_c = min(x1, x2 - 0.01)
    y1_c = min(y1, y2 - 0.01)
    return {
        "text": text,
        "label": label,
        "bbox": {
            "x1": round(max(0.01, min(0.97, x1_c)), 3),
            "y1": round(max(0.01, min(0.97, y1_c)), 3),
            "x2": round(max(0.02, min(0.99, max(x1_c + 0.015, x2))), 3),
            "y2": round(max(0.02, min(0.99, max(y1_c + 0.015, y2))), 3)
        }
    }


def _build_layout_template_1(vendor_name: str, inv_num: str, inv_date: str, gstin: str, subtotal: float, tax: float, total: float) -> List[Dict[str, Any]]:
    """Template 1: Modern Corporate Two-Column Layout with Right Totals and Distractor Tokens."""
    tokens = []
    base_y = jitter(0.04, 0.01)

    # Header
    tokens.append(make_token("TAX", "O", jitter(0.44), base_y, jitter(0.49), base_y + 0.025))
    tokens.append(make_token("INVOICE", "O", jitter(0.50), base_y, jitter(0.58), base_y + 0.025))

    # Vendor Top-Left
    vx = jitter(0.07, 0.01)
    vy = base_y + jitter(0.05, 0.01)
    for w in vendor_name.split():
        w_len = len(w) * 0.014
        tokens.append(make_token(w, "VENDOR", vx, vy, vx + w_len, vy + 0.022))
        vx += w_len + 0.01

    # GSTIN below Vendor
    gy = vy + jitter(0.035, 0.005)
    tokens.append(make_token(random.choice(["GSTIN:", "GST:", "GSTIN No:"]), "O", jitter(0.07), gy, jitter(0.15), gy + 0.022))
    tokens.append(make_token(gstin, "GSTIN", jitter(0.16), gy, jitter(0.38), gy + 0.022))

    # Noise: Phone & PIN code
    py = gy + jitter(0.03, 0.004)
    tokens.append(make_token("Phone:", "O", jitter(0.07), py, jitter(0.13), py + 0.02))
    tokens.append(make_token(f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}", "O", jitter(0.14), py, jitter(0.32), py + 0.02))

    # Invoice No & Date Top-Right
    ny = vy
    tokens.append(make_token(random.choice(["Invoice No:", "Inv #:", "Bill No:"]), "O", jitter(0.60), ny, jitter(0.70), ny + 0.022))
    tokens.append(make_token(inv_num, "INVOICE_NUM", jitter(0.71), ny, jitter(0.91), ny + 0.022))

    dy = gy
    tokens.append(make_token(random.choice(["Date:", "Dated:", "Invoice Date:"]), "O", jitter(0.60), dy, jitter(0.68), dy + 0.022))
    tokens.append(make_token(inv_date, "DATE", jitter(0.69), dy, jitter(0.85), dy + 0.022))

    # Noise: PO Number and Payment Due Date (Distractor date & code)
    poy = py
    tokens.append(make_token("PO Ref:", "O", jitter(0.60), poy, jitter(0.68), poy + 0.02))
    tokens.append(make_token(f"PO-{random.randint(10000, 99999)}", "O", jitter(0.69), poy, jitter(0.82), poy + 0.02))

    # Line item noise with quantities, rates, and HSN codes
    item = random.choice(LINE_ITEMS_POOL)
    iy = poy + jitter(0.06, 0.01)
    tokens.append(make_token("Item Description", "O", jitter(0.07), iy, jitter(0.22), iy + 0.02))
    tokens.append(make_token("HSN", "O", jitter(0.40), iy, jitter(0.48), iy + 0.02))
    tokens.append(make_token("Qty", "O", jitter(0.55), iy, jitter(0.60), iy + 0.02))
    tokens.append(make_token("Rate", "O", jitter(0.65), iy, jitter(0.72), iy + 0.02))
    tokens.append(make_token("Amount", "O", jitter(0.78), iy, jitter(0.86), iy + 0.02))

    row_y = iy + jitter(0.035, 0.005)
    tokens.append(make_token(item[0].split()[0], "O", jitter(0.07), row_y, jitter(0.25), row_y + 0.02))
    tokens.append(make_token(item[2], "O", jitter(0.38), row_y, jitter(0.50), row_y + 0.02))
    tokens.append(make_token(str(item[3]), "O", jitter(0.56), row_y, jitter(0.60), row_y + 0.02))
    tokens.append(make_token(f"{item[4]:.2f}", "O", jitter(0.64), row_y, jitter(0.74), row_y + 0.02))
    tokens.append(make_token(f"{item[1]:.2f}", "O", jitter(0.77), row_y, jitter(0.88), row_y + 0.02))

    # Financial totals bottom-right
    tot_y = jitter(0.66, 0.02)
    tokens.append(make_token(random.choice(["Subtotal:", "Sub-Total:", "Taxable Value:"]), "O", jitter(0.58), tot_y, jitter(0.70), tot_y + 0.022))
    tokens.append(make_token(f"{subtotal:.2f}", "SUBTOTAL", jitter(0.73), tot_y, jitter(0.87), tot_y + 0.022))

    tax_y = tot_y + jitter(0.04, 0.005)
    tax_lbl = random.choice(["Tax (18%):", "GST:", "IGST:", "Output Tax:"])
    tokens.append(make_token(tax_lbl, "O", jitter(0.58), tax_y, jitter(0.70), tax_y + 0.022))
    tokens.append(make_token(f"{tax:.2f}", "TAX", jitter(0.73), tax_y, jitter(0.87), tax_y + 0.022))

    grand_y = tax_y + jitter(0.045, 0.005)
    tot_lbl = random.choice(["Total Amount:", "Grand Total:", "Total Payable:", "Total:"])
    tokens.append(make_token(tot_lbl, "O", jitter(0.58), grand_y, jitter(0.72), grand_y + 0.022))
    tokens.append(make_token(f"{total:.2f}", "TOTAL", jitter(0.73), grand_y, jitter(0.90), grand_y + 0.022))

    return tokens


def _build_layout_template_2(vendor_name: str, inv_num: str, inv_date: str, gstin: str, subtotal: float, tax: float, total: float) -> List[Dict[str, Any]]:
    """Template 2: Minimalist Centered Header with Left-Aligned Metadata and Distractors."""
    tokens = []
    base_y = jitter(0.05, 0.01)

    # Vendor Centered
    v_words = vendor_name.split()
    vx = max(0.20, 0.50 - (len(vendor_name) * 0.012) / 2)
    for w in v_words:
        w_len = len(w) * 0.014
        tokens.append(make_token(w, "VENDOR", vx, base_y, vx + w_len, base_y + 0.024))
        vx += w_len + 0.01

    # Centered GSTIN
    gy = base_y + jitter(0.035, 0.005)
    tokens.append(make_token("GSTIN", "O", jitter(0.36), gy, jitter(0.43), gy + 0.02))
    tokens.append(make_token(gstin, "GSTIN", jitter(0.44), gy, jitter(0.68), gy + 0.02))

    # Left-aligned Invoice & Date
    ny = gy + jitter(0.045, 0.005)
    tokens.append(make_token("INVOICE:", "O", jitter(0.08), ny, jitter(0.18), ny + 0.022))
    tokens.append(make_token(inv_num, "INVOICE_NUM", jitter(0.19), ny, jitter(0.40), ny + 0.022))

    tokens.append(make_token("DATE:", "O", jitter(0.60), ny, jitter(0.68), ny + 0.022))
    tokens.append(make_token(inv_date, "DATE", jitter(0.69), ny, jitter(0.86), ny + 0.022))

    # Noise: Due Date distractor
    due_y = ny + jitter(0.035, 0.005)
    tokens.append(make_token("Due Date:", "O", jitter(0.60), due_y, jitter(0.69), due_y + 0.02))
    tokens.append(make_token("28/02/2026", "O", jitter(0.70), due_y, jitter(0.85), due_y + 0.02))

    # Items Noise
    item_y = due_y + jitter(0.06, 0.01)
    tokens.append(make_token("Professional Services", "O", jitter(0.08), item_y, jitter(0.35), item_y + 0.022))
    tokens.append(make_token(f"Rate: {subtotal*0.5:.2f}", "O", jitter(0.55), item_y, jitter(0.72), item_y + 0.022))

    # Financial totals
    tot_y = jitter(0.56, 0.02)
    tokens.append(make_token("Subtotal:", "O", jitter(0.55), tot_y, jitter(0.68), tot_y + 0.022))
    tokens.append(make_token(f"{subtotal:.2f}", "SUBTOTAL", jitter(0.70), tot_y, jitter(0.85), tot_y + 0.022))

    tax_y = tot_y + jitter(0.04, 0.005)
    tokens.append(make_token("Taxes:", "O", jitter(0.55), tax_y, jitter(0.68), tax_y + 0.022))
    tokens.append(make_token(f"{tax:.2f}", "TAX", jitter(0.70), tax_y, jitter(0.85), tax_y + 0.022))

    grand_y = tax_y + jitter(0.04, 0.005)
    tokens.append(make_token("Grand Total:", "O", jitter(0.55), grand_y, jitter(0.69), grand_y + 0.024))
    tokens.append(make_token(f"{total:.2f}", "TOTAL", jitter(0.70), grand_y, jitter(0.88), grand_y + 0.024))

    return tokens


def _build_layout_template_3(vendor_name: str, inv_num: str, inv_date: str, gstin: str, subtotal: float, tax: float, total: float) -> List[Dict[str, Any]]:
    """Template 3: Corporate Boxed Grid with Right-Aligned Header Metadata."""
    tokens = []
    base_y = jitter(0.04, 0.01)

    # Vendor Top-Left
    vx = jitter(0.08, 0.01)
    for w in vendor_name.split():
        w_len = len(w) * 0.014
        tokens.append(make_token(w, "VENDOR", vx, base_y, vx + w_len, base_y + 0.022))
        vx += w_len + 0.01

    tokens.append(make_token("Tax Invoice", "O", jitter(0.65), base_y, jitter(0.80), base_y + 0.022))

    ny = base_y + jitter(0.035, 0.005)
    tokens.append(make_token("Invoice #", "O", jitter(0.60), ny, jitter(0.70), ny + 0.022))
    tokens.append(make_token(inv_num, "INVOICE_NUM", jitter(0.71), ny, jitter(0.92), ny + 0.022))

    dy = ny + jitter(0.035, 0.005)
    tokens.append(make_token("Issue Date:", "O", jitter(0.60), dy, jitter(0.70), dy + 0.022))
    tokens.append(make_token(inv_date, "DATE", jitter(0.71), dy, jitter(0.88), dy + 0.022))

    gy = dy + jitter(0.035, 0.005)
    tokens.append(make_token("GST Number:", "O", jitter(0.60), gy, jitter(0.72), gy + 0.022))
    tokens.append(make_token(gstin, "GSTIN", jitter(0.73), gy, jitter(0.95), gy + 0.022))

    # Bill-To Box on Left with PAN / City noise
    tokens.append(make_token("Billed To:", "O", jitter(0.08), dy, jitter(0.18), dy + 0.022))
    tokens.append(make_token("Enterprise Client Ltd", "O", jitter(0.08), gy, jitter(0.35), gy + 0.022))
    tokens.append(make_token("PAN: AABCE8921M", "O", jitter(0.08), gy + 0.03, jitter(0.28), gy + 0.05))

    # Totals bottom
    tot_y = jitter(0.72, 0.02)
    tokens.append(make_token("Net Amount:", "O", jitter(0.58), tot_y, jitter(0.72), tot_y + 0.022))
    tokens.append(make_token(f"{subtotal:.2f}", "SUBTOTAL", jitter(0.74), tot_y, jitter(0.88), tot_y + 0.022))

    tax_y = tot_y + jitter(0.04, 0.005)
    tokens.append(make_token("GST Amount:", "O", jitter(0.58), tax_y, jitter(0.72), tax_y + 0.022))
    tokens.append(make_token(f"{tax:.2f}", "TAX", jitter(0.74), tax_y, jitter(0.88), tax_y + 0.022))

    grand_y = tax_y + jitter(0.045, 0.005)
    tokens.append(make_token("Final Total:", "O", jitter(0.58), grand_y, jitter(0.72), grand_y + 0.022))
    tokens.append(make_token(f"{total:.2f}", "TOTAL", jitter(0.74), grand_y, jitter(0.90), grand_y + 0.022))

    return tokens


def _build_layout_template_4(vendor_name: str, inv_num: str, inv_date: str, gstin: str, subtotal: float, tax: float, total: float) -> List[Dict[str, Any]]:
    """Template 4: Compact / Retail POS Service Invoice (Totals appear around y: 0.40 - 0.55)."""
    tokens = []
    base_y = jitter(0.03, 0.008)

    # Vendor Top
    vx = jitter(0.10, 0.01)
    for w in vendor_name.split():
        w_len = len(w) * 0.014
        tokens.append(make_token(w, "VENDOR", vx, base_y, vx + w_len, base_y + 0.022))
        vx += w_len + 0.01

    gy = base_y + jitter(0.03, 0.005)
    tokens.append(make_token("GST:", "O", jitter(0.10), gy, jitter(0.16), gy + 0.02))
    tokens.append(make_token(gstin, "GSTIN", jitter(0.17), gy, jitter(0.40), gy + 0.02))

    ny = gy + jitter(0.035, 0.005)
    tokens.append(make_token("Bill #:", "O", jitter(0.10), ny, jitter(0.18), ny + 0.02))
    tokens.append(make_token(inv_num, "INVOICE_NUM", jitter(0.19), ny, jitter(0.40), ny + 0.02))

    tokens.append(make_token("Date:", "O", jitter(0.55), ny, jitter(0.63), ny + 0.02))
    tokens.append(make_token(inv_date, "DATE", jitter(0.64), ny, jitter(0.82), ny + 0.02))

    # Noise item with barcode / batch
    row_y = ny + jitter(0.045, 0.005)
    tokens.append(make_token("Batch #98214", "O", jitter(0.10), row_y, jitter(0.28), row_y + 0.02))
    tokens.append(make_token("Qty: 1", "O", jitter(0.32), row_y, jitter(0.42), row_y + 0.02))
    tokens.append(make_token(f"Rate: {subtotal:.2f}", "O", jitter(0.50), row_y, jitter(0.68), row_y + 0.02))

    # Financial totals appear much earlier (compact receipt)
    tot_y = jitter(0.42, 0.015)
    tokens.append(make_token("Subtotal:", "O", jitter(0.50), tot_y, jitter(0.65), tot_y + 0.022))
    tokens.append(make_token(f"{subtotal:.2f}", "SUBTOTAL", jitter(0.68), tot_y, jitter(0.85), tot_y + 0.022))

    tax_y = tot_y + jitter(0.035, 0.005)
    tokens.append(make_token("Tax:", "O", jitter(0.50), tax_y, jitter(0.65), tax_y + 0.022))
    tokens.append(make_token(f"{tax:.2f}", "TAX", jitter(0.68), tax_y, jitter(0.85), tax_y + 0.022))

    grand_y = tax_y + jitter(0.038, 0.005)
    tokens.append(make_token("Total:", "O", jitter(0.50), grand_y, jitter(0.65), grand_y + 0.024))
    tokens.append(make_token(f"{total:.2f}", "TOTAL", jitter(0.68), grand_y, jitter(0.88), grand_y + 0.024))

    return tokens


LAYOUT_BUILDERS = [
    _build_layout_template_1,
    _build_layout_template_2,
    _build_layout_template_3,
    _build_layout_template_4
]


def generate_synthetic_invoice_document(vendor_name: str, doc_index: int = 1) -> Dict[str, Any]:
    """
    Generates a single synthetic invoice with multi-layout templates,
    distractor tokens, bounding box jitter, and ground truth token labels.
    """
    inv_num = generate_invoice_number()
    inv_date = generate_invoice_date()
    gstin = generate_valid_gstin()
    subtotal, tax, total = generate_financial_amounts()

    ground_truth = {
        "vendor_name": vendor_name,
        "invoice_number": inv_num,
        "invoice_date": inv_date,
        "gstin": gstin,
        "subtotal": f"{subtotal:.2f}",
        "tax_amount": f"{tax:.2f}",
        "total_amount": f"{total:.2f}"
    }

    # Select random layout template
    layout_builder = random.choice(LAYOUT_BUILDERS)
    tokens = layout_builder(vendor_name, inv_num, inv_date, gstin, subtotal, tax, total)

    # Sort tokens naturally by vertical flow, then horizontal
    tokens.sort(key=lambda t: (round(t["bbox"]["y1"], 2), t["bbox"]["x1"]))
    for i, t in enumerate(tokens):
        t["confidence"] = round(random.uniform(0.91, 1.0), 3)
        t["page_number"] = 1
        t["line_number"] = i // 3

    return {
        "document_id": f"synthetic_{doc_index}",
        "vendor_name": vendor_name,
        "ground_truth": ground_truth,
        "tokens": tokens,
        "full_text": " ".join(t["text"] for t in tokens)
    }


def generate_dataset(total_documents: int = 250) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates a full synthetic dataset with Train (70%), Validation (15%),
    and Test (15%) splits, ensuring vendors are isolated across splits
    to prevent template overfitting and data leakage.
    """
    random.seed(42)
    shuffled_vendors = list(VENDORS)
    random.shuffle(shuffled_vendors)

    n_vendors = len(shuffled_vendors)
    train_end = int(n_vendors * 0.70)
    val_end = int(n_vendors * 0.85)

    train_vendors = shuffled_vendors[:train_end]
    val_vendors = shuffled_vendors[train_end:val_end]
    test_vendors = shuffled_vendors[val_end:]

    docs_per_split = {
        "train": int(total_documents * 0.70),
        "val": int(total_documents * 0.15),
        "test": total_documents - int(total_documents * 0.70) - int(total_documents * 0.15)
    }

    dataset = {"train": [], "val": [], "test": []}
    doc_idx = 1

    for split, vendors in [("train", train_vendors), ("val", val_vendors), ("test", test_vendors)]:
        count = docs_per_split[split]
        for _ in range(count):
            vendor = random.choice(vendors)
            doc = generate_synthetic_invoice_document(vendor, doc_idx)
            dataset[split].append(doc)
            doc_idx += 1

    return dataset


if __name__ == "__main__":
    data = generate_dataset(100)
    print(f"Generated dataset splits: Train={len(data['train'])}, Val={len(data['val'])}, Test={len(data['test'])}")
