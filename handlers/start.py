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


async def parse_media(path='media/main_media_1.jpg'):
    return FSInputFile(path)


@router.message(Command(commands='start'))
async def process_start(message: Message, state: FSMContext):
    uid, username = message.from_user.id, message.from_user.username
    await db.add_user(uid, username)
    media = await parse_media()
    await message.answer_photo(media)
    await message.answer('<b>Добро пожаловать!</b>', reply_markup=main_kb.start_btns(uid))
    logger.info(f'User connected: {message.from_user.username}')


@router.message(Command(commands='cancel'))
async def process_start(message: Message, state: FSMContext):
    await state.clear()
    uid, username = message.from_user.id, message.from_user.username
    await db.add_user(uid, username)
    media = await parse_media()
    await message.answer_photo(media)
    await message.answer('<b>Добро пожаловать!</b>', reply_markup=main_kb.start_btns(uid))
    logger.info(f'User connected: {message.from_user.username}')


@router.callback_query(F.data == 'back_to_main')
async def p_bctm(callback: Message):
    uid = callback.from_user.id
    await callback.message.edit_text('<b>Добро пожаловать</b>', reply_markup=main_kb.start_btns(uid))


@router.callback_query(F.data == 'check_sub')
async def p_check_sub(callback: CallbackQuery):
    uid, username = callback.from_user.id, callback.from_user.username
    await db.add_user(uid, username)
    media = await parse_media()
    await callback.message.answer_photo(media)
    await callback.message.answer('<b>Добро пожаловать!</b>', reply_markup=main_kb.start_btns(uid))
    logger.info(f'User connected: {callback.from_user.username}')
