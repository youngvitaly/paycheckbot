import os
import random
from datetime import datetime
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
    "Camila Alejandra Morales Рíos",
    "Diego Andrés Fernández Cruz",
    "Paola Andrea Ramírez Ortega"
]

def random_latam_name():
    return random.choice(LATAM_NAMES)

def random_sum():
    return f"$ {random.randint(4500000, 5500000):,}".replace(",", ".")

def current_datetime_str():
    now = datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia_semana = dias[now.weekday()]
    mes_nombre = meses[now.month - 1]
    return f"{dia_semana}, {now.day} de {mes_nombre} de {now.year} a las {now.strftime('%H:%M')} hs"

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

def render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths, color=(0, 0, 0, 255)):
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

# --- Message tracking and cleanup ---

def track_message(context, msg_id):
    msgs = context.user_data.get("msg_ids", set())
    msgs.add(msg_id)
    context.user_data["msg_ids"] = msgs

def cleanup_messages(context, chat_id, preserve_ids):
    # Delete previously tracked messages except those we want to keep
    msgs = context.user_data.get("msg_ids", set())
    to_delete = [mid for mid in msgs if mid not in preserve_ids]
    for mid in to_delete:
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
        msgs.discard(mid)
    context.user_data["msg_ids"] = msgs

def send_and_pin_menu(update_or_query, context):
    keyboard = [
        [InlineKeyboardButton("📂 Выбрать PSD", callback_data="choose_psd")],
        [InlineKeyboardButton("🗓 Настроить Дату", callback_data="set_date")],
        [InlineKeyboardButton("💰 Настроить Сумму", callback_data="set_sum")],
        [InlineKeyboardButton("👤 Настроить Имя", callback_data="set_client")],
        [InlineKeyboardButton("🖼 Сгенерировать PNG", callback_data="generate_png")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "message") and update_or_query.message:
        msg = update_or_query.message.reply_text("📋 Главное меню (закреплено):", reply_markup=reply_markup)
        chat_id = update_or_query.message.chat_id
    else:
        # For callback queries: send a new message (so we can pin it)
        chat_id = update_or_query.message.chat_id
        msg = context.bot.send_message(chat_id=chat_id, text="📋 Главное меню (закреплено):", reply_markup=reply_markup)

    # Pin the menu message (wrap in try in case of insufficient rights)
    try:
        context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
    except Exception:
        pass

    # Track the menu message id
    track_message(context, msg.message_id)
    # Save latest pinned menu id for preservation
    context.user_data["menu_message_id"] = msg.message_id
    return msg

# --- Telegram Handlers ---

def start(update, context):
    # Optional welcome message
    welcome = update.message.reply_text("✨ Все данные генерируются рандомно.")
    track_message(context, welcome.message_id)
    send_and_pin_menu(update, context)

def button(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id

    if query.data == "choose_psd":
        keyboard = [
            [InlineKeyboardButton("🖼 template.psd", callback_data="psd_template")],
            [InlineKeyboardButton("📑 invoice.psd", callback_data="psd_invoice")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        edited = query.edit_message_text("📂 Выберите PSD:", reply_markup=reply_markup)
        track_message(context, edited.message_id)

    elif query.data.startswith("psd_"):
        context.user_data["psd"] = query.data.replace("psd_", "")
        edited = query.edit_message_text(f"✅ Выбран PSD: {context.user_data['psd']}")
        track_message(context, edited.message_id)
        send_and_pin_menu(query, context)

    elif query.data == "set_date":
        context.user_data["awaiting"] = "Date"
        keyboard = [
            [InlineKeyboardButton(
                "💡 Скопировать пример",
                switch_inline_query_current_chat="Viernes, 1 de diciembre de 2025 a las 06:26 hs"
            )],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        edited = query.edit_message_text(
            "🗓 Введите дату и время:\n"
            'к примеру "Viernes, 1 de diciembre de 2025 a las 06:26 hs"\n\n'
            "⬅️ Или вернитесь в меню (дата выставится сегодняшняя)",
            reply_markup=reply_markup
        )
        track_message(context, edited.message_id)

    elif query.data == "set_sum":
        context.user_data["awaiting"] = "Sum"
        keyboard = [
            [InlineKeyboardButton(
                "💡 Скопировать пример",
                switch_inline_query_current_chat="$ 4.778.223"
            )],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        edited = query.edit_message_text(
            "💰 Введите сумму:\n"
            'к примеру "$ 4.778.223"\n\n'
            "⬅️ Или вернитесь в меню (сумма выставится рандомная от $ 4.500.000 до $ 5.500.000)",
            reply_markup=reply_markup
        )
        track_message(context, edited.message_id)

    elif query.data == "set_client":
        context.user_data["awaiting"] = "clientName"
        keyboard = [
            [InlineKeyboardButton(
                "💡 Скопировать пример",
                switch_inline_query_current_chat="José Alberto González Contreras"
            )],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        edited = query.edit_message_text(
            "👤 Введите имя:\n"
            'к примеру "José Alberto González Contreras"\n\n'
            "⬅️ Или вернитесь в меню (имя выставится рандомное)",
            reply_markup=reply_markup
        )
        track_message(context, edited.message_id)

    elif query.data == "generate_png":
        generate_png(update, context)

    elif query.data == "back_menu":
        context.user_data["awaiting"] = None
        send_and_pin_menu(query, context)

def handle_message(update, context):
    chat_id = update.message.chat_id
    awaiting = context.user_data.get("awaiting")

    if awaiting:
        saved = update.message.reply_text(f"✅ Слой {awaiting} обновлён.")
        track_message(context, saved.message_id)
        context.user_data[awaiting] = update.message.text.strip()
        context.user_data["awaiting"] = None
        menu_msg = send_and_pin_menu(update, context)
        # Preserve the latest menu + the confirmation + user's message that updated the layer
        preserve = {menu_msg.message_id, saved.message_id, update.message.message_id}
        cleanup_messages(context, chat_id, preserve)
        return

    # Treat any free text as a Date update
    context.user_data["Date"] = update.message.text.strip()
    saved = update.message.reply_text("🗓 Дата обновлена.")
    track_message(context, saved.message_id)
    menu_msg = send_and_pin_menu(update, context)
    preserve = {menu_msg.message_id, saved.message_id, update.message.message_id}
    cleanup_messages(context, chat_id, preserve)

def generate_png(update, context):
    # Handle both callback and normal update
    if hasattr(update, "callback_query") and update.callback_query:
        chat_id = update.callback_query.message.chat_id
        origin_message_id = update.callback_query.message.message_id
    else:
        chat_id = update.message.chat_id
        origin_message_id = update.message.message_id

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
        "Date": context.user_data.get("Date", current_datetime_str()),
        "Sum": context.user_data.get("Sum", random_sum()),
        "clientName": context.user_data.get("clientName", random_latam_name()),
    }

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths)

    with open(png_file, "rb") as f:
        if hasattr(update, "callback_query") and update.callback_query:
            sent = update.callback_query.message.reply_document(document=InputFile(f, filename="render.png"))
        else:
            sent = update.message.reply_document(document=InputFile(f, filename="render.png"))
    # Track the PNG message id
    track_message(context, sent.message_id)
    context.user_data["last_png_message_id"] = sent.message_id

    # Show and pin menu again
    menu_msg = send_and_pin_menu(update.callback_query if hasattr(update, "callback_query") and update.callback_query else update, context)

    # Preserve the latest PNG + latest menu + the origin message that triggered generation
    preserve = {sent.message_id, menu_msg.message_id, origin_message_id}
    cleanup_messages(context, chat_id, preserve)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
