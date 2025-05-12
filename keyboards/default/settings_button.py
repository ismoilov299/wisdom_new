import asyncio

from aiogram import types
from aiogram.dispatcher import FSMContext

from handlers.users import texts
from handlers.users.texts import CHOOSE_LANG, BTN_ABOUT_US, BTN_SETTINGS, \
    KORZINKA, BTN_INFO, BTN_BATTLE, BTN_BOOK
from loader import dp, db
from states.userStates import SettingName


@dp.message_handler(text=['⚙ Sozlamalar', '⚙ Настройки'])
async def setting_menu(message: types.Message, state: FSMContext):

    keyboard_setting = types.ReplyKeyboardMarkup(resize_keyboard=True)
    setting_buttons = ["Tilni o'zgartirish", "Ismni o'zgartirish"]
    keyboard_setting.add(*setting_buttons)

    await message.answer("Nimani o'zgartirmoqchisiz", reply_markup=keyboard_setting)

@dp.message_handler(text="Tilni o'zgartirish")
async def lang_setting(message: types.Message):
    keyboard_lang = types.ReplyKeyboardMarkup(resize_keyboard=True)
    lang_buttons = [texts.BTN_LANG_UZ, texts.BTN_LANG_RU]
    keyboard_lang.add(*lang_buttons)

    await message.answer(CHOOSE_LANG, reply_markup=keyboard_lang)


from aiogram.dispatcher import FSMContext


@dp.message_handler(text="Ismni o'zgartirish")
async def name_setting(message: types.Message, state: FSMContext):
    await message.answer("Ismingizni kiriting!")

    # Set the state to 'name' of the 'SettingName' state group
    await SettingName.name.set()


@dp.message_handler(state=SettingName.name)
async def process_name(message: types.Message, state: FSMContext):
    # Retrieve the user's name from the message
    user_id = message.from_user.id
    user_name = message.text

    db.update_user_field(key='first_name', value=user_name, chat_id=user_id)
    keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    lang_id = db.get_user_language_id(user_id)
    # Add the first button separately
    keyboard_menu.add(BTN_BOOK[lang_id])

    # Add the remaining buttons in pairs
    buttons_menu_row1 = [BTN_BATTLE[lang_id], BTN_ABOUT_US[lang_id]]
    buttons_menu_row2 = [BTN_INFO[lang_id], BTN_SETTINGS[lang_id]]

    keyboard_menu.add(*buttons_menu_row1)
    keyboard_menu.add(*buttons_menu_row2)
    await message.answer(f"Sizning ismingiz: {user_name} ga o'zgardi",reply_markup=keyboard_menu)
    # Reset the state to the initial state
    await state.finish()




@dp.message_handler(lambda message: message.text in [texts.BTN_LANG_UZ, texts.BTN_LANG_RU])
async def handle_language_selection(message: types.Message, state: FSMContext):
    user_language = message.text


    language_id = 1 if user_language == texts.BTN_LANG_UZ else 2


    user_id = message.from_user.id
    db.update_user_field(user_id, "lang_id", language_id)
    keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_id = message.from_user.id
    lang_id = db.get_user_language_id(user_id)

    keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard_menu.add(BTN_BOOK[lang_id])

    # Add the remaining buttons in pairs
    buttons_menu_row1 = [BTN_BATTLE[lang_id], BTN_ABOUT_US[lang_id]]
    buttons_menu_row2 = [BTN_INFO[lang_id], BTN_SETTINGS[lang_id]]

    keyboard_menu.add(*buttons_menu_row1)
    keyboard_menu.add(*buttons_menu_row2)


    # You can customize the response based on the selected language
    if language_id == 1:
        await message.answer("Siz O'zbek tilini tanladingiz.",reply_markup=keyboard_menu)
    elif language_id == 2:
        await message.answer("Вы выбрали русский язык.",reply_markup=keyboard_menu)