import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

# Загружаем переменные окружения (например, TOKEN)
load_dotenv()

def render_psd_to_png(psd_path, outputs, replacements, fonts, font_size=36, color=(0, 0, 0, 255)):
    # Загружаем PSD
    psd = PSDImage.open(psd_path)
    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Проходим по слоям PSD
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            bbox = layer.bbox  # (x1, y1, x2, y2)
            x, y = bbox[0], bbox[1]
            text = replacements[layer.name]

            # Выбираем шрифт по имени слоя
            font_path = fonts.get(layer.name, fonts["default"])
            font = ImageFont.truetype(font_path, font_size)

            # очищаем область слоя
            draw.rectangle(bbox, fill=(255, 255, 255, 0))
            # рисуем новый текст
            draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(outputs["png"]), exist_ok=True)
    base.save(outputs["png"])
    print(f"✅ PNG сохранён: {outputs['png']}")
    return outputs["png"]

def handle_message(update, context):
    # Пути к файлам
    psd_path = "assets/template.psd"
    outputs = {"png": "out/render.png"}

    # Шрифты для разных слоёв
    fonts = {
        "clientName": "assets/SFPRODISPLAYBOLD.OTF",
        "Sum": "assets/SFPRODISPLAYBOLD.OTF",
        "Date": "assets/SFPRODISPLAYREGULAR.OTF",
        "default": "assets/SFPRODISPLAYREGULAR.OTF"
    }

    # Данные для замены (пример: имя берём из текста сообщения)
    replacements = {
        "Date": "Сегодня",
        "Sum": "$ 123",
        "clientName": update.message.text
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts)
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
