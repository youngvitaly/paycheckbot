import os
import random
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

load_dotenv()

# Список латамовских имён для генерации
LATAM_NAMES = [
    "José Alberto González Contreras",
    "María Fernanda López Ramírez",
    "Carlos Eduardo Pérez Díaz",
    "Ana Sofía Rodríguez Martínez",
    "Juan Manuel Torres Castillo",
    "Lucía Valentina Herrera Gómez",
    "Miguel Ángel Sánchez Vargas",
    "Camila Alejandra Morales Ríos",
    "Diego Andrés Fernández Cruz",
    "Paola Andrea Ramírez Ortega"
]

def random_latam_name():
    return random.choice(LATAM_NAMES)

def random_sum():
    return f"$ {random.randint(4500000, 5500000):,}".replace(",", ".")

def fit_text_to_width(draw, text, font_path, base_size, target_width):
    """
    Подбирает размер шрифта так, чтобы текст влезал в target_width.
    """
    size = int(base_size)
    font = ImageFont.truetype(font_path, size)
    tb = draw.textbbox((0, 0), text, font=font)
    tw = tb[2] - tb[0]

    if tw > target_width:
        scale = target_width / tw
        size = max(1, int(size * scale))
        font = ImageFont.truetype(font_path, size)

    return font

def render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths, color=(0,0,0,255)):
    psd = PSDImage.open(psd_path)

    # Скрываем исходные текстовые слои
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            layer.visible = False

    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Рисуем новый текст по фиксированным координатам
    for name, text in replacements.items():
        if name in positions:
            x, y = positions[name]
            font_path = fonts.get(name, fonts["default"])
            base_size = sizes.get(name, sizes["default"])
            target_width = widths.get(name, None)

            if target_width:
                font = fit_text_to_width(draw, text, font_path, base_size, target_width)
            else:
                font = ImageFont.truetype(font_path, int(base_size))

            draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"✅ PNG сохранён: {outputs['png']}")
    return outputs["png"]

def handle_message(update, context):
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}

    fonts = {
        "clientName": "assets/SFPRODISPLAYBOLD.OTF",
        "Sum": "assets/SFPRODISPLAYBOLD.OTF",
        "Date": "assets/SFPRODISPLAYREGULAR.OTF",
        "default": "assets/SFPRODISPLAYREGULAR.OTF",
    }

    positions = {
        "Date": (34.6, 190.23),
        "Sum": (55.52, 286.45),
        "clientName": (57.72, 693.84),
    }

    sizes = {
        "Date": 17,
        "Sum": 27,
        "clientName": 19,
        "default": 18,
    }

    widths = {
        "Date": 385.40,
        "Sum": 194.91,
        "clientName": 466.93,
    }

    # Пользователь присылает только дату и время
    user_datetime = update.message.text.strip()

    replacements = {
        "Date": user_datetime,
        "Sum": random_sum(),
        "clientName": random_latam_name(),
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths)
    with open(png_file, "rb") as f:
        update.message.reply_document(document=InputFile(f, filename="render.png"))

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
