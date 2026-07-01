"""Generate PWA PNG icons from TX BizFinder brand colors."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Install Pillow: pip install pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public"

BG = (16, 26, 48)
TEAL = (0, 245, 212)
COPPER = (232, 165, 92)
WHITE = (244, 247, 251)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)
    margin = int(size * 0.08)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.22),
        outline=TEAL,
        width=max(2, size // 48),
    )

    lens_r = int(size * 0.27)
    cx = int(size * 0.42)
    cy = int(size * 0.42)
    draw.ellipse(
        (cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r),
        outline=TEAL,
        width=max(3, size // 32),
    )

    font_size = int(size * 0.22)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    text = "TX"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2 - size * 0.02), text, fill=WHITE, font=font)

    hx0 = int(size * 0.62)
    hy0 = int(size * 0.62)
    hx1 = int(size * 0.86)
    hy1 = int(size * 0.86)
    draw.line((hx0, hy0, hx1, hy1), fill=COPPER, width=max(4, size // 24))

    dot_r = max(3, size // 40)
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=TEAL,
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    specs = {
        "pwa-192.png": 192,
        "pwa-512.png": 512,
        "apple-touch-icon.png": 180,
        "maskable-512.png": 512,
    }
    for name, size in specs.items():
        icon = draw_icon(size)
        if name.startswith("maskable"):
            # Extra padding for Android maskable safe zone
            padded = Image.new("RGBA", (size, size), BG + (255,))
            inner = int(size * 0.8)
            resized = icon.resize((inner, inner), Image.Resampling.LANCZOS)
            offset = (size - inner) // 2
            padded.paste(resized, (offset, offset), resized)
            icon = padded
        icon.save(OUT / name, format="PNG")
        print(f"Wrote {OUT / name}")


if __name__ == "__main__":
    main()