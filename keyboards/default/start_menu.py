from aiogram import types
from aiogram.dispatcher import FSMContext

from handlers.users import texts
from handlers.users.texts import BTN_ABOUT_US, BTN_SETTINGS, TEXT_MAIN_MENU, \
    KORZINKA, BTN_BOOK, BTN_BATTLE, BTN_INFO
from loader import db, dp
from states.userStates import UserStates


@dp.message_handler(lambda message: message.text in [texts.BTN_LANG_UZ, texts.BTN_LANG_RU], state=UserStates.IN_LANG)
async def process_language(message: types.Message, state: FSMContext):
    user_language = message.text

    # Map language to numeric value
    language_id = 1 if user_language == texts.BTN_LANG_UZ else 2

    # Save the user's language in the state
    await state.update_data(language=language_id)

    # Save the user's language in the database
    user_id = message.from_user.id
    db.update_user_field(user_id, "lang_id", language_id)

    # Transition to the next state (IN_MENU)
    await UserStates.IN_MENU.set()

    user_id = message.from_user.id
    lang_id = db.get_user_language_id(user_id)

    # Continue with your conversation flow for existing users
    keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Add the first button separately
    keyboard_menu.add(BTN_BOOK[lang_id])

    # Add the remaining buttons in pairs
    buttons_menu_row1 = [BTN_BATTLE[lang_id], BTN_ABOUT_US[lang_id]]
    buttons_menu_row2 = [BTN_INFO[lang_id], BTN_SETTINGS[lang_id]]

    keyboard_menu.add(*buttons_menu_row1)
    keyboard_menu.add(*buttons_menu_row2)

    # Send the main menu with keyboard_menu
    await message.answer(text=TEXT_MAIN_MENU[lang_id], reply_markup=keyboard_menu)

    # Finish the state
    await state.finish()