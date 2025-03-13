from aiogram import Bot
from config import BOT_TOKEN

_bot = None

async def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=BOT_TOKEN)
    return _bot
