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
import magic
from config import logger, aiogram_bot
from database import db
from keyboards import main_kb
from states import SearchGirls, UkassaPayment, BuyGirl, ChatConnect, PeopleCount
from utils import inform_admins, Scheduler

router = Router()
timers = {}


async def get_mime_type(file_path):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    return mime_type


async def is_video(file_path):
    mime_type = await get_mime_type(file_path)
    return mime_type.startswith('video')


async def is_photo(file_path):
    mime_type = await get_mime_type(file_path)
    return mime_type.startswith('image')


async def parse_media(path):
    return FSInputFile(path)


async def send_chat_request(hours: str, message: Message | CallbackQuery, g_id: int,
                            state: FSMContext, uid: int, ):
    schd = Scheduler()
    print(f'{hours=}')
    if int(hours) == 0:
        timing = 1 * 3600
        hours = 12
        await schd.schedule_review(timing=timing, message=message, g_id=g_id)
    else:
        timing = int(hours) * 3600
        await schd.schedule_review(timing=timing, message=message, g_id=g_id)

    print(f'schd timing {timing}')
    # await state.update_data(self_id=uid)
    if isinstance(message, Message):
        await message.reply("Ожидайте подключения...")
    else:
        await message.message.answer("Ожидайте подключения...")

    await state.set_state(ChatConnect.chatting)
    await state.update_data(user_1=uid, user_2=g_id)
    await db.set_user_state(uid, state=await state.get_state())
    print('user_1_state')
    print(await state.get_state())
    # Notify User 2 (replace USER_2_ID with the actual user id)
    user2_id = g_id
    print(uid, user2_id)
    data = await state.get_data()
    print(data)
    try:
        await aiogram_bot.send_message(user2_id, f"Пользователь хочет начать чат с вами.",
                                       reply_markup=main_kb.chat_menu(uid, hours))

    except Exception as e:
        logger.error(e)
        if isinstance(message, Message):
            await message.answer('Ошибка при попытке соединения. Пожалуйста, попробуйте позднее.')
        else:
            await message.message.answer('Ошибка при попытке соединения. Пожалуйста, попробуйте позднее.')
        await state.clear()
        return


async def chat_timer(user_1_id, user_2_id, duration_hours):
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours, minutes=10)
    timers[user_1_id] = {'start': start_time, 'end': end_time, 'task': asyncio.current_task()}
    timers[user_2_id] = {'start': start_time, 'end': end_time, 'task': asyncio.current_task()}
    try:
        await asyncio.sleep(duration_hours * 3600 + 600)  # Преобразуем часы в секунды
        # Здесь код, который выполнится после завершения таймера
        await aiogram_bot.send_message(user_1_id, "Время чата истекло.")
        await aiogram_bot.send_message(user_2_id, "Время чата истекло.")
    finally:
        # Удаляем таймер из активных, независимо от того, произошла ли ошибка
        if user_1_id in timers:
            del timers[user_1_id]
        if user_2_id in timers:
            del timers[user_2_id]


async def p_user_lk(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    user_balance = await db.get_user_balance(uid)
    user_info = (f'<b>Ваш ID</b>: {uid}'
                 f'\n<b>Баланс:</b> {user_balance} рублей')
    await callback.message.edit_text(user_info, reply_markup=main_kb.lk_menu())


async def p_add_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('<b>Введите сумму пополнения:</b>'
                                     '\n\n<b>Минимальная сумма:</b> 300 рублей ')
    await state.set_state(UkassaPayment.input_value)


async def p_select_game(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите игру:', reply_markup=main_kb.game_menu())


async def search_girls(girls: dict, callback: CallbackQuery, stop_event: asyncio.Event):
    await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing')
    for girl in girls:
        if not stop_event.is_set():
            g_id = int(girl['user_id'])
            g_status = await db.get_user_state(g_id)
            g_shift = await db.get_shift_status(g_id)
            print(f'girl state = {g_status}')
            print(f'girl shift = {g_shift}')

            match g_status:
                case 'ChatConnect:chatting':
                    g_status = 'Занята 🟡'
                case 'None':
                    g_status = 'Онлайн 🟢'
            print(g_status)
            print(g_shift)
            match g_shift['shift_status']:
                case 'Offline':
                    g_status = 'Оффлайн 🔴'
                case 'Online':
                    if not g_status == 'Занята 🟡':
                        g_status = 'Онлайн 🟢'
                    else:
                        g_status = 'Занята 🟡'
            print(g_status)

            await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing', request_timeout=1)
            g_name, g_age = girl['name'], girl['age']
            data = (f'<b>{g_name}</b>, {g_age}'
                    f'\n<b>Игры:</b> {girl["games"]}'
                    f'\n<b>О себе:</b> {girl["description"]}'
                    f'\n<b>Статус:</b> {g_status}')
            avatar_paths = json.loads(girl['avatar_path'])
            print(avatar_paths)
            # Создание альбома медиафайлов
            album_builder = MediaGroupBuilder()
            for avatar_path in avatar_paths:
                if await is_video(avatar_path):
                    album_builder.add_video(media=FSInputFile(avatar_path))
                elif await is_photo(avatar_path):
                    album_builder.add_photo(media=FSInputFile(avatar_path))
            if album_builder:
                await callback.message.answer_media_group(media=album_builder.build())
                await callback.message.answer(text=data, reply_markup=main_kb.g_intr_menu(g_id))
            await asyncio.sleep(random.randint(3, 7))


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


@router.callback_query(F.data.startswith('g_intr_menu_'))
async def p_intr_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_id = int(call.data.split('_')[-1])
    g_info = await get_girl_data(g_id)
    avatar_paths, g_data, g_serv = g_info['avatar_paths'], g_info['data'], g_info['services']
    if g_serv:
        for s in g_serv:
            print(s['service_name'], s['price'])

        album_builder = MediaGroupBuilder()
        for avatar_path in avatar_paths:
            if await is_video(avatar_path):
                album_builder.add_video(media=FSInputFile(avatar_path))
            elif await is_photo(avatar_path):
                album_builder.add_photo(media=FSInputFile(avatar_path))
        if album_builder:
            await call.message.answer_media_group(media=album_builder.build())
            await call.message.answer(text=g_data + '\n\nДополнительные услуги: Не выбраны',
                                      reply_markup=main_kb.create_services_keyboard(g_serv, g_id, g_info['h_price']))
    else:
        album_builder = MediaGroupBuilder()
        for avatar_path in avatar_paths:
            if await is_video(avatar_path):
                album_builder.add_video(media=FSInputFile(avatar_path))
            elif await is_photo(avatar_path):
                album_builder.add_photo(media=FSInputFile(avatar_path))
        if album_builder:
            await call.message.answer_media_group(media=album_builder.build())
            await call.message.answer(text=g_data, reply_markup=main_kb.create_services_keyboard(g_id=g_id, h_price=g_info['h_price']))


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
    random.shuffle(girls)
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
        # await callback.message.answer('Поиск завершен.')
        # await callback.message.answer('Поиск завершен', reply_markup=main_kb.start_btns(uid))
    else:
        await callback.message.answer('Анкеты не найдены.')


@router.message(Command('stop_search'))
async def stop_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    print(current_state)
    if current_state == SearchGirls.searching.state:
        stop_event = (await state.get_data())['event']
        stop_event.set()
        await message.answer('Поиск остановлен.')
        await state.clear()
        return
    else:
        await message.answer('Поиск не запущен.')
        return

# @router.callback_query(F.data.startswith('bg_buy_'))
# async def p_bg_buy(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#     g_id = int(callback.data.split('_')[-1])
#     g_status = await db.check_user_state(g_id, ChatConnect.chatting)

#
# @router.callback_query(F.data.startswith('bg_buy_'))
# async def p_bg_buy(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#     print(callback.data)
#     g_id = int(callback.data.split('_')[-1])
#     if await db.check_user_state(g_id, ChatConnect.chatting):
#         await callback.message.answer('На данный момент девушка занята. Пожалуйста, попробуйте позднее.')
#         return
#     if await db.get_shift_status(g_id) == 'Offline':
#         await callback.message.answer('На данный момент девушка оффлайн. Пожалуйста, попробуйте позднее.')
#         return
#     g_data = await db.get_girls_by_id(g_id)
#     g_str = ''
#     for g in g_data:
#         avatar_paths = json.loads(g['avatar_path'])
#         hour_price = g['price']
#         print(avatar_paths)
#         # Создание альбома медиафайлов
#         album_builder = MediaGroupBuilder()
#         for avatar_path in avatar_paths:
#             if await is_video(avatar_path):
#                 album_builder.add_video(media=FSInputFile(avatar_path))
#             elif await is_photo(avatar_path):
#                 album_builder.add_photo(media=FSInputFile(avatar_path))
#         if album_builder:
#             await callback.message.answer_media_group(media=album_builder.build())
#             await callback.message.answer(text='Какой то текст', reply_markup=main_kb.buy_girl(g_id, hour_price))



# @router.callback_query(F.data.startswith('buy_girl_'))
# async def p_bg_buy(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     g_id = call.data.split('_')[-2]
#     g_price = call.data.split('_'[-1])
#     msg = await call.message.answer('Введите кол-во часов:')
#     mkup = main_kb.web_q(g_price, msg.message_id, g_id)
#     await aiogram_bot.edit_message_reply_markup(
#         chat_id=call.message.chat.id,
#         message_id=msg.message_id,
#         reply_markup=mkup
#     )


# @router.callback_query(F.data.startswith('web_q_y_'))
# async def p_bg_web_y(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     g_id = call.data.split('_')[-1]
#     g_price = int(call.data.split('_')[-2]) + 200
#
#     del_mes = call.data.split('_')[-3]
#     await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
#     msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.\nВы будете один?')
#     mkup = main_kb.alone_q(g_price, msg.message_id, g_id)
#     await aiogram_bot.edit_message_reply_markup(
#         chat_id=call.message.chat.id,
#         message_id=msg.message_id,
#         reply_markup=mkup
#     )


# @router.callback_query(F.data.startswith('web_q_n_'))
# async def p_bg_web_n(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     g_id = call.data.split('_')[-1]
#     g_price = int(call.data.split('_')[-2])
#     del_mes = call.data.split('_')[-3]
#     await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
#     msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.\nВы будете один?')
#     mkup = main_kb.alone_q(g_price, msg.message_id, g_id)
#     await aiogram_bot.edit_message_reply_markup(
#         chat_id=call.message.chat.id,
#         message_id=msg.message_id,
#         reply_markup=mkup
#     )


# @router.callback_query(F.data.startswith('alone_q_y_'))
# async def p_alone_q_y(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     g_id = call.data.split('_')[-1]
#     g_price = int(call.data.split('_')[-2]) + 200
#     del_mes = call.data.split('_')[-3]
#     await aiogram_bot.delete_message(call.chat.id, int(del_mes))
#     msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.')
#
#
#
# @router.callback_query(F.data.startswith('alone_q_n_'))
# async def p_alone_q_n(call: CallbackQuery, state: FSMContext):
#     await call.answer()
#     g_id = call.data.split('_')[-1]
#     g_price = int(call.data.split('_')[-2])
#     del_mes = call.data.split('_')[-3]
#     await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
#     msg = await call.message.answer(f'Сколько будет людей?')
#     await state.set_state(PeopleCount.input_ppl)
#     await state.update_data(g_id=g_id, g_price=g_price, msg=msg)


# @router.message(PeopleCount.input_ppl, lambda message: message.text.isdigit() and int(message.text) <= 10)
# async def p_bg_buy_wppl(message: Message, state: FSMContext):
#     ppl = int(message.text)
#     data = await state.get_data()
#     await state.clear()
#     ttl_price = int(data['g_price']) + ppl * 10
#     await state.set_state(BuyGirl.input_hours)
#     g_id = data['g_id']
#     await state.update_data(g_id=g_id)
#     await state.update_data(price=ttl_price)
#     g_data = await db.get_girls_by_id(int(g_id))
#     await message.answer(f'<b>Стоимость одного часа:</b> {ttl_price} рублей'
#                          '\nВведите количество <b>часов (цифра)</b>: ')
#     await state.set_state(BuyGirl.process_req)



@router.callback_query(F.data.startswith('complete_buy_girl_'))
async def p_bg_buy(call: CallbackQuery, state: FSMContext):
    # action after payment button pressed with servs
    print('serv_handler')
    await call.answer()
    print(len(call.data.split('_')))
    if len(call.data.split('_')) == 7:
        g_id = int(call.data.split('_')[-2])
        g_price = call.data.split('_')[-3]
        g_data = await db.get_girls_by_id(int(g_id))
        serv_price = call.data.split('_')[-1]
        ttl_hours = call.data.split('_')[-4]
        print(g_id, g_price, serv_price)
    else:
        g_id = int(call.data.split('_')[-1])
        g_price = call.data.split('_')[-2]
        serv_price = 0
        print(g_id, g_price)
        await call.message.answer('Пожалуйста, сначала выберите услуги')
        return
    print(call.data)
    g_state = await db.get_user_state(g_id)
    print(g_state)
    g_status = await db.check_user_state(g_id, ChatConnect.chatting)
    if g_status:
        await call.message.answer('На данный момент девушка занята. Пожалуйста, попробуйте позднее.')
        return
    g_shift = await db.get_shift_status(g_id)
    if g_shift['shift_status'] == 'Offline':
        await call.message.answer('На данный момент девушка оффлайн. Пожалуйста, попробуйте позднее.')
        return
    await state.set_state(BuyGirl.web_q)

    print(g_id, g_price, serv_price)
    await state.update_data(g_id=g_id, price=g_price, serv_price=serv_price, ttl_hours=ttl_hours)
    await call.message.answer(f'Хотите ли вы, чтобы девушка включила веб-камеру?'
                              f'\nСтоимость услуги: {g_price} рублей', reply_markup=main_kb.u_webcam_req())


@router.callback_query(F.data.startswith('cbg_noserv_'))
async def p_bg_buy(call: CallbackQuery, state: FSMContext):
    # action after payment button pressed with no additional services
    print('noserv_handler')
    await call.answer()
    data_split = call.data.split('_')
    g_id = int(data_split[-1])
    g_status = await db.check_user_state(g_id, ChatConnect.chatting)
    if g_status:
        await call.message.answer('На данный момент девушка занята. Пожалуйста, попробуйте позднее.')
        return
    g_shift = await db.get_shift_status(g_id)
    if g_shift['shift_status'] == 'Offline':
        await call.message.answer('На данный момент девушка оффлайн. Пожалуйста, попробуйте позднее.')
        return
    await state.set_state(BuyGirl.web_q)
    print(call.data)
    g_price = data_split[-2]
    g_data = await db.get_girls_by_id(int(g_id))
    print(g_id, g_price)
    await state.update_data(g_id=g_id, price=g_price)
    await call.message.answer(f'Хотите ли вы, чтобы девушка включила веб-камеру?'
                              f'\nСтоимость услуги: {g_price} рублей', reply_markup=main_kb.u_webcam_req())


@router.message(BuyGirl.process_req, lambda message: message.text.isdigit() and 1 <= int(message.text) <= 12)
async def p_buy(message: Message, state: FSMContext):
    g_username = None
    ppl_cnt = int(message.text)
    await state.update_data(ppl_cnt=ppl_cnt)
    g_data = await state.get_data()
    ttl_ppl_price = int(g_data['price_per_ppl']) * ppl_cnt
    ttl_hours = g_data['ttl_hours']
    uid = message.from_user.id
    username = message.from_user.username
    g_id = g_data["g_id"]
    web_price = int(g_data["price"])
    serv_price = g_data.get('serv_price', 0)
    g_price = 0
    if g_data['webcam'] == 'yes':
        ttl_price = g_price + int(serv_price) + ttl_ppl_price + int(web_price)
    else:
        ttl_price = g_price + int(serv_price) + ttl_ppl_price
    user_balance = await db.get_user_balance(uid)
    if user_balance < ttl_price:
        await message.answer('На вашем балансе <b>недостаточно средств</b>.'
                             f'\n<b>Баланс: </b> {user_balance} руб.'
                             f'\n<b>Общая стоимость: </b> {ttl_price} руб.',
                             reply_markup=main_kb.buy_girl_fxd(g_id, ttl_price, ttl_hours))
        await state.clear()
    else:
        g_data = await db.get_girls_by_id(int(g_id))
        girl_payment = (67 / 100) * ttl_price
        logger.info(f'girl payment" {girl_payment}')
        await db.withdraw_from_balance(uid, ttl_price)
        await db.top_up_girl_balance(int(g_id), int(girl_payment))
        for g in g_data:
            g_username = g['username']
        await message.answer(f'<b>Вы успешно оплатили доступ.</b> '
                             f'\nС вашего баланса списано <b>{ttl_price} руб</b>.'
                             f'\n\nПолучено <b>{ttl_hours}</b> часов игрового времени'
                             '\n<b>Приятной игры!</b>')

        adm_text = f'Пользователь {username} оплатил доступ к девушке {g_username}. Сумма: {ttl_price} руб.'
        if uid != 46281319:
            await inform_admins(adm_text)
        await state.clear()
        await send_chat_request(ttl_hours, message, g_id, state, uid)


@router.callback_query(F.data.startswith('webcam_req_y_'))
async def p_webcam_y(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(webcam='yes')
    await call.message.edit_text('Вы будете один?', reply_markup=main_kb.additional_part_req())


@router.callback_query(F.data.startswith('webcam_req_n_'))
async def p_webcam_n(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(webcam='no')
    await call.message.edit_text('Вы будете один?', reply_markup=main_kb.additional_part_req())


@router.callback_query(F.data.startswith('add_part_req_n_'))
async def p_alone_q_n(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    print(data)
    g_data = await db.get_girls_by_id(int(data["g_id"]))
    price_per_ppl = 0
    for r in g_data:
        price_per_ppl = r['price_per_ppl']
    await state.set_state(BuyGirl.process_req)
    await state.update_data(price_per_ppl=price_per_ppl)
    await call.message.edit_text(f'Стоимость услуги: {price_per_ppl} рублей за человека.'
                              f'\nПожалуйста, введите количество людей:')


@router.message(BuyGirl.alone_q, lambda message: message.text.isdigit() and 0 < int(message.text) < 20)
async def p_alone_q_n(message: Message, state: FSMContext):
    ppl_cnt = int(message.text)
    await state.update_data(ppl_cnt=ppl_cnt)


@router.message(BuyGirl.alone_q, lambda message: message.text.isdigit() and 0 < int(message.text) < 20)
async def p_alone_q_y(message: Message, state: FSMContext):
    await message.answer('Неверно указано кол-во людей. Это может быть цифра от 1 до 20.')
    return


@router.callback_query(F.data.startswith('add_part_req_y_'))
async def p_alone_q_n(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_data = await state.get_data()
    uid = call.from_user.id
    username = call.message.from_user.username
    print(g_data)
    g_id = g_data["g_id"]
    web_price = int(g_data["price"])
    serv_price = g_data.get('serv_price', 0)
    ttl_hours = g_data['ttl_hours']
    g_price = 0
    if g_data['webcam'] == 'yes':
        ttl_price = g_price + int(serv_price) + int(web_price)
    else:
        ttl_price = g_price + int(serv_price)
    user_balance = await db.get_user_balance(uid)
    print(user_balance)
    print('ttl_price', ttl_price)
    if user_balance < ttl_price:
        await call.message.edit_text('На вашем балансе <b>недостаточно средств</b>.'
                             f'\n<b>Баланс: </b> {user_balance} руб.'
                             f'\n<b>Общая стоимость: </b> {ttl_price} руб.',
                             reply_markup=main_kb.buy_girl_fxd(g_id, ttl_price, ttl_hours))
        await state.clear()
    else:
        g_data = await db.get_girls_by_id(int(g_id))
        girl_payment = (67 / 100) * ttl_price
        logger.info(f'girl payment" {girl_payment}')
        await db.withdraw_from_balance(uid, ttl_price)
        await db.top_up_girl_balance(int(g_id), int(girl_payment))
        for g in g_data:
            g_username = g['username']
        await call.message.edit_text(f'<b>Вы успешно оплатили доступ.</b> '
                             f'\nС вашего баланса списано <b>{ttl_price} руб</b>.'
                             f'\n\nПолучено <b>{ttl_hours}</b> часов игрового времени'
                             '\n<b>Приятной игры!</b>')

        adm_text = f'Пользователь {username} оплатил доступ к девушке {g_username}. Сумма: {ttl_price} руб.'
        if uid != 46281319:
            await inform_admins(adm_text)
        await state.clear()
        await send_chat_request(ttl_hours, call, g_id, state, uid)


@router.callback_query(F.data == 'cancel_buy_girl')
async def p_cbg(callback: CallbackQuery):
    await p_select_game(callback)


@router.callback_query(F.data.startswith('decline_'))
async def p_dec_chat(call: CallbackQuery, state: FSMContext):
    user_1_id = call.data.split('_')[-1]
    await call.message.answer("Вы отменили запрос чата.")
    await aiogram_bot.send_message(user_1_id, "Пользователь отменил запрос на чат.")
    await state.clear()
    await call.answer()
    await db.set_user_state(user_1_id, 'None')


@router.callback_query(F.data.startswith('accept_'))
async def p_acc_chat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatConnect.waiting_for_user2_approval)
    user_1_id = int(callback.data.split('_')[-1])
    hours = int(callback.data.split('_')[-2])
    user_2_id = callback.from_user.id

    # storage = MemoryStorage()
    # user1_state = FSMContext(storage=storage, key=StorageKey(bot_id=aiogram_bot.id, chat_id=user_1_id, user_id=user_1_id))
    # user2_state = FSMContext(storage=storage, key=StorageKey(bot_id=aiogram_bot.id, chat_id=user_2_id, user_id=user_2_id))
    await callback.answer()
    await callback.message.edit_text("Вы приняли заявку на чат."
                                     "\n\n<b>Управление чатом:</b> "
                                     "\n<b>Проверить оставшееся время чата:</b> /remaining_time"
                                     "\n<b>Остановить чат:</b> /stop_chat", reply_markup=None)
    await callback.message.answer('Перейдите на "ссылка дискорда", займите свободную комнату, дождитесь заказчика и переместите его из лобби ожидания')
    await aiogram_bot.send_message(user_1_id, "Пользователь принял вашу заявку. Чат запущен."
                                              "\nВам был начислен бонус: 10 минут чата."
                                              "\n\n<b>Управление чатом:</b> "
                                              "\n<b>Проверить оставшееся время чата:</b> /remaining_time"
                                              "\n<b>Остановить чат:</b> /stop_chat")
    await aiogram_bot.send_message(user_1_id, 'Перейдите на "ссылка дискорда", зайдите в Waiting Room, сообщите девушке свой никнейм в Telegram чате')
    await state.set_state(ChatConnect.chatting)
    await state.update_data(user_1=user_1_id, user_2=user_2_id)
    await db.set_user_state(user_2_id, state=await state.get_state())
    task = asyncio.create_task(chat_timer(user_1_id, user_2_id, hours))
    print(f'{hours=}')
    print('user_2_state')
    print(await state.get_state())


@router.message(Command('remaining_time'))
async def remaining_time_command(message: Message):
    user_id = message.from_user.id
    if user_id in timers:
        end_time = timers[user_id]['end']
        remaining = end_time - datetime.now()
        if remaining.total_seconds() > 0:
            hours, remainder = divmod(remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            await message.answer(f"Осталось времени: {int(hours)} часов, {int(minutes)} минут, {int(seconds)} секунд.")
        else:
            await message.answer("Чат уже завершился.")
    else:
        await message.answer("Нет активного чата.")


@router.message(ChatConnect.chatting)
async def handle_message(message: Message, state: FSMContext):
    data = await state.get_data()
    user_1_id, user_2_id = data['user_1'], data['user_2']
    match message.text:
        case '/stop_chat':
            await message.answer('Чат завершен.')
            await db.set_user_state(user_1_id, 'None')
            await db.set_user_state(user_2_id, 'None')
            if user_1_id in timers:
                del timers[user_1_id]
            if user_2_id in timers:
                del timers[user_2_id]
            await state.clear()
            return
        case '/remaining_time':
            await remaining_time_command(message)
        case '/cancel_timer':
            await cancel_timer_command(message)

    if message.from_user.id == user_1_id:
        recipient_id = user_2_id
    else:
        recipient_id = user_1_id
    rec_state = await db.check_user_state(recipient_id, ChatConnect.chatting)
    if rec_state:
        await aiogram_bot.send_message(recipient_id, message.text)
    else:
        await message.answer('Чат завершен.')
        await db.set_user_state(user_1_id, 'None')
        await db.set_user_state(user_2_id, 'None')
        await state.clear()


@router.message(Command('stop_chat'))
async def p_c_stop_chat(message: Message, state: FSMContext):
    if await state.get_state() == ChatConnect.chatting:
        await message.answer('Чат завершен.')
        await db.set_user_state(message.from_user.id, 'None')
        await state.clear()


@router.message(Command('cancel_timer'))
async def cancel_timer_command(message: Message):
    user_id = message.from_user.id
    if user_id in timers and 'task' in timers[user_id]:
        timers[user_id]['task'].cancel()  # Отменяем задачу
        del timers[user_id]  # Удаляем таймер из словаря
        await message.answer("Таймер был успешно отменен.")
    else:
        await message.answer("Нет активного таймера для отмены.")


