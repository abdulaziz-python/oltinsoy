import functools
import aiohttp
from aiogram import types

from config import API_URL, ADMIN_IDS

async def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
        
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/user-info/?telegram_id={user_id}") as response:
            if response.status == 200:
                data = await response.json()
                user = data.get('user', {})
                return user.get('is_staff', False)
            return False

def admin_only(func):
    @functools.wraps(func)
    async def wrapper(message_or_query, *args, **kwargs):
        if isinstance(message_or_query, types.Message):
            user_id = message_or_query.from_user.id
            if not await is_admin(user_id):
                await message_or_query.answer("Sizda bu amalni bajarish uchun huquq yo'q.")
                return
        elif isinstance(message_or_query, types.CallbackQuery):
            user_id = message_or_query.from_user.id
            if not await is_admin(user_id):
                await message_or_query.answer("Sizda bu amalni bajarish uchun huquq yo'q.", show_alert=True)
                return
        
        return await func(message_or_query, *args, **kwargs)
    return wrapper

