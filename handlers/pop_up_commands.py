from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from config import logger
from filters.is_admin import IsAdmin
from keyboards import main_kb
from database import db
router = Router()


@router.message(Command('support'))
async def p_support(message: Message):
    await message.answer('Тех. Поддержка: @stepusiks')