import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

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
            draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"✅ PNG сохранён: {outputs['png']}")
    return outputs["png"]

def handle_message(update, context):
    # Пути к файлам
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}
    font_path = "assets/Arial.ttf"

    # Данные для замены (пример: имя берём из текста сообщения)
    replacements = {
        "Date": "Сегодня",
        "Sum": "$ 123",
        "clientName": update.message.text
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, font_path)
    with open(png_file, "rb") as f:
        update.message.reply_document(document=InputFile(f, filename="render.png"))

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обрабатываем все текстовые сообщения
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
