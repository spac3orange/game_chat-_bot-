import asyncio
import json
import random
from datetime import datetime, timedelta
import base64
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder

from config import logger, aiogram_bot
from database import db
from keyboards import main_kb
from states import SearchGirls, UkassaPayment, BuyGirl, ChatConnect, PeopleCount, AddService
from utils import inform_admins, Scheduler

router = Router()

async def get_girl_data(g_id: int):
    girl = await db.get_girls_by_id(g_id)
    girl = girl[0]
    avatar_paths = json.loads(girl['avatar_path'])
    g_status = await db.get_user_state(g_id)
    g_shift = await db.get_shift_status(g_id)

    # Определение статуса девушки
    match g_status:
        case 'ChatConnect:chatting':
            g_status = 'Занята 🟡'
        case 'None':
            g_status = 'Онлайн 🟢'

    # Определение статуса смены
    match g_shift['shift_status']:
        case 'Offline':
            g_status = 'Оффлайн 🔴'
        case 'Online':
            if g_status != 'Занята 🟡':
                g_status = 'Онлайн 🟢'

    g_name, g_age = girl['name'], girl['age']
    data = (f'<b>{g_name}</b>, {g_age}'
            f'\n<b>Игры:</b> {girl["games"]}'
            f'\n<b>О себе:</b> {girl["description"]}'
            f'\n<b>Статус:</b> {g_status}')

    g_services = await db.get_services_by_user_id(g_id)

    return {
        'avatar_paths': avatar_paths,
        'data': data,
        'services': g_services,
        'h_price': girl['price']
    }


@router.callback_query(F.data.startswith('u_add_service_'))
async def p_u_add_serv(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data_split = call.data.split('_')
    s_id, s_price, g_id = data_split[-3], data_split[-2], data_split[-1]
    s_name = await db.get_service_name_by_s_id(int(s_id))
    await call.message.edit_text(f'Услуга: {s_name}\n'
                                     f'Стоимость: {s_price}', reply_markup=main_kb.u_choose_serv(s_id, s_price, g_id))
    print(s_name, s_price, g_id)
    pass


@router.callback_query(F.data.startswith('bg_add_serv_'))
async def bg_add_serv(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(AddService.input_service)
    data = await state.get_data()
    print(data)
    data_split = call.data.split('_')
    s_id, s_price, g_id = data_split[-3], data_split[-2], int(data_split[-1])
    s_name = await db.get_service_name_by_s_id(int(s_id))
    g_data = await get_girl_data(g_id)
    # Найти первый свободный ключ (serv1, serv2, ...)
    key_index = 1
    while f"serv{key_index}" in data:
        key_index += 1
    key = f"serv{key_index}"
    print(key)
    # Обновить состояние с новым ключом
    updated_data = {key: {'name': s_name, 'price': s_price}}
    await state.update_data(updated_data)

    state_data = await state.get_data()
    g_services = await db.get_services_by_user_id(g_id)
    serv_str = ''
    for k, v in state_data.items():
        print(k, v)
        if isinstance(v, dict) and 'name' in v and 'price' in v:
            serv_str += f'\n{v["name"]}'
    total_price = sum(int(service['price']) for service in state_data.values())
    ttl_hours = serv_str.count('1 час')
    print(ttl_hours)
    await call.message.edit_text(f'{g_data['data']}'
                                      f'\n\nСписок добавленных услуг: {serv_str}'
                                      f'\n\nОбщая стоимость доп. услуг: \n{total_price} рублей',
                                      reply_markup=main_kb.create_add_services_keyboard(g_id, g_services,
                                                                                        total_price, g_data['h_price'], ttl_hours))


@router.callback_query(F.data.startswith('back_to_add_serv_'))
async def back_to_add_serv(call: CallbackQuery, state: FSMContext):
    await call.answer()
    state_data = await state.get_data()
    g_id = int(call.data.split('_')[-1])
    g_data = await get_girl_data(g_id)

    serv_str = ''
    for k, v in state_data.items():
        if isinstance(v, dict) and 'name' in v and 'price' in v:
            serv_str += f'\n{v["name"]}'
    total_price = sum(int(service['price']) for service in state_data.values())
    ttl_hours = serv_str.count('1 час')
    print(ttl_hours)
    g_services = await db.get_services_by_user_id(g_id)
    await call.message.edit_text(f'{g_data["data"]}'
                                 f'\n\nСписок добавленных услуг: {serv_str}'
                                 f'\n\nОбщая стоимость доп. услуг: \n{total_price} рублей',
                                 reply_markup=main_kb.create_add_services_keyboard(g_id, g_services, total_price, g_data['h_price']))
