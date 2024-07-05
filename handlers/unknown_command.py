from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message()
async def p_message(message: Message):
    await message.answer('Я не знаю такой команды🤨')
