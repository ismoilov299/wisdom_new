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
from loader import db, dp, bot
from states.userStates import QuizStates

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
        print(callback_data)
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
    await callback_query.answer()
    user_id = callback_query.from_user.id
    lang_id = db.get_user_language_id(user_id)
    battles = db.get_root_battle()

    keyboard = await create_keyboard_with_categories(battles, lang_id, "select")
    await callback_query.message.edit_text(TEXT_QUIZ[lang_id], reply_markup=keyboard)
    await RoomQuizStates.selecting_category.set()

@dp.callback_query_handler(lambda callback: callback.data.startswith('select_'), state=RoomQuizStates.selecting_category)
async def handle_category_callback(callback: CallbackQuery, state: FSMContext):
    """
    Kategoriya tanlashni boshqarish.
    """
    try:
        parts = callback.data.split('_')
        parent_id = int(parts[-1])
        categories = db.get_battle_by_parent_id(parent_id)
        lang_id = db.get_user_language_id(callback.from_user.id)
        keyboard = await create_keyboard_with_categories(categories, lang_id, "quiz_battle")
        await callback.message.edit_text(TEXT_QUIZ[lang_id], reply_markup=keyboard)
        await RoomQuizStates.selecting_battle.set()
    except (ValueError, IndexError) as e:
        logging.error(f"Kategoriya parsingida xato: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('quiz_battle_'), state=RoomQuizStates.selecting_battle)
async def handle_select_battle(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang_id = db.get_user_language_id(user_id)
    """
    Jang tanlashni boshqarish.
    """
    try:
        await callback_query.answer()
        parts = callback_query.data.split('_')
        quiz_id = int(parts[-1])
        all_tests = db.get_questions_by_battle_id(quiz_id)
        categories = db.get_battle_by_parent_id(quiz_id)
        if not all_tests and not categories:
            await callback_query.message.answer("Bu bo'limda hozirda hech qanday ma'lumot mavjud emas")
            return
        if not all_tests:
            keyboard = await create_keyboard_with_categories(categories, lang_id, 'quiz_battle_')
            await callback_query.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)

        if not categories:
            print(quiz_id,"quiz")
            await state.update_data(quiz_id=quiz_id)
            await bot.send_message(callback_query.from_user.id, "Savollar sonini kiriting:")
            await RoomQuizStates.quiz_number.set()
    except (ValueError, IndexError) as e:
        logging.error(f"Viktorina ID parsingida xato: {e}")

@dp.message_handler(state=RoomQuizStates.quiz_number)
async def process_quiz_number(message: types.Message, state: FSMContext):
    """
    Savollar sonini qayta ishlash.
    """
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

@dp.message_handler(state=RoomQuizStates.quiz_time)
async def process_quiz_time(message: types.Message, state: FSMContext):
    """
    Savollarni vaqtini qayta ishlash.
    """
    if not message.text.isdigit():
        await message.answer("Iltimos, vaqtni sonlarda kiriting.")
        return

    data = await state.get_data()
    quiz_id = data.get("quiz_id")
    quiz_number = data.get("quiz_number")
    quiz_time = int(message.text)

    await state.update_data(quiz_time=quiz_time)

    uuid_val = uuid.uuid4()
    unique_id = base64.urlsafe_b64encode(uuid_val.bytes)[:4].decode('utf-8').replace('_', '-')
    bot_username =  "wisdom_lc_vocab_bot"
    user_id = message.from_user.id
    current_time = datetime.now()
    formatted_time = current_time.strftime('%m-%d-%Y %H:%M')

    invite_link = (
        f"https://t.me/{bot_username}?start={user_id}_quiz_{quiz_id}_{unique_id}_number_{quiz_number}_time_{quiz_time}"
    )

    invite_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton(text="Botga qo'shilish", url=invite_link))
    await message.answer("Botga qo'shilish uchun quyidagi tugmani bosing:", reply_markup=invite_keyboard)
    db.add_history_entry(user_id, quiz_id, unique_id, quiz_number, quiz_time, formatted_time)
    await state.finish()

@dp.message_handler(state=GroupQuizStates.waiting_for_answer, content_types=types.ContentType.TEXT)
async def answer_received(message: types.Message, state: FSMContext):
    """
    Javob qabul qilishni boshqarish.
    """
    user_data = await state.get_data()
    true_answer = user_data['true_answer'].strip()
    answers_list = user_data.get('answers_list', [])
    user_answer = message.text.strip().lower()

    answer_is_correct = user_answer == true_answer.lower()
    answers_list.append(answer_is_correct)

    await state.update_data(answers_list=answers_list, answered=True)
    await message.answer("Javobingiz to'g'ri!" if answer_is_correct else f"Javobingiz noto'g'ri! To'g'ri javob: {true_answer}")

    await GroupQuizStates.sending_next_question.set()
    await send_next_question(message, state)

async def send_next_question(message: types.Message, state: FSMContext):
    """
    Keyingi savolni yuborishni boshqarish.
    """
    user_data = await state.get_data()
    questions = user_data.get('questions', [])
    current_question_index = user_data.get('current_question_index', 0)
    quiz_ended = user_data.get('quiz_ended', False)

    if current_question_index < len(questions) and not quiz_ended:
        question = questions[current_question_index]
        question_text = question['answer_a']
        true_answer = question['question']
        question_number = current_question_index + 1
        total_questions = len(questions)
        await message.answer(f"{question_number}/{total_questions}\n<b>Savol:</b> {question_text}", parse_mode='html')

        task_id = random.randint(1, 1_000_000)
        await state.update_data(true_answer=true_answer, current_question_index=current_question_index + 1, answered=False, current_task_id=task_id)
        await GroupQuizStates.waiting_for_answer.set()

        timeout_task = asyncio.create_task(check_answer_timeout(message, state, task_id))

        await state.update_data(timeout_task_id=id(timeout_task))
    elif not quiz_ended:
        await GroupQuizStates.quiz_ended.set()
        await end_quiz(message, state)

async def safe_send_message(message: types.Message, text: str, retry_after: int = 5, retry_count: int = 0):
    try:
        sent_message = await message.answer(text)
        return sent_message
    except RetryAfter as e:
        if retry_count < 5:
            logging.warning(f"Flood control oshdi. {e.timeout} soniyada qayta urinib ko'ring.")
            await asyncio.sleep(e.timeout + retry_after)
            return await safe_send_message(message, text, retry_after * 2, retry_count + 1)
        else:
            logging.error(f"Maksimal qayta urinishlar oshdi: {text}")
            return None
    except Throttled as e:
        if retry_count < 5:
            logging.warning(f"Throttle error. Retry in {e.rate} seconds.")
            await asyncio.sleep(e.rate + retry_after)
            return await safe_send_message(message, text, retry_after * 2, retry_count + 1)
        else:
            logging.error(f"Throttle error retries exceeded: {text}")
            return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

async def check_answer_timeout(message: types.Message, state: FSMContext, task_id: int):
    """
    Javob vaqtini tekshirish.
    """
    await asyncio.sleep(TIMEOUT_DURATION)
    user_data = await state.get_data()
    if user_data.get('answered') or user_data.get('current_task_id') != task_id:
        return

    quiz_ended = user_data.get('quiz_ended', False)
    if quiz_ended:
        return

    current_question_index = user_data.get('current_question_index', 0)
    answers_list = user_data.get('answers_list', [])

    if len(answers_list) < current_question_index:
        answers_list.append(False)

        await state.update_data(answers_list=answers_list)
        await message.answer("Vaqt tugadi! Siz javob bermadingiz.")
        await GroupQuizStates.sending_next_question.set()
        await send_next_question(message, state)

async def end_quiz(message: types.Message, state: FSMContext):
    """
    Viktorinani tugatishni boshqarish.
    """
    user_data = await state.get_data()
    answers_list = user_data.get('answers_list', [])
    quiz_num = user_data.get('quiz_number', NUM_QUESTIONS)
    answers_list = answers_list[:int(quiz_num)]  # Javoblar sonini belgilangan savollar soni bilan cheklash

    correct_answers_count = sum(answers_list)

    result_message = "\n".join(
        [f"{idx + 1}. {'✅' if result else '❌'}" for idx, result in enumerate(answers_list)]
    )
    name = user_data.get('name', 'Foydalanuvchi')
    result_message = f"{name} ning natijalari:\n{result_message}\n\n{name} foydalanuvchi {len(answers_list)} dan {correct_answers_count} taga to'g'ri javob berdi."

    db.add_results_entry(chat_id=message.from_user.id, unique_id=user_data.get('unique_id'), true_answers=correct_answers_count, false_answers=len(answers_list) - correct_answers_count, user_name=name)

    inline_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Reytingni olish", callback_data=f"get_rating_{user_data.get('unique_id')}")
    )

    await bot.send_message(chat_id=user_data.get('user_id'), text=result_message, reply_markup=inline_kb)
    await message.answer("Savollar tugadi. Natijalar ustozga jo'natildi.")
    await state.update_data(quiz_ended=True)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('get_rating_'))
async def get_rating_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Reytingni olish callbackini boshqarish.
    """
    unique_id = callback_query.data.split('_')[-1]

    try:
        results = db.get_results_by_unique_id(unique_id)

        if not results:
            raise ValueError("Berilgan unique ID uchun natijalar topilmadi.")

        sorted_results = sorted(results, key=lambda x: x['true_answers'], reverse=True)

        result_message = f"Unique ID {unique_id} uchun reyting:\n\n"
        for idx, result in enumerate(sorted_results):
            result_message += (
                f"{idx + 1}. Foydalanuvchi ismi: {result['user_name']}\n"
                f"To'g'ri javoblar: {result['true_answers']}\n"
                f"Noto'g'ri javoblar: {result['false_answers']}\n"
                "----------------------------------\n"
            )

        await callback_query.message.answer(result_message)

    except ValueError as e:
        await callback_query.message.answer(str(e))

    except Exception as e:
        logging.error(f"Natijalarni olishda xatolik yuz berdi: {e}")
        await callback_query.message.answer("Natijalarni olishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")

@dp.message_handler(state=QuizStates.QUIZ_START)
async def quiz_start_handler(message: types.Message, state: FSMContext):
    """
    Viktorinani boshlashni boshqarish.
    """
    name = message.text
    await state.update_data(name=name)
    user_id = message.from_user.id
    user_exists = db.get_user_by_chat_id(user_id)

    if not user_exists:
        language_id = 1
        db.add_user(chat_id=user_id)
        db.update_user_field(user_id, "lang_id", language_id)
        db.update_user_field(key='first_name', value=name, chat_id=user_id)

    user_data = await state.get_data()
    quiz_num = int(user_data.get('quiz_number'))
    quiz_time = user_data.get('quiz_time')
    owner_id = user_data.get('user_id')
    quiz_id = user_data.get('quiz_id')
    unique_id = user_data.get('unique_id')
    db.update_user_field(key='first_name', value=name, chat_id=user_id)

    await bot.send_message(text=f"{unique_id}ga {name} qo'shildi", chat_id=owner_id)
    await message.answer(f"Savollarga javob bering. Har bir savol uchun {quiz_time} soniya vaqt beriladi.")

    questions = db.get_questions_by_battle_id(quiz_id)
    random.shuffle(questions)
    selected_questions = questions[:quiz_num]
    await state.update_data(questions=selected_questions, current_question_index=0, answers_list=[])
    await GroupQuizStates.sending_next_question.set()
    await send_next_question(message, state)