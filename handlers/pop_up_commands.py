from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command('support'))
async def p_support(message: Message):
    await message.answer('Тех. Поддержка: @egirlforyou')
