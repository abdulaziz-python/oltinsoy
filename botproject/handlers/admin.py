from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import ADMIN_IDS
from utils.logger import setup_logger
from contextlib import suppress
from keyboards.admin import (
    get_admin_menu, get_back_to_admin_menu, get_statistics_period_keyboard, 
    get_grading_keyboard, get_broadcast_target_keyboard, get_districts_keyboard,
    get_mahallas_keyboard, get_broadcast_confirm_keyboard
)
from states.admin import TaskState, GradingState, BroadcastState
import asyncio
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import numpy as np
from utils.api import (
    get_statistics, get_task_detail, grade_task, send_broadcast,
    get_districts, get_mahallas
)
from utils.bot import get_bot
from aiogram.types import FSInputFile

logger = setup_logger(__name__)
router = Router()

def is_admin_filter(message: Message):
    return message.from_user.id in ADMIN_IDS

@router.message(Command("admin"), is_admin_filter)
async def cmd_admin(message: Message):
    await message.answer(
        "👨‍💼 <b>Admin panel</b>\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=get_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "🔙 Orqaga", is_admin_filter)
async def back_to_admin(message: Message):
    await message.answer(
        "👨‍💼 <b>Admin panel</b>",
        reply_markup=get_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📊 Statistika", is_admin_filter)
async def show_admin_stats(message: Message):
    await message.answer(
        "Qaysi davr uchun statistikani ko'rmoqchisiz?",
        reply_markup=get_statistics_period_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("stats_"), is_admin_filter)
async def process_stats_period(callback: CallbackQuery):
    await callback.answer()
    period = callback.data.split("_")[1]
    
    processing_msg = await callback.message.answer("⌛ Statistika yuklanmoqda...", parse_mode=ParseMode.HTML)
    
    try:
        response = await get_statistics(period)
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            stats = response.data
            
            if period == "daily":
                title = f"📊 <b>Kunlik statistika ({datetime.now().strftime('%d.%m.%Y')})</b>"
            elif period == "monthly":
                title = f"📊 <b>Oylik statistika ({datetime.now().strftime('%m.%Y')})</b>"
            else:
                title = "📊 <b>Umumiy statistika</b>"
                
            summary = (
                f"{title}\n\n"
                f"✅ Bajarilgan topshiriqlar: {stats.get('completed_tasks', 0)}\n"
                f"⏳ Jarayondagi topshiriqlar: {stats.get('active_tasks', 0)}\n"
                f"❌ Rad etilgan topshiriqlar: {stats.get('rejected_tasks', 0)}\n"
                f"👥 Faol foydalanuvchilar: {stats.get('active_users', 0)}\n\n"
                f"🏆 <b>Eng yaxshi mahallalar:</b>\n"
            )
            
            top_mahallas = stats.get('top_mahallas', [])
            for i, mahalla in enumerate(top_mahallas[:5], 1):
                completion_rate = mahalla.get('completion_rate', 0)
                status_emoji = "🟢" if completion_rate >= 85 else "🟡" if completion_rate >= 55 else "🔴"
                summary += f"{i}. {status_emoji} {mahalla.get('name')}: {completion_rate:.1f}%\n"
                
            await callback.message.answer(summary, parse_mode=ParseMode.HTML)
            
            await send_statistics_charts(callback.message, stats, period)
        else:
            await callback.message.answer(
                "Statistikani yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error in process_stats_period: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await callback.message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_admin_menu(),
            parse_mode=ParseMode.HTML
        )

async def send_statistics_charts(message: Message, stats: dict, period: str):
    try:
        district_data = stats.get('district_stats', [])
        if district_data:
            plt.figure(figsize=(10, 6))
            districts = [d.get('name', '') for d in district_data]
            rates = [d.get('completion_rate', 0) for d in district_data]
            
            # Handle empty data
            if not districts or not rates or all(r == 0 for r in rates):
                await message.answer("Tumanlar bo'yicha ma'lumotlar mavjud emas.", parse_mode=ParseMode.HTML)
                return
                
            colors = ['green' if r >= 85 else 'yellow' if r >= 55 else 'red' for r in rates]
            
            # Create the bar chart
            plt.figure(figsize=(10, 6))
            y_pos = np.arange(len(districts))
            plt.bar(y_pos, rates, color=colors)
            plt.axhline(y=85, color='green', linestyle='--', alpha=0.7)
            plt.axhline(y=55, color='red', linestyle='--', alpha=0.7)
            plt.xlabel('Tumanlar')
            plt.ylabel('Bajarilish darajasi (%)')
            plt.title('Tumanlar bo\'yicha bajarilish darajasi')
            plt.xticks(y_pos, districts, rotation=45, ha='right')
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            # Convert BytesIO to BufferedInputFile
            from aiogram.types import BufferedInputFile
            input_file = BufferedInputFile(buf.getvalue(), filename="districts.png")
            
            await message.answer_photo(
                input_file, 
                caption="📊 Tumanlar bo'yicha bajarilish darajasi",
                parse_mode=ParseMode.HTML
            )
            
        completed = stats.get('completed_tasks', 0)
        active = stats.get('active_tasks', 0)
        rejected = stats.get('rejected_tasks', 0)
        
        # Only create pie chart if there's data
        if completed > 0 or active > 0 or rejected > 0:
            plt.figure(figsize=(8, 8))
            plt.pie(
                [completed, active, rejected],
                labels=['Bajarilgan', 'Jarayonda', 'Rad etilgan'],
                colors=['green', 'blue', 'red'],
                autopct='%1.1f%%',
                startangle=90
            )
            plt.axis('equal')
            plt.title('Topshiriqlar holati')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            # Convert BytesIO to BufferedInputFile
            from aiogram.types import BufferedInputFile
            input_file = BufferedInputFile(buf.getvalue(), filename="tasks.png")
            
            await message.answer_photo(
                input_file, 
                caption="📊 Topshiriqlar holati",
                parse_mode=ParseMode.HTML
            )
        
        if period == "monthly" and 'daily_stats' in stats:
            daily_stats = stats.get('daily_stats', [])
            if daily_stats:
                dates = [d.get('date', '') for d in daily_stats]
                completed_counts = [d.get('completed_tasks', 0) for d in daily_stats]
                
                # Only create line chart if there's data
                if dates and completed_counts and any(c > 0 for c in completed_counts):
                    plt.figure(figsize=(12, 6))
                    plt.plot(dates, completed_counts, marker='o', linestyle='-', color='green')
                    plt.xlabel('Sana')
                    plt.ylabel('Bajarilgan topshiriqlar')
                    plt.title('Oylik bajarilgan topshiriqlar dinamikasi')
                    plt.xticks(rotation=45, ha='right')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    plt.close()
                    
                    # Convert BytesIO to BufferedInputFile
                    from aiogram.types import BufferedInputFile
                    input_file = BufferedInputFile(buf.getvalue(), filename="monthly.png")
                    
                    await message.answer_photo(
                        input_file, 
                        caption="📊 Oylik bajarilgan topshiriqlar dinamikasi",
                        parse_mode=ParseMode.HTML
                    )
    
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
        await message.answer("Diagrammalarni yaratishda xatolik yuz berdi.", parse_mode=ParseMode.HTML)

@router.message(F.text == "👥 Foydalanuvchilar", is_admin_filter)
async def show_users(message: Message):
    await message.answer(
        "⚠️ Foydalanuvchilar ro'yxati funksiyasi hozirda mavjud emas.\nBu funksiya Django admin panelida mavjud.",
        reply_markup=get_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📝 Yangi topshiriq", is_admin_filter)
async def new_task(message: Message):
    await message.answer(
        "⚠️ Yangi topshiriq yaratish funksiyasi hozirda mavjud emas.\nTopshiriqlar Django admin paneli orqali yaratiladi.",
        reply_markup=get_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "🔙 Asosiy menyu", is_admin_filter)
async def back_to_main_menu(message: Message):
    from keyboards.reply import get_main_menu
    await message.answer(
        "Asosiy menyuga qaytdingiz.",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("grade_task_"))
async def start_grading_task(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    task_id = int(callback.data.split("_")[2])
    
    processing_msg = await callback.message.answer("⌛ Topshiriq ma'lumotlari yuklanmoqda...", parse_mode=ParseMode.HTML)
    
    try:
        response = await get_task_detail(task_id)
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            task = response.data.get('task', {})
            
            await state.set_state(GradingState.percentage)
            await state.update_data(task_id=task_id, task_title=task.get('title'))
            
            await callback.message.answer(
                f"🔹 <b>{task.get('title')}</b> topshirig'ini baholash\n\nBajarilish darajasini foizda kiriting (0-100):",
                reply_markup=get_grading_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.answer(
                "Topshiriq ma'lumotlarini yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error in start_grading_task: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await callback.message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_admin_menu(),
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data.startswith("grade_percent_"), GradingState.percentage)
async def process_grade_percentage(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    percentage = int(callback.data.split("_")[2])
    
    await process_grading(callback.message, state, percentage)

@router.message(GradingState.percentage)
async def process_grade_input(message: Message, state: FSMContext):
    try:
        percentage = int(message.text.strip())
        if percentage < 0 or percentage > 100:
            await message.answer("Foiz 0 dan 100 gacha bo'lishi kerak. Qaytadan kiriting:", parse_mode=ParseMode.HTML)
            return
            
        await process_grading(message, state, percentage)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting (0-100):", parse_mode=ParseMode.HTML)

async def process_grading(message: Message, state: FSMContext, percentage: int):
    data = await state.get_data()
    task_id = data.get('task_id')
    task_title = data.get('task_title')
    
    status = "green" if percentage >= 85 else "yellow" if percentage >= 55 else "red"
    status_emoji = "🟢" if status == "green" else "🟡" if status == "yellow" else "🔴"
    
    processing_msg = await message.answer("⌛ Baho saqlanmoqda...", parse_mode=ParseMode.HTML)
    
    try:
        response = await grade_task(
            task_id=task_id,
            percentage=percentage,
            status=status,
            admin_id=message.from_user.id if hasattr(message, 'from_user') else None
        )
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            await message.answer(
                f"✅ <b>{task_title}</b> topshirig'i muvaffaqiyatli baholandi!\n\nBajarilish darajasi: {percentage}% {status_emoji}\nStatus: {status_emoji} {status.capitalize()}",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
        else:
            error_message = response.message or "Xatolik yuz berdi"
            await message.answer(
                f"❌ {error_message}",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error in process_grading: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_admin_menu(),
            parse_mode=ParseMode.HTML
        )
    
    await state.clear()

# Broadcasting handlers
@router.message(F.text == "📢 Xabar yuborish", is_admin_filter)
async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(BroadcastState.title)
    await message.answer(
        "📢 <b>Xabar yuborish</b>\n\nXabar sarlavhasini kiriting:",
        reply_markup=get_back_to_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(BroadcastState.title)
async def process_broadcast_title(message: Message, state: FSMContext):
    if not message.text or message.text == "🔙 Orqaga":
        await state.clear()
        await cmd_admin(message)
        return
    
    await state.update_data(title=message.text)
    await state.set_state(BroadcastState.message)
    
    await message.answer(
        "Endi xabar matnini kiriting:\n\n"
        "<i>Markdown formatini qo'llash mumkin:</i>\n"
        "- <b>Qalin</b> matn uchun: `*Qalin*` yoki `<b>Qalin</b>`\n"
        "- <i>Kursiv</i> matn uchun: `_Kursiv_` yoki `<i>Kursiv</i>`\n"
        "- <u>Tagiga chizilgan</u> matn uchun: `<u>Tagiga chizilgan</u>`\n"
        "- <code>Kod</code> matn uchun: `` `Kod` `` yoki `<code>Kod</code>`\n"
        "- <a href='https://example.com'>Havola</a> uchun: `[Havola matni](https://example.com)` yoki `<a href='https://example.com'>Havola</a>`",
        reply_markup=get_back_to_admin_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(BroadcastState.message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if not message.text or message.text == "🔙 Orqaga":
        await state.clear()
        await cmd_admin(message)
        return
    
    await state.update_data(message=message.text)
    await state.set_state(BroadcastState.target)
    
    # Preview the formatted message
    await message.answer(
        "Xabar quyidagicha ko'rinadi:\n\n"
        f"{message.text}",
        parse_mode=ParseMode.HTML
    )
    
    await message.answer(
        "Xabar kimga yuborilsin?",
        reply_markup=get_broadcast_target_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("broadcast_"), BroadcastState.target)
async def process_broadcast_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data.split("_")[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.answer(
            "Xabar yuborish bekor qilindi.",
            reply_markup=get_admin_menu(),
            parse_mode=ParseMode.HTML
        )
        return
    
    if action == "all":
        await state.update_data(target_type="all")
        await show_broadcast_confirmation(callback.message, state)
    elif action == "district":
        await state.set_state(BroadcastState.district)
        
        processing_msg = await callback.message.answer("⌛ Tumanlar ro'yxati yuklanmoqda...", parse_mode=ParseMode.HTML)
        
        try:
            response = await get_districts()
            
            with suppress(Exception):
                await processing_msg.delete()
                
            if response.success:
                districts = response.data
                await callback.message.edit_text(
                    "Qaysi tumanga yuborilsin?",
                    reply_markup=get_districts_keyboard(districts),
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.message.answer(
                    "Tumanlar ro'yxatini yuklashda xatolik yuz berdi.",
                    reply_markup=get_admin_menu(),
                    parse_mode=ParseMode.HTML
                )
                await state.clear()
        except Exception as e:
            logger.error(f"Error in process_broadcast_target (district): {e}")
            with suppress(Exception):
                await processing_msg.delete()
            await callback.message.answer(
                "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
            await state.clear()
    elif action == "mahalla":
        await state.set_state(BroadcastState.mahalla)
        
        processing_msg = await callback.message.answer("⌛ Mahallalar ro'yxati yuklanmoqda...", parse_mode=ParseMode.HTML)
        
        try:
            response = await get_mahallas()
            
            with suppress(Exception):
                await processing_msg.delete()
                
            if response.success:
                mahallas = response.data
                await callback.message.edit_text(
                    "Qaysi mahallaga yuborilsin?",
                    reply_markup=get_mahallas_keyboard(mahallas),
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.message.answer(
                    "Mahallalar ro'yxatini yuklashda xatolik yuz berdi.",
                    reply_markup=get_admin_menu(),
                    parse_mode=ParseMode.HTML
                )
                await state.clear()
        except Exception as e:
            logger.error(f"Error in process_broadcast_target (mahalla): {e}")
            with suppress(Exception):
                await processing_msg.delete()
            await callback.message.answer(
                "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
            await state.clear()
    elif action == "back_target":
        await state.set_state(BroadcastState.target)
        await callback.message.edit_text(
            "Xabar kimga yuborilsin?",
            reply_markup=get_broadcast_target_keyboard(),
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data.startswith("district_"), BroadcastState.district)
async def process_district_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    district_id = int(callback.data.split("_")[1])
    
    await state.update_data(target_type="district", target_id=district_id)
    await show_broadcast_confirmation(callback.message, state)

@router.callback_query(F.data.startswith("mahalla_"), BroadcastState.mahalla)
async def process_mahalla_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    mahalla_id = int(callback.data.split("_")[1])
    
    await state.update_data(target_type="mahalla", target_id=mahalla_id)
    await show_broadcast_confirmation(callback.message, state)

async def show_broadcast_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data.get('title')
    msg_text = data.get('message')
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    
    target_text = "Barcha foydalanuvchilarga"
    if target_type == "district":
        district_response = await get_districts()
        if district_response.success:
            districts = district_response.data
            for district in districts:
                if district.get('id') == target_id:
                    target_text = f"{district.get('name')} tumanidagi foydalanuvchilarga"
                    break
    elif target_type == "mahalla":
        mahalla_response = await get_mahallas()
        if mahalla_response.success:
            mahallas = mahalla_response.data
            for mahalla in mahallas:
                if mahalla.get('id') == target_id:
                    target_text = f"{mahalla.get('name')} mahallasidagi foydalanuvchilarga"
                    break
    
    confirmation_text = (
        f"📢 <b>Xabar yuborish tasdiqlash</b>\n\n"
        f"<b>Sarlavha:</b> {title}\n"
        f"<b>Matn:</b> {msg_text}\n\n"
        f"<b>Kimga:</b> {target_text}\n\n"
        f"Xabarni yuborishni tasdiqlaysizmi?"
    )
    
    await state.set_state(BroadcastState.confirm)
    
    await message.edit_text(
        confirmation_text,
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("broadcast_"), BroadcastState.confirm)
async def process_broadcast_confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data.split("_")[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.answer(
            "Xabar yuborish bekor qilindi.",
            reply_markup=get_admin_menu(),
            parse_mode=ParseMode.HTML
        )
        return
    
    if action == "confirm":
        data = await state.get_data()
        title = data.get('title')
        msg_text = data.get('message')
        target_type = data.get('target_type')
        target_id = data.get('target_id')
        
        processing_msg = await callback.message.answer("⌛ Xabar yuborilmoqda...", parse_mode=ParseMode.HTML)
        
        try:
            response = await send_broadcast(
                title=title,
                message=msg_text,
                target_type=target_type,
                target_id=target_id,
                admin_id=callback.from_user.id
            )
            
            with suppress(Exception):
                await processing_msg.delete()
                
            if response.success:
                telegram_ids = response.data.get('telegram_ids', [])
                sent_count = len(telegram_ids)
                
                # Send messages to users
                bot = await get_bot()
                success_count = 0
                
                for user_id in telegram_ids:
                    try:
                        await bot.send_message(
                            user_id,
                            f"📢 <b>{title}</b>\n\n{msg_text}",
                            parse_mode=ParseMode.HTML
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send message to user {user_id}: {e}")
                    
                    await asyncio.sleep(0.05)
                
                await callback.message.answer(
                    f"✅ Xabar muvaffaqiyatli yuborildi!\n\n"
                    f"Yuborilgan foydalanuvchilar soni: {success_count}/{sent_count}",
                    reply_markup=get_admin_menu(),
                    parse_mode=ParseMode.HTML
                )
            else:
                error_message = response.message or "Xatolik yuz berdi"
                await callback.message.answer(
                    f"❌ {error_message}",
                    reply_markup=get_admin_menu(),
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error in process_broadcast_confirmation: {e}")
            with suppress(Exception):
                await processing_msg.delete()
            await callback.message.answer(
                "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_admin_menu(),
                parse_mode=ParseMode.HTML
            )
        
        await state.clear()

