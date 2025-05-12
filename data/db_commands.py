
import sqlite3
import traceback
from datetime import datetime
from typing import List, Tuple
from uuid import uuid4


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


    @property
    def connection(self):
        return sqlite3.connect(self.path_to_db)

    def execute(self, sql: str, parameters: tuple = None, fetchone=False, fetchall=False, commit=False):
        if not parameters:
            parameters = ()
        connection = self.connection
        connection.set_trace_callback(logger)
        cursor = connection.cursor()
        data = None
        cursor.execute(sql, parameters)

        if commit:
            connection.commit()
        if fetchall:
            data = cursor.fetchall()
        if fetchone:
            data = cursor.fetchone()
        connection.close()
        return data

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
        # SQL query to select categories based on parent_id
        sql = "SELECT * FROM bot_app_category WHERE parent_id = ?"

        # Execute the query with the provided parent_id and fetch all the results
        categories_data = self.execute(sql, (parent_id,), fetchall=True)

        # Return the list of category data tuples
        return categories_data

    def get_battle_by_parent_id(self, parent_id):
        """
        Retrieve categories from the bot_app_battle table based on the provided parent_id.

        :param parent_id: The parent_id to filter categories.
        :return: List of category data tuples.
        """
        # SQL query to select categories based on parent_id
        sql = "SELECT * FROM bot_app_battle WHERE parent_id = ?"

        # Execute the query with the provided parent_id and fetch all the results
        categories_data = self.execute(sql, (parent_id,), fetchall=True)

        # Return the list of category data tuples
        return categories_data

    def get_full_subcategory_name(self, id):
        """
        Retrieve the subcategory name from the bot_app_battle table based on the provided id.

        :param id: The id to filter categories.
        :return: The subcategory name as a string.
        """
        # SQL query to select the subcategory name based on id
        sql = "SELECT name_uz FROM bot_app_battle WHERE id = ?"

        # Execute the query with the provided id and fetch one result
        result = self.execute(sql, (id,), fetchone=True)

        # If a result is found, return the name (first element of the tuple)
        if result:
            return result[0]
        else:
            return None  # or you could return an empty string or raise an exception

    def get_test_by_battle_id(self, battle_id):
        """
        Retrieve categories from the bot_app_battle table based on the provided parent_id.

        :param parent_id: The parent_id to filter categories.
        :return: List of category data tuples.
        """
        # SQL query to select categories based on parent_id
        sql = "SELECT * FROM bot_app_test WHERE battle_id = ?"

        # Execute the query with the provided parent_id and fetch all the results
        categories_data = self.execute(sql, (battle_id,), fetchall=True)

        # Return the list of category data tuples
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



    def get_order_products_by_order_id(self, order_id: int):
        """
        Retrieve order products from the bot_app_orderproduct table based on the provided order_id.

        :param order_id: The order_id to filter order products.
        :return: List of order product data tuples.
        """
        sql = "SELECT * FROM bot_app_orderproduct WHERE id = ?"

        # Assuming self.execute is a method for executing SQL queries in your class
        order_products_data = self.execute(sql, (order_id,), fetchall=True)

        return order_products_data
    def get_products_by_category_id(self, category_id: int):
        """
        Retrieve products from the bot_app_product table based on the provided category_id.

        :param category_id: The id of the category to filter products.
        :return: List of product data tuples.
        """
        sql = "SELECT * FROM bot_app_product WHERE category_id = ?"
        products_data = self.execute(sql, (category_id,), fetchall=True)
        return products_data

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

    def add_history_entry(self, user_id: int, quiz_id: int, unique_id: str, quiz_number: int, quiz_time: int, created_at: str):
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

        sql = """
        INSERT INTO bot_app_results (user_id, unique_id, true_answers, false_answers, user_name)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute(sql, (chat_id, unique_id, true_answers, false_answers, user_name), commit=True)

    def get_results_by_unique_id(self, unique_id: str) -> list:
        """
        Retrieve all data from the bot_app_results table by unique_id.

        :param unique_id: The unique ID to filter the results.
        :return: A list of dictionaries containing the results data.
        :raises ValueError: If no results are found for the given unique_id.
        """
        try:
            sql = """
                SELECT * FROM bot_app_results
                WHERE unique_id = ?
            """
            rows = self.execute(sql, (unique_id,), fetchall=True)

            if not rows:
                error_message = f"No results found for unique_id {unique_id}."
                # logging.error(error_message)
                raise ValueError(error_message)

            # Assuming the column names are known
            column_names = ["id", "user_name", "true_answers", "false_answers", "user_id","unique_id"]#["user_id", "unique_id", "true_answers", "false_answers", "user_name"]

            results = [dict(zip(column_names, row)) for row in rows]
            # logging.info(f"Retrieved {len(results)} results for unique_id {unique_id}.")
            return results

        except Exception as e:
            print(e)
            # logging.error(f"Failed to retrieve results for unique_id {unique_id}: {e}")
            raise

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