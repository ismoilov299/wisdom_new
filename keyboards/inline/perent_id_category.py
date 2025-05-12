from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from handlers.users.texts import BACK, TEXT_ALL
from loader import dp, db

# admin_user_ids = {5449550709,624301767,1161180912}

@dp.callback_query_handler(lambda callback: callback.data.startswith('category_'))
async def handle_category_callback(callback: CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id
    lang_id = db.get_user_language_id(user_id)
    parent_id = int(callback.data.split('_')[1])
    categories = db.get_categories_by_parent_id(parent_id)
    keyboard = InlineKeyboardMarkup()
    for category in categories:
        category_id, category_name, _, _, _ = category
        button_text = f"{category_name}"
        callback_data = f"product_{category_name}_parent_id_{parent_id}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)
    back_button = InlineKeyboardButton(text=BACK[lang_id], callback_data="back_to_root")
    keyboard.add(back_button)
    await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)



@dp.callback_query_handler(lambda callback: callback.data == 'back_to_root')
async def handle_back_to_root_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_id = db.get_user_language_id(user_id)
    root_categories = db.get_root_categories()
    keyboard = InlineKeyboardMarkup()
    for category in root_categories:
        category_id, category_name, _, _, _ = category
        button_text = f"{category_name}"
        callback_data = f"category_{category_id}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)

    await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)


@dp.callback_query_handler(lambda callback: callback.data.startswith('battle_'))
async def handle_battle(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_id = db.get_user_language_id(user_id)
    parent_id = int(callback.data.split('_')[1])
    data_parts = callback.data.split('_')
    print(data_parts)

    try:
        parent_name = callback.data.split('_')[2]
    except IndexError:
        parent_name = None  # parent_name mavjud bo'lmasa, None qilib belgilaymiz

    categories = db.get_battle_by_parent_id(parent_id)
    keyboard = InlineKeyboardMarkup()

    for category in categories:
        category_id, category_name, _, _, _ = category
        button_text = f"{category_name}"

        # parent_name mavjudligini tekshiramiz
        if parent_name:
            callback_data = f"test_{category_id}_{category_name}_{parent_name}"
        else:
            callback_data = f"test_{category_id}_{category_name}"

        print(f'callback: {callback_data}')
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)

    back_button = InlineKeyboardButton(text=BACK[lang_id], callback_data="back_to_battle")
    keyboard.add(back_button)

    await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)


async def is_user_admin(user_id: int) -> bool:
    user_ids = db.get_all_setadmin_user_ids()
    admin_ids = []

    for id in user_ids:
        admin_id = db.get_chat_id_by_user_id(id)
        admin_ids.append(admin_id)


    return user_id in admin_ids

@dp.callback_query_handler(lambda callback: callback.data == 'back_to_battle')
async def handle_back_to_root_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_id = db.get_user_language_id(user_id)
    top_level_categories = db.get_root_battle()
    keyboard_product = InlineKeyboardMarkup()
    for category in top_level_categories:
        category_name = category[1]
        keyboard_product.add(InlineKeyboardButton(text=category_name, callback_data=f"battle_{category[0]}"))

    # Agar foydalanuvchi admin bo'lsa, test o'tkazish tugmasini qo'shish
    if await is_user_admin(user_id):
        keyboard_product.add(InlineKeyboardButton(text="Test o'tkazish", callback_data="start_quiz"))

    await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard_product)


