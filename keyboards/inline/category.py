
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.users.texts import TEXT_ALL
from loader import db, dp
from states.userStates import UserStates

# Constants
BOOKS_TEXT = ['📚 Kitoblar', '📚Книги']
BATTLE_TEXT = ['⚔️ Bellashuv', '⚔️ Соревнование']
# admin_user_ids = {624301767, 1161180912,}


@dp.message_handler(text=BOOKS_TEXT)
async def handle_product_request(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    lang_id = db.get_user_language_id(user_id)
    top_level_categories = db.get_root_categories()

    if lang_id == 1:

        keyboard_product = InlineKeyboardMarkup()
        for category in top_level_categories:
            category_name = category[1]
            keyboard_product.add(InlineKeyboardButton(text=category_name, callback_data=f"category_{category[0]}"))

        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
    else:
        keyboard_product = InlineKeyboardMarkup()
        for category in top_level_categories:
            category_name = category[2]
            keyboard_product.add(InlineKeyboardButton(text=category_name, callback_data=f"category_{category[0]}"))

        # Send the keyboard to the user
        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)

# admin_user_ids = [624301767]
async def is_user_admin(user_id: int) -> bool:
    user_ids = db.get_all_setadmin_user_ids()
    admin_ids = []

    for id in user_ids:
        admin_id = db.get_chat_id_by_user_id(id)
        admin_ids.append(admin_id)


    return user_id in admin_ids



@dp.message_handler(text=BATTLE_TEXT)
async def handle_product_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang_id = db.get_user_language_id(user_id)
    top_level_categories = db.get_root_battle()

    if lang_id == 1:
        keyboard_product = InlineKeyboardMarkup()
        for category in top_level_categories:
            category_name = category[1]
            keyboard_product.add(InlineKeyboardButton(text=category_name, callback_data=f"battle_{category[0]}_{category_name}"))

        # Agar foydalanuvchi admin bo'lsa, test o'tkazish tugmasini qo'shish
        if await is_user_admin(user_id):
            keyboard_product.add(InlineKeyboardButton(text="Test o'tkazish", callback_data="start_quiz"))

        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)
    else:
        keyboard_product = InlineKeyboardMarkup()
        for category in top_level_categories:
            category_name = category[2]
            keyboard_product.add(InlineKeyboardButton(text=category_name, callback_data=f"battle_{category[0]}"))

        # Agar foydalanuvchi admin bo'lsa, test o'tkazish tugmasini qo'shish
        if await is_user_admin(user_id):
            keyboard_product.add(InlineKeyboardButton(text="Пройти тест", callback_data="start_quiz"))

        await message.answer(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)

