from aiogram import Router, F
from aiogram.types import CallbackQuery

from filters.is_admin import IsAdmin

router = Router()
router.message.filter(
    IsAdmin(F)
)


@router.callback_query(F.data == 'adm_edit_descriptions')
async def p_edit_descriptions(callback: CallbackQuery):
    pass
