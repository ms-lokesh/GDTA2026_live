import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings


def _receipt_dir() -> Path:
    target = Path(settings.MEDIA_ROOT)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _load_logo() -> Optional[Image.Image]:
    logo_candidates = [
        Path(settings.BASE_DIR) / "static" / "img" / "Logo" / "gdta_logo.png",
        Path(settings.BASE_DIR) / "static" / "img" / "Logo" / "gdta_main_logo.png",
        Path(settings.BASE_DIR) / "static" / "img" / "Logo" / "Screenshot 2026-01-24 143837.png",
    ]
    for path in logo_candidates:
        if path.exists():
            return Image.open(path).convert("RGBA")
    return None


def _font(size: int) -> ImageFont.ImageFont:
    return ImageFont.load_default()


def build_receipt_pdf(
    *,
    receipt_number: str,
    registrant_name: str,
    email: str,
    category: str,
    amount_paid: float,
    payment_method: str,
    transaction_id: str,
    payment_date: str,
    status: str,
) -> Dict[str, str]:
    # Render a simple, dependency-light PDF using Pillow so deployment stays easy.
    width, height = 1240, 1754  # A4-ish at 150 DPI
    canvas = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(canvas)

    title_font = _font(24)
    heading_font = _font(18)
    text_font = _font(14)

    draw.rectangle((40, 40, width - 40, height - 40), outline=(18, 18, 18), width=3)
    draw.rectangle((40, 40, width - 40, 220), fill=(245, 247, 250), outline=(18, 18, 18), width=2)

    logo = _load_logo()
    if logo:
        logo.thumbnail((180, 120))
        logo_x = 70
        logo_y = 70
        canvas.paste(logo, (logo_x, logo_y), logo)

    draw.text((280, 84), "GDTA 2026 PAYMENT RECEIPT", fill=(0, 0, 0), font=title_font)
    draw.text((280, 130), f"Receipt Number: {receipt_number}", fill=(0, 0, 0), font=heading_font)

    y = 290
    line_gap = 86
    rows = [
        ("Registrant Name", registrant_name),
        ("Email", email),
        ("Category", category),
        ("Amount Paid", f"INR {amount_paid:.2f}"),
        ("Payment Method", payment_method),
        ("Transaction ID", transaction_id),
        ("Payment Date", payment_date),
        ("Status", status),
    ]

    for label, value in rows:
        draw.text((90, y), f"{label}:", fill=(50, 50, 50), font=heading_font)
        draw.text((450, y), str(value or "-"), fill=(10, 10, 10), font=text_font)
        y += line_gap

    footer_y = height - 140
    draw.line((80, footer_y - 20, width - 80, footer_y - 20), fill=(180, 180, 180), width=2)
    draw.text((90, footer_y), "Thank you for registering for GDTA 2026.", fill=(70, 70, 70), font=text_font)

    safe_receipt = receipt_number.replace("/", "-").replace(" ", "")
    file_name = f"receipt_{safe_receipt}.pdf"
    output_path = _receipt_dir() / file_name

    canvas.save(output_path, format="PDF", resolution=150.0)

    return {
        "receipt_number": receipt_number,
        "receipt_file_path": str(output_path),
        "receipt_download_url": os.path.join(settings.MEDIA_URL.rstrip("/"), file_name),
    }
