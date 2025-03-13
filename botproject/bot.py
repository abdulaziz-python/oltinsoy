import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import user_router, admin_router, task_router
from utils.logger import setup_logger

logger = setup_logger(__name__)

class HTMLBot(Bot):
    async def send_message(self, chat_id, text, **kwargs):
        if 'parse_mode' not in kwargs:
            kwargs['parse_mode'] = ParseMode.HTML
        return await super().send_message(chat_id, text, **kwargs)

    async def answer(self, message, text, **kwargs):
        if 'parse_mode' not in kwargs:
            kwargs['parse_mode'] = ParseMode.HTML
        return await super().answer(message, text, **kwargs)

async def main():
    bot = HTMLBot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(task_router)

    logger.info("Starting bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
