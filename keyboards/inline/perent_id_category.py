from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from handlers.users.texts import TEXT_ALL, BTN_BOOK, BTN_BATTLE
from loader import dp, db, get_cache, set_cache, delete_cache
from states.userStates import UserStates

# BTN_BOOK va BTN_BATTLE qiymatlaridan ro'yxatlar yaratamiz
BOOKS_TEXT = [BTN_BOOK[1], BTN_BOOK[2]]
BATTLE_TEXT = [BTN_BATTLE[1], BTN_BATTLE[2]]

# Xatoliklarni tizimli ravishda qayd qilish uchun logging ni yoqamiz
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dp.message_handler(lambda message: message.text in BOOKS_TEXT)
async def handle_product_request(message: types.Message, state: FSMContext):
    """Kitoblar tugmasi bosilganda ishlaydi"""
    try:
        logger.info(f"Kitoblar tugmasi bosildi: {message.text}")

        user_id = message.from_user.id

        # Keshdan tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        # Keshdan kategoriyalarni olish
        top_level_categories = await get_cache("categories:root")
        if top_level_categories is None:
            top_level_categories = db.get_root_categories()
            if top_level_categories:
                await set_cache("categories:root", top_level_categories, ttl=3600)

        if not top_level_categories:
            logger.warning("Kategoriyalar topilmadi!")
            await message.answer("Kategoriyalar topilmadi.")
            return

        # Klaviatura yaratish
        keyboard_product = InlineKeyboardMarkup()

        for category in top_level_categories:
            if isinstance(category, dict):  # Django ORM qo'llanganda
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:  # SQLite ga murojaat qilinganda (katta ehtimol bilan tuple)
                category_id = category[0]
                category_name = category[1] if lang_id == 1 else category[2]

            if category_name:
                button = InlineKeyboardButton(
                    text=category_name,
                    callback_data=f"category_{category_id}"
                )
                keyboard_product.add(button)

        # Xabar yuborish
        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
        logger.info(f"Kategoriyalar muvaffaqiyatli ko'rsatildi - {len(top_level_categories)} ta topildi")

    except Exception as e:
        logger.error(f"Kategoriyalarni ko'rsatishda xato: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


async def is_user_admin(user_id: int) -> bool:
    """
    Foydalanuvchi admin ekanligini tekshirish (kesh bilan)
    """
    # Keshdan admin ma'lumotlarini olish
    cache_key = f"is_admin:{user_id}"
    is_admin = await get_cache(cache_key)

    if is_admin is not None:
        return is_admin

    # Admin foydalanuvchi ID-larini bir marta olish
    admin_user_ids = await get_cache("admin:user_ids")

    if admin_user_ids is None:
        user_ids = db.get_all_setadmin_user_ids()
        admin_ids = []

        for id in user_ids:
            admin_id = db.get_chat_id_by_user_id(id)
            if admin_id:
                admin_ids.append(admin_id)
                # Har bir admin ID-sini keshlaymiz
                await set_cache(f"is_admin:{admin_id}", True, ttl=3600)

        await set_cache("admin:user_ids", admin_ids, ttl=3600)
        admin_user_ids = admin_ids

    is_admin = user_id in admin_user_ids
    await set_cache(cache_key, is_admin, ttl=3600)

    return is_admin


@dp.message_handler(lambda message: message.text in BATTLE_TEXT)
async def handle_battle_request(message: types.Message, state: FSMContext):
    """Bellashuv tugmasi bosilganda ishlaydi"""
    try:
        logger.info(f"Bellashuv tugmasi bosildi: {message.text}")

        user_id = message.from_user.id

        # Keshdan tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        # Keshdan ildiz bellashuvlarni olish
        top_level_categories = await get_cache("battles:root")
        if top_level_categories is None:
            top_level_categories = db.get_root_battle()
            if top_level_categories:
                await set_cache("battles:root", top_level_categories, ttl=3600)

        if not top_level_categories:
            logger.warning("Bellashuvlar topilmadi!")
            await message.answer("Bellashuvlar topilmadi.")
            return

        # Klaviatura yaratish
        keyboard_product = InlineKeyboardMarkup()

        for category in top_level_categories:
            if isinstance(category, dict):  # Django ORM qo'llanganda
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:  # SQLite ga murojaat qilinganda (katta ehtimol bilan tuple)
                category_id = category[0]
                category_name = category[1] if lang_id == 1 else category[2]

            if category_name:
                button = InlineKeyboardButton(
                    text=category_name,
                    callback_data=f"battle_{category_id}_{category_name}"
                )
                keyboard_product.add(button)

        # Admin foydalanuvchilar uchun test o'tkazish tugmasini qo'shish
        is_admin = await is_user_admin(user_id)
        if is_admin:
            admin_text = "Test o'tkazish" if lang_id == 1 else "Пройти тест"
            keyboard_product.add(InlineKeyboardButton(text=admin_text, callback_data="start_quiz"))

        # Xabar yuborish
        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
        logger.info(f"Bellashuvlar muvaffaqiyatli ko'rsatildi - {len(top_level_categories)} ta topildi")

    except Exception as e:
        logger.error(f"Bellashuvlarni ko'rsatishda xato: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


# Kategoriyalar uchun callback handler
@dp.callback_query_handler(lambda callback: callback.data.startswith('category_'))
async def handle_category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Kategoriyani tanlaganda ishlaydi"""
    try:
        # Qabul qilish uchun tezda javob beramiz
        await callback.answer()

        user_id = callback.from_user.id

        # Tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        parent_id = int(callback.data.split('_')[1])

        # Keshdan subkategoriyalarni olish
        cache_key = f"categories:parent:{parent_id}"
        categories = await get_cache(cache_key)

        if categories is None:
            categories = db.get_categories_by_parent_id(parent_id)
            if categories:
                await set_cache(cache_key, categories, ttl=1800)  # 30 daqiqa keshlaymiz

        if not categories:
            await callback.message.answer("Bu kategoriyada hech qanday ma'lumot mavjud emas")
            return

        # Klaviatura yaratish
        keyboard = InlineKeyboardMarkup()

        for category in categories:
            if isinstance(category, dict):
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:
                category_id, category_name = category[0], category[1]
                if lang_id == 2 and len(category) > 2:
                    category_name = category[2]  # Rus tili uchun

            if category_name:
                callback_data = f"product_{category_name}_parent_id_{parent_id}"
                button = InlineKeyboardButton(text=category_name, callback_data=callback_data)
                keyboard.add(button)

        # Orqaga tugmasini qo'shish
        back_button = InlineKeyboardButton(text=TEXT_ALL[lang_id], callback_data="back_to_root")
        keyboard.add(back_button)

        # Xabarni yangilash
        await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
        logger.info(f"Subkategoriyalar muvaffaqiyatli ko'rsatildi - parent_id: {parent_id}")

    except Exception as e:
        logger.error(f"Subkategoriyalarni ko'rsatishda xato: {e}", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(lambda callback: callback.data == 'back_to_root')
async def handle_back_to_root_callback(callback: types.CallbackQuery, state: FSMContext):
    """Ildiz kategoriyalarga qaytish"""
    try:
        # Qabul qilish uchun tezda javob beramiz
        await callback.answer()

        user_id = callback.from_user.id

        # Tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        # Keshdan ildiz kategoriyalarni olish
        root_categories = await get_cache("categories:root")

        if root_categories is None:
            root_categories = db.get_root_categories()
            if root_categories:
                await set_cache("categories:root", root_categories, ttl=3600)  # 1 soat keshlaymiz

        if not root_categories:
            await callback.message.answer("Hech qanday kategoriya topilmadi")
            return

        # Klaviatura yaratish
        keyboard = InlineKeyboardMarkup()

        for category in root_categories:
            if isinstance(category, dict):
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:
                category_id, category_name = category[0], category[1]
                if lang_id == 2 and len(category) > 2:
                    category_name = category[2]  # Rus tili uchun

            if category_name:
                callback_data = f"category_{category_id}"
                button = InlineKeyboardButton(text=category_name, callback_data=callback_data)
                keyboard.add(button)

        # Xabarni yangilash
        await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
        logger.info("Ildiz kategoriyalarga qaytildi")

    except Exception as e:
        logger.error(f"Ildiz kategoriyalarga qaytishda xato: {e}", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(lambda callback: callback.data.startswith('battle_'))
async def handle_battle(callback: types.CallbackQuery, state: FSMContext):
    """Bellashuv kategoriyasini tanlaganda ishlaydi"""
    try:
        # Qabul qilish uchun tezda javob beramiz
        await callback.answer()

        user_id = callback.from_user.id

        # Tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        data_parts = callback.data.split('_')
        parent_id = int(data_parts[1])

        try:
            parent_name = data_parts[2]
        except IndexError:
            parent_name = None  # parent_name mavjud bo'lmasa, None qilib belgilaymiz

        # Keshdan subkategoriyalarni olish
        cache_key = f"battles:parent:{parent_id}"
        categories = await get_cache(cache_key)

        if categories is None:
            categories = db.get_battle_by_parent_id(parent_id)
            if categories:
                await set_cache(cache_key, categories, ttl=1800)  # 30 daqiqa keshlaymiz

        if not categories:
            await callback.message.answer("Bu kategoriyada hech qanday ma'lumot mavjud emas")
            return

        # Klaviatura yaratish
        keyboard = InlineKeyboardMarkup()

        for category in categories:
            if isinstance(category, dict):
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:
                category_id, category_name = category[0], category[1]
                if lang_id == 2 and len(category) > 2:
                    category_name = category[2]  # Rus tili uchun

            if category_name:
                # parent_name mavjudligini tekshiramiz
                if parent_name:
                    callback_data = f"test_{category_id}_{category_name}_{parent_name}"
                else:
                    callback_data = f"test_{category_id}_{category_name}"

                button = InlineKeyboardButton(text=category_name, callback_data=callback_data)
                keyboard.add(button)

        # Orqaga tugmasini qo'shish
        back_button = InlineKeyboardButton(text=TEXT_ALL[lang_id], callback_data="back_to_battle")
        keyboard.add(back_button)

        # Xabarni yangilash
        await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
        logger.info(f"Bellashuv subkategoriyalari muvaffaqiyatli ko'rsatildi - parent_id: {parent_id}")

    except Exception as e:
        logger.error(f"Bellashuv subkategoriyalarini ko'rsatishda xato: {e}", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(lambda callback: callback.data == 'back_to_battle')
async def handle_back_to_battle_callback(callback: types.CallbackQuery, state: FSMContext):
    """Ildiz bellashuvlarga qaytish"""
    try:
        # Qabul qilish uchun tezda javob beramiz
        await callback.answer()

        user_id = callback.from_user.id

        # Tilni olish
        lang_id = await get_cache(f"user:lang:{user_id}")
        if lang_id is None:
            lang_id = db.get_user_language_id(user_id)
            if lang_id:
                await set_cache(f"user:lang:{user_id}", lang_id, ttl=3600)
            else:
                lang_id = 1  # Default til

        # Keshdan ildiz bellashuvlarni olish
        root_battles = await get_cache("battles:root")

        if root_battles is None:
            root_battles = db.get_root_battle()
            if root_battles:
                await set_cache("battles:root", root_battles, ttl=3600)

        if not root_battles:
            await callback.message.answer("Hech qanday bellashuv topilmadi")
            return

        # Klaviatura yaratish
        keyboard = InlineKeyboardMarkup()

        for category in root_battles:
            if isinstance(category, dict):
                category_id = category.get('id')
                category_name = category.get('name_uz') if lang_id == 1 else category.get('name_ru')
            else:
                category_id, category_name = category[0], category[1]
                if lang_id == 2 and len(category) > 2:
                    category_name = category[2]  # Rus tili uchun

            if category_name:
                callback_data = f"battle_{category_id}"
                keyboard.add(InlineKeyboardButton(text=category_name, callback_data=callback_data))

        # Admin foydalanuvchilar uchun test o'tkazish tugmasini qo'shish
        is_admin = await is_user_admin(user_id)
        if is_admin:
            admin_text = "Test o'tkazish" if lang_id == 1 else "Пройти тест"
            keyboard.add(InlineKeyboardButton(text=admin_text, callback_data="start_quiz"))

        # Xabarni yangilash
        await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
        logger.info("Ildiz bellashuvlarga qaytildi")

    except Exception as e:
        logger.error(f"Ildiz bellashuvlarga qaytishda xato: {e}", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")