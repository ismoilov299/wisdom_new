from aiogram import executor
import asyncio
import logging
import middlewares, filters, handlers, keyboards
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from loader import dp, init_redis, close_redis

# Debug darajadagi logging ni yoqish
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)

# Aiogram debug loglarini yoqish
# logging.getLogger('aiogram').setLevel(logging.DEBUG)
# logging.getLogger('aiogram.event').setLevel(logging.DEBUG)
#
# # Boshqa kerakli loggerlarni yoqish
# logging.getLogger('keyboards').setLevel(logging.DEBUG)
# logging.getLogger('handlers').setLevel(logging.DEBUG)
# logging.getLogger('data').setLevel(logging.DEBUG)


async def on_startup(dispatcher):
    # Bot haqida ma'lumot
    logging.info("Bot ishga tushirilmoqda...")
    bot_info = await dispatcher.bot.get_me()
    logging.info(f"Bot ma'lumotlari: @{bot_info.username} ({bot_info.id})")

    # Redis initializatsiyasi
    logging.info("Redis initializatsiyasi boshlandi...")
    await init_redis()
    logging.info("Redis initializatsiyasi yakunlandi!")

    # Birlamchi komandalar (/start va /help)
    logging.info("Bot komandalarini o'rnatish...")
    await set_default_commands(dispatcher)
    logging.info("Bot komandalari o'rnatildi!")

    # Bot ishga tushgani haqida adminga xabar berish
    logging.info("Admin xabardor qilinmoqda...")
    await on_startup_notify(dispatcher)
    logging.info("Admin xabardor qilindi!")

    logging.info("Bot muvaffaqiyatli ishga tushdi!")


async def on_shutdown(dispatcher):
    # Redis ulanishini yopish
    logging.info("Redis ulanishini yopish...")
    await close_redis()
    logging.info("Redis ulanishi yopildi!")

    # Storage tozalanishi
    logging.info("FSM storage tozalanmoqda...")
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
    logging.info("FSM storage tozalandi!")

    logging.info("Bot to'xtatildi!")


if __name__ == '__main__':
    # Havola ma'lumotlarini ko'rsatish
    logging.info("Starting bot...")
    logging.info("Middleware, filter va handlerlar yuklanmoqda...")

    # Uvloop ishlatish agar mavjud bo'lsa
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logging.info("Uvloop tezroq ishlash uchun qo'llanilmoqda")
    except ImportError:
        logging.info("Uvloop topilmadi, standart asyncio event loop ishlatilmoqda")

    # Start polling
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=False,
        timeout=20,
        relax=0.1,
    )