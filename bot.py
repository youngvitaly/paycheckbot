import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

# Загружаем переменные окружения (например, TOKEN)
load_dotenv()

def render_psd_to_png(psd_path, outputs, replacements, fonts, positions, font_size=36, color=(0, 0, 0, 255)):
    # Загружаем PSD
    psd = PSDImage.open(psd_path)

    # Скрываем исходные текстовые слои
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            layer.visible = False

    # Сводим картинку без исходных текстовых слоёв
    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Рисуем новый текст по фиксированным координатам
    for name, text in replacements.items():
        if name in positions:
            x, y = positions[name]
            font_path = fonts.get(name, fonts["default"])
            font = ImageFont.truetype(font_path, font_size)
            draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"✅ PNG сохранён: {outputs['png']}")
    return outputs["png"]

def handle_message(update, context):
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}

    # Шрифты для разных слоёв
    fonts = {
        "clientName": "assets/SFPRODISPLAYBOLD.OTF",
        "Sum": "assets/SFPRODISPLAYBOLD.OTF",
        "Date": "assets/SFPRODISPLAYREGULAR.OTF",
        "default": "assets/SFPRODISPLAYREGULAR.OTF",
    }

    # Фиксированные координаты из Photoshop
    positions = {
        "Date": (34.6, 190.23),
        "Sum": (55.52, 286.45),
        "clientName": (57.72, 693.84),
    }

    # Данные для замены
    replacements = {
        "Date": "Сегодня",
        "Sum": "$ 123",
        "clientName": update.message.text.strip(),
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions)
    with open(png_file, "rb") as f:
        update.message.reply_document(document=InputFile(f, filename="render.png"))

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
