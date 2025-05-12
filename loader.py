from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
import asyncio
import json

from data import config
from data.db_commands import DataBase

# logging konfiguratsiyasi
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Redis connection pool
redis_pool = None
redis_connection = None
USE_REDIS = config.USE_REDIS if hasattr(config, 'USE_REDIS') else False


# Redis bog'lanishni yaratish
async def init_redis():
    global redis_pool, redis_connection
    if not USE_REDIS:
        logging.info("Redis o'chirilgan, MemoryStorage ishlatiladi")
        return None

    try:
        # aioredis v2+ uchun
        import redis.asyncio as aioredis
        redis_connection = aioredis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD,
            db=config.REDIS_CACHE_DB,
            decode_responses=True
        )
        # Ulanishni tekshirish
        await redis_connection.ping()
        logging.info("Redis ulanishi o'rnatildi")
        return redis_connection
    except Exception as e:
        logging.error(f"Redis ulanish xatosi: {e}")
        logging.warning("Redis ulanishi amalga oshmadi, MemoryStorage ishlatilmoqda")
        return None


# Storage tanlash (Redis yoki Memory)
def get_storage():
    if USE_REDIS:
        try:
            # Redis-based storage for FSM
            return RedisStorage2(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_FSM_DB,
                password=config.REDIS_PASSWORD,
                pool_size=20
            )
        except Exception as e:
            logging.error(f"Redis storage yaratish xatosi: {e}")
            logging.warning("MemoryStorage ishlatilmoqda")

    # Default holat - MemoryStorage
    return MemoryStorage()


# Bot va Dispatcher
bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = get_storage()
dp = Dispatcher(bot, storage=storage)
db = DataBase(path_to_db=config.DATABASE_PATH)


# Redis kesh funksiyalari

async def get_redis_cache(key, default=None, ttl=None):
    """Redis keshdan qiymat olish"""
    if redis_connection is None:
        return default

    try:
        value = await redis_connection.get(key)
        if value is None:
            return default

        # JSON ni deserialize qilish
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # JSON bo'lmagan qiymatlar uchun
            return value
    except Exception as e:
        logging.error(f"Redis get xatosi: {e}")
        return default


async def set_redis_cache(key, value, ttl=300):
    """Redis keshga qiymat saqlash"""
    if redis_connection is None:
        return False

    try:
        # Qiymatni JSON ga serialize qilish
        if not isinstance(value, (str, bytes)):
            serialized = json.dumps(value)
        else:
            serialized = value

        if ttl:
            await redis_connection.setex(key, ttl, serialized)
        else:
            await redis_connection.set(key, serialized)
        return True
    except Exception as e:
        logging.error(f"Redis set xatosi: {e}")
        return False


async def delete_redis_cache(key):
    """Redis keshdan kalit o'chirish"""
    if redis_connection is None:
        return False

    try:
        await redis_connection.delete(key)
        return True
    except Exception as e:
        logging.error(f"Redis delete xatosi: {e}")
        return False


async def close_redis():
    """Redis ulanishini yopish"""
    if redis_connection is not None:
        await redis_connection.close()
        logging.info("Redis ulanishi yopildi")


# Memory-based fallback kesh
_local_cache = {}


async def get_cache(key, default=None, ttl=300):
    """Keshdan qiymat olish (Redis yoki local)"""
    # Avval Redis keshdan olishga harakat
    if USE_REDIS and redis_connection is not None:
        redis_value = await get_redis_cache(key)
        if redis_value is not None:
            return redis_value

    # Redis ishlamasa yoki qiymat topilmasa - local keshdan olish
    if key in _local_cache:
        value, timestamp = _local_cache[key]
        import time
        if time.time() - timestamp < ttl:
            return value

    return default


async def set_cache(key, value, ttl=300):
    """Keshga qiymat saqlash (Redis yoki local)"""
    # Avval Redis keshga saqlashga harakat
    if USE_REDIS and redis_connection is not None:
        await set_redis_cache(key, value, ttl)

    # Qo'shimcha ravishda local keshga saqlash
    import time
    _local_cache[key] = (value, time.time())

    # Eskirgan qiymatlarni tozalash (local kesh uchun)
    async def _cleanup():
        await asyncio.sleep(ttl)
        if key in _local_cache and _local_cache[key][1] + ttl <= time.time():
            del _local_cache[key]

    asyncio.create_task(_cleanup())
    return value


async def delete_cache(key):
    """Keshdan qiymat o'chirish (Redis va local)"""
    # Redis keshdan o'chirish
    if USE_REDIS and redis_connection is not None:
        await delete_redis_cache(key)

    # Local keshdan o'chirish
    if key in _local_cache:
        del _local_cache[key]

    return True