from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
router = Router()


@router.message()
async def p_message(message: Message):
    await message.answer('Я не знаю такой команды🤨')
