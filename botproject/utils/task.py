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

