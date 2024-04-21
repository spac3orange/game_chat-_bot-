from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from config import logger, aiogram_bot
from filters.is_admin import IsAdmin
from keyboards import main_kb
from database import db
from states import AdmMailing, EditBot, EnterPromo
import random
import os
router = Router()
router.message.filter(
    IsAdmin(F)
)


async def check_folder(folder_name):
    if not os.path.exists(f'media/{folder_name}'):
        # Создаем папку
        os.makedirs(f'media/{folder_name}')
        logger.info(f"Папка {folder_name} успешно создана.")
    else:
        logger.info(f"Папка {folder_name} уже существует.")


async def rt_adm_panel(message: Message):
    await message.answer('<b>Выберите действие: </b>', reply_markup=main_kb.adm_p_menu())


@router.callback_query(F.data == 'admin_panel')
async def p_admin_panel(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('<b>Выберите действие: </b>', reply_markup=main_kb.adm_p_menu())


@router.callback_query(F.data == 'adm_mailing')
async def p_adm_mailing(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите текст рассылки: ')
    await state.set_state(AdmMailing.input_message)


@router.message(AdmMailing.input_message)
async def p_adm_message(message: Message, state: FSMContext):
    users = await db.get_all_users()
    msg_text = message.text
    for u in users:
        try:
            uid = u['user_id']
            await aiogram_bot.send_message(uid, msg_text)
        except Exception as e:
            logger.error(e)
            continue

    await message.answer('Рассылка выполнена.')
    await state.clear()


@router.callback_query(F.data == 'adm_get_users')
async def p_adm_gu(callback: CallbackQuery):
    await callback.answer()
    all_users = await db.get_all_users()
    for u in all_users:
        try:
            await callback.message.answer(text=f'{u["user_id"]}'
                                               f'\n{u["username"]}'
                                               f'\n{u["balance"]} рублей')
        except Exception as e:
            logger.error(e)


@router.callback_query(F.data == 'adm_edit_descriptions')
async def p_edit_bot(callback: CallbackQuery, state: FSMContext):
    return 
    await callback.answer()
    await callback.message.answer('Загрузите новую главную картинку: ')
    await state.set_state(EditBot.input_media)


@router.message(EditBot.input_media)
async def p_input_media(message: Message, state: FSMContext):
    try:
        uid = message.from_user.id
        randint = random.randint(1000, 9999)

        if message.content_type == ContentType.PHOTO:
            media_type = 'photo'
            file_id = message.photo[-1].file_id
            file_extension = 'jpg'
        elif message.content_type == ContentType.VIDEO:
            media_type = 'video'
            file_id = message.video.file_id
            file_extension = 'mp4'

        media_name = f'{uid}_{randint}_{media_type}.{file_extension}'
        file_info = await aiogram_bot.get_file(file_id)
        downloaded_file = await aiogram_bot.download_file(file_info.file_path)
        await check_folder(uid)
        with open(f'media/{uid}/{media_name}', 'wb') as media_file:
            media_file.write(downloaded_file.read())

        await state.update_data(avatar_path=f'media/{uid}/{media_name}')
        await message.answer('Фото успешно загружено.\nВведите текст главной странцы:')
        await state.set_state(EditBot.input_maint)
    except Exception as e:
        logger.error(e)
        await state.clear()


@router.message(EditBot.input_maint)
async def p_edit_main_t(message: Message, state: FSMContext):
    await state.update_data(maint=message.text)
    await message.answer('Введите текст, который будет отображаться на странцие выбора игр:')
    await state.set_state(EditBot.input_gst)


@router.message(EditBot.input_gst)
async def p_edit_gst(message: Message, state: FSMContext):
    uid = message.from_user.id
    await state.update_data(gst=message.text)
    data = await state.get_data()
    await db.write_bot_settings(uid, data['avatar_path'], data['maint'], data['gst'])
    await message.answer('Настройки успешно обновлены.')
    await state.clear()
    await rt_adm_panel(message)


@router.callback_query(F.data == 'edit_promo_codes')
async def p_promo_codes(call: CallbackQuery):
    await call.answer()
    promo_codes = await db.get_all_promo()
    codes_str = ''
    for code in promo_codes:
        print(code)
        codes_str += f'\n{code["code"]}: {code["value"]} рублей'
    print(codes_str)
    await call.message.answer(f'Промо коды: {codes_str}', reply_markup=main_kb.edit_promo_codes())


@router.callback_query(F.data == 'add_promo_code')
async def p_add_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(EnterPromo.input_code)
    code = random.randint(10000, 1000000)
    await state.update_data(code=code)
    await call.message.answer(f'Сгенерирован промо код: {code}'
                              '\nВведите сумму:')


@router.message(EnterPromo.input_code)
async def p_add_promo(message: Message, state: FSMContext):
    try:
        code = str((await state.get_data())["code"])
        value = int(message.text)
        await db.add_promo_code(code, value)
        await message.answer('Промо-код добавлен.')
        await state.clear()
        await rt_adm_panel(message)
    except Exception as e:
        logger.error(e)
        await message.answer('Ошибка при добавлении Промо-кода.')
        await state.clear()


@router.callback_query(F.data == 'del_last_promo')
async def p_del_last(call: CallbackQuery):
    await call.answer()
    await call.message.delete()


@router.callback_query(F.data == 'rm_promo_code')
async def p_del_promo(call: CallbackQuery):
    await call.answer()
    codes = await db.get_all_promo()
    await call.message.answer('Выберите промо-код для удаления: ', reply_markup=main_kb.del_promo_codes(codes))


@router.callback_query(F.data.startswith('del_code_'))
async def p_code_deleted(call: CallbackQuery):
    await call.answer()
    try:
        code = call.data.split('_')[-1]
        await db.remove_promo_code(code)
        await call.message.answer(f'Промо-код {code} удален.')
        await p_admin_panel(call)
    except Exception as e:
        logger.error(e)
