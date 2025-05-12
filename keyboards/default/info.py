from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import dp, db

@dp.message_handler(text=["ℹ️ Ma'lumotlarim"])
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    info = db.get_user_by_chat_id(user_id)
    print(info[3])
    if info[3] == 1:
        lang = "O'zbek tili"
    else:
        lang = "Rus tili"

    name = info[1]
    await message.answer(f"Sizning ma'lumotlaringiz\n"
                         f"Ism {name}\n"
                         f"tanlagan tilingiz {lang}")
