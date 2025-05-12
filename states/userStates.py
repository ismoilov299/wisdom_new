from aiogram.dispatcher.filters.state import StatesGroup, State


class UserStates(StatesGroup):
    # Define states inside the UserStates class
    IN_START = State()
    IN_LANG = State()
    IN_NAME = State()
    IN_MENU = State()




class QuizStates(StatesGroup):
    QUIZ_START = State()
    WAIT_QUIZ = State()


class SettingName(StatesGroup):
    name = State()



class AdminBroadcast(StatesGroup):
    BROADCAST = State()


