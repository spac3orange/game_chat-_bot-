from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards import main_kb

router = Router()


@router.callback_query(F.data == 'select_game')
async def p_select_game(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Здесь ты можешь найти девушек по играм'
                                     '\n<b>Выбери игру:</b>', reply_markup=main_kb.game_menu())
