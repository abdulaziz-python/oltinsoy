from aiogram import Bot
from database import SessionLocal
from models.base import User
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def broadcast_message(bot: Bot, message: str) -> tuple[int, int]:
    successful, failed = 0, 0
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        for user in users:
            try:
                await bot.send_message(user.telegram_id, message)
                successful += 1
                logger.info(f"Message sent to {user.telegram_id}")
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send message to {user.telegram_id}: {e}")
    finally:
        db.close()
    
    return successful, failed

