from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    builder.add(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="👥 Foydalanuvchilar"),
    )

    builder.row(
        KeyboardButton(text="📢 Xabar yuborish")
    )

    builder.row(KeyboardButton(text="🔙 Asosiy menyu"))

    return builder.as_markup(resize_keyboard=True)

def get_back_to_admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)

def get_statistics_period_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📅 Kunlik", callback_data="stats_daily"),
        InlineKeyboardButton(text="📆 Oylik", callback_data="stats_monthly"),
        InlineKeyboardButton(text="📈 Umumiy", callback_data="stats_all")
    )

    return builder.as_markup()

def get_task_grading_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="⭐ Baholash", callback_data=f"grade_task_{task_id}")
    )

    return builder.as_markup()

def get_grading_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="100%", callback_data="grade_percent_100"),
        InlineKeyboardButton(text="90%", callback_data="grade_percent_90"),
        InlineKeyboardButton(text="85%", callback_data="grade_percent_85")
    )

    builder.row(
        InlineKeyboardButton(text="80%", callback_data="grade_percent_80"),
        InlineKeyboardButton(text="70%", callback_data="grade_percent_70"),
        InlineKeyboardButton(text="60%", callback_data="grade_percent_60")
    )

    builder.row(
        InlineKeyboardButton(text="55%", callback_data="grade_percent_55"),
        InlineKeyboardButton(text="50%", callback_data="grade_percent_50"),
        InlineKeyboardButton(text="40%", callback_data="grade_percent_40")
    )

    builder.row(
        InlineKeyboardButton(text="30%", callback_data="grade_percent_30"),
        InlineKeyboardButton(text="20%", callback_data="grade_percent_20"),
        InlineKeyboardButton(text="10%", callback_data="grade_percent_10")
    )

    return builder.as_markup()

def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="broadcast_all")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏙️ Tuman bo'yicha", callback_data="broadcast_district"),
        InlineKeyboardButton(text="🏘️ Mahalla bo'yicha", callback_data="broadcast_mahalla")
    )
    
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
    )
    
    return builder.as_markup()


def get_districts_keyboard(districts: list) -> InlineKeyboardMarkup:
  builder = InlineKeyboardBuilder()
  
  if not isinstance(districts, list):
      districts = []
  
  for district in districts:
      if isinstance(district, dict) and 'id' in district and 'name' in district:
          builder.row(
              InlineKeyboardButton(
                  text=district["name"], 
                  callback_data=f"district_{district['id']}"
              )
          )
  
  builder.row(
      InlineKeyboardButton(text="🔙 Orqaga", callback_data="broadcast_back_target"),
      InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
  )
  
  return builder.as_markup()


def get_mahallas_keyboard(mahallas: list) -> InlineKeyboardMarkup:
  builder = InlineKeyboardBuilder()
  
  if not isinstance(mahallas, list):
      mahallas = []
  
  for mahalla in mahallas:
      if isinstance(mahalla, dict) and 'id' in mahalla and 'name' in mahalla:
          builder.row(
              InlineKeyboardButton(
                  text=mahalla["name"], 
                  callback_data=f"mahalla_{mahalla['id']}"
              )
          )
  
  builder.row(
      InlineKeyboardButton(text="🔙 Orqaga", callback_data="broadcast_back_target"),
      InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
  )
  
  return builder.as_markup()



def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
    )
    
    return builder.as_markup()
