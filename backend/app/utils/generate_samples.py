import fitz  # PyMuPDF
from pathlib import Path


def create_invoice_pdf(
    filepath: Path,
    title: str,
    vendor: str,
    gstin: str,
    inv_num: str,
    inv_date: str,
    items: list,
    subtotal: float,
    tax_label: str,
    tax_amount: float,
    total_amount: float,
    notes: str = ""
):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Decorative header banner
    page.draw_rect(fitz.Rect(40, 40, 555, 95), color=(0.05, 0.45, 0.8), fill=(0.05, 0.45, 0.8))
    page.insert_text((55, 75), title.upper(), fontsize=20, color=(1, 1, 1))

    # Vendor Details (Left)
    page.insert_text((55, 125), vendor, fontsize=13, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((55, 145), f"GSTIN: {gstin}", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((55, 160), "Address: Plot 42, Tech Corridor Phase II, Industrial Area", fontsize=9, color=(0.4, 0.4, 0.4))
    page.insert_text((55, 175), "Email: billing@enterprisesolutions.com | Tel: +91 80 4455 6677", fontsize=9, color=(0.4, 0.4, 0.4))

    # Invoice Details (Right)
    page.insert_text((370, 125), f"Invoice No: {inv_num}", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((370, 145), f"Date: {inv_date}", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((370, 160), "Payment Terms: Net 30 Days", fontsize=9, color=(0.4, 0.4, 0.4))
    page.insert_text((370, 175), "Currency: Indian Rupee (INR)", fontsize=9, color=(0.4, 0.4, 0.4))

    # Divider
    page.draw_line(fitz.Point(40, 200), fitz.Point(555, 200), color=(0.8, 0.8, 0.8), width=1)

    # Table Header
    page.draw_rect(fitz.Rect(40, 215, 555, 240), color=(0.92, 0.94, 0.96), fill=(0.92, 0.94, 0.96))
    page.insert_text((50, 232), "Item Description", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((320, 232), "Qty", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((380, 232), "Unit Price", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((470, 232), "Amount (INR)", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))

    y = 260
    for desc, qty, price, amt in items:
        page.insert_text((50, y), desc, fontsize=9, color=(0.15, 0.15, 0.15))
        page.insert_text((325, y), str(qty), fontsize=9, color=(0.3, 0.3, 0.3))
        page.insert_text((380, y), f"{price:,.2f}", fontsize=9, color=(0.3, 0.3, 0.3))
        page.insert_text((470, y), f"{amt:,.2f}", fontsize=9, color=(0.15, 0.15, 0.15))
        page.draw_line(fitz.Point(40, y + 8), fitz.Point(555, y + 8), color=(0.93, 0.93, 0.93), width=0.5)
        y += 28

    # Financial Totals Section (Right Aligned)
    totals_y = max(y + 20, 480)
    page.draw_rect(fitz.Rect(320, totals_y - 10, 555, totals_y + 105), color=(0.96, 0.97, 0.98), fill=(0.96, 0.97, 0.98))

    page.insert_text((340, totals_y + 15), "Subtotal:", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((470, totals_y + 15), f"{subtotal:,.2f}", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))

    page.insert_text((340, totals_y + 45), f"Tax ({tax_label}):", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((470, totals_y + 45), f"{tax_amount:,.2f}", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))

    page.draw_line(fitz.Point(340, totals_y + 60), fitz.Point(545, totals_y + 60), color=(0.8, 0.8, 0.8), width=1)

    page.insert_text((340, totals_y + 85), "Total Amount:", fontsize=12, fontname="helv", color=(0.05, 0.3, 0.7))
    page.insert_text((470, totals_y + 85), f"{total_amount:,.2f}", fontsize=12, fontname="helv", color=(0.05, 0.3, 0.7))

    # Notes & Footer
    if notes:
        page.insert_text((50, totals_y + 20), "Auditor / Compliance Notes:", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
        page.insert_text((50, totals_y + 35), notes, fontsize=8, color=(0.5, 0.5, 0.5))

    page.insert_text((50, 780), "This is a computer generated invoice and requires no physical signature.", fontsize=8, color=(0.6, 0.6, 0.6))

    doc.save(str(filepath))
    doc.close()
    print(f"Generated sample invoice: {filepath}")


def generate_all_samples():
    out_dir = Path("data/sample_invoices")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean Standard Invoice
    create_invoice_pdf(
        filepath=out_dir / "01_clean_standard_invoice.pdf",
        title="Tax Invoice",
        vendor="Nexus Digital Systems Inc",
        gstin="27AABCN1234F1Z8",
        inv_num="INV-2026-4401",
        inv_date="15/03/2026",
        items=[
            ("Managed Cloud Hosting Dedicated Instance", 1, 6000.0, 6000.0),
            ("Database Backup & Recovery License", 2, 2000.0, 4000.0)
        ],
        subtotal=10000.0,
        tax_label="GST 18%",
        tax_amount=1800.0,
        total_amount=11800.0,
        notes="Standard commercial cloud services transaction."
    )

    # 2. Math Discrepancy Invoice (Expected: Warning/Review)
    create_invoice_pdf(
        filepath=out_dir / "02_math_discrepancy_invoice.pdf",
        title="Tax Invoice",
        vendor="Titan Industrial Equipment Ltd",
        gstin="29ABCDE1234F1Z5",
        inv_num="INV-2026-9022",
        inv_date="10/02/2026",
        items=[
            ("Heavy Duty Industrial Hydraulic Pumps", 1, 8500.0, 8500.0)
        ],
        subtotal=8500.0,
        tax_label="GST 18%",
        tax_amount=1530.0,
        total_amount=12000.0,  # Intentionally incorrect total (8500 + 1530 = 10030 != 12000)
        notes="Notice: Discrepancy between calculated total (10,030) and stated total (12,000)."
    )

    # 3. Tax Anomaly Invoice (Expected: Isolation Forest flag)
    create_invoice_pdf(
        filepath=out_dir / "03_tax_anomaly_invoice.pdf",
        title="Tax Invoice",
        vendor="Quantum Dynamics Infotech",
        gstin="33AABCQ9999F1Z2",
        inv_num="INV-2026-8104",
        inv_date="05/01/2026",
        items=[
            ("Specialized Cryptographic ASIC Module", 1, 4000.0, 4000.0)
        ],
        subtotal=4000.0,
        tax_label="Custom Surcharge 70%",
        tax_amount=2800.0,  # 70% tax rate, far exceeding normal brackets
        total_amount=6800.0,
        notes="Notice: High tax ratio of 70% will trigger Isolation Forest anomaly model."
    )

    # 4. Malformed GSTIN Invoice (Expected: GSTIN Validation Failure)
    create_invoice_pdf(
        filepath=out_dir / "04_malformed_gstin_invoice.pdf",
        title="Tax Invoice",
        vendor="Apex Cloud Solutions Pvt Ltd",
        gstin="99XYZ1234F",  # Invalid state code and wrong length (10 chars instead of 15)
        inv_num="INV-2026-7219",
        inv_date="20/02/2026",
        items=[
            ("Enterprise Software Seat Subscription", 4, 1250.0, 5000.0)
        ],
        subtotal=5000.0,
        tax_label="GST 18%",
        tax_amount=900.0,
        total_amount=5900.0,
        notes="Notice: Invalid GSTIN length and state code triggers validation alert."
    )


if __name__ == "__main__":
    generate_all_samples()

