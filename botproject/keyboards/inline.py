from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


    
def get_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📝 Batafsil", callback_data=f"task_view_{task_id}"),
        InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"task_complete_{task_id}"),
        InlineKeyboardButton(text="📊 Hisobot", callback_data=f"task_report_{task_id}")
    )

    return builder.as_markup()

def get_task_detail_keyboard(task_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if status == 'active':
        builder.add(
            InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"task_complete_{task_id}"),
            InlineKeyboardButton(text="📊 Hisobot", callback_data=f"task_report_{task_id}"),
            InlineKeyboardButton(text="📈 Statistika", callback_data=f"task_stats_{task_id}")
        )
    else:
        builder.add(
            InlineKeyboardButton(text="📈 Statistika", callback_data=f"task_stats_{task_id}")
        )

    return builder.as_markup()

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="✅ Ha", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_no")
    )

    return builder.as_markup()

def get_task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        status_emoji = "✅" if task['status'] == 'completed' else "❌" if task['status'] == 'rejected' else "⏳"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {task['title']}",
                callback_data=f"task_{task['id']}"
            )
        )
    
    return builder.as_markup()

    
    return builder.as_markup()

def get_task_detail_keyboard(task_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if status == 'active':
        builder.row(
            InlineKeyboardButton(text="📝 Topshirish", callback_data=f"submit_task_{task_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_tasks")
    )
    
    return builder.as_markup()

def get_task_submission_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)

def get_back_to_tasks_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Yuborishni yakunlash"))
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)

