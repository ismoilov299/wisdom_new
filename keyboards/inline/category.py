from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from handlers.users.texts import TEXT_ALL
from loader import dp, db
from states.userStates import UserStates

# Debug uchun logger
logger = logging.getLogger('category_handler')
logger.setLevel(logging.DEBUG)

# Qiymatlarni aniq belgilash
BOOKS_TEXT = ['📚 Kitoblar', '📚Книги']
BATTLE_TEXT = ['⚔️ Bellashuv', '⚔️ Соревнование']

# Debug uchun: constantalarni chiqarish
logger.debug(f"BOOKS_TEXT: {BOOKS_TEXT}")
logger.debug(f"BATTLE_TEXT: {BATTLE_TEXT}")


# books handler uchun alohida filter
@dp.message_handler(lambda message: message.text in BOOKS_TEXT)
async def handle_books_request(message: types.Message, state: FSMContext):
    """Kitoblar tugmasi bosilganda ishlaydi"""
    logger.debug(f"Kitoblar tugmasi bosildi: '{message.text}'")

    try:
        user_id = message.from_user.id
        lang_id = db.get_user_language_id(user_id)
        logger.debug(f"User ID: {user_id}, Lang ID: {lang_id}")

        # Bazadan kategoriya ma'lumotlarini olish
        top_level_categories = db.get_root_categories()
        logger.debug(f"Top level categories count: {len(top_level_categories) if top_level_categories else 0}")

        if not top_level_categories:
            logger.warning("Kategoriyalar topilmadi!")
            await message.answer("Kategoriyalar topilmadi.")
            return

        keyboard_product = InlineKeyboardMarkup()

        for category in top_level_categories:
            try:
                category_id = category[0]
                if lang_id == 1:
                    category_name = category[1]  # O'zbek tili
                else:
                    category_name = category[2]  # Rus tili

                logger.debug(f"Adding category: ID={category_id}, Name='{category_name}'")
                keyboard_product.add(InlineKeyboardButton(
                    text=category_name,
                    callback_data=f"category_{category_id}"
                ))
            except Exception as e:
                logger.error(f"Kategoriya qo'shishda xato: {e}", exc_info=True)

        # Xabar yuborish
        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
        logger.debug("Kategoriyalar muvaffaqiyatli ko'rsatildi")

    except Exception as e:
        logger.error(f"Kategoriyalarni ko'rsatishda xato: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


# admin tekshirish uchun yordamchi funksiya
async def is_user_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    try:
        user_ids = db.get_all_setadmin_user_ids()
        logger.debug(f"Admin user IDs count: {len(user_ids) if user_ids else 0}")

        admin_ids = []
        for id in user_ids:
            admin_id = db.get_chat_id_by_user_id(id)
            if admin_id:
                admin_ids.append(admin_id)

        logger.debug(f"Admin chat IDs: {admin_ids}")
        return user_id in admin_ids

    except Exception as e:
        logger.error(f"Admin tekshirishda xato: {e}", exc_info=True)
        return False


# battle handler uchun alohida filter
@dp.message_handler(lambda message: message.text in BATTLE_TEXT)
async def handle_battle_request(message: types.Message, state: FSMContext):
    """Bellashuv tugmasi bosilganda ishlaydi"""
    logger.debug(f"Bellashuv tugmasi bosildi: '{message.text}'")

    try:
        user_id = message.from_user.id
        lang_id = db.get_user_language_id(user_id)
        logger.debug(f"User ID: {user_id}, Lang ID: {lang_id}")

        # Bazadan bellashuv ma'lumotlarini olish
        top_level_categories = db.get_root_battle()
        logger.debug(f"Top level battles count: {len(top_level_categories) if top_level_categories else 0}")

        if not top_level_categories:
            logger.warning("Bellashuvlar topilmadi!")
            await message.answer("Bellashuvlar topilmadi.")
            return

        keyboard_product = InlineKeyboardMarkup()

        for category in top_level_categories:
            try:
                category_id = category[0]
                if lang_id == 1:
                    category_name = category[1]  # O'zbek tili
                    callback_data = f"battle_{category_id}_{category_name}"
                else:
                    category_name = category[2]  # Rus tili
                    callback_data = f"battle_{category_id}"

                logger.debug(f"Adding battle: ID={category_id}, Name='{category_name}', Callback='{callback_data}'")
                keyboard_product.add(InlineKeyboardButton(
                    text=category_name,
                    callback_data=callback_data
                ))
            except Exception as e:
                logger.error(f"Bellashuv qo'shishda xato: {e}", exc_info=True)

        # Admin foydalanuvchilar uchun test o'tkazish tugmasini qo'shish
        is_admin = await is_user_admin(user_id)
        if is_admin:
            admin_text = "Test o'tkazish" if lang_id == 1 else "Пройти тест"
            keyboard_product.add(InlineKeyboardButton(text=admin_text, callback_data="start_quiz"))
            logger.debug(f"Admin tugmasi qo'shildi: '{admin_text}'")

        # Xabar yuborish
        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
        logger.debug("Bellashuvlar muvaffaqiyatli ko'rsatildi")

    except Exception as e:
        logger.error(f"Bellashuvlarni ko'rsatishda xato: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")