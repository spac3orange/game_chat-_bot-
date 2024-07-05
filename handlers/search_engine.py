import asyncio
import random
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from config import logger, aiogram_bot
from keyboards import main_kb
from database import db
from states import SearchGirls, UkassaPayment, BuyGirl, ChatConnect, PeopleCount
from utils import inform_admins, Scheduler
import json
from aiogram.types import InputMediaPhoto, InputFile
from aiogram.utils.media_group import MediaGroupBuilder


router = Router()
timers = {}


async def parse_media(path):
    return FSInputFile(path)


async def send_chat_request(hours: str, message: Message | CallbackQuery, g_id: int,
                            state: FSMContext, uid: int,):
    schd = Scheduler()
    timing = int(hours) * 3600
    await schd.schedule_review(timing=timing, message=message, g_id=g_id)
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
    for girl in girls:
        await aiogram_bot.send_chat_action(callback.message.chat.id, 'typing')
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
                    f'\n<b>Час игры: </b> {girl["price"]}'
                    f'\n<b>Статус:</b> {g_status}')
            avatar_paths = json.loads(girl['avatar_path'])
            print(avatar_paths)
            # Создание альбома медиафайлов
            album_builder = MediaGroupBuilder()
            for avatar_path in avatar_paths:
                album_builder.add_photo(media=FSInputFile(avatar_path))
            if album_builder:
                await callback.message.answer_media_group(media=album_builder.build())
                await callback.message.answer(text=data, reply_markup=main_kb.bg_menu(g_id))
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


@router.callback_query(F.data.startswith('bg_buy_'))
async def p_bg_buy(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    g_id = int(callback.data.split('_')[-1])
    g_status = await db.check_user_state(g_id, ChatConnect.chatting)
    if g_status:
        await callback.message.answer('На данный момент девушка занята. Пожалуйста, попробуйте позднее.')
        return
    g_shift = await db.get_shift_status(g_id)
    if g_shift['shift_status'] == 'Offline':
        await callback.message.answer('На данный момент девушка оффлайн. Пожалуйста, попробуйте позднее.')
        return
    g_data = await db.get_girls_by_id(g_id)
    g_str = ''
    for g in g_data:
        g_str = (f'<b>{g["name"]}</b>, {g["age"]}'
                 f'\n<b>Игры:</b> {g["games"]}'
                 f'\n{g["description"]}'
                 f'\n<b>Час игры:</b> {g["price"]} ')
        g_price = g["price"]
        # g_avatar = await parse_media(g["avatar_path"])

        avatar_paths = json.loads(g['avatar_path'])
        print(avatar_paths)
        # Создание альбома медиафайлов
        album_builder = MediaGroupBuilder()
        for avatar_path in avatar_paths:
            album_builder.add_photo(media=FSInputFile(avatar_path))
        if album_builder:
            await callback.message.answer_media_group(media=album_builder.build())
            await callback.message.answer(text='<b>Выбрана девушка:</b>'
                                               f'\n{g_str}'
                                               f'\n\nЧтобы открыть контактные данные девушки для совместной игры, оплатите доступ.'
                                               f'\n<b>Цена:</b> {g_price} рублей', reply_markup=main_kb.buy_girl(g_id, g_price))





@router.callback_query(F.data.startswith('buy_girl_'))
async def p_bg_buy(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_id = call.data.split('_')[-2]
    g_data = await db.get_girls_by_id(int(g_id))
    for g in g_data:
        g_price = g['price']
    msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.'
                                        f'\nХотите ли вы,чтобы девушка включила веб-камеру?')
    mkup = main_kb.web_q(g_price, msg.message_id, g_id)
    await aiogram_bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=msg.message_id,
        reply_markup=mkup
    )


@router.callback_query(F.data.startswith('web_q_y_'))
async def p_bg_web_y(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_id = call.data.split('_')[-1]
    g_price = int(call.data.split('_')[-2]) + 200

    del_mes = call.data.split('_')[-3]
    await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
    msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.\nВы будете один?')
    mkup = main_kb.alone_q(g_price, msg.message_id, g_id)
    await aiogram_bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=msg.message_id,
        reply_markup=mkup
    )

@router.callback_query(F.data.startswith('web_q_n_'))
async def p_bg_web_n(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_id = call.data.split('_')[-1]
    g_price = int(call.data.split('_')[-2])
    del_mes = call.data.split('_')[-3]
    await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
    msg = await call.message.answer(f'<b>Стоимость одного часа:</b> {g_price} рублей.\nВы будете один?')
    mkup = main_kb.alone_q(g_price, msg.message_id, g_id)
    await aiogram_bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=msg.message_id,
        reply_markup=mkup
    )


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
@router.callback_query(F.data.startswith('alone_q_n_'))
async def p_alone_q_n(call: CallbackQuery, state: FSMContext):
    await call.answer()
    g_id = call.data.split('_')[-1]
    g_price = int(call.data.split('_')[-2])
    del_mes = call.data.split('_')[-3]
    await aiogram_bot.delete_message(call.message.chat.id, int(del_mes))
    msg = await call.message.answer(f'Сколько будет людей?')
    await state.set_state(PeopleCount.input_ppl)
    await state.update_data(g_id=g_id, g_price=g_price, msg=msg)


@router.message(PeopleCount.input_ppl, lambda message: message.text.isdigit() and int(message.text) <= 10)
async def p_bg_buy_wppl(message: Message, state: FSMContext):
    ppl = int(message.text)
    data = await state.get_data()
    await state.clear()
    ttl_price = int(data['g_price']) + ppl * 10
    await state.set_state(BuyGirl.input_hours)
    g_id = data['g_id']
    await state.update_data(g_id=g_id)
    await state.update_data(price=ttl_price)
    g_data = await db.get_girls_by_id(int(g_id))
    await message.answer(f'<b>Стоимость одного часа:</b> {ttl_price} рублей'
                          '\nВведите количество <b>часов (цифра)</b>: ')
    await state.set_state(BuyGirl.process_req)


@router.callback_query(F.data.startswith('complete_buy_girl_'))
async def p_bg_buy(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(BuyGirl.input_hours)
    g_id = call.data.split('_')[-1]
    g_price = call.data.split('_')[-2]
    await state.update_data(g_id=g_id)
    await state.update_data(price=g_price)
    g_data = await db.get_girls_by_id(int(g_id))

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
                             reply_markup=main_kb.buy_girl_fxd(g_id, g_price, hours))
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
        await send_chat_request(hours, message, g_id, state, uid)




@router.message(BuyGirl.process_req)
async def p_buy(message: Message, state: FSMContext):
    await message.answer('Неверно указано количество часов. Это должна быть цифра от 1 до 20.')


@router.callback_query(F.data == 'cancel_buy_girl')
async def p_cbg(callback: CallbackQuery):
    await p_select_game(callback)


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


@router.callback_query(F.data.startswith('decline_'))
async def p_dec_chat(call: CallbackQuery, state: FSMContext):
    user_1_id = (await state.get_data())['self_id']
    await call.message.answer("Вы отменили запрос чата..")
    await aiogram_bot.send_message(user_1_id, "Пользователь отменил запрос на чат.")
    await state.clear()
    await db.set_user_state(user_1_id, 'None')


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