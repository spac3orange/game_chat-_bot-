from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from config import logger
from filters.is_admin import IsAdmin
from keyboards import main_kb
from database import db
router = Router()
router.message.filter(
    IsAdmin(F)
)


@router.callback_query(F.data == 'adm_edit_descriptions')
async def p_edit_descriptions(callback: CallbackQuery):
    pass
