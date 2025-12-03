import os
import re
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
    "Camila Alejandra Morales Ríos",
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

def sanitize_input(text: str) -> str:
    """
    Убирает ведущий @username если пользователь вставил команду вида:
    "@botusername some text" -> "some text"
    Также обрезает лишние пробелы в начале/конце.
    """
    if not text:
        return text
    text = text.strip()
    cleaned = re.sub(r'^\s*@\S+\s+', '', text)
    return cleaned.strip()

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
    """
    Удаляет ранее отслеживаемые сообщения, кроме тех, что в preserve_ids.
    preserve_ids — множество message_id, которые нужно сохранить.
    """
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
        [InlineKeyboardButton("📂 Выбрать Исходник (PSD)", callback_data="choose_psd")],
        [InlineKeyboardButton("🗓 Настроить Дату", callback_data="set_date")],
        [InlineKeyboardButton("💰 Настроить Сумму", callback_data="set_sum")],
        [InlineKeyboardButton("👤 Настроить Имя", callback_data="set_client")],
        [InlineKeyboardButton("🖼 Сгенерировать PNG", callback_data="generate_png")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение с меню, чтобы его можно было закрепить
    if hasattr(update_or_query, "message") and update_or_query.message:
        chat_id = update_or_query.message.chat_id
    else:
        chat_id = update_or_query.message.chat_id

    try:
        msg = context.bot.send_message(chat_id=chat_id, text="📋 Главное меню (закреплено):", reply_markup=reply_markup)
    except Exception:
        # fallback: try to edit if send fails
        try:
            msg = update_or_query.edit_message_text("📋 Главное меню (закреплено):", reply_markup=reply_markup)
        except Exception:
            return None

    # Попытка закрепить сообщение (если есть права)
    try:
        context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
    except Exception:
        pass

    # Трек и сохранение id меню
    track_message(context, msg.message_id)
    context.user_data["menu_message_id"] = msg.message_id
    return msg

# --- Telegram Handlers ---

def show_menu(update_or_query, context):
    # Для совместимости: просто отправляем и не обязательно пинить
    return send_and_pin_menu(update_or_query, context)

def start(update, context):
    welcome = update.message.reply_text("✨ Все данные генерируются рандомно.")
    track_message(context, welcome.message_id)
    send_and_pin_menu(update, context)

def button(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id

    if query.data == "choose_psd":
        keyboard = [
            [InlineKeyboardButton("🖼 arsInvest.psd", callback_data="psd_arsInvest")],
            [InlineKeyboardButton("📑 invoice.psd", callback_data="psd_invoice")],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            edited = query.edit_message_text("📂 Выберите исходник (PSD):", reply_markup=reply_markup)
            track_message(context, edited.message_id)
        except Exception:
            pass

    elif query.data.startswith("psd_"):
        context.user_data["psd"] = query.data.replace("psd_", "")
        try:
            edited = query.edit_message_text(f"✅ Выбран PSD: {context.user_data['psd']}")
            track_message(context, edited.message_id)
        except Exception:
            pass
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
        try:
            edited = query.edit_message_text(
                "🗓 Введите дату и время:\n"
                'к примеру "Viernes, 1 de diciembre de 2025 a las 06:26 hs"\n\n'
                "⬅️ Или вернитесь в меню (дата выставится сегодняшняя)",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

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
        try:
            edited = query.edit_message_text(
                "💰 Введите сумму:\n"
                'к примеру "$ 4.778.223"\n\n'
                "⬅️ Или вернитесь в меню (сумма выставится рандомная от $ 4.500.000 до $ 5.500.000)",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

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
        try:
            edited = query.edit_message_text(
                "👤 Введите имя:\n"
                'к примеру "José Alberto González Contreras"\n\n'
                "⬅️ Или вернитесь в меню (имя выставится рандомное)",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

    elif query.data == "generate_png":
        generate_png(update, context)

    elif query.data == "back_menu":
        context.user_data["awaiting"] = None
        send_and_pin_menu(query, context)

def handle_message(update, context):
    chat_id = update.message.chat_id
    raw_text = update.message.text or ""
    text = sanitize_input(raw_text)

    awaiting = context.user_data.get("awaiting")
    if awaiting:
        context.user_data[awaiting] = text
        context.user_data["awaiting"] = None
        saved = update.message.reply_text(f"✅ Слой {awaiting} обновлён.")
        track_message(context, saved.message_id)
        menu_msg = send_and_pin_menu(update, context)
        preserve = {menu_msg.message_id, saved.message_id, update.message.message_id}
        cleanup_messages(context, chat_id, preserve)
        return

    # Если нет режима ожидания — считаем ввод датой
    context.user_data["Date"] = text
    saved = update.message.reply_text("🗓 Дата обновлена.")
    track_message(context, saved.message_id)
    menu_msg = send_and_pin_menu(update, context)
    preserve = {menu_msg.message_id, saved.message_id, update.message.message_id}
    cleanup_messages(context, chat_id, preserve)

def generate_png(update, context):
    # Определяем chat_id и origin_message_id
    if hasattr(update, "callback_query") and update.callback_query:
        chat_id = update.callback_query.message.chat_id
        origin_message_id = update.callback_query.message.message_id
    else:
        chat_id = update.message.chat_id
        origin_message_id = update.message.message_id

    # Подготавливаем значения, очищая возможные @username
    date_val = sanitize_input(context.user_data.get("Date", ""))
    sum_val = sanitize_input(context.user_data.get("Sum", ""))
    name_val = sanitize_input(context.user_data.get("clientName", ""))

    replacements = {
        "Date": date_val if date_val else current_datetime_str(),
        "Sum": sum_val if sum_val else random_sum(),
        "clientName": name_val if name_val else random_latam_name(),
    }

    psd_file = context.user_data.get("psd", "arsInvest") + ".psd"
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

    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes, widths)

    with open(png_file, "rb") as f:
        if hasattr(update, "callback_query") and update.callback_query:
            sent = update.callback_query.message.reply_document(document=InputFile(f, filename="render.png"))
        else:
            sent = update.message.reply_document(document=InputFile(f, filename="render.png"))

    # Трек PNG сообщения
    track_message(context, sent.message_id)
    context.user_data["last_png_message_id"] = sent.message_id

    # Показать и закрепить меню снова
    menu_msg = send_and_pin_menu(update.callback_query if hasattr(update, "callback_query") and update.callback_query else update, context)

    # Сохранить и удалить старые сообщения, кроме текущих важных
    preserve = {sent.message_id}
    if menu_msg:
        preserve.add(menu_msg.message_id)
    preserve.add(origin_message_id)
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
