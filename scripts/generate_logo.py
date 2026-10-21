#!/usr/bin/env python3
"""
Generate high-resolution branding logo for AgentGreenHydrogen.
"""

from PIL import Image, ImageDraw, ImageFont
import math
from pathlib import Path


def generate_logo():
    width = 800
    height = 800
    image = Image.new("RGBA", (width, height), (6, 17, 24, 255))
    draw = ImageDraw.Draw(image)

    cx, cy = 400, 360

    # Background ambient circular glow
    for r in range(320, 150, -5):
        alpha = int(35 * (1 - (r - 150) / 170))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(6, 182, 212, alpha), width=3)

    # Hexagonal cage (representing molecular catalyst / electrolyzer cell stack)
    def draw_hex(radius, color, width=4):
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        draw.polygon(points, outline=color, width=width)

    draw_hex(220, (16, 185, 129, 90), width=3)
    draw_hex(180, (6, 182, 212, 160), width=4)

    # Core Hydrogen H2 molecules: 2 connected glowing atomic orbs
    orb1_x, orb1_y = cx - 75, cy
    orb2_x, orb2_y = cx + 75, cy
    orb_radius = 55

    # Connecting covalent bond
    draw.line([(orb1_x, orb1_y), (orb2_x, orb2_y)], fill=(16, 185, 129, 220), width=18)
    draw.line([(orb1_x, orb1_y), (orb2_x, orb2_y)], fill=(6, 182, 212, 255), width=8)

    # Orbs
    for ox, oy, tag in [(orb1_x, orb1_y, "H¹"), (orb2_x, orb2_y, "H²")]:
        for glow_r in range(orb_radius + 25, orb_radius, -2):
            draw.ellipse([ox - glow_r, oy - glow_r, ox + glow_r, oy + glow_r], outline=(16, 185, 129, 60), width=2)
        draw.ellipse([ox - orb_radius, oy - orb_radius, ox + orb_radius, oy + orb_radius], fill=(12, 30, 40, 255), outline=(6, 182, 212, 255), width=6)
        draw.ellipse([ox - orb_radius + 15, oy - orb_radius + 15, ox + orb_radius - 15, oy + orb_radius - 15], fill=(16, 185, 129, 230))

    # Electrolysis Spark / Lightning accent in center
    spark = [
        (cx - 15, cy - 80),
        (cx + 8, cy - 20),
        (cx - 5, cy - 10),
        (cx + 18, cy + 60),
        (cx - 4, cy + 10),
        (cx + 8, cy),
    ]
    draw.polygon(spark, fill=(234, 179, 8, 240))

    # Text Banner
    # Try default font
    try:
        font_title = ImageFont.truetype("arial.ttf", 46)
        font_sub = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((400, 640), "AGENT GREEN HYDROGEN", fill=(240, 253, 250, 255), font=font_title, anchor="mm")
    draw.text((400, 700), "ISO 14687 Purity & Clean Electrolysis Escrow", fill=(6, 182, 212, 255), font=font_sub, anchor="mm")
    draw.text((400, 735), "GenLayer StudioNet · Chain 61999", fill=(148, 163, 184, 200), font=font_sub, anchor="mm")

    out_path = Path(__file__).parent.parent / "logo.png"
    image.save(out_path, "PNG")
    print(f"[+] Successfully generated logo at {out_path}")


if __name__ == "__main__":
    generate_logo()
