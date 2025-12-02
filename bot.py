import os
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
from telegram import InputFile

load_dotenv()

def draw_text_with_tracking(draw, position, text, font, fill, tracking=0):
    """Рисует текст посимвольно с учётом трекинга (letter-spacing)."""
    x, y = position
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        # ширина символа + трекинг
        x += font.getsize(ch)[0] + tracking

def render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, trackings, color=(0,0,0,255)):
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
            font_size = sizes.get(name, sizes["default"])
            tracking = trackings.get(name, 0)

            font = ImageFont.truetype(font_path, font_size)
            draw_text_with_tracking(draw, (x, y), text, font, color, tracking)

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
        "Date": 16.84,
        "Sum": 27.26,
        "clientName": 18.9,
        "default": 18,
    }

    trackings = {
        "Date": -40,
        "Sum": -40,
        "clientName": -40,
        "default": 0,
    }

    replacements = {
        "Date": "Сегодня",
        "Sum": "$ 123",
        "clientName": update.message.text.strip(),
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, trackings)
    with open(png_file, "rb") as f:
        update.message.reply_document(document=InputFile(f, filename="render.png"))

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
