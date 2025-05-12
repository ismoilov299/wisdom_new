import sys
from unicodedata import category

from aiogram import types
from handlers.users.texts import BACK, TEXT_ALL
import logging
import random
import asyncio
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import RetryAfter
from loader import db, dp

sys.stdout.reconfigure(encoding='utf-8')

class QuizState(StatesGroup):
    waiting_for_answer = State()
    sending_next_question = State()
    quiz_ended = State()

PRODUCT_PREFIX = 'product_'
TEST_PREFIX = 'test_'
NUM_QUESTIONS = 30
TIMEOUT_DURATION = 20

logging.basicConfig(level=logging.INFO)

@dp.callback_query_handler(lambda callback: callback.data.startswith(PRODUCT_PREFIX))
async def handle_product_callback(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split('_')
        print(f'parts {parts}')
        category_range = parts[1]
        print("category range ", category_range)
        print(category_range)
        start_range, end_range = map(int, category_range.split('-'))
        parent_id = int(parts[-1])
    except (ValueError, IndexError) as e:
        logging.error(f"Xatolik: {e}")
        return
    await start_quiz(callback.message, state, start_range, end_range, parent_id, is_battle=False)


@dp.callback_query_handler(lambda c: c.data.startswith(TEST_PREFIX))
async def handle_battle_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split('_')
        print("parts: ", parts)

        if len(parts) < 2:
            logging.error(f"Unexpected number of parts in callback data: {len(parts)}")
            await callback.message.answer("Noto'g'ri formatdagi ma'lumot. Iltimos, qayta urinib ko'ring.")
            return
        if len(parts) == 5:
            category_id = parts[1]
            parent_name = parts[2]
            sub_name = parts[3]
            name = parts[4]

            # Ma'lumotlar bazasidan to'liq subkategoriya nomini olish
            full_subcategory = db.get_full_subcategory_name(category_id)
            # await callback.message.answer(f"parent name: {parent_name}, sub_name:{sub_name}, name: {name}")

        parent_id = int(parts[1])  # Asosan ikkinchi bo'limda bo'lishi kutilmoqda

        # Get the current state data
        user_data = await state.get_data()
        current_parent = user_data.get('parent_name', 'Unknown')
        current_category = user_data.get('category_name', 'Unknown')

        if len(parts) == 3:
            # Bu subkategoriya tanlovi
            category_id = parts[1]
            shortened_name = parts[2]

            # Ma'lumotlar bazasidan to'liq subkategoriya nomini olish
            full_subcategory = db.get_full_subcategory_name(category_id)
            category_name_2 = full_subcategory

            # print(f"Parent name: {current_parent}, Category name: {current_category}, Category name 2: {category_name_2}")

            # State'ni yangilash
            await state.update_data(
                parent_name=current_parent,
                category_name=current_category,
                category_name_2=category_name_2
            )
        elif len(parts) == 4:
            # Bu asosiy kategoriya tanlovi
            new_category_name = parts[2]
            parent_name = parts[3]

            # print(f"Parent name: {parent_name}, Category name: {new_category_name}")

            # State'ni yangilash
            await state.update_data(
                parent_name=parent_name,
                category_name=new_category_name,
                category_name_2=None
            )
        else:
            logging.error(f"Unexpected number of parts in callback data: {len(parts)}")
            await callback.message.answer("Noto'g'ri formatdagi ma'lumot. Iltimos, qayta urinib ko'ring.")
            return

        user_id = callback.from_user.id
        lang_id = db.get_user_language_id(user_id)
        categories = db.get_battle_by_parent_id(parent_id)

        if categories:
            # Subkategoriyalar uchun yangi klaviatura yaratish
            keyboard = InlineKeyboardMarkup()
            for category in categories:
                category_id, sub_category_name, _, _, _ = category
                button_text = f"{sub_category_name}"
                short_callback_data = f"test_{category_id}_{sub_category_name[:20]}"
                button = InlineKeyboardButton(text=button_text, callback_data=short_callback_data)
                keyboard.add(button)

            back_button = InlineKeyboardButton(text=BACK[lang_id], callback_data="back_to_battle")
            keyboard.add(back_button)
            await callback.message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
        else:
            # Savollarni olish
            all_tests = db.get_questions_by_battle_id(parent_id)
            if not all_tests:
                await callback.message.answer("Bu bo'limda hozirda hech qanday ma'lumot mavjud emas")
                return

            selected_tests = random.sample(all_tests, NUM_QUESTIONS) if len(all_tests) >= NUM_QUESTIONS else all_tests

            # Davlatdan hozirgi ma'lumotlarni qayta oling
            user_data = await state.get_data()
            current_parent = user_data.get('parent_name', 'Unknown')
            current_category = user_data.get('category_name', 'Unknown')
            current_category_2 = user_data.get('category_name_2', 'Unknown')

            print(f"Starting quiz - Parent name: {current_parent}, Category name: {current_category}, Category name 2: {current_category_2}")

            await state.update_data(selected_tests=selected_tests)
            await start_quiz_battle(callback.message, state, 1, len(selected_tests), parent_id, is_battle=True)

    except (ValueError, IndexError) as e:
        logging.error(f"Xatolik: {e}")
        await callback.message.answer("Xatolik yuz berdi, iltimos qayta urinib ko'ring.")
        return


async def start_quiz_battle(message: types.Message, state: FSMContext, start_range: int, end_range: int, parent_id: int, is_battle: bool = False):
    user_data = await state.get_data()
    selected_questions = user_data['selected_tests']
    filtered_questions = selected_questions[start_range - 1:end_range]
    random.shuffle(filtered_questions)
    selected_questions = filtered_questions[:NUM_QUESTIONS]
    await state.update_data(questions=selected_questions, current_question_index=0, answers_list=[], quiz_ended=False, current_task_id=None)
    await safe_send_message(message, f"Sizga {NUM_QUESTIONS} ta savol beriladi. Har bir savol uchun {TIMEOUT_DURATION} soniya vaqt beriladi")
    await QuizState.sending_next_question.set()
    await send_next_question(message, state)

@dp.message_handler(state=QuizState.waiting_for_answer, content_types=types.ContentType.TEXT)
async def answer_received(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    true_answer = user_data['true_answer'].strip()
    answers_list = user_data.get('answers_list', [])
    user_answer = message.text.strip().lower()
    answer_is_correct = user_answer == true_answer.lower()
    answers_list.append(answer_is_correct)
    await state.update_data(answers_list=answers_list, answered=True)
    await safe_send_message(message, "Javobingiz to'g'ri!" if answer_is_correct else f"Javobingiz noto'g'ri! To'g'ri javob: {true_answer}")
    await QuizState.sending_next_question.set()
    await send_next_question(message, state)

async def send_next_question(message: types.Message, state: FSMContext):
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
        await safe_send_message(message, f"{question_number}/{total_questions}\n<b>Savol:</b> {question_text}")

        task_id = random.randint(1, 1_000_000)
        await state.update_data(true_answer=true_answer, current_question_index=current_question_index + 1, answered=False, current_task_id=task_id)
        await QuizState.waiting_for_answer.set()

        timeout_task = asyncio.create_task(check_answer_timeout(message, state, task_id))
        await state.update_data(timeout_task_id=id(timeout_task))

    elif not quiz_ended:
        await QuizState.quiz_ended.set()
        await end_quiz(message, state)

async def safe_send_message(message: types.Message, text: str, retry_after: int = 5, retry_count: int = 0):
    try:
        sent_message = await message.answer(text)
        return sent_message
    except RetryAfter as e:
        if retry_count < 5:  # Maksimal qayta urinishlar soni
            logging.warning(f"Flood control oshdi. {e.timeout} soniyada qayta urinib ko'ring.")
            await asyncio.sleep(e.timeout + retry_after)
            return await safe_send_message(message, text, retry_after * 2, retry_count + 1)
        else:
            logging.error(f"Maksimal qayta urinishlar oshdi: {text}")
            return None

async def check_answer_timeout(message: types.Message, state: FSMContext, task_id: int):
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
        await safe_send_message(message, "Vaqt tugadi! Siz javob bermadingiz.")
        await QuizState.sending_next_question.set()
        await send_next_question(message, state)


async def end_quiz(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    answers_list = user_data.get('answers_list', [])
    correct_answers_count = sum(answers_list)
    result_message = "\n".join(
        [f"{idx + 1}. {'✅' if result else '❌'}" for idx, result in enumerate(answers_list)]
    )
    parent_name = user_data.get('parent_name', 'Unknown')
    category_name = user_data.get('category_name', 'Unknown')
    category_name_2 = user_data.get('category_name_2', 'Unknown')

    if parent_name == "Lesson":
        result_text = f"Savollar tugadi! Siz{category_name} {parent_name} "
    elif category_name_2 is not None and category_name_2.lower() != 'unknown':
        result_text = f"Savollar tugadi! Siz {parent_name}, {category_name}, {category_name_2} dan test topshirdingiz!"
    else:
        result_text = f"Savollar tugadi! Siz {parent_name}, {category_name} dan test topshirdingiz!"

    print(f"Quiz ended - Parent name: {parent_name}, Category name: {category_name}, Category name 2: {category_name_2}")

    await safe_send_message(message,
                            f"{result_text}\nSizning natijalaringiz:\n{result_message}\nSiz {len(answers_list)} ta savoldan {correct_answers_count} taga to'g'ri javob berdingiz.")
    await state.update_data(quiz_ended=True)
    timeout_task_id = user_data.get('timeout_task_id')
    if timeout_task_id:
        loop = asyncio.get_event_loop()
        for task in asyncio.all_tasks(loop=loop):
            if id(task) == timeout_task_id:
                task.cancel()
                break
    await state.finish()

async def start_quiz(message: types.Message, state: FSMContext, start_range: int, end_range: int, parent_id: int, is_battle: bool = False):
    try:
        user_id = message.from_user.id
        lang_id = db.get_user_language_id(user_id)
        categories = db.get_battle_by_parent_id(parent_id)
        keyboard = InlineKeyboardMarkup()

        for category in categories:
            category_id, category_name, _, _, _ = category
            button_text = f"{category_name}"
            callback_data = f"test_{category_id}_{category_name}"
            button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
            keyboard.add(button)
        back_button = InlineKeyboardButton(text=BACK[lang_id], callback_data="back_to_battle")
        keyboard.add(back_button)

        await message.edit_text(text=TEXT_ALL[lang_id], reply_markup=keyboard)
    except:
        questions = db.get_questions_by_battle_id(parent_id) if is_battle else db.get_questions_by_category_id(parent_id)
        filtered_questions = questions[start_range - 1:end_range]
        random.shuffle(filtered_questions)
        selected_questions = filtered_questions[:NUM_QUESTIONS]
        await state.update_data(questions=selected_questions, current_question_index=0, answers_list=[], quiz_ended=False, current_task_id=None)
        await safe_send_message(message, f"Sizga {NUM_QUESTIONS} ta savol beriladi. Har bir savol uchun {TIMEOUT_DURATION} soniya vaqt beriladi")
        await QuizState.sending_next_question.set()
        await send_next_question(message, state)