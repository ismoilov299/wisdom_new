from aiogram.dispatcher.filters.state import StatesGroup, State


class UserStates(StatesGroup):
    # Foydalanuvchi holatlari
    IN_START = State()
    IN_LANG = State()
    IN_NAME = State()
    IN_MENU = State()
    IN_PROFILE = State()    # Yangi: profil ko'rish holati
    SEARCH_MODE = State()   # Yangi: qidiruv holati


class QuizStates(StatesGroup):
    QUIZ_START = State()
    WAITING_FOR_ADMIN = State()  # Admin testni boshlashini kutish
    ACTIVE_QUIZ = State()  # Test hozir aktiv
    WAIT_QUIZ = State()    # Yangi: natijalarni ko'rib chiqish


class SettingName(StatesGroup):
    name = State()
    bio = State()           # Yangi: foydalanuvchi biografiyasi


class AdminBroadcast(StatesGroup):
    BROADCAST = State()
    SELECT_USERS = State()  # Yangi: foydalanuvchilarni tanlash
    CONFIRM = State()       # Yangi: xabarni tasdiqlash


class StatisticsStates(StatesGroup):
    # Yangi: Statistika bo'limi uchun holatlar
    VIEWING = State()
    FILTERING = State()
    EXPORTING = State()


class LeaderboardStates(StatesGroup):
    # Yangi: Yutuqlar taxtasi bo'limi uchun holatlar
    GLOBAL = State()
    CATEGORY = State()
    TIME_PERIOD = State()  # Haftalik/oylik/umumiy