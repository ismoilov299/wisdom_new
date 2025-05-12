from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import ReplyKeyboardRemove
from datetime import datetime, timedelta

from handlers.users import texts
from handlers.users.texts import BTN_ABOUT_US, BTN_SETTINGS, TEXT_MAIN_MENU, \
    KORZINKA, BTN_BOOK, BTN_BATTLE, BTN_INFO
from loader import dp, db
from states.userStates import UserStates, QuizStates
from keyboards.default import start_menu

import logging

@dp.message_handler(CommandStart(),state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        start_args = message.get_args()

        if start_args:
            args = start_args.split('_')


            if len(args) >= 8 and args[1] == "quiz" and args[4] == "number" and args[6] == "time":
                user_id = args[0]
                quiz_id = args[2]
                unique_id = args[3]
                quiz_number = args[5]
                quiz_time = args[7]
                current_time = datetime.now()

                # Retrieve created_at timestamp from bot_app_history table
                created_at = db.get_created_at_by_unique_id(unique_id)


                if created_at:
                    # Assuming created_at is in 'YYYY-MM-DD HH:MM:SS' format
                    created_at_time = datetime.strptime(created_at, '%m-%d-%Y %H:%M')#%Y-%m
                    if current_time - created_at_time > timedelta(minutes=30):
                        await message.answer("Bu havola muddati tugagan.")
                        return
                else:
                    await message.answer("Xatolik yuz berdi. Ma'lumotlarni olishda xatolik.")
                    return

                await state.update_data(user_id=user_id, quiz_id=quiz_id, unique_id=unique_id, quiz_number=quiz_number, quiz_time=quiz_time)
                await QuizStates.QUIZ_START.set()
                await message.answer("Ismingizni kiriting!")
                return
            else:
                await message.answer("Bu havola noto'g'ri.")
                return
        else:
            user_exists = db.get_user_by_chat_id(user_id)

            if not user_exists:
                db.add_user(chat_id=user_id)
                await UserStates.IN_LANG.set()

                keyboard_lang = types.ReplyKeyboardMarkup(resize_keyboard=True)
                lang_buttons = [texts.BTN_LANG_UZ, texts.BTN_LANG_RU]
                keyboard_lang.add(*lang_buttons)

                await message.answer(texts.WELCOME_TEXT)
                await message.answer(texts.CHOOSE_LANG, reply_markup=keyboard_lang)
            else:
                await UserStates.IN_MENU.set()
                lang_id = db.get_user_language_id(user_id)

                keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard_menu.add(BTN_BOOK[lang_id])

                buttons_menu_row1 = [BTN_BATTLE[lang_id], BTN_ABOUT_US[lang_id]]
                buttons_menu_row2 = [BTN_INFO[lang_id], BTN_SETTINGS[lang_id]]
                keyboard_menu.add(*buttons_menu_row1)
                keyboard_menu.add(*buttons_menu_row2)

                is_admin = await check_admin(user_id)
                if is_admin:
                    admin_buttons_row = ['All users', 'Broadcast']
                    keyboard_menu.add(*admin_buttons_row)

                await message.answer(text=TEXT_MAIN_MENU[lang_id], reply_markup=keyboard_menu)
                await state.finish()
    except Exception as e:
        logging.error(f"Error in cmd_start: {e}")
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


async def check_admin(user_id: int) -> bool:
    # Implement the logic to check if the user is an admin (e.g., check against a list of admin IDs)
    admins = [624301767]  # Replace with actual admin IDs
    return user_id in admins





