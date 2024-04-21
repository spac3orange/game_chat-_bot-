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
)


@router.callback_query(F.data == 'user_lk')
async def p_user_lk(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    user_balance = await db.get_user_balance(uid)
    user_info = (f'<b>Ваш ID</b>: {uid}'
                 f'\n<b>Баланс:</b> {user_balance} рублей')
    await callback.message.edit_text(user_info, reply_markup=main_kb.lk_menu())
