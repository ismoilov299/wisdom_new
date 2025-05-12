import logging
import random
import asyncio
import uuid
import base64
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.exceptions import BotBlocked, RetryAfter, Throttled
from datetime import datetime
from handlers.users.texts import BACK, TEXT_QUIZ, TEXT_ALL
from loader import dp, db, bot

# Debug uchun logger
logger = logging.getLogger('room_handler')
logger.setLevel(logging.DEBUG)


# Viktorinani boshqarish uchun holatlar
class RoomQuizStates(StatesGroup):
    quiz_number = State()
    quiz_time = State()
    selecting_category = State()
    selecting_battle = State()


class GroupQuizStates(StatesGroup):
    waiting_for_answer = State()
    sending_next_question = State()
    quiz_ended = State()


# Doimiy qiymatlar
NUM_QUESTIONS = 30
TIMEOUT_DURATION = 30


async def create_keyboard_with_categories(categories, lang_id, callback_data_prefix):
    """
    Kategoriyalar bilan klaviatura yaratish.
    """
    keyboard = InlineKeyboardMarkup()
    for category in categories:
        category_id, category_name, *_ = category
        button_text = category_name if lang_id == 1 else category_name  # Til shartini qo'shish kerak bo'lsa
        callback_data = f"{callback_data_prefix}_{category_id}"
        logger.debug(f"Category: ID={category_id}, Name='{category_name}', Callback='{callback_data}'")
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)
    back_button = InlineKeyboardButton(text=BACK[lang_id], callback_data="back_to_battle")
    keyboard.add(back_button)
    return keyboard


@dp.callback_query_handler(text="start_quiz")
async def start_quiz(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Viktorina boshlanishini boshqarish.
    """
    try:
        await callback_query.answer()
        logger.debug(f"Start quiz callback received from user {callback_query.from_user.id}")

        user_id = callback_query.from_user.id
        lang_id = db.get_user_language_id(user_id)
        battles = db.get_root_battle()

        if not battles:
            logger.warning("No battles found for quiz")
            await callback_query.message.answer("Bellashuvlar topilmadi!")
            return

        keyboard = await create_keyboard_with_categories(battles, lang_id, "select")
        await callback_query.message.edit_text(TEXT_QUIZ[lang_id], reply_markup=keyboard)
        await RoomQuizStates.selecting_category.set()
        logger.debug("Displaying categories for quiz")
    except Exception as e:
        logger.error(f"Error starting quiz: {e}", exc_info=True)
        await callback_query.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(lambda callback: callback.data.startswith('select_'),
                           state=RoomQuizStates.selecting_category)
async def handle_category_callback(callback: CallbackQuery, state: FSMContext):
    """
    Kategoriya tanlashni boshqarish.
    """
    try:
        logger.debug(f"Category selected for quiz: {callback.data}")
        parts = callback.data.split('_')
        parent_id = int(parts[-1])
        categories = db.get_battle_by_parent_id(parent_id)
        lang_id = db.get_user_language_id(callback.from_user.id)

        if not categories:
            logger.warning(f"No subcategories found for parent ID {parent_id}")
            await callback.message.answer("Ushbu kategoriyada bellashuvlar topilmadi!")
            return

        keyboard = await create_keyboard_with_categories(categories, lang_id, "quiz_battle")
        await callback.message.edit_text(TEXT_QUIZ[lang_id], reply_markup=keyboard)
        await RoomQuizStates.selecting_battle.set()
        logger.debug(f"Displaying subcategories for parent ID {parent_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"Category parsing error: {e}", exc_info=True)
        await callback.message.answer("Ma'lumotlarni qayta ishlashda xatolik yuz berdi!")
    except Exception as e:
        logger.error(f"Error handling category selection: {e}", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(lambda c: c.data.startswith('quiz_battle_'), state=RoomQuizStates.selecting_battle)
async def handle_select_battle(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Jang tanlashni boshqarish.
    """
    try:
        logger.debug(f"Battle selected for quiz: {callback_query.data}")
        await callback_query.answer()
        parts = callback_query.data.split('_')
        quiz_id = int(parts[-1])

        # Bazadan ma'lumotlarni olish
        all_tests = db.get_questions_by_battle_id(quiz_id)
        categories = db.get_battle_by_parent_id(quiz_id)

        if not all_tests and not categories:
            logger.warning(f"No tests or subcategories found for battle ID {quiz_id}")
            await callback_query.message.answer("Bu bo'limda hozirda hech qanday ma'lumot mavjud emas")
            return

        # Agar subkategoriyalar topilsa, ularni ko'rsatish
        user_id = callback_query.from_user.id
        lang_id = db.get_user_language_id(user_id)

        if not all_tests:
            keyboard = await create_keyboard_with_categories(categories, lang_id, 'quiz_battle_')
            await callback_query.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
            logger.debug(f"Showing subcategories for battle ID {quiz_id}")
            return

        # Savollar topilgan bo'lsa
        logger.debug(f"Found {len(all_tests)} questions for battle ID {quiz_id}")
        await state.update_data(quiz_id=quiz_id)
        await bot.send_message(callback_query.from_user.id, "Savollar sonini kiriting:")
        await RoomQuizStates.quiz_number.set()
        logger.debug(f"Asking for number of questions")
    except (ValueError, IndexError) as e:
        logger.error(f"Battle selection error: {e}", exc_info=True)
        await callback_query.message.answer("Ma'lumotlarni qayta ishlashda xatolik yuz berdi!")
    except Exception as e:
        logger.error(f"Error handling battle selection: {e}", exc_info=True)
        await callback_query.message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.message_handler(state=RoomQuizStates.quiz_number)
async def process_quiz_number(message: types.Message, state: FSMContext):
    """
    Savollar sonini qayta ishlash.
    """
    try:
        logger.debug(f"Received quiz number: {message.text}")
        if not message.text.isdigit():
            await message.answer("Iltimos, son kiriting.")
            return

        quiz_number = int(message.text)
        if quiz_number > 200:
            await message.answer("Savollar soni 200 tadan oshmasligi kerak. Iltimos, qaytadan kiriting.")
            return

        await state.update_data(quiz_number=quiz_number)
        await message.answer("Savollarni vaqtini kiriting (sekunda, masalan, 20):")
        await RoomQuizStates.quiz_time.set()
        logger.debug(f"Quiz number set to {quiz_number}, asking for time")
    except Exception as e:
        logger.error(f"Error processing quiz number: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


@dp.message_handler(state=RoomQuizStates.quiz_time)
async def process_quiz_time(message: types.Message, state: FSMContext):
    """
    Savollarni vaqtini qayta ishlash.
    """
    try:
        logger.debug(f"Received quiz time: {message.text}")
        if not message.text.isdigit():
            await message.answer("Iltimos, vaqtni sonlarda kiriting.")
            return

        data = await state.get_data()
        quiz_id = data.get("quiz_id")
        quiz_number = data.get("quiz_number")
        quiz_time = int(message.text)

        # Ma'lumotlarni davlatga saqlash
        await state.update_data(quiz_time=quiz_time)

        # Unique identifikator yaratish
        uuid_val = uuid.uuid4()
        unique_id = base64.urlsafe_b64encode(uuid_val.bytes)[:4].decode('utf-8').replace('_', '-')
        bot_username = await get_bot_username()
        user_id = message.from_user.id
        current_time = datetime.now()
        formatted_time = current_time.strftime('%m-%d-%Y %H:%M')

        invite_link = (
            f"https://t.me/{bot_username}?start={user_id}_quiz_{quiz_id}_{unique_id}_number_{quiz_number}_time_{quiz_time}"
        )

        # Room ma'lumotlarini saqlash
        await save_room_data(unique_id, quiz_id, quiz_number, quiz_time, message.from_user.id)

        invite_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton(text="Botga qo'shilish", url=invite_link))
        await message.answer("Botga qo'shilish uchun quyidagi tugmani bosing:", reply_markup=invite_keyboard)

        # Bazaga yozish
        db.add_history_entry(user_id, quiz_id, unique_id, quiz_number, quiz_time, formatted_time)

        await state.finish()
        logger.debug(f"Room created: ID={unique_id}, link={invite_link}")
    except Exception as e:
        logger.error(f"Error processing quiz time: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


async def get_bot_username():
    """Bot username-ini olish"""
    try:
        bot_info = await bot.get_me()
        return bot_info.username
    except Exception as e:
        logger.error(f"Error getting bot username: {e}", exc_info=True)
        return "wisdom_lc_vocab_bot"  # Default


async def save_room_data(unique_id, quiz_id, quiz_number, quiz_time, owner_id):
    """Room ma'lumotlarini keshga saqlash"""
    from loader import set_cache
    room_data = {
        "quiz_id": quiz_id,
        "quiz_number": quiz_number,
        "quiz_time": quiz_time,
        "owner_id": owner_id,
        "created_at": datetime.now().isoformat()
    }
    await set_cache(f"room:{unique_id}", room_data, ttl=3600)  # 1 soat saqlanadi
    logger.debug(f"Saved room data to cache: {room_data}")


async def get_room_data(unique_id):
    """Room ma'lumotlarini keshdan olish"""
    try:
        from loader import get_cache

        # Keshdan ma'lumotlarni olish
        room_data = await get_cache(f"room:{unique_id}")
        logger.debug(f"Retrieved room data from cache for unique_id {unique_id}: {room_data}")

        # Agar keshda ma'lumot bo'lmasa, bazadan olishga harakat qilish
        if not room_data:
            logger.debug(f"No room data in cache for unique_id {unique_id}, trying database")

            # Bazadan olish
            try:
                quiz_id = db.get_quiz_number_by_unique_id(unique_id)
                created_at = db.get_created_at_by_unique_id(unique_id)

                if quiz_id and created_at:
                    # Ma'lumotlarni shakllantirish
                    room_data = {
                        "quiz_id": quiz_id,
                        "created_at": created_at,
                        # Boshqa ma'lumotlar bazada saqlanmagan bo'lishi mumkin
                        "quiz_number": 5,  # Default qiymat
                        "quiz_time": 20,  # Default qiymat
                    }

                    # Keshga saqlash
                    from loader import set_cache
                    await set_cache(f"room:{unique_id}", room_data, ttl=3600)
                    logger.debug(f"Retrieved and cached room data from database for unique_id {unique_id}: {room_data}")
            except Exception as e:
                logger.error(f"Error getting room data from database: {e}", exc_info=True)

        return room_data
    except Exception as e:
        logger.error(f"Error retrieving room data for unique_id {unique_id}: {e}", exc_info=True)
        return None


async def get_room_participants(unique_id):
    """Room qatnashchilarini olish"""
    try:
        from loader import get_cache

        # Keshdan olish
        participants = await get_cache(f"room_participants:{unique_id}")
        logger.debug(f"Got participants from cache: {participants}")

        if not participants:
            # Agar keshda yo'q bo'lsa, bo'sh ro'yxat qaytarish
            participants = []

        return participants
    except Exception as e:
        logger.error(f"Error getting room participants: {e}", exc_info=True)
        return []


async def add_room_participant(unique_id, user_id, name):
    """
    Room-ga yangi qatnashchi qo'shish
    """
    try:
        from loader import get_cache, set_cache

        # Mavjud qatnashchilarni olish
        participants = await get_cache(f"room_participants:{unique_id}") or []

        # Agar bu foydalanuvchi allaqachon ro'yxatda bo'lsa, qo'shmaslik
        for participant in participants:
            if participant.get('user_id') == user_id:
                logger.debug(f"User {user_id} already in room {unique_id}")
                return participants

        # Yangi qatnashchini qo'shish
        participants.append({
            "user_id": user_id,
            "name": name
        })

        # Yangilangan ro'yxatni saqlash
        await set_cache(f"room_participants:{unique_id}", participants, ttl=3600)
        logger.debug(f"Added user {user_id} ({name}) to room {unique_id}")

        return participants
    except Exception as e:
        logger.error(f"Error adding room participant: {e}", exc_info=True)
        return []


# Start room quiz callback handler
# Alohida callback handler har qanday holatda ham ishlaydi
@dp.callback_query_handler(lambda query: query.data.startswith('start_room_quiz_'), state="*")
async def start_room_quiz_callback(callback_query: types.CallbackQuery):
    """
    Admin testni boshlash tugmasini bosganda ishlaydigan handler
    """
    logger.info(f"START ROOM QUIZ CALLBACK CALLED: {callback_query.data}")
    try:
        # Javob qaytarish
        await callback_query.answer("Test boshlanmoqda...")

        # Unique ID ni olish
        unique_id = callback_query.data.split('_')[-1]
        logger.info(f"Extracted unique_id: {unique_id}")

        # Adminga xabar beramiz
        await callback_query.message.edit_text("Test boshlanmoqda, iltimos kuting...")

        # Room ma'lumotlarini olish
        quiz_id = None
        quiz_number = 5  # Default qiymat
        quiz_time = 20  # Default qiymat

        # Keshdan ma'lumotlarni olish
        room_data = await get_room_data(unique_id)
        if room_data:
            quiz_id = room_data.get('quiz_id')
            quiz_number = int(room_data.get('quiz_number', 5))
            quiz_time = int(room_data.get('quiz_time', 20))
            logger.info(
                f"Got room data from cache: quiz_id={quiz_id}, quiz_number={quiz_number}, quiz_time={quiz_time}")

        # Agar keshda ma'lumotlar bo'lmasa, bazadan olish
        if not quiz_id:
            try:
                # get_history_by_unique_id metodi bor bo'lsa
                history_data = db.get_history_by_unique_id(unique_id)
                if history_data:
                    quiz_id = history_data.get('quiz_id')
                    quiz_number_str = history_data.get('quiz_number')
                    quiz_time_str = history_data.get('quiz_time')

                    quiz_number = int(quiz_number_str) if quiz_number_str else 5
                    quiz_time = int(quiz_time_str) if quiz_time_str else 20

                    logger.info(
                        f"Got quiz data from history: quiz_id={quiz_id}, quiz_number={quiz_number}, quiz_time={quiz_time}")
            except Exception as e:
                logger.error(f"Error getting history data: {e}")

        # Agar hali ham quiz_id bo'lmasa, boshqa usullar bilan olish
        if not quiz_id:
            try:
                # get_quiz_id_by_unique_id metodi bor bo'lsa
                quiz_id = db.get_quiz_id_by_unique_id(unique_id)
                logger.info(f"Got quiz_id from database: {quiz_id}")

                # Quiz number va time ni olish
                quiz_number_from_db = db.get_quiz_number_by_unique_id(unique_id)
                if quiz_number_from_db:
                    quiz_number = int(quiz_number_from_db)

            except (TypeError, ValueError) as e:
                logger.warning(f"Could not get quiz_id from database: {e}")
                # Default qiymat
                quiz_id = 28  # Default quiz ID

        # Room qatnashchilarini olish
        participants = await get_room_participants(unique_id)
        logger.info(f"Room participants: {participants}")

        if not participants:
            participants = [{
                "user_id": callback_query.from_user.id,
                "name": "Test foydalanuvchi"
            }]
            logger.warning(f"No participants found, using admin as default participant")

        # Savollarni olish
        if not quiz_id:
            logger.error(f"Quiz ID not found for unique_id: {unique_id}")
            await callback_query.message.answer("Test ID topilmadi! Iltimos, qayta harakat qiling.")
            return

        questions = db.get_questions_by_battle_id(quiz_id)
        if not questions:
            logger.error(f"No questions found for quiz_id: {quiz_id}")
            await callback_query.message.answer("Bu bellashuvda savollar topilmadi!")
            return

        logger.info(f"Found {len(questions)} questions for quiz_id {quiz_id}")

        # Savollarni aralashtirib, tanlangan miqdorini olish
        random.shuffle(questions)
        selected_questions = questions[:quiz_number]
        logger.info(f"Selected {len(selected_questions)} questions for the quiz")

        # Barcha foydalanuvchilarga testni boshlash haqida xabar yuborish
        success_count = 0
        for participant in participants:
            user_id = participant.get('user_id')
            name = participant.get('name', 'Foydalanuvchi')

            try:
                # FSM state yaratish
                from aiogram.dispatcher import FSMContext
                await dp.current_state(user=user_id, chat=user_id).set_state(GroupQuizStates.waiting_for_answer.state)
                state = dp.current_state(user=user_id, chat=user_id)

                # Foydalanuvchiga xabar yuborish
                first_msg = await bot.send_message(
                    chat_id=user_id,
                    text=f"Test boshlanmoqda! Har bir savol uchun {quiz_time} soniya vaqtingiz bor."
                )
                logger.info(f"Sent start message to user {user_id}")

                # Birinchi savolni yuborish
                if len(selected_questions) > 0:
                    # Savolni tayyorlash
                    question = selected_questions[0]
                    question_text = question['answer_a'] if isinstance(question, dict) else question[1]
                    true_answer = question['question'] if isinstance(question, dict) else question[0]

                    first_question_msg = await bot.send_message(
                        chat_id=user_id,
                        text=f"1/{len(selected_questions)}\n<b>Savol:</b> {question_text}",
                        parse_mode='HTML'
                    )
                    logger.info(f"Sent first question to user {user_id}")

                    # Timeout task yaratish
                    task_id = random.randint(1, 1_000_000)  # Task uchun unikal ID
                    timeout_task = asyncio.create_task(
                        check_answer_timeout(first_question_msg, state, task_id, quiz_time))

                    # State ma'lumotlarini to'ldirish
                    await state.update_data(
                        questions=selected_questions,
                        current_question_index=1,  # 0-chi savol yuqorida yuborilgan
                        true_answer=true_answer,
                        answers_list=[],
                        quiz_ended=False,
                        unique_id=unique_id,
                        owner_id=callback_query.from_user.id,
                        name=name,
                        quiz_time=quiz_time,  # Vaqt limitini saqlash
                        current_task_id=task_id,
                        timeout_task_id=id(timeout_task)
                    )

                    success_count += 1

            except Exception as e:
                logger.error(f"Error sending start message to user {user_id}: {e}", exc_info=True)

        # Adminga xabar qaytarish
        await callback_query.message.edit_text(
            f"Test muvaffaqiyatli boshlandi! Jami {success_count} nafar ishtirokchi qatnashmoqda."
        )
        logger.info(f"Quiz started successfully with {success_count} participants")

    except Exception as e:
        logger.error(f"Error starting room quiz: {e}", exc_info=True)
        await callback_query.message.answer("Testni boshlashda xatolik yuz berdi!")

# Room ma'lumotlarini o'chirish
async def delete_room_data(unique_id):
    """Room ma'lumotlarini o'chirish"""
    try:
        from loader import delete_cache

        # Barcha tegishli ma'lumotlarni o'chirish
        await delete_cache(f"room:{unique_id}")
        await delete_cache(f"room_participants:{unique_id}")

        logger.debug(f"Deleted room data for unique_id {unique_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting room data: {e}", exc_info=True)
        return False


# Savollarga javob qabul qilish handleri
@dp.message_handler(state=GroupQuizStates.waiting_for_answer)
async def answer_received(message: types.Message, state: FSMContext):
    """
    Foydalanuvchi javoblarini qayta ishlash
    """
    try:
        logger.info(f"Received answer from user {message.from_user.id}: {message.text}")
        user_data = await state.get_data()
        true_answer = user_data.get('true_answer', '').strip()
        answers_list = user_data.get('answers_list', [])
        user_answer = message.text.strip().lower()

        if not true_answer:
            logger.error(f"No true_answer found in state data: {user_data}")
            await message.answer("Xatolik: Savol javoblari topilmadi.")
            return

        # Javobni tekshirish
        answer_is_correct = user_answer.lower() == true_answer.lower()
        answers_list.append(answer_is_correct)

        # Davlatni yangilash
        await state.update_data(answers_list=answers_list, answered=True)

        # Xabar yuborish
        if answer_is_correct:
            await message.answer("Javobingiz to'g'ri!")
        else:
            await message.answer(f"Javobingiz noto'g'ri! To'g'ri javob: {true_answer}")

        # Keyingi savolga o'tish
        await state.set_state(GroupQuizStates.sending_next_question.state)

        # Davlatdagi savollarni olish
        user_data = await state.get_data()
        questions = user_data.get('questions', [])
        current_question_index = user_data.get('current_question_index',
                                               1)  # 1-dan boshlanadi chunki 0-chi savol boshida yuborilgan

        if current_question_index < len(questions):
            # Savolni tayyorlash
            question = questions[current_question_index]
            question_text = question['answer_a'] if isinstance(question, dict) else question[1]
            true_answer = question['question'] if isinstance(question, dict) else question[0]

            # Savolni yuborish
            await message.answer(
                f"{current_question_index + 1}/{len(questions)}\n<b>Savol:</b> {question_text}",
                parse_mode='HTML'
            )

            # Davlatni yangilash
            await state.update_data(
                current_question_index=current_question_index + 1,
                true_answer=true_answer,
                answered=False
            )

            # Javob kutish holatiga o'tish
            await state.set_state(GroupQuizStates.waiting_for_answer.state)
            logger.info(f"Sent next question to user {message.from_user.id}")
        else:
            # Barcha savollar tugadi
            await state.set_state(GroupQuizStates.quiz_ended.state)
            await end_user_quiz(message, state)
            logger.info(f"Quiz completed for user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error processing answer: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi, iltimos keyinroq qayta urinib ko'ring.")


async def end_user_quiz(message: types.Message, state: FSMContext):
    """
    Testni yakunlash va natijalarni qayd qilish
    """
    try:
        user_id = message.from_user.id
        logger.info(f"Ending quiz for user {user_id}")

        # State ma'lumotlarini olish
        user_data = await state.get_data()
        answers_list = user_data.get('answers_list', [])
        unique_id = user_data.get('unique_id')
        owner_id = user_data.get('owner_id')
        name = user_data.get('name', 'Foydalanuvchi')

        # To'g'ri javoblar sonini hisoblash
        correct_answers_count = sum(1 for answer in answers_list if answer)

        # Natijalar matnini yaratish
        result_message = "\n".join(
            [f"{idx + 1}. {'✅' if result else '❌'}" for idx, result in enumerate(answers_list)]
        )

        result_text = f"{name} ning natijalari:\n{result_message}\n\n{name} foydalanuvchi {len(answers_list)} dan {correct_answers_count} taga to'g'ri javob berdi."

        # Bazaga natijalarni saqlash
        try:
            db.add_results_entry(
                chat_id=user_id,
                unique_id=unique_id,
                true_answers=correct_answers_count,
                false_answers=len(answers_list) - correct_answers_count,
                user_name=name
            )
            logger.info(f"Saved results to database for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving results: {e}", exc_info=True)

        # Reyting tugmasini yaratish
        rating_button = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📊 Reytingni ko'rish", callback_data=f"show_rating_{unique_id}")
        )

        # Adminni natijalar haqida xabardor qilish
        if owner_id:
            try:
                await bot.send_message(
                    chat_id=owner_id,
                    text=result_text,
                    reply_markup=rating_button  # Reyting tugmasini qo'shamiz
                )
                logger.info(f"Sent results to admin {owner_id}")
            except Exception as e:
                logger.error(f"Error sending results to admin: {e}", exc_info=True)

        # Foydalanuvchiga xabar yuborish (reyting tugmasi bilan)
        # await message.answer(
        #     "Test tugadi. Natijalaringiz muvaffaqiyatli saqlab qolindi.",
        #     reply_markup=rating_button  # Reyting tugmasini qo'shamiz
        # )

        # State ni tozalash
        await state.finish()
        logger.info(f"Quiz completed for user {user_id}")
    except Exception as e:
        logger.error(f"Error ending quiz: {e}", exc_info=True)
        await message.answer("Natijalarni qayd qilishda xatolik yuz berdi.")
        await state.finish()


@dp.callback_query_handler(lambda query: query.data.startswith('show_rating_'))
async def show_rating_callback(callback_query: types.CallbackQuery):
    """
    Reytingni ko'rsatish tugmasi bosilganda ishlaydigan handler
    """
    logger.info(f"Show rating callback called: {callback_query.data}")
    try:
        # Javob qaytarish
        await callback_query.answer("Reyting olinmoqda...")

        # Unique ID ni olish
        unique_id = callback_query.data.split('_')[-1]
        logger.info(f"Extracted unique_id for rating: {unique_id}")

        # Bazadan natijalarni olish
        try:
            results = db.get_results_by_unique_id(unique_id)
            logger.info(f"Found {len(results) if results else 0} results for unique_id {unique_id}")

            if not results or len(results) == 0:
                await callback_query.message.answer("Bu test uchun natijalar topilmadi.")
                return

            # Natijalarni to'g'ri javoblar soniga ko'ra tartiblash
            sorted_results = sorted(results, key=lambda x: int(x.get('true_answers', 0)), reverse=True)

            # Reyting matnini yaratish
            rating_text = f"📊 Unique ID {unique_id} uchun reyting:\n\n"

            for idx, result in enumerate(sorted_results):
                # Ma'lumotlarni olish
                user_name = result.get('user_name', 'Noma\'lum')
                true_answers = int(result.get('true_answers', 0))
                false_answers = int(result.get('false_answers', 0))
                total_questions = true_answers + false_answers

                # O'rin belgisini qo'shish
                position_emoji = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx + 1}."

                # Reyting qatorini qo'shish
                rating_text += (
                    f"{position_emoji} {user_name}: {true_answers}/{total_questions} "
                    f"({(true_answers / total_questions * 100) if total_questions > 0 else 0:.1f}%)\n"
                )

            # Reyting xabarini yuborish
            await callback_query.message.answer(rating_text)
            logger.info(f"Sent rating for unique_id {unique_id}")
        except Exception as e:
            logger.error(f"Error getting quiz results: {e}", exc_info=True)
            await callback_query.message.answer("Natijalarni olishda xatolik yuz berdi.")

    except Exception as e:
        logger.error(f"Error showing rating: {e}", exc_info=True)
        await callback_query.message.answer("Reytingni ko'rsatishda xatolik yuz berdi.")

async def check_answer_timeout(message: types.Message, state: FSMContext, task_id: int, quiz_time: int = 20):
    """
    Javob vaqti tugaganini tekshirish

    :param message: Xabar obyekti
    :param state: Foydalanuvchi state obyekti
    :param task_id: Timeout task ID-si
    :param quiz_time: Sekund hisobida vaqt (default: 20)
    """
    try:
        logger.info(f"Starting timeout check for user {message.from_user.id}, task ID {task_id}, time {quiz_time}s")

        # Belgilangan vaqt kutish
        await asyncio.sleep(quiz_time)

        # State ni olish
        user_data = await state.get_data()

        # Agar javob berilgan bo'lsa yoki task ID boshqa bo'lsa
        if user_data.get('answered') or user_data.get('current_task_id') != task_id:
            logger.info(
                f"Timeout not needed: answered={user_data.get('answered')}, task_id_match={user_data.get('current_task_id') == task_id}")
            return

        # Quiz tugagan bo'lsa
        if user_data.get('quiz_ended'):
            logger.info(f"Quiz already ended for user {message.from_user.id}")
            return

        # Vaqt tugadi, javob berilmadi
        logger.info(f"TIMEOUT: No answer received from user {message.from_user.id}")

        # Javoblarni olish
        answers_list = user_data.get('answers_list', [])
        current_question_index = user_data.get('current_question_index', 0)

        # Noto'g'ri javob sifatida qo'shish
        if len(answers_list) < current_question_index:
            answers_list.append(False)
            await state.update_data(answers_list=answers_list)

            # Foydalanuvchiga xabar berish
            await message.answer("⏱ Vaqt tugadi! Javob berilmadi.")

            # Keyingi savolga o'tish
            await state.set_state(GroupQuizStates.sending_next_question.state)

            # Keyingi savol
            questions = user_data.get('questions', [])

            if current_question_index < len(questions):
                # Savolni tayyorlash
                question = questions[current_question_index]
                question_text = question['answer_a'] if isinstance(question, dict) else question[1]
                true_answer = question['question'] if isinstance(question, dict) else question[0]

                # Savolni yuborish
                await message.answer(
                    f"{current_question_index + 1}/{len(questions)}\n<b>Savol:</b> {question_text}",
                    parse_mode='HTML'
                )

                # Timeout task yaratish
                quiz_time = user_data.get('quiz_time', 20)  # Default: 20 sekund
                new_task_id = random.randint(1, 1_000_000)  # Task uchun unikal ID
                timeout_task = asyncio.create_task(check_answer_timeout(message, state, new_task_id, quiz_time))

                # Davlatni yangilash
                await state.update_data(
                    current_question_index=current_question_index + 1,
                    true_answer=true_answer,
                    answered=False,
                    current_task_id=new_task_id,
                    timeout_task_id=id(timeout_task)
                )

                # Javob kutish holatiga o'tish
                await state.set_state(GroupQuizStates.waiting_for_answer.state)
                logger.info(f"Sent next question to user {message.from_user.id} after timeout")
            else:
                # Barcha savollar tugadi
                await state.set_state(GroupQuizStates.quiz_ended.state)
                await end_user_quiz(message, state)
                logger.info(f"Quiz completed for user {message.from_user.id} after timeout")

    except asyncio.CancelledError:
        # Task bekor qilingan (foydalanuvchi javob bergan)
        logger.info(f"Timeout task cancelled for user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in timeout checker: {e}", exc_info=True)


