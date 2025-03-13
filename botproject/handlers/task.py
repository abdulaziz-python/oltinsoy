from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from utils.api import get_task_detail, update_task_status, submit_task_progress, get_task_stats, get_user_info
from utils.logger import setup_logger
from keyboards.inline import get_task_detail_keyboard, get_confirm_keyboard
from keyboards.reply import get_main_menu, get_cancel_keyboard
from states.user import TaskState
from contextlib import suppress
import asyncio
from utils.bot import get_bot
from config import ADMIN_IDS
import os



logger = setup_logger(__name__)
router = Router()

@router.callback_query(F.data.startswith("task_"))
async def process_task_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    task_id = int(callback.data.split("_")[2])

    if action == "view":
        await show_task_detail(callback, task_id)
    elif action == "complete":
        await start_complete_task(callback, task_id, state)
    elif action == "report":
        await start_submit_report(callback, task_id, state)
    elif action == "stats":
        await show_task_stats(callback, task_id)
    else:
        await callback.answer("Noma'lum amal")

async def show_task_detail(message: Message, task_id: int):
    processing_msg = await message.answer("⌛ Topshiriq ma'lumotlari yuklanmoqda...")
    
    try:
        response = await get_task_detail(task_id)
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            task = response.data.get('task', {})
            
            status_emoji = "✅" if task.get('status') == 'completed' else "❌" if task.get('status') == 'rejected' else "⏳"
            deadline = task.get('deadline', 'Belgilanmagan')
            
            description = task.get('description', '')
            if len(description) > 500:
                description = description[:500] + "..."
            
            detail_text = (
                f"📝 <b>{task.get('title')}</b>\n\n"
                f"{description}\n\n"
                f"<b>Status:</b> {status_emoji} {task.get('status').capitalize()}\n"
                f"<b>Bajarilish darajasi:</b> {task.get('completion_percentage')}%\n"
                f"<b>Muddat:</b> {deadline}\n"
                f"<b>Yaratilgan sana:</b> {task.get('created_at')}\n"
            )
            mahallas = task.get('mahallas', [])
            if mahallas:
                detail_text += "\n<b>Mahallalar:</b>\n"
                for mahalla in mahallas:
                    detail_text += f"- {mahalla.get('name')}\n"
            
           
            await message.answer(
                detail_text,
                reply_markup=get_task_detail_keyboard(task_id, task.get('status'))
            )
            
            files = task.get('files', [])
            if files:
                await message.answer(f"📎 <b>Topshiriq fayllari ({len(files)}):</b>")
                
                for file in files:
                    file_url = file.get('url')
                    file_name = file.get('name')
                    
                    if file_url:
                        try:
                            temp_dir = tempfile.mkdtemp()
                            temp_file_path = os.path.join(temp_dir, file_name)
                            
                            async with aiohttp.ClientSession() as session:
                                async with session.get(file_url) as resp:
                                    if resp.status == 200:
                                        with open(temp_file_path, 'wb') as fd:
                                            while True:
                                                chunk = await resp.content.read(1024)
                                                if not chunk:
                                                    break
                                                fd.write(chunk)
                                        
                                        await message.answer_document(
                                            FSInputFile(temp_file_path, filename=file_name),
                                            caption=f"📎 {file_name}"
                                        )
                                        
                                        os.remove(temp_file_path)
                                        os.rmdir(temp_dir)
                                    else:
                                        await message.answer(f"❌ Faylni yuklab bo'lmadi: {file_name}")
                        except Exception as e:
                            logger.error(f"Error downloading file {file_name}: {e}")
                            await message.answer(f"❌ Faylni yuklab bo'lmadi: {file_name}")
        else:
            await message.answer(
                "Topshiriq ma'lumotlarini yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
            )
    except Exception as e:
        logger.error(f"Error in show_task_detail: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
        )

async def start_complete_task(callback: CallbackQuery, task_id: int, state: FSMContext):
    await callback.answer()

    await state.set_state(TaskState.confirm_completion)
    await state.update_data(task_id=task_id)

    await callback.message.answer(
        "Topshiriqni bajarilgan deb belgilashni tasdiqlaysizmi?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_"), TaskState.confirm_completion)
async def process_complete_confirmation(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]

    if action == "yes":
        await complete_task(callback, state)
    else:
        await state.clear()
        await callback.answer("Bekor qilindi")
        await callback.message.delete()

async def complete_task(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    processing_msg = await callback.message.answer("⌛ Topshiriq bajarilmoqda...", parse_mode="HTML")

    try:
        data = await state.get_data()
        task_id = data.get('task_id')

        response = await update_task_status(
            task_id=task_id,
            status="completed",
            telegram_id=callback.from_user.id
        )

        await state.clear()

        with suppress(Exception):
            await processing_msg.delete()
            await callback.message.delete()

        if response.success:
            await callback.message.answer(
                "✅ Topshiriq muvaffaqiyatli bajarildi!",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

            await notify_admins_about_completed_task(task_id, callback.from_user.id)
        else:
            error_message = response.message or "Xatolik yuz berdi"
            await callback.message.answer(
                f"❌ {error_message}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        await state.clear()
        with suppress(Exception):
            await processing_msg.delete()
        await callback.message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

async def notify_admins_about_completed_task(task_id: int, user_id: int):
    try:
        from utils.api import get_task_detail, get_user_info
        from config import ADMIN_IDS
        from utils.bot import get_bot
        from keyboards.admin import get_task_grading_keyboard
        from utils.logger import setup_logger
        
        logger = setup_logger(__name__)
        
        task_response = await get_task_detail(task_id)
        user_response = await get_user_info(user_id)
        
        if not task_response.success or not user_response.success:
            logger.error("Failed to get task or user details for admin notification")
            return
            
        task = task_response.data.get('task', {})
        user = user_response.data.get('user', {})
        
        notification = (
            f"🔔 <b>Yangi bajarilgan topshiriq!</b>\n\n"
            f"🔹 <b>Topshiriq:</b> {task.get('title')}\n"
            f"👤 <b>Foydalanuvchi:</b> {user.get('full_name')}\n"
            f"🏙️ <b>Mahalla:</b> {user.get('mahalla_name')}\n"
            f"📅 <b>Bajarilgan vaqt:</b> {task.get('completed_at')}\n\n"
            f"Ushbu topshiriqni baholash uchun quyidagi tugmani bosing:"
        )
        
        keyboard = get_task_grading_keyboard(task_id)
        
        bot = await get_bot()
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    notification,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in notify_admins_about_completed_task: {e}")

    

async def start_submit_report(callback: CallbackQuery, task_id: int, state: FSMContext):
    await callback.answer()

    await state.set_state(TaskState.report_description)
    await state.update_data(task_id=task_id)

    await callback.message.answer(
        "Topshiriq bo'yicha hisobot yuborish uchun matn kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "❌ Bekor qilish", TaskState.report_description)
@router.message(F.text == "❌ Bekor qilish", TaskState.report_files)
async def cancel_report(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Hisobot yuborish bekor qilindi.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.message(TaskState.report_description)
async def process_report_description(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Iltimos, hisobot uchun matn kiriting.", parse_mode="HTML")
        return

    await state.update_data(description=message.text)
    await state.set_state(TaskState.report_files)

    await message.answer(
        "Endi hisobotga fayllarni biriktiring (ixtiyoriy).\n"
        "Fayllarni yuborib bo'lgach, \"✅ Yuborish\" tugmasini bosing.",
        reply_markup=get_cancel_keyboard(with_submit=True),
        parse_mode="HTML"
    )

@router.message(F.text == "✅ Yuborish", TaskState.report_files)
async def submit_report(message: Message, state: FSMContext):
    processing_msg = await message.answer("⌛ Hisobot yuborilmoqda...", parse_mode="HTML")

    try:
        data = await state.get_data()
        task_id = data.get('task_id')
        description = data.get('description')
        files = data.get('files', [])

        response = await submit_task_progress(
            task_id=task_id,
            telegram_id=message.from_user.id,
            description=description,
            files=files
        )

        await state.clear()

        with suppress(Exception):
            await processing_msg.delete()

        if response.success:
            await message.answer(
                "✅ Hisobot muvaffaqiyatli yuborildi!",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
        else:
            error_message = response.message or "Xatolik yuz berdi"
            await message.answer(
                f"❌ {error_message}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in submit_report: {e}")
        await state.clear()
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

@router.message(F.photo | F.document | F.video, TaskState.report_files)
async def process_report_file(message: Message, state: FSMContext):
    try:
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id
        elif message.video:
            file_id = message.video.file_id

        if file_id:
            data = await state.get_data()
            files = data.get('files', [])
            files.append({'file_id': file_id})
            await state.update_data(files=files)

            await message.answer(
                f"✅ Fayl qo'shildi. Jami fayllar soni: {len(files)}.\n"
                f"Yana fayl qo'shish uchun faylni yuboring yoki \"✅ Yuborish\" tugmasini bosing.",
                reply_markup=get_cancel_keyboard(with_submit=True),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ Fayl qo'shilmadi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_cancel_keyboard(with_submit=True),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in process_report_file: {e}")
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_cancel_keyboard(with_submit=True),
            parse_mode="HTML"
        )

async def show_task_stats(callback: CallbackQuery, task_id: int):
    await callback.answer()
    processing_msg = await callback.message.answer("⌛ Statistika yuklanmoqda...", parse_mode="HTML")

    try:
        response = await get_task_stats(task_id)

        with suppress(Exception):
            await processing_msg.delete()

        if response.success:
            stats = response.data.get('stats', {})

            total_users = stats.get('total_users', 0)
            completed_users = stats.get('completed_users', 0)
            pending_users = stats.get('pending_users', 0)

            completion_rate = (completed_users / total_users * 100) if total_users > 0 else 0

            stats_text = (
                f"📊 <b>Topshiriq statistikasi:</b>\n\n"
                f"👥 Jami foydalanuvchilar: {total_users}\n"
                f"✅ Bajarilgan: {completed_users} ({completion_rate:.1f}%)\n"
                f"⏳ Jarayonda: {pending_users}\n\n"
            )

            mahalla_stats = stats.get('mahalla_stats', [])
            if mahalla_stats:
                stats_text += f"🏙️ <b>Mahallalar bo'yicha:</b>\n"
                for mahalla in mahalla_stats:
                    m_completion_rate = (mahalla.get('completed', 0) / mahalla.get('total', 0) * 100) if mahalla.get('total', 0) > 0 else 0
                    stats_text += f"• {mahalla.get('name')}: {mahalla.get('completed', 0)}/{mahalla.get('total', 0)} ({m_completion_rate:.1f}%)\n"

            await callback.message.answer(stats_text, parse_mode="HTML")
        else:
            await callback.message.answer(
                "Statistikani yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in show_task_stats: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await callback.message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
