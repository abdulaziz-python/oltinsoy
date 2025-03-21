from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.user import LoginState, TaskSubmissionState 
from keyboards.reply import get_phone_number_kb, get_main_menu
from keyboards.inline import (
    get_task_keyboard, get_task_detail_keyboard, 
    get_task_submission_keyboard, get_back_to_tasks_keyboard,
    get_confirm_keyboard, get_task_list_keyboard
)
from utils.api import (
    get_user_info, verify_user, get_user_tasks, get_tasks, 
    get_task_detail, update_task_status, submit_task_progress
)
from utils.logger import setup_logger
import asyncio
from contextlib import suppress
import os
import tempfile
import aiohttp
from config import MEDIA_ROOT

logger = setup_logger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    processing_msg = await message.answer("⌛ Tekshirilmoqda...", parse_mode="HTML")

    try:
        async with asyncio.timeout(5):
            response = await get_user_info(message.from_user.id)

            if response.success:
                user = response.data.get('user', {})
                welcome_text = (
                    f"Xush kelibsiz, {user.get('full_name', 'Foydalanuvchi')}!\n\n"
                    f"Lavozim: {user.get('job_title_name', 'Mavjud emas')}\n"
                    f"Mahalla: {user.get('mahalla_name', 'Mavjud emas')}\n"
                    f"Tuman: {user.get('tuman_name', 'Mavjud emas')}"
                )

                with suppress(Exception):
                    await processing_msg.delete()
                await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")
                logger.info(f"User {message.from_user.id} logged in successfully")
            else:
                await state.set_state(LoginState.phone_number)
                with suppress(Exception):
                    await processing_msg.delete()
                await message.answer(
                    "Assalomu alaykum! Botdan foydalanish uchun ro'yxatdan o'ting.\n"
                    "Telefon raqamingizni yuboring:",
                    reply_markup=get_phone_number_kb(),
                    parse_mode="HTML"
                )
                logger.info(f"User {message.from_user.id} started registration")

    except asyncio.TimeoutError:
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Serverga ulanishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan /start buyrug'ini yuboring.",
            parse_mode="HTML"
        )


@router.message(F.text == "📋 Mening topshiriqlarim")
async def show_tasks(message: Message):
    processing_msg = await message.answer("⌛ Topshiriqlar yuklanmoqda...", parse_mode="HTML")

    try:
        response = await get_user_tasks(message.from_user.id)

        with suppress(Exception):
            await processing_msg.delete()

        if response and response.success:
            tasks = response.data.get('tasks', [])

            if not tasks:
                await message.answer(
                    "Sizda hozircha topshiriqlar mavjud emas.",
                    reply_markup=get_main_menu(),
                    parse_mode="HTML"
                )
                return

            active_tasks = [t for t in tasks if t.get('status') == 'active']
            completed_tasks = [t for t in tasks if t.get('status') == 'completed']
            rejected_tasks = [t for t in tasks if t.get('status') == 'rejected']

            if active_tasks:
                await message.answer("📋 <b>Faol topshiriqlar:</b>", parse_mode="HTML")
                for task in active_tasks:
                    task_text = (
                        f"🔹 <b>{task.get('title')}</b>\n"
                        f"📅 Muddati: {task.get('deadline', 'Noma\'lum')}\n"
                        f"📝 {task.get('description', '')[:100]}..."
                    )
                    await message.answer(
                        task_text,
                        reply_markup=get_task_keyboard(task.get('id')),
                        parse_mode="HTML"
                    )

            if completed_tasks:
                await message.answer("✅ <b>Bajarilgan topshiriqlar:</b>", parse_mode="HTML")
                for task in completed_tasks[:3]:
                    task_text = (
                        f"🔹 <b>{task.get('title')}</b>\n"
                        f"📅 Muddati: {task.get('deadline', 'Noma\'lum')}\n"
                        f"✅ Bajarilgan: {task.get('completed_at', 'Noma\'lum')}"
                    )
                    await message.answer(task_text, parse_mode="HTML")

                if len(completed_tasks) > 3:
                    await message.answer(f"... va yana {len(completed_tasks) - 3} ta bajarilgan topshiriq", parse_mode="HTML")

            if rejected_tasks:
                await message.answer("❌ <b>Rad etilgan topshiriqlar:</b>", parse_mode="HTML")
                for task in rejected_tasks[:3]:
                    rejection_reason = task.get('rejection_reason', 'Sabab ko\'rsatilmagan')
                    task_text = (
                        f"🔹 <b>{task.get('title')}</b>\n"
                        f"📅 Muddati: {task.get('deadline', 'Noma\'lum')}\n"
                        f"❌ Rad etilgan: {task.get('rejected_at', 'Noma\'lum')}\n"
                        f"📝 Sababi: {rejection_reason}"
                    )
                    await message.answer(task_text, parse_mode="HTML")

                if len(rejected_tasks) > 3:
                    await message.answer(f"... va yana {len(rejected_tasks) - 3} ta rad etilgan topshiriq", parse_mode="HTML")

        else:
            await message.answer(
                "Topshiriqlarni yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )


@router.message(F.text == "📊 Mening statistikam")
async def show_stats(message: Message):
    processing_msg = await message.answer("⌛ Statistika yuklanmoqda...", parse_mode="HTML")

    try:
        response = await get_user_tasks(message.from_user.id)

        with suppress(Exception):
            await processing_msg.delete()

        if response.success:
            tasks = response.data.get('tasks', [])

            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.get('status') == 'completed')
            pending_tasks = sum(1 for t in tasks if t.get('status') == 'active')
            rejected_tasks = sum(1 for t in tasks if t.get('status') == 'rejected')

            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            stats_text = (
                f"📊 <b>Sizning statistikangiz:</b>\n\n"
                f"📋 Jami topshiriqlar: {total_tasks}\n"
                f"✅ Bajarilgan: {completed_tasks} ({completion_rate:.1f}%)\n"
                f"⏳ Jarayonda: {pending_tasks}\n"
                f"❌ Rad etilgan: {rejected_tasks}\n\n"
            )

            recent_tasks = sorted(tasks, key=lambda x: x.get('updated_at', ''), reverse=True)[:5]
            if recent_tasks:
                stats_text += f"🔄 <b>So'nggi faoliyat:</b>\n"
                for task in recent_tasks:
                    status_text = ""
                    if task.get('status') == 'completed':
                        status_text = "✅ Bajarilgan"
                    elif task.get('status') == 'active':
                        status_text = "⏳ Jarayonda"
                    elif task.get('status') == 'rejected':
                        status_text = "❌ Rad etilgan"

                    stats_text += f"• {task.get('updated_at', 'N/A')}: {task.get('title')} - {status_text}\n"

            await message.answer(
                stats_text,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "Statistikani yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

@router.message(F.text == "❓ Yordam")
async def show_help(message: Message):
    help_text = (
        "🔍 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1️⃣ <b>Topshiriqlarni ko'rish</b>\n"
        "   • 📋 Mening topshiriqlarim - faol topshiriqlarni ko'rish\n\n"
        "2️⃣ <b>Topshiriq bilan ishlash</b>\n"
        "   • ✅ Bajarildi - topshiriqni bajarilgan deb belgilash\n"
        "   • 📝 Hisobot - topshiriq bo'yicha hisobot yuborish\n"
        "   • 📊 Statistika - topshiriq statistikasini ko'rish\n\n"
        "3️⃣ <b>Statistika</b>\n"
        "   • 📊 Mening statistikam - shaxsiy statistikani ko'rish\n\n"
        "❓ Qo'shimcha savollar bo'lsa, administrator bilan bog'laning"
    )
    await message.answer(help_text, reply_markup=get_main_menu(), parse_mode="HTML")

@router.message(LoginState.phone_number)
async def process_phone(message: Message, state: FSMContext):
    try:
        if not message.contact and not message.text:
            await message.answer(
                "Iltimos, telefon raqamingizni yuboring yoki kiriting.\n"
                "Format: +998 XX XXX XX XX",
                parse_mode="HTML"
            )
            return

        phone = message.contact.phone_number if message.contact else message.text

        await state.update_data(phone_number=phone)
        await state.set_state(LoginState.jshir)
        await message.answer(
            "Endi JSHIR raqamingizni kiriting:\n"
            "Masalan: 12345678901234",
            parse_mode="HTML"
        )
        logger.info(f"User {message.from_user.id} provided phone number: {phone}")
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan telefon raqamingizni yuboring.",
            parse_mode="HTML"
        )

@router.message(LoginState.jshir)
async def process_jshir(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("Iltimos, JSHIR raqamingizni kiriting.", parse_mode="HTML")
            return

        user_data = await state.get_data()
        phone = user_data.get('phone_number')

        processing_msg = await message.answer("Ma'lumotlar tekshirilmoqda...", parse_mode="HTML")

        try:
            response = await verify_user(phone, message.text, message.from_user.id)

            if response.success:
                user = response.data.get('user', {})

                await state.clear()

                welcome_text = (
                    f"Xush kelibsiz, {user.get('full_name', 'Foydalanuvchi')}!\n\n"
                    f"Lavozim: {user.get('job_title_name', 'Mavjud emas')}\n"
                    f"Mahalla: {user.get('mahalla_name', 'Mavjud emas')}\n"
                    f"Tuman: {user.get('tuman_name', 'Mavjud emas')}"
                )

                with suppress(Exception):
                    await processing_msg.delete()
                await message.answer(
                    welcome_text,
                    reply_markup=get_main_menu(),
                    parse_mode="HTML"
                )

                help_text = (
                    "🔍 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
                    "1️⃣ <b>Topshiriqlarni ko'rish</b>\n"
                    "   • 📋 Mening topshiriqlarim - faol topshiriqlarni ko'rish\n\n"
                    "2️⃣ <b>Topshiriq bilan ishlash</b>\n"
                    "   • ✅ Bajarildi - topshiriqni bajarilgan deb belgilash\n"
                    "   • 📝 Hisobot - topshiriq bo'yicha hisobot yuborish\n"
                    "   • 📊 Statistika - topshiriq statistikasini ko'rish\n\n"
                    "❓ Yordam kerak bo'lsa, /help buyrug'ini yuboring"
                )
                await message.answer(help_text, parse_mode="HTML")

                logger.info(f"User {message.from_user.id} successfully logged in")

            else:
                error_message = response.message or 'Xatolik yuz berdi'
                with suppress(Exception):
                    await processing_msg.delete()
                await message.answer(
                    f"{error_message}\n\n"
                    "Qaytadan urinish uchun /start buyrug'ini yuboring.",
                    parse_mode="HTML"
                )
                await state.clear()
                logger.warning(f"Login failed for phone: {phone}, JSHIR: {message.text}")

        except Exception as e:
            with suppress(Exception):
                await processing_msg.delete()
            await message.answer(
                "Serverda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.\n"
                "Qaytadan urinish uchun /start buyrug'ini yuboring.",
                parse_mode="HTML"
            )
            await state.clear()
            logger.error(f"Error in verify_user request: {e}")

    except Exception as e:
        logger.error(f"Error in process_jshir: {e}")
        await message.answer(
            "Xatolik yuz berdi. Qaytadan urinish uchun /start buyrug'ini yuboring.",
            parse_mode="HTML"
        )
        await state.clear()

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    user_id = message.from_user.id
    
    processing_msg = await message.answer("⌛ Topshiriqlar yuklanmoqda...", parse_mode="HTML")
    
    try:
        response = await get_tasks(user_id=user_id)
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            tasks = response.data.get('tasks', [])
            
            if not tasks:
                await message.answer("Sizga hozircha topshiriqlar berilmagan.", parse_mode="HTML")
                return
                
            await message.answer(
                "📋 <b>Topshiriqlar ro'yxati</b>\n\nBatafsil ma'lumot olish uchun topshiriqni tanlang:",
                reply_markup=get_task_list_keyboard(tasks),
                parse_mode="HTML"
            )
        else:
            await message.answer("Topshiriqlarni yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_tasks: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

# Handle task_view_X callbacks
@router.callback_query(F.data.startswith("task_view_"))
async def process_task_view(callback: CallbackQuery):
    await callback.answer()
    try:
        task_id = int(callback.data.split("_")[2])
        await show_task_detail(callback.message, task_id)
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing task_view callback data: {e}")
        await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

# Handle task_complete_X callbacks
@router.callback_query(F.data.startswith("task_complete_"))
async def process_task_complete(callback: CallbackQuery):
    await callback.answer()
    try:
        task_id = int(callback.data.split("_")[2])
        
        # Show processing message
        processing_msg = await callback.message.answer("⌛ Topshiriq bajarilmoqda...", parse_mode="HTML")
        
        # Import the update_task_status function
        from utils.api import update_task_status
        
        # Call the API to update task status
        response = await update_task_status(
            task_id=task_id,
            status="completed",
            telegram_id=callback.from_user.id
        )
        
        # Delete processing message
        with suppress(Exception):
            await processing_msg.delete()
        
        if response.success:
            await callback.message.answer(
                "✅ Topshiriq muvaffaqiyatli bajarildi!",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            
            # Notify admins about completed task (optional)
            from utils.task import notify_admins_about_completed_task
            await notify_admins_about_completed_task(task_id, callback.from_user.id)
        else:
            error_message = response.message or "Xatolik yuz berdi"
            await callback.message.answer(
                f"❌ {error_message}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing task_complete callback data: {e}")
        await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

# Handle task_report_X callbacks
@router.callback_query(F.data.startswith("task_report_"))
async def process_task_report(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        task_id = int(callback.data.split("_")[2])
        await state.set_state(TaskSubmissionState.comment)
        await state.update_data(task_id=task_id)
        
        await callback.message.answer(
            "📝 <b>Topshiriqni topshirish</b>\n\n"
            "Izoh yozing (ixtiyoriy):",
            reply_markup=get_task_submission_keyboard(),
            parse_mode="HTML"
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing task_report callback data: {e}")
        await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

# Handle task_stats_X callbacks
@router.callback_query(F.data.startswith("task_stats_"))
async def process_task_stats(callback: CallbackQuery):
    await callback.answer()
    try:
        task_id = int(callback.data.split("_")[2])
        await callback.message.answer("Statistika ma'lumotlari yuklanmoqda...", parse_mode="HTML")
        # Implement task statistics logic here
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing task_stats callback data: {e}")
        await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

# Handle simple task_X callbacks (from task list)
@router.callback_query(F.data.startswith("task_"))
async def process_task_selection(callback: CallbackQuery):
    await callback.answer()
    # Check if this is a simple task_ID format (not task_action_ID)
    parts = callback.data.split("_")
    if len(parts) == 2:
        try:
            task_id = int(parts[1])
            await show_task_detail(callback.message, task_id)
        except ValueError as e:
            logger.error(f"Invalid task ID in callback data: {callback.data}, error: {e}")
            await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")
    # If it's not a simple task_ID format, it should be handled by other handlers

async def show_task_detail(message: Message, task_id: int):
  processing_msg = await message.answer("⌛ Topshiriq ma'lumotlari yuklanmoqda...", parse_mode="HTML")
  
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
              f"<b>Status:</b> {status_emoji} {task.get('status', 'active').capitalize()}\n"
              f"<b>Bajarilish darajasi:</b> {task.get('completion_percentage', 0)}%\n"
              f"<b>Muddat:</b> {deadline}\n"
              f"<b>Yaratilgan sana:</b> {task.get('created_at', '')}\n"
          )
          
          mahallas = task.get('mahallas', [])
          if mahallas:
              detail_text += "\n<b>Mahallalar:</b>\n"
              for mahalla in mahallas:
                  detail_text += f"- {mahalla.get('name')}\n"
          
          await message.answer(
              detail_text,
              reply_markup=get_task_detail_keyboard(task_id, task.get('status', 'active')),
              parse_mode="HTML"
          )

          # Handle files safely through API
          files = task.get('files', [])
          if files:
              await message.answer(f"📎 <b>Topshiriq fayllari ({len(files)}):</b>", parse_mode="HTML")
              
              for file in files:
                  file_url = file.get('url')
                  file_name = file.get('name')
                  
                  if file_url:
                      try:
                          # Download file from API URL
                          async with aiohttp.ClientSession() as session:
                              async with session.get(file_url) as resp:
                                  if resp.status == 200:
                                      file_content = await resp.read()
                                      
                                      # Create a BytesIO object to send as document
                                      from io import BytesIO
                                      file_obj = BytesIO(file_content)
                                      
                                      # Send as document
                                      await message.answer_document(
                                          types.BufferedInputFile(
                                              file_obj.getvalue(),
                                              filename=file_name
                                          ),
                                          caption=f"📎 {file_name}"
                                      )
                                  else:
                                      await message.answer(f"❌ Faylni yuklab bo'lmadi: {file_name}", parse_mode="HTML")
                      except Exception as e:
                          logger.error(f"Error downloading file {file_name}: {e}")
                          await message.answer(f"❌ Faylni yuklab bo'lmadi: {file_name}", parse_mode="HTML")
      else:
          await message.answer(
              "Topshiriq ma'lumotlarini yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
              parse_mode="HTML"
          )
  except Exception as e:
      logger.error(f"Error in show_task_detail: {e}")
      with suppress(Exception):
          await processing_msg.delete()
      await message.answer(
          "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
          parse_mode="HTML"
      )

@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks_list(callback: CallbackQuery):
    await callback.answer()
    await cmd_tasks(callback.message)

@router.callback_query(F.data.startswith("submit_task_"))
async def start_task_submission(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        task_id = int(callback.data.split("_")[2])
        
        await state.set_state(TaskSubmissionState.comment)
        await state.update_data(task_id=task_id)
        
        await callback.message.answer(
            "📝 <b>Topshiriqni topshirish</b>\n\n"
            "Izoh yozing (ixtiyoriy):",
            reply_markup=get_task_submission_keyboard(),
            parse_mode="HTML"
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing submit_task callback data: {e}")
        await callback.message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", parse_mode="HTML")

@router.message(TaskSubmissionState.comment)
async def process_task_comment(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await cmd_tasks(message)
        return
    
    comment = message.text
    await state.update_data(comment=comment)
    await state.set_state(TaskSubmissionState.files)
    
    await message.answer(
        "📎 <b>Fayllarni yuklang</b>\n\n"
        "Topshiriq uchun fayllarni yuklang (ixtiyoriy).\n"
        "Fayllarni yuklashni tugatgach, \"✅ Yuborishni yakunlash\" tugmasini bosing.",
        reply_markup=get_back_to_tasks_keyboard(),
        parse_mode="HTML"
    )

@router.message(TaskSubmissionState.files, F.document)
async def process_task_files(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    
    document = message.document
    file_id = document.file_id
    file_name = document.file_name
    
    files.append({
        'file_id': file_id,
        'file_name': file_name
    })
    
    await state.update_data(files=files)
    await message.answer(
        f"✅ Fayl qabul qilindi: {file_name}\n\nYana fayl yuklash mumkin yoki \"✅ Yuborishni yakunlash\" tugmasini bosing.",
        parse_mode="HTML"
    )

@router.message(TaskSubmissionState.files, F.text == "✅ Yuborishni yakunlash")
async def finish_task_submission(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get('task_id')
    comment = data.get('comment', '')
    files = data.get('files', [])
    
    processing_msg = await message.answer("⌛ Topshiriq yuborilmoqda...", parse_mode="HTML")
    
    try:
        # Call the API to submit the task progress
        response = await submit_task_progress(
            task_id=task_id,
            telegram_id=message.from_user.id,
            description=comment,
            files=files
        )
        
        with suppress(Exception):
            await processing_msg.delete()
            
        if response.success:
            await message.answer(
                "✅ <b>Topshiriq muvaffaqiyatli yuborildi!</b>\n\n"
                f"Izoh: {comment}\n"
                f"Yuklangan fayllar soni: {len(files)}",
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
        logger.error(f"Error in finish_task_submission: {e}")
        with suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    
    await state.clear()

