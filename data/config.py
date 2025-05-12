import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# .env fayl ichidan quyidagilarni o'qiymiz
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Bot token
ADMINS = os.getenv("ADMINS", "").split(",") if os.getenv("ADMINS") else []  # adminlar ro'yxati

DATABASE_PATH = 'back/db.sqlite3'

# Redis ishlatish yoki yo'q
USE_REDIS = os.getenv("USE_REDIS", "false").lower() in ['true', 't', '1', 'yes', 'y']

# Redis konfiguratsiyasi
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = f"redis://{'' if REDIS_PASSWORD is None else f':{REDIS_PASSWORD}@'}{REDIS_HOST}:{REDIS_PORT}"
REDIS_CACHE_DB = int(os.getenv("REDIS_CACHE_DB", "0"))
REDIS_FSM_DB = int(os.getenv("REDIS_FSM_DB", "1"))