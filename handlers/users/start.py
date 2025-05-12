from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import ReplyKeyboardRemove
from datetime import datetime, timedelta
import logging

from handlers.users import texts
from handlers.users.texts import BTN_ABOUT_US, BTN_SETTINGS, TEXT_MAIN_MENU, \
    KORZINKA, BTN_BOOK, BTN_BATTLE, BTN_INFO
from loader import dp, db, bot, get_cache, set_cache, delete_cache
from states.userStates import UserStates, QuizStates
import asyncio


@dp.message_handler(CommandStart(), state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        # Har qanday holatni tozalash
        await state.finish()

        user_id = message.from_user.id
        start_args = message.get_args()

        # Debug uchun
        logging.debug(f"Start command received with args: {start_args}")

        # Deep link parametrlari mavjud bo'lsa
        if start_args:
            # Parametrlarni ajratish
            args = start_args.split('_')
            logging.debug(f"Split args: {args}")

            # Quiz deep link strukturasini tekshirish
            if len(args) >= 8 and args[1] == "quiz" and args[4] == "number" and args[6] == "time":
                logging.debug("Valid quiz deeplink structure detected")

                # Ma'lumotlarni ajratib olish
                owner_id = args[0]
                quiz_id = args[2]
                unique_id = args[3]
                quiz_number = args[5]
                quiz_time = args[7]

                # Debug uchun
                logging.debug(f"Parsed quiz parameters: owner_id={owner_id}, quiz_id={quiz_id}, "
                              f"unique_id={unique_id}, quiz_number={quiz_number}, quiz_time={quiz_time}")

                # Yaroqliliik tekshirish
                current_time = datetime.now()
                created_at = db.get_created_at_by_unique_id(unique_id)

                logging.debug(f"Created at time for unique_id {unique_id}: {created_at}")

                if created_at:
                    # 'MM-DD-YYYY HH:MM' formatidagi vaqtni parse qilish
                    try:
                        created_at_time = datetime.strptime(created_at, '%m-%d-%Y %H:%M')
                        if current_time - created_at_time > timedelta(minutes=30):
                            await message.answer("Bu havola muddati tugagan.")
                            return
                    except ValueError as e:
                        logging.error(f"Error parsing created_at time: {e}")
                        await message.answer("Xatolik yuz berdi. Vaqt formatini o'qishda muammo.")
                        return
                else:
                    logging.warning(f"No created_at time found for unique_id {unique_id}")
                    await message.answer("Xatolik yuz berdi. Ma'lumotlarni olishda xatolik.")
                    return

                # Davlatni to'ldirish
                await state.update_data(
                    user_id=owner_id,
                    quiz_id=quiz_id,
                    unique_id=unique_id,
                    quiz_number=quiz_number,
                    quiz_time=quiz_time
                )

                # Quiz state ga o'tish
                await QuizStates.QUIZ_START.set()

                # Foydalanuvchidan ismini so'rash
                await message.answer("Ismingizni kiriting!")
                return
            else:
                logging.warning(f"Invalid deeplink structure: {args}")
                await message.answer("Bu havola noto'g'ri.")
                return

        # Oddiy start komandasi (deeplink bo'lmasa)
        user_exists = db.get_user_by_chat_id(user_id)

        if not user_exists:
            # Yangi foydalanuvchi
            db.add_user(chat_id=user_id)
            await UserStates.IN_LANG.set()

            keyboard_lang = types.ReplyKeyboardMarkup(resize_keyboard=True)
            lang_buttons = [texts.BTN_LANG_UZ, texts.BTN_LANG_RU]
            keyboard_lang.add(*lang_buttons)

            await message.answer(texts.WELCOME_TEXT)
            await message.answer(texts.CHOOSE_LANG, reply_markup=keyboard_lang)
        else:
            # Mavjud foydalanuvchi
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
        logging.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


async def process_quiz_deeplink(message: types.Message, state: FSMContext, args):
    """Quiz deep link parametrlarini qayta ishlash"""
    user_id = args[0]
    quiz_id = args[2]
    unique_id = args[3]
    quiz_number = args[5]
    quiz_time = args[7]
    current_time = datetime.now()

    # bot_app_history jadvalidan created_at vaqtini olish
    created_at = db.get_created_at_by_unique_id(unique_id)

    if created_at:
        # created_at 'YYYY-MM-DD HH:MM:SS' formatida bo'lsin
        created_at_time = datetime.strptime(created_at, '%m-%d-%Y %H:%M')
        if current_time - created_at_time > timedelta(minutes=30):
            await message.answer("Bu havola muddati tugagan.")
            return
    else:
        await message.answer("Xatolik yuz berdi. Ma'lumotlarni olishda xatolik.")
        return

    await state.update_data(user_id=user_id, quiz_id=quiz_id, unique_id=unique_id, quiz_number=quiz_number,
                            quiz_time=quiz_time)
    await QuizStates.QUIZ_START.set()
    await message.answer("Ismingizni kiriting!")


async def show_main_menu(message: types.Message, user_id: int):
    """Asosiy menyuni ko'rsatish"""
    # Tilni olish (kesh bilan)
    lang_id_key = f"user:lang:{user_id}"
    lang_id = await get_cache(lang_id_key)

    if lang_id is None:
        lang_id = db.get_user_language_id(user_id)
        if lang_id is not None:
            await set_cache(lang_id_key, lang_id, ttl=3600)  # 1 soat keshlaymiz

    # Asosiy menyu klaviaturasini yaratish
    keyboard_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_menu.add(BTN_BOOK[lang_id])

    buttons_menu_row1 = [BTN_BATTLE[lang_id], BTN_ABOUT_US[lang_id]]
    buttons_menu_row2 = [BTN_INFO[lang_id], BTN_SETTINGS[lang_id]]

    keyboard_menu.add(*buttons_menu_row1)
    keyboard_menu.add(*buttons_menu_row2)

    # Foydalanuvchi admin ekanligini tekshirish
    is_admin = await check_admin(user_id)
    if is_admin:
        admin_buttons_row = ['All users', 'Broadcast']
        keyboard_menu.add(*admin_buttons_row)

    await message.answer(text=TEXT_MAIN_MENU[lang_id], reply_markup=keyboard_menu)


async def check_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish (kesh bilan)"""
    cache_key = f"is_admin:{user_id}"
    is_admin = await get_cache(cache_key)

    if is_admin is None:
        # Admin foydalanuvchi ID-larini bir marta olish
        user_ids = db.get_all_setadmin_user_ids()
        admin_ids = []

        for id in user_ids:
            admin_id = db.get_chat_id_by_user_id(id)
            if admin_id:
                admin_ids.append(admin_id)
                # Har bir admin ID-sini keshlaymiz
                await set_cache(f"is_admin:{admin_id}", True, ttl=3600)  # 1 soat keshlaymiz

        is_admin = user_id in admin_ids
        if not is_admin:
            await set_cache(cache_key, False, ttl=3600)  # 1 soat keshlaymiz

    return is_admin


@dp.message_handler(state=QuizStates.QUIZ_START)
async def quiz_start_handler(message: types.Message, state: FSMContext):
    """
    Foydalanuvchi ismini kiritganda ishlaydigan handler
    """
    try:
        logging.info(f"Quiz start handler called with user name: {message.text}")
        name = message.text
        user_id = message.from_user.id

        # State ma'lumotlarini olish
        user_data = await state.get_data()
        unique_id = user_data.get('unique_id')
        owner_id = user_data.get('user_id')

        # Debug ma'lumotlari
        logging.info(f"User data: {user_data}")
        logging.info(f"Unique ID: {unique_id}, Owner ID: {owner_id}")

        # Foydalanuvchini bazada yaratish/yangilash
        user_exists = db.get_user_by_chat_id(user_id)
        if not user_exists:
            language_id = 1
            db.add_user(chat_id=user_id)
            db.update_user_field(user_id, "lang_id", language_id)
            db.update_user_field(key='first_name', value=name, chat_id=user_id)
            logging.info(f"Created new user: ID={user_id}, Name={name}")
        else:
            # Ismni yangilash
            db.update_user_field(key='first_name', value=name, chat_id=user_id)

        # Davlatni yangilash
        await state.update_data(name=name)

        # Foydalanuvchini roomga qo'shish
        from keyboards.inline.room import add_room_participant
        await add_room_participant(unique_id, user_id, name)

        # Admindan boshlanish signalini kutish
        await QuizStates.WAITING_FOR_ADMIN.set()

        # Adminga xabar yuborish va boshlash tugmasini ko'rsatish
        inline_kb = types.InlineKeyboardMarkup()
        inline_kb.add(types.InlineKeyboardButton(
            "Testni boshlash",
            callback_data=f"start_room_quiz_{unique_id}"
        ))

        # Adminga xabar yuborish
        try:
            await bot.send_message(
                chat_id=owner_id,
                text=f"<b>{name}</b> testga qo'shildi! Ishtirokchilar barchasini kutib, testni boshlash tugmasini bosing.",
                reply_markup=inline_kb,
                parse_mode='HTML'
            )
            logging.info(f"Sent notification to admin ID {owner_id}")
        except Exception as e:
            logging.error(f"Error sending message to admin: {e}")
            # Admin topilmasa, foydalanuvchiga boshqa xabar berish
            await message.answer("Testni yaratgan shaxsga xabar yuborishda xatolik yuz berdi.")

        # Foydalanuvchiga kutish haqida xabar
        await message.answer("Ro'yxatdan o'tdingiz! Test boshlanganda sizga xabar beriladi, iltimos kuting...")
        logging.info(f"User {user_id} registered for quiz {unique_id}")

    except Exception as e:
        logging.error(f"Error in quiz start handler: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")
        await state.finish()