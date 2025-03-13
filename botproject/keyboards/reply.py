from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_phone_number_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(
        text="📱 Telefon raqamni yuborish",
        request_contact=True
    ))
    return builder.as_markup(resize_keyboard=True)

def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    builder.add(
        KeyboardButton(text="📋 Mening topshiriqlarim"),
        KeyboardButton(text="📊 Mening statistikam"),
        KeyboardButton(text="❓ Yordam")
    )

    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard(with_submit: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    if with_submit:
        builder.add(
            KeyboardButton(text="✅ Yuborish"),
            KeyboardButton(text="❌ Bekor qilish")
        )
    else:
        builder.add(KeyboardButton(text="❌ Bekor qilish"))

    return builder.as_markup(resize_keyboard=True)

