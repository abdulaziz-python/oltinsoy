import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

API_URL = os.getenv("API_URL", "https://oltinsoy.onrender.com/api")
API_BASE_URL = "https://oltinsoy.onrender.com/api/"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "1"))
API_POOL_SIZE = int(os.getenv("API_POOL_SIZE", "100"))

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "False").lower() in ("true", "1", "t")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "media")

