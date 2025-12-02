# bot.py
import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont

def render_psd_to_png(psd_path, outputs, replacements, font_path, font_size=36, color=(0,0,0,255)):
    psd = PSDImage.open(psd_path)
    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, font_size)

    # replacements: {layer_name: text}
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            bbox = layer.bbox
            x, y = bbox.x1, bbox.y1
            draw.text((x, y), replacements[layer.name], font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"Saved PNG: {outputs['png']}")

if __name__ == "__main__":
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}
    replacements = {
        "Date": "Viernes, 28 de noviembre de 2025 a las 19:07 hs",
        "Sum": "$ 4.994.326",
        "clientName": "José Alberto González Contreras"
    }
    font_path = "assets/Arial.ttf"  # replace with your font
    render_psd_to_png(psd_path, outputs, replacements, font_path)
