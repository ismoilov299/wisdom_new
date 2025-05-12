from aiogram import types
from aiogram.dispatcher.filters import BoundFilter

class FromGroupFilter(BoundFilter):
    def __init__(self, group_id: int):
        self.group_id = group_id

    async def check(self, message: types.Message):
        return message.chat.id == self.group_id