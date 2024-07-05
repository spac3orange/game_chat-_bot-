import asyncio
import json

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder

from config import aiogram_bot
from database import db
from filters.is_admin import IsAdmin
from keyboards import main_kb

router = Router()
router.message.filter(
    IsAdmin(F)
)


async def parse_media(path):
    return FSInputFile(path)


@router.callback_query(F.data == 'edit_reviews')
async def p_edit_revs(callback: CallbackQuery):
    all_girls = await db.get_all_girls()
    await callback.answer()
    if all_girls:
        for girl in all_girls:
            await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing')
            await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing', request_timeout=1)
            g_id = girl['user_id']
            g_name, g_age = girl['name'], girl['age']
            data = (f'<b>{g_name}</b>, {g_age}'
                    f'\n<b>Игры:</b> {girl["games"]}'
                    f'f\n<b>О себе:</b> {girl["description"]}'
                    f'\n<b>Час игры: </b> {girl["price"]}')
            avatar_paths = json.loads(girl['avatar_path'])
            print(avatar_paths)
            # Создание альбома медиафайлов
            album_builder = MediaGroupBuilder()
            for avatar_path in avatar_paths:
                album_builder.add_photo(media=FSInputFile(avatar_path))
            if album_builder:
                await callback.message.answer_media_group(media=album_builder.build())
                await callback.message.answer(text=data, reply_markup=main_kb.edit_revs_menu(g_id))
            await asyncio.sleep(0.5)


@router.callback_query(F.data.startswith('adm_edit_revs_'))
async def p_admin_edit_revs(call: CallbackQuery):
    await call.answer()
    g_id = int(call.data.split('_')[-1])
    revs = await db.get_reviews_for_g_id(g_id)
    if revs:
        for rev in revs:
            from_user = rev['from_username']
            date = rev['date']
            text = rev['rev_text']
            await call.message.answer(f'<b>От кого:</b> {from_user}'
                                      f'\n<b>Дата:</b> {date}'
                                      f'\n<b>Отзыв:</b> {text}', reply_markup=main_kb.adm_del_rev(rev['rev_id']))
    else:
        await call.message.answer('Отзывы не найдены.')


@router.callback_query(F.data.startswith('adm_del_rev_'))
async def p_adm_del_rev(call: CallbackQuery):
    rev_id = int(call.data.split('_')[-1])
    await db.delete_review(rev_id)
    await call.message.answer('Отзыв удален')
    await call.answer()
