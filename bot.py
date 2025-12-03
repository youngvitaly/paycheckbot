import os
import random
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackQueryHandler

load_dotenv()

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

    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            layer.visible = False

    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

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
    return outputs["png"]

# --- Telegram Handlers ---

def show_menu(update_or_query, context):
    keyboard = [
        [InlineKeyboardButton("📂 Выбрать PSD", callback_data="choose_psd")],
        [InlineKeyboardButton("🗓 Настроить Date", callback_data="set_date")],
        [InlineKeyboardButton("💰 Настроить Sum", callback_data="set_sum")],
        [InlineKeyboardButton("👤 Настроить clientName", callback_data="set_client")],
        [InlineKeyboardButton("🖼 Сгенерировать PNG", callback_data="generate_png")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "message"):
        update_or_query.message.reply_text("📋 Главное меню:", reply_markup=reply_markup)
    else:
        update_or_query.edit_message_text("📋 Главное меню:", reply_markup=reply_markup)

def start(update, context):
    update.message.reply_text("✨ Все данные генерируются рандомно.")
    show_menu(update, context)

def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "choose_psd":
        keyboard = [
            [InlineKeyboardButton("🖼 template.psd", callback_data="psd_template")],
            [InlineKeyboardButton("📑 invoice.psd", callback_data="psd_invoice")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("📂 Выберите PSD:", reply_markup=reply_markup)

    elif query.data.startswith("psd_"):
        context.user_data["psd"] = query.data.replace("psd_", "")
        query.edit_message_text(f"✅ Выбран PSD: {context.user_data['psd']}")
        show_menu(query, context)

    elif query.data == "set_date":
        context.user_data["awaiting"] = "Date"
        query.edit_message_text("🗓 Введите дату/время:\n⬅️ Назад в меню доступен ниже",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]]))

    elif query.data == "set_sum":
        context.user_data["awaiting"] = "Sum"
        query.edit_message_text("💰 Введите сумму:\n⬅️ Назад в меню доступен ниже",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]]))

    elif query.data == "set_client":
        context.user_data["awaiting"] = "clientName"
        query.edit_message_text("👤 Введите имя клиента:\n⬅️ Назад в меню доступен ниже",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]]))

    elif query.data == "generate_png":
        generate_png(update, context)

    elif query.data == "back_menu":
        show_menu(query, context)

def handle_message(update, context):
    awaiting = context.user_data.get("awaiting")
    if awaiting:
        context.user_data[awaiting] = update.message.text.strip()
        context.user_data["awaiting"] = None
        update.message.reply_text(f"✅ Слой {awaiting} обновлён.")
        show_menu(update, context)
        return

    # если нет режима ожидания — просто обновляем Date
    context.user_data["Date"] = update.message.text.strip()
    update.message.reply_text("🗓 Дата обновлена.")
    show_menu(update, context)

def generate_png(update, context):
    psd_file = context.user_data.get("psd", "template") + ".psd"
    psd_path = f"assets/{psd_file}"
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
        "Date": int(16.84 * 96 / 72),        # ≈ 22 px
        "Sum": int(27.26 * 96 / 72),         # ≈ 36 px
        "clientName": int(18.9 * 96 / 72),   # ≈ 25 px
        "default": 24,
    }

    widths = {
        "Date": 385.40,
        "Sum": 194.91,
        "clientName": 466.93,
    }

    replacements = {
        "Date": context.user_data.get("Date", "Сегодня"),
        "Sum": context.user_data.get("Sum", random_sum()),
        "clientName": context.user_data.get("clientName", random_latam_name()),
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths)
    with open(png_file, "rb") as f:
        if hasattr(update, "callback_query"):
            update.callback_query.message.reply_document(document=InputFile(f, filename="render.png"))
        else:
            update.message.reply_document(document=InputFile(f, filename="render.png"))

    # после отправки PNG снова показываем меню
    show_menu(update, context)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
