"""
Generate placeholder PNG assets for the Bookstocker UI using Pillow.
Run:
    python tools/generate_placeholders.py
It will create files under `assets/` with the recommended names and sizes.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "assets"
ICONS = {
    "logo.png": (320, 64),
    "icon_dashboard.png": (48, 48),
    "icon_inventory.png": (48, 48),
    "icon_orders.png": (48, 48),
    "icon_purchase.png": (48, 48),
    "icon_reporting.png": (48, 48),
    "icon_support.png": (48, 48),
    "icon_settings.png": (48, 48),
    "icon_logout.png": (48, 48),
    "avatar.png": (64, 64),
    "icon_search.png": (24, 24),
    "icon_toggle.png": (24, 24),
    "icon_notifications.png": (24, 24),
    "stat_total.png": (48, 48),
    "stat_orders.png": (48, 48),
    "stat_stock.png": (48, 48),
    "stat_out.png": (48, 48),
    "btn_primary.png": (160, 40),
    "btn_secondary.png": (160, 40),
}

OUT.mkdir(parents=True, exist_ok=True)

try:
    font = ImageFont.load_default()
except Exception:
    font = None

for name, size in ICONS.items():
    path = OUT / name
    w, h = size
    img = Image.new("RGBA", (w, h), (200, 220, 230, 255))
    draw = ImageDraw.Draw(img)
    text = name.replace(".png", "")
    # center text
    if font:
        tw, th = draw.textsize(text, font=font)
    else:
        tw, th = draw.textsize(text)
    draw.text(((w - tw) / 2, (h - th) / 2), text, fill=(30, 40, 60), font=font)
    img.save(path)

print(f"Wrote {len(ICONS)} placeholder images to {OUT}")
