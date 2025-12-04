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

def pt_to_px(pt: float, dpi: int = 96) -> int:
    return int(round(pt * dpi / 72))

def fit_text_to_width(draw, text, font_path, base_size_px, target_width_px):
    size = int(base_size_px)
    font = ImageFont.truetype(font_path, size)
    tb = draw.textbbox((0, 0), text, font=font)
    tw = tb[2] - tb[0]
    if target_width_px and tw > target_width_px:
        scale = target_width_px / tw
        size = max(1, int(size * scale))
        font = ImageFont.truetype(font_path, size)
    return font

def render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes_px, widths_px, color=(0, 0, 0, 255)):
    psd = PSDImage.open(psd_path)

    # Hide text layers that we will replace (if present)
    for layer in psd.descendants():
        if layer.kind == "type" and layer.name in replacements:
            layer.visible = False

    base = psd.composite().convert("RGBA")
    draw = ImageDraw.Draw(base)

    for name, text in replacements.items():
        if name in positions:
            x, y = positions[name]
            font_path = fonts.get(name, fonts.get("default"))
            base_size = sizes_px.get(name, sizes_px.get("default", 24))
            target_width = widths_px.get(name, None)

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

# --- Telegram Handlers and logic ---

def start(update, context):
    welcome = update.message.reply_text("✨ Все данные генерируются рандомно.")
    track_message(context, welcome.message_id)
    send_and_pin_menu(update, context)

def show_nalogDom_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("Настроить Имя", callback_data="nalog_set_name")],
        [InlineKeyboardButton("Настроить ID", callback_data="nalog_set_id")],
        [InlineKeyboardButton("Настроить Вывод", callback_data="nalog_set_amount")],
        [InlineKeyboardButton("Настроить Налог", callback_data="nalog_set_tax")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        edited = query.edit_message_text("📂 Настройки nalogDom.psd:", reply_markup=reply_markup)
        track_message(context, edited.message_id)
    except Exception:
        # fallback: send new message
        msg = context.bot.send_message(chat_id=query.message.chat_id, text="📂 Настройки nalogDom.psd:", reply_markup=reply_markup)
        track_message(context, msg.message_id)

def button(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id

    if query.data == "choose_psd":
        keyboard = [
            [InlineKeyboardButton("🖼 arsInvest.psd", callback_data="psd_arsInvest")],
            [InlineKeyboardButton("🏠 nalogDom.psd", callback_data="psd_nalogDom")],
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

        # Если выбран nalogDom — показать специальное меню настроек
        if context.user_data["psd"] == "nalogDom":
            show_nalogDom_menu(query, context)
        else:
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

    # --- nalogDom specific callbacks ---
    elif query.data == "nalog_set_name":
        context.user_data["awaiting"] = "clientName"
        keyboard = [
            [InlineKeyboardButton("💡 Скопировать пример", switch_inline_query_current_chat="Ana Virginia Mamani Bernal")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="psd_nalogDom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            edited = query.edit_message_text(
                "👤 Введите имя (clientName):\n"
                'к примеру "Ana Virginia Mamani Bernal"\n\n'
                "⬅️ Или вернитесь в настройки nalogDom",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

    elif query.data == "nalog_set_id":
        context.user_data["awaiting"] = "numCuenta"
        keyboard = [
            [InlineKeyboardButton("💡 Скопировать пример", switch_inline_query_current_chat="9843893")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="psd_nalogDom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            edited = query.edit_message_text(
                "🔢 Введите ID (numCuenta):\n"
                'к примеру "9843893"\n\n'
                "⬅️ Или вернитесь в настройки nalogDom",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

    elif query.data == "nalog_set_amount":
        context.user_data["awaiting"] = "amount"
        keyboard = [
            [InlineKeyboardButton("💡 Скопировать пример", switch_inline_query_current_chat="85,349.60 DOP")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="psd_nalogDom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            edited = query.edit_message_text(
                "💸 Введите Вывод (amount):\n"
                'к примеру "85,349.60 DOP"\n\n'
                "⬅️ Или вернитесь в настройки nalogDom",
                reply_markup=reply_markup
            )
            track_message(context, edited.message_id)
        except Exception:
            pass

    elif query.data == "nalog_set_tax":
        context.user_data["awaiting"] = "depAmount"
        keyboard = [
            [InlineKeyboardButton("💡 Скопировать пример", switch_inline_query_current_chat="1,349 DOP")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="psd_nalogDom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            edited = query.edit_message_text(
                "🏷 Введите Налог (depAmount):\n"
                'к примеру "1,349 DOP"\n\n'
                "⬅️ Или вернитесь в настройки nalogDom",
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
        # После изменения — показать меню и очистить старые сообщения, сохранив важные
        menu_msg = send_and_pin_menu(update, context)
        preserve = {menu_msg.message_id, saved.message_id, update.message.message_id}
        cleanup_messages(context, chat_id, preserve)
        return

    # Если нет режима ожидания — считаем ввод датой (как раньше), но тоже очищаем
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
    num_cuenta_val = sanitize_input(context.user_data.get("numCuenta", ""))
    dep_amount_val = sanitize_input(context.user_data.get("depAmount", ""))
    amount_val = sanitize_input(context.user_data.get("amount", ""))

    psd_key = context.user_data.get("psd", "arsInvest")  # default arsInvest

    # Font mapping: default regular, bold for some, medium for nalogDom
    fonts = {
        "clientName": "assets/SFPRODISPLAYBOLD.OTF",
        "Sum": "assets/SFPRODISPLAYBOLD.OTF",
        "Date": "assets/SFPRODISPLAYREGULAR.OTF",
        "default": "assets/SFPRODISPLAYREGULAR.OTF",
    }
    if psd_key == "nalogDom":
        fonts.update({
            "clientName": "assets/SFPRODISPLAYMEDIUM.OTF",
            "amount": "assets/SFPRODISPLAYMEDIUM.OTF",
            "numCuenta": "assets/SFPRODISPLAYMEDIUM.OTF",
            "depAmount": "assets/SFPRODISPLAYMEDIUM.OTF",
            "default": "assets/SFPRODISPLAYMEDIUM.OTF",
        })

    # Positions and sizes per PSD
    if psd_key == "arsInvest":
        psd_path = "assets/arsInvest.psd"
        positions = {
            "Date": (34.6, 190.23),
            "Sum": (55.52, 286.45),
            "clientName": (57.72, 693.84),
        }
        sizes_px = {
            "Date": pt_to_px(16.84),
            "Sum": pt_to_px(27.26),
            "clientName": pt_to_px(18.9),
            "default": 24,
        }
        widths_px = {
            "Date": 385.40,
            "Sum": 194.91,
            "clientName": 466.93,
        }
        replacements = {
            "Date": date_val if date_val else current_datetime_str(),
            "Sum": sum_val if sum_val else random_sum(),
            "clientName": name_val if name_val else random_latam_name(),
        }

    elif psd_key == "nalogDom":
        psd_path = "assets/nalogDom.psd"
        # Координаты и размеры — примерные плейсхолдеры. При необходимости замени на точные значения из PSD.
        positions = {
            "clientName": (120.0, 200.0),
            "amount": (120.0, 260.0),
            "numCuenta": (120.0, 320.0),
            "depAmount": (120.0, 380.0),
        }
        sizes_px = {
            "clientName": pt_to_px(18.0),
            "amount": pt_to_px(18.0),
            "numCuenta": pt_to_px(18.0),
            "depAmount": pt_to_px(18.0),
            "default": pt_to_px(18.0),
        }
        widths_px = {
            "clientName": 900.0,
            "amount": 500.0,
            "numCuenta": 400.0,
            "depAmount": 400.0,
        }
        replacements = {
            "clientName": name_val if name_val else "Ana Virginia Mamani Bernal",
            "amount": amount_val if amount_val else "85,349.60 DOP",
            "numCuenta": num_cuenta_val if num_cuenta_val else "9843893",
            "depAmount": dep_amount_val if dep_amount_val else "1,349 DOP",
        }

    else:
        # Fallback for "invoice" or others
        psd_path = f"assets/{psd_key}.psd"
        positions = {}
        sizes_px = {"default": 24}
        widths_px = {}
        replacements = {}

    outputs = {"png": "out/render.png"}
    png_file = render_psd_to_png(psd_path, outputs, replacements, fonts, positions, sizes_px, widths_px)

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
    preserve.add(origin_message_id if 'origin_message_id' in locals() else (update.callback_query.message.message_id if hasattr(update, "callback_query") and update.callback_query else update.message.message_id))
    cleanup_messages(context, chat_id if 'chat_id' in locals() else (update.callback_query.message.chat_id if hasattr(update, "callback_query") and update.callback_query else update.message.chat_id), preserve)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()
