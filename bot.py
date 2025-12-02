import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

# Загружаем переменные окружения (например, TOKEN)
load_dotenv()

def render_psd_to_png(psd_path, outputs, replacements, fonts, default_font_size=36, color=(0, 0, 0, 255)):
    # Загружаем PSD
    psd = PSDImage.open(psd_path)

    # Соберём метаданные по целевым слоям и скрываем их перед композитом
    targets = {}
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            bbox = layer.bbox  # (x1, y1, x2, y2)
            targets[layer.name] = {
                "bbox": bbox,
                "font_path": fonts.get(layer.name, fonts["default"]),
                "font_size": default_font_size,
                "text": replacements[layer.name],
            }
            # Скрываем исходный текстовый слой, чтобы не было прозрачных «окон»
            layer.visible = False

    # Сводим картинку уже без исходных текстовых слоёв
    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Рисуем новый текст, центрируя в границах исходного bbox
    for name, info in targets.items():
        x1, y1, x2, y2 = info["bbox"]
        w_box = x2 - x1
        h_box = y2 - y1

        font = ImageFont.truetype(info["font_path"], info["font_size"])
        # Получаем размер текста (с учётом шрифта)
        # textbbox возвращает (left, top, right, bottom)
        tb = draw.textbbox((0, 0), info["text"], font=font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]

        # Центровка: по горизонтали и вертикали внутри bbox
        tx = x1 + max(0, (w_box - tw) // 2)
        ty = y1 + max(0, (h_box - th) // 2)

        draw.text((tx, ty), info["text"], font=font, fill=color)

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
        "default": "assets/SFPRODISPLAYREGULAR.OTF",
    }

    # Данные для замены: имя берём из сообщения
    replacements = {
        "Date": "Сегодня",
        "Sum": "$ 123",
        "clientName": update.message.text.strip(),
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
