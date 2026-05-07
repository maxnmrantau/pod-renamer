"""Generate app icon for POD Renamer."""
from PIL import Image, ImageDraw, ImageFont
import os

SIZES = [16, 32, 48, 64, 128, 256]

def create_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 8
    r = size // 6

    # Background: rounded rectangle (package box)
    box_color = (137, 180, 250)  # blue
    draw.rounded_rectangle(
        [margin, margin + size//6, size - margin, size - margin],
        radius=r, fill=box_color
    )

    # Top flap
    flap_color = (116, 199, 236)  # lighter blue
    draw.polygon([
        (margin, margin + size//6),
        (size//2, margin),
        (size - margin, margin + size//6),
    ], fill=flap_color)

    # Label on box
    label_color = (30, 30, 46)  # dark
    label_margin = size // 4
    label_top = size // 3
    draw.rounded_rectangle(
        [label_margin, label_top, size - label_margin, size - margin - size//10],
        radius=r//2, fill=label_color
    )

    # Text "POD" on label
    try:
        font_size = size // 5
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "POD"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = label_top + (size - label_top - margin - size//10 - label_top - th) // 2
    draw.text((tx, ty), text, fill=(166, 227, 161), font=font)  # green text

    return img


def main():
    icons = []
    for s in SIZES:
        icons.append(create_icon(s))

    output_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    icons[0].save(output_path, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Icon saved: {output_path}")


if __name__ == "__main__":
    main()
