import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Загружаем переменные окружения (например, TOKEN)
load_dotenv()

def render_psd_to_png(psd_path, outputs, replacements, font_path, font_size=36, color=(0, 0, 0, 255)):
    # Загружаем PSD
    psd = PSDImage.open(psd_path)
    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, font_size)

    # Проходим по слоям PSD
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            bbox = layer.bbox  # tuple (x1, y1, x2, y2)
            x, y = bbox[0], bbox[1]  # верхний левый угол
            text = replacements[layer.name]
            # Можно очистить область, если нужно:
            # draw.rectangle(bbox, fill=(255,255,255,0))
            draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"✅ PNG сохранён: {outputs['png']}")

if __name__ == "__main__":
    # Пути к файлам
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}
    font_path = "assets/Arial.ttf"

    # Данные для замены
    replacements = {
        "Date": "Viernes, 28 de noviembre de 2025 a las 19:07 hs",
        "Sum": "$ 4.994.326",
        "clientName": "José Alberto González Contreras"
    }

    render_psd_to_png(psd_path, outputs, replacements, font_path)
