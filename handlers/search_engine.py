import asyncio
import random
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from config import logger, aiogram_bot
from filters.is_admin import IsAdmin
from keyboards import main_kb
from database import db
from states import SearchGirls, UkassaPayment, BuyGirl
from utils import inform_admins
router = Router()


async def parse_media(path):
    return FSInputFile(path)


async def p_user_lk(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    user_balance = await db.get_user_balance(uid)
    user_info = (f'<b>Ваш ID</b>: {uid}'
                 f'\n<b>Баланс:</b> {user_balance} рублей')
    await callback.message.edit_text(user_info, reply_markup=main_kb.lk_menu())


async def p_add_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('<b>Введите сумму пополнения:</b>'
                                     '\n\n<b>Минимальная сумма:</b> 500 рублей ')
    await state.set_state(UkassaPayment.input_value)


async def p_select_game(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите игру:', reply_markup=main_kb.game_menu())


async def search_girls(girls: dict, callback: CallbackQuery, stop_event: asyncio.Event):
    for girl in girls:
        await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing')
        if not stop_event.is_set():
            await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing', request_timeout=1)
            g_id = girl['user_id']
            g_name, g_age = girl['name'], girl['age']
            data = (f'<b>{g_name}</b>, {g_age}'
                    f'\n<b>Игры:</b> {girl["games"]}'
                    f'f\n{girl["description"]}'
                    f'\n<b>Час игры: </b> {girl["price"]}')
            media = await parse_media(girl['avatar_path'])
            await callback.message.answer_photo(photo=media, caption=data, reply_markup=main_kb.bg_menu(g_id))
            await asyncio.sleep(random.randint(3, 7))


@router.callback_query(F.data.startswith('game_'))
async def p_search_girls(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    stop_event = asyncio.Event()
    uid = callback.from_user.id
    game = callback.data.split('_')[-1]
    games_dict = {'cs2': 'CS 2', 'dota2': 'DOTA 2',
                  'val': 'VALORANT', 'apex': 'APEX',
                  'talk': 'Общение'}
    game = games_dict[game]
    print(game)
    girls = await db.get_girls_by_game(game)
    print(girls)
    if girls:
        await callback.message.answer('Запущен поиск... ⌛️'
                                      '\n\nОстановить - /stop_search')
        await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing')
        await asyncio.sleep(random.randint(2, 5))
        await state.set_state(SearchGirls.searching)
        await state.update_data(event=stop_event)
        await search_girls(girls, callback, stop_event)
        await state.clear()
        await callback.message.answer('Поиск завершен.')
        # await callback.message.answer('Поиск завершен', reply_markup=main_kb.start_btns(uid))
    else:
        await callback.message.answer('Анкеты не найдены.')


@router.message(Command('stop_search'), SearchGirls.searching)
async def stop_handler(message: Message, state: FSMContext):
    stop_event = (await state.get_data())['event']
    stop_event.set()
    await message.answer('Поиск остановлен.')
    await state.clear()


@router.callback_query(F.data.startswith('bg_buy_'))
async def p_bg_buy(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    g_id = callback.data.split('_')[-1]
    g_data = await db.get_girls_by_id(int(g_id))
    g_str = ''
    for g in g_data:
        g_str = (f'<b>{g["name"]}</b>, {g["age"]}'
                 f'\n<b>Игры:</b> {g["games"]}'
                 f'\n{g["description"]}'
                 f'\n<b>Час игры:</b> {g["price"]} ')
        g_price = g["price"]
        g_avatar = await parse_media(g["avatar_path"])

    await callback.message.answer_photo(photo=g_avatar,
                                        caption='<b>Выбрана девушка:</b>'
                                                f'\n{g_str}'
                                                f'\n\nЧтобы открыть контактные данные девушки для совместной игры, оплатите доступ.'
                                                f'\n<b>Цена:</b> {g_price} рублей', reply_markup=main_kb.buy_girl(g_id, g_price))


@router.callback_query(F.data.startswith('buy_girl_'))
async def p_bg_buy(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(BuyGirl.input_hours)
    g_id = call.data.split('_')[-2]
    await state.update_data(g_id=g_id)
    g_data = await db.get_girls_by_id(int(g_id))
    for g in g_data:
        g_price = g['price']
        await state.update_data(price=g_price)
    await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей'
                              '\nВведите количество <b>часов (цифра)</b>: ')
    await state.set_state(BuyGirl.process_req)


@router.message(BuyGirl.process_req, lambda message: message.text.isdigit() and 1 <= int(message.text) <= 20)
async def p_buy(message: Message, state: FSMContext):
    uid = message.from_user.id
    username = message.from_user.username
    g_data = await state.get_data()
    g_id = g_data["g_id"]
    g_price = g_data["price"]
    hours = message.text
    g_price = int(g_price) * int(hours)
    user_balance = await db.get_user_balance(uid)
    if user_balance < g_price:
        await message.answer('На вашем балансе <b>недостаточно средств</b>.'
                             f'\n<b>Баланс: </b> {user_balance} руб.'
                             f'\n<b>Стоимость услуги: </b> {g_price} руб.',
                             reply_markup=main_kb.buy_girl_fxd(g_id, g_price))
        await state.clear()
    else:
        g_data = await db.get_girls_by_id(int(g_id))
        girl_payment = (67 / 100) * g_price
        logger.info(f'girl payment" {girl_payment}')
        await db.withdraw_from_balance(uid, g_price)
        await db.top_up_girl_balance(int(g_id), int(girl_payment))
        for g in g_data:
            g_username = g['username']
        await message.answer(f'<b>Вы успешно оплатили доступ.</b> '
                                      f'\nС вашего баланса списано <b>{g_price} руб.</b>.'
                                      f'\n\nПолучен <b>{hours}</b> игрового времени с <b>@{g_username}</b>'
                                      '\n<b>Приятной игры!</b>')
        adm_text = f'Пользователь {username} оплатил доступ к девушке {g_username}. Сумма: {g_price} руб.'
        await inform_admins(adm_text)
        await state.clear()


@router.message(BuyGirl.process_req)
async def p_buy(message: Message, state: FSMContext):
    await message.answer('Неверно указано количество часов. Это должна быть цифра от 1 до 20.')





@router.callback_query(F.data == 'cancel_buy_girl')
async def p_cbg(callback: CallbackQuery):
    await p_select_game(callback)