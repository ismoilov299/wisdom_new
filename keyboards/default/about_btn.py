from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp, db


@dp.message_handler(text=['👨‍👩‍👦 Biz haqimizda', '👨‍👩‍👦 O нас'])
async def setting_menu(message: types.Message):

    user_ids = db.get_all_setadmin_user_ids()

    for user_id in user_ids:
        chat_id = db.get_chat_id_by_user_id(user_id)

    user_id = message.from_user.id
    lang_id = db.get_user_language_id(user_id)
    bios = db.fetch_all_setbio_data()
    if lang_id == 1:
        bio = bios[0]
        uz_text = bio[1]
        await message.answer(uz_text)
    else:
        bio = bios[0]
        ru_text = bio[2]
        await message.answer(ru_text)
