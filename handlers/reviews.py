from aiogram.types import Message, CallbackQuery, FSInputFile
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


@router.callback_query(F.data.startswith('revs_'))
async def get_revs(call: CallbackQuery):
    g_id = call.data.split('_')[-1]


    pass

