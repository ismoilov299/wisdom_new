import sqlite3
import traceback
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from uuid import uuid4
import asyncio
import json
import os

# Django ORM-ni faqat mavjud bo'lsa ishlaydigan qilamiz
USE_DJANGO_ORM = False

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back.config.settings')
    django.setup()
    from back.bot_app.models import User, Category, Battle, Test, History, Results, SetAdmin, SetBio
    USE_DJANGO_ORM = True
    logging.info("Django ORM muvaffaqiyatli yuklandi")
except ImportError as e:
    logging.warning(f"Django ORM ni yuklashda xatolik yuz berdi: {e}")
    logging.warning("SQLite to'g'ridan-to'g'ri ishlatiladi")
except Exception as e:
    logging.warning(f"Django ORM ni yuklashda xatolik yuz berdi: {e}")
    logging.warning("SQLite to'g'ridan-to'g'ri ishlatiladi")

# Loader va kesh funksiyalarini keyinroq import qilamiz
# Circular import xatosidan qochish uchun


# Loader va kesh funksiyalarini keyinroq import qilamiz
# Circular import xatosidan qochish uchun

def logger(statement):
    print(f"""
--------------------------------------------------------
Executing:
 {statement}
--------------------------------------------------------
""")


class DataBase:
    order_id_counter = 1010

    def __init__(self, path_to_db='back/db.sqlite3'):
        self.path_to_db = path_to_db
        self._connection_cache = {}

    # SQLite bilan ishlash metodlari

    @property
    def connection(self):
        return sqlite3.connect(self.path_to_db)

    def get_connection(self):
        """Get a database connection from the connection pool"""
        import threading
        thread_id = threading.get_ident()

        if thread_id not in self._connection_cache:
            conn = sqlite3.connect(self.path_to_db)
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode = WAL')
            # Optimize for speed with reasonable safety
            conn.execute('PRAGMA synchronous = NORMAL')
            self._connection_cache[thread_id] = conn

        return self._connection_cache[thread_id]

    def execute(self, sql: str, parameters: tuple = None, fetchone=False, fetchall=False, commit=False):
        """Execute SQL with better error handling and connection management"""
        if not parameters:
            parameters = ()

        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(sql, parameters)

            data = None
            if commit:
                connection.commit()
            if fetchall:
                data = cursor.fetchall()
            if fetchone:
                data = cursor.fetchone()

            return data
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            logging.error(f"SQL: {sql}")
            logging.error(f"Parameters: {parameters}")
            raise

    # Sinxron (oddiy) metodlar

    def get_user_by_chat_id(self, chat_id: int):
        """
        Retrieve user data from bot_app_user based on the provided chat_id.

        :param chat_id: The chat_id of the user.
        :return: User data as a tuple or None if not found.
        """
        sql = "SELECT * FROM bot_app_user WHERE chat_id = ?"
        user_data = self.execute(sql, (chat_id,), fetchone=True)
        return user_data

    def get_user_language_id(self, chat_id: int):
        """
        Retrieve the language ID of the user based on the provided chat_id.

        :param chat_id: The chat_id of the user.
        :return: Language ID as an integer or None if the user is not found.
        """
        sql = "SELECT lang_id FROM bot_app_user WHERE chat_id = ?"
        lang_id = self.execute(sql, (chat_id,), fetchone=True)
        return lang_id[0] if lang_id else None

    def get_all_users(self):
        """
        Retrieve all users from the bot_app_user table.

        :return: List of user data tuples.
        """
        sql = "SELECT * FROM bot_app_user"
        users_data = self.execute(sql, fetchall=True)
        return users_data

    def get_root_categories(self):
        """
        Retrieve root categories from the bot_app_category table where parent_id is NULL.

        :return: List of root category data tuples.
        """
        sql = "SELECT * FROM bot_app_category WHERE parent_id IS NULL"
        root_categories_data = self.execute(sql, fetchall=True)
        return root_categories_data

    def get_root_battle(self):
        """
        Retrieve root categories from the bot_app_battle table where parent_id is NULL.

        :return: List of root category data tuples.
        """
        sql = "SELECT * FROM bot_app_battle WHERE parent_id IS NULL"
        root_categories_data = self.execute(sql, fetchall=True)
        return root_categories_data

    def get_categories_by_parent_id(self, parent_id):
        """
        Retrieve categories from the bot_app_category table based on the provided parent_id.

        :param parent_id: The parent_id to filter categories.
        :return: List of category data tuples.
        """
        sql = "SELECT * FROM bot_app_category WHERE parent_id = ?"
        categories_data = self.execute(sql, (parent_id,), fetchall=True)
        return categories_data

    def get_battle_by_parent_id(self, parent_id):
        """
        Retrieve categories from the bot_app_battle table based on the provided parent_id.

        :param parent_id: The parent_id to filter categories.
        :return: List of category data tuples.
        """
        sql = "SELECT * FROM bot_app_battle WHERE parent_id = ?"
        categories_data = self.execute(sql, (parent_id,), fetchall=True)
        return categories_data

    def get_full_subcategory_name(self, id):
        """
        Retrieve the subcategory name from the bot_app_battle table based on the provided id.

        :param id: The id to filter categories.
        :return: The subcategory name as a string.
        """
        sql = "SELECT name_uz FROM bot_app_battle WHERE id = ?"
        result = self.execute(sql, (id,), fetchone=True)
        return result[0] if result else None

    def get_test_by_battle_id(self, battle_id):
        """
        Retrieve categories from the bot_app_battle table based on the provided parent_id.

        :param parent_id: The parent_id to filter categories.
        :return: List of category data tuples.
        """
        sql = "SELECT * FROM bot_app_test WHERE battle_id = ?"
        categories_data = self.execute(sql, (battle_id,), fetchall=True)
        return categories_data

    def get_parent_id_by_category_id(self, category_id: int):
        """
        Retrieve parent_id from bot_app_category based on the provided category_id.

        :param category_id: The id of the category.
        :return: The parent_id or None if not found.
        """
        sql = "SELECT parent_id FROM bot_app_category WHERE id = ?"
        result = self.execute(sql, (category_id,), fetchone=True)
        return result[0] if result else None

    def get_questions_by_battle_id(self, battle_id: int):
        """
        Retrieve questions and their answers based on the given battle_id from the bot_app_test table,
        including the column names in the result.

        :param battle_id: The battle_id to filter questions.
        :return: A list of dictionaries, each containing the question and answers for the given battle_id,
                 with column names as keys.
        """
        sql = """
            SELECT question, answer_a, answer_b, answer_c, answer_d
            FROM bot_app_test
            WHERE battle_id = ?
        """
        connection = self.connection
        cursor = connection.cursor()
        cursor.execute(sql, (battle_id,))
        data = cursor.fetchall()

        # Fetching column names from the cursor
        columns = [column[0] for column in cursor.description]

        connection.close()

        # Zipping column names with data to create a list of dictionaries
        questions = [dict(zip(columns, row)) for row in data]
        return questions

    def get_questions_by_category_id(self, category_id: int):
        """
        Retrieve questions and their answers based on the given battle_id from the bot_app_test table,
        including the column names in the result.

        :param category_id: The battle_id to filter questions.
        :return: A list of dictionaries, each containing the question and answers for the given category_id,
                 with column names as keys.
        """
        sql = """
            SELECT question, answer_a, answer_b, answer_c, answer_d
            FROM bot_app_test
            WHERE category_id = ?
        """
        connection = self.connection
        cursor = connection.cursor()
        cursor.execute(sql, (category_id,))
        data = cursor.fetchall()

        # Fetching column names from the cursor
        columns = [column[0] for column in cursor.description]

        connection.close()

        # Zipping column names with data to create a list of dictionaries
        questions = [dict(zip(columns, row)) for row in data]
        return questions

    def update_user_field(self, chat_id: int, key: str, value: str):
        """
        Update a field in the bot_app_user table based on chat_id.

        :param chat_id: The chat_id of the user.
        :param field: The field name to update.
        :param value: The new value for the field.
        """
        sql = f"UPDATE bot_app_user SET {key} = ? WHERE chat_id = ?"
        self.execute(sql, (value, chat_id), commit=True)

    def add_user(self, chat_id: int):
        """
        Add a new user to the bot_app_user table with the specified chat_id.

        :param chat_id: The chat_id of the user.
        """
        sql = """
            INSERT INTO bot_app_user(chat_id)
            VALUES (?)
        """
        self.execute(sql, (chat_id,), commit=True)

    def add_test_question(self, question: str, answer_a: str, answer_b: str, answer_c: str, answer_d: str,
                          battle_id: int = 2):
        """
        Add a test question and its answers to the bot_app_test table along with an associated battle_id.
        If no battle_id is provided, defaults to 2.

        :param question: The test question.
        :param answer_a: Answer option A.
        :param answer_b: Answer option B.
        :param answer_c: Answer option C.
        :param answer_d: Answer option D.
        :param battle_id: The ID of the battle associated with the question (default is 2).
        """
        sql = """
            INSERT INTO bot_app_test (question, answer_a, answer_b, answer_c, answer_d, battle_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, (question, answer_a, answer_b, answer_c, answer_d, battle_id), commit=True)

    def add_history_entry(self, user_id: int, quiz_id: int, unique_id: str, quiz_number: int, quiz_time: int,
                          created_at: str):
        """
        Add an entry to the bot_app_history table.

        :param user_id: The user ID associated with the history entry.
        :param quiz_id: The quiz ID associated with the history entry.
        :param unique_id: The unique ID associated with the history entry.
        :param quiz_number: The quiz number associated with the history entry.
        :param quiz_time: The time taken for the quiz in seconds.
        """
        sql = """
            INSERT INTO bot_app_history(user_id, quiz_id, unique_id, quiz_number, quiz_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, (user_id, quiz_id, unique_id, quiz_number, quiz_time, created_at), commit=True)

    def get_quiz_number_by_unique_id(self, unique_id: str):
        sql = "SELECT quiz_number FROM bot_app_history WHERE unique_id = ?"
        result = self.execute(sql, (unique_id,), fetchone=True)
        return result[0] if result else None

    def get_created_at_by_unique_id(self, unique_id: str):
        """
        Retrieve the 'created_at' timestamp from the bot_app_history table based on the unique_id.

        :param unique_id: The unique ID associated with the history entry.
        :return: The 'created_at' timestamp as a string or None if not found.
        """
        sql = "SELECT created_at FROM bot_app_history WHERE unique_id = ?"
        created_at = self.execute(sql, (unique_id,), fetchone=True)
        return created_at[0] if created_at else None

    def get_user_info_by_chat_id(self, chat_id: int):
        """
        Retrieve the user ID and first name based on the provided chat ID.

        :param chat_id: The chat ID.
        :return: Tuple containing (user_id, first_name) or None if not found.
        """
        sql = "SELECT id, first_name FROM bot_app_user WHERE chat_id = ?"
        result = self.execute(sql, (chat_id,), fetchone=True)
        return result if result else None

    def add_results_entry(self, chat_id, unique_id, true_answers, false_answers, user_name):
        # user_name qiymatini tekshirish
        if user_name is None:
            user_name = "unknown"  # yoki mos qiymat

        # Avval foydalanuvchi ID-ni olish
        sql_user = "SELECT id FROM bot_app_user WHERE chat_id = ?"
        user_id_result = self.execute(sql_user, (chat_id,), fetchone=True)

        if user_id_result:
            user_id = user_id_result[0]

            sql = """
            INSERT INTO bot_app_results (user_id, unique_id, true_answers, false_answers, user_name)
            VALUES (?, ?, ?, ?, ?)
            """
            self.execute(sql, (user_id, unique_id, true_answers, false_answers, user_name), commit=True)

    def get_results_by_unique_id(self, unique_id: str) -> list:
        """
        Unique ID bo'yicha natijalarni olish

        :param unique_id: Unique ID
        :return: Natijalar ro'yxati
        """
        try:
            sql = """
                SELECT r.id, r.user_name, r.true_answers, r.false_answers, r.user_id, r.unique_id
                FROM bot_app_results r
                WHERE r.unique_id = ?
            """
            rows = self.execute(sql, (unique_id,), fetchall=True)

            if not rows:
                return []

            # Column names
            column_names = ["id", "user_name", "true_answers", "false_answers", "user_id", "unique_id"]

            # Rows to dictionaries
            results = [dict(zip(column_names, row)) for row in rows]
            return results
        except Exception as e:
            print(f"Error in get_results_by_unique_id: {e}")
            return []

    # def get_results_by_unique_id(self, unique_id: str) -> list:
    #     """
    #     Retrieve all data from the bot_app_results table by unique_id.
    #
    #     :param unique_id: The unique ID to filter the results.
    #     :return: A list of dictionaries containing the results data.
    #     :raises ValueError: If no results are found for the given unique_id.
    #     """
    #     try:
    #         sql = """
    #             SELECT * FROM bot_app_results
    #             WHERE unique_id = ?
    #         """
    #         rows = self.execute(sql, (unique_id,), fetchall=True)
    #
    #         if not rows:
    #             error_message = f"No results found for unique_id {unique_id}."
    #             # logging.error(error_message)
    #             raise ValueError(error_message)
    #
    #         # Assuming the column names are known
    #         column_names = ["id", "user_name", "true_answers", "false_answers", "user_id", "unique_id"]
    #
    #         results = [dict(zip(column_names, row)) for row in rows]
    #         # logging.info(f"Retrieved {len(results)} results for unique_id {unique_id}.")
    #         return results
    #
    #     except Exception as e:
    #         print(e)
    #         # logging.error(f"Failed to retrieve results for unique_id {unique_id}: {e}")
    #         raise

    def fetch_all_setbio_data(self):
        """
        Fetch all data from the bot_app_setbio table.

        :return: List of tuples containing all rows from the bot_app_setbio table.
        """
        sql = "SELECT * FROM bot_app_setbio"
        results = self.execute(sql, fetchall=True)
        return results

    def get_all_setadmin_user_ids(self):
        """
        Retrieve the user_id column from the bot_app_setadmin table.

        :return: A list of user_id values.
        """
        # Construct the SQL query to select the user_id column from bot_app_setadmin
        sql = "SELECT user_id FROM bot_app_setadmin"

        # Execute the query and fetch all user_id values
        user_ids = self.execute(sql, fetchall=True)

        # Extract user_id values from the result
        user_ids = [row[0] for row in user_ids]

        return user_ids

    def get_chat_id_by_user_id(self, user_id: int):
        """
        Retrieve chat_id from bot_app_user based on the provided user_id from bot_app_setadmin.

        :param user_id: The id of the user in bot_app_setadmin.
        :return: Chat id as an integer or None if not found.
        """
        # Retrieve chat_id from bot_app_user using the provided user_id
        sql_user = "SELECT chat_id FROM bot_app_user WHERE id = ?"
        chat_id_data = self.execute(sql_user, (user_id,), fetchone=True)

        if chat_id_data:
            # If chat_id found, return it
            return chat_id_data[0]

        return None

    # Asinxron wrapper metodlar - loader.py dagi get_cache, set_cache funksiyalarini ishlatish uchun

    async def get_user_by_chat_id_cached(self, chat_id: int):
        """Keshlashtirish bilan foydalanuvchini olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = f"user:data:{chat_id}"
        cached_data = await get_cache(cache_key)

        if cached_data is not None:
            return cached_data

        user_data = self.get_user_by_chat_id(chat_id)

        if user_data:
            await set_cache(cache_key, user_data, ttl=600)

        return user_data

    async def get_user_language_id_cached(self, chat_id: int):
        """Keshlashtirish bilan til ID-sini olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = f"user:lang:{chat_id}"
        cached_lang = await get_cache(cache_key)

        if cached_lang is not None:
            return cached_lang

        lang_id = self.get_user_language_id(chat_id)

        if lang_id is not None:
            await set_cache(cache_key, lang_id, ttl=3600)

        return lang_id

    async def get_root_categories_cached(self):
        """Keshlashtirish bilan ildiz kategoriyalarni olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = "categories:root"
        cached_categories = await get_cache(cache_key)

        if cached_categories is not None:
            return cached_categories

        categories = self.get_root_categories()

        if categories:
            await set_cache(cache_key, categories, ttl=3600)

        return categories

    async def get_root_battle_cached(self):
        """Keshlashtirish bilan ildiz bellashuvlarni olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = "battles:root"
        cached_battles = await get_cache(cache_key)

        if cached_battles is not None:
            return cached_battles

        battles = self.get_root_battle()

        if battles:
            await set_cache(cache_key, battles, ttl=3600)

        return battles

    async def get_categories_by_parent_id_cached(self, parent_id):
        """Keshlashtirish bilan kategoriyalarni olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = f"categories:parent:{parent_id}"
        cached_categories = await get_cache(cache_key)

        if cached_categories is not None:
            return cached_categories

        categories = self.get_categories_by_parent_id(parent_id)

        if categories:
            await set_cache(cache_key, categories, ttl=1800)

        return categories

    async def get_battle_by_parent_id_cached(self, parent_id):
        """Keshlashtirish bilan bellashuvlarni olish"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        cache_key = f"battles:parent:{parent_id}"
        cached_battles = await get_cache(cache_key)

        if cached_battles is not None:
            return cached_battles

        battles = self.get_battle_by_parent_id(parent_id)

        if battles:
            await set_cache(cache_key, battles, ttl=1800)

        return battles

    async def update_user_field_cached(self, chat_id: int, key: str, value: str):
        """Keshni yangilash bilan foydalanuvchi maydonini yangilash"""
        # loader.py dan kesh funksiyalarini import qilish
        from loader import get_cache, set_cache, delete_cache

        # Bazada yangilash
        self.update_user_field(chat_id, key, value)

        # Keshni tozalash
        await delete_cache(f"user:data:{chat_id}")
        await delete_cache(f"user:lang:{chat_id}")

        # Agar til yangilangan bo'lsa, keshga saqlash
        if key == "lang_id":
            await set_cache(f"user:lang:{chat_id}", value, ttl=3600)

        return True

    def get_history_by_unique_id(self, unique_id: str):
        """
        Unique ID bo'yicha history ma'lumotlarini olish

        :param unique_id: Unique ID
        :return: (quiz_id, quiz_number, quiz_time, user_id, created_at) yoki None
        """
        try:
            sql = """
                SELECT quiz_id, quiz_number, quiz_time, user_id, created_at 
                FROM bot_app_history 
                WHERE unique_id = ?
            """
            result = self.execute(sql, (unique_id,), fetchone=True)

            if result:
                # Dictionary ga aylantiramiz
                return {
                    'quiz_id': result[0],
                    'quiz_number': result[1],
                    'quiz_time': result[2],
                    'user_id': result[3],
                    'created_at': result[4]
                }
            return None
        except Exception as e:
            print(f"Error in get_history_by_unique_id: {e}")
            return None

    def get_quiz_id_by_unique_id(self, unique_id: str):
        """
        Unique ID bo'yicha quiz ID olish

        :param unique_id: Unique ID
        :return: Quiz ID yoki None
        """
        sql = "SELECT quiz_id FROM bot_app_history WHERE unique_id = ?"
        result = self.execute(sql, (unique_id,), fetchone=True)
        return result[0] if result else None

