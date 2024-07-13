import hashlib
import http.client
import json
import random
import string
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, CallbackQuery
from aiogram.types.message import ContentType
from environs import Env

from config import aiogram_bot, logger
from database import db
from keyboards import main_kb
from states import UkassaPayment
from utils import inform_admins
from ..search_engine import send_chat_request

router = Router()
env = Env()
t_token = env('t_api')
t_password = env('t_pass')
terminal_key = env.str('t_key')


async def calculate_price_without_vat(price_with_vat, vat_rate):
    price_without_vat = price_with_vat / (1 + vat_rate)
    return price_without_vat


# Функция для создания платежа
async def create_payment(amount, description, return_url=None):
    try:
        amount_rub = amount
        amount = amount * 100
        return_url = 'https://t.me/Gifdeomes_bot'
        invoice_number = ''.join(random.choices(string.digits, k=15))
        due_date = (datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d')
        invoice_date = datetime.now().strftime('%Y-%m-%d')

        # Корневые параметры для токена
        params = {
            "TerminalKey": terminal_key,
            "Amount": amount,  # Сумма в копейках
            "OrderId": invoice_number,
            "Description": f"Пополнение баланса на {amount_rub} рублей",
            "Password": t_password
        }

        # Сортируем параметры по ключу и конкатенируем их значения
        sorted_values = ''.join(str(params[k]) for k in sorted(params.keys()))

        # Вычисляем SHA-256 хеш
        token = hashlib.sha256(sorted_values.encode('utf-8')).hexdigest()

        conn = http.client.HTTPSConnection("securepay.tinkoff.ru")
        payload = json.dumps({
            "TerminalKey": terminal_key,
            "Amount": amount,
            "OrderId": invoice_number,
            "Description": f"Пополнение баланса на {amount_rub} рублей",
            "Token": token,

            "Receipt": {
                "Email": "stepdronpro@gmail.com",
                "Phone": "+79031234555",
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": f"Пополнение баланса на {amount_rub} рублей",
                        "Price": amount,
                        "Quantity": 1,
                        "Amount": amount,
                        "Tax": "vat10",
                    }
                ]
            }
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {t_token}'
        }
        conn.request("POST", "/v2/Init", payload, headers)
        res = conn.getresponse()
        data = res.read()
        print(data.decode("utf-8"))
        # Декодируем байты и парсим JSON
        response_json = json.loads(data.decode("utf-8"))
        payment_id = response_json.get('PaymentId')
        payment_url = response_json.get('PaymentURL')
        print(f'Payment ID: {payment_id}')
        return payment_id, payment_url, amount_rub

    except Exception as e:
        print(e)
        logger.error("Произошла ошибка:", e)


# Функция для проверки статуса платежа
async def check_payment_status(payment_id):
    try:
        params = {
            "TerminalKey": terminal_key,
            "PaymentId": payment_id,
            "Password": t_password
        }

        # Сортируем параметры по ключу и конкатенируем их значения
        sorted_values = ''.join(str(params[k]) for k in sorted(params.keys()))
        token = hashlib.sha256(sorted_values.encode('utf-8')).hexdigest()
        conn = http.client.HTTPSConnection("securepay.tinkoff.ru")
        payload = json.dumps({
            "TerminalKey": terminal_key,
            "PaymentId": payment_id,
            "Token": token,
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        conn.request("POST", "/v2/GetState", payload, headers)
        res = conn.getresponse()
        data = res.read()
        print(data.decode("utf-8"))
        # Декодируем байты и парсим JSON
        response_json = json.loads(data.decode("utf-8"))
        pay_status = response_json.get('Status')
        print(f'Payment status: {pay_status}')
        return pay_status
    except Exception as e:
        print("Произошла ошибка:", e)
        return None

    # try:
    #     payment = Payment.find_one(payment_id)
    #     status = payment.status
    #     rec_status = payment.receipt_registration
    #     print(f'status: {status}')
    #     print(f'rec status: {rec_status}')
    #     return status
    # except Exception as e:
    #     print("Произошла ошибка:", e)
    #     return None


# Пример использования


async def p_lk(message: Message):
    uid = message.from_user.id
    user_balance = await db.get_user_balance(uid)
    user_info = (f'<b>Ваш ID</b>: {uid}'
                 f'\n<b>Баланс:</b> {user_balance} рублей')
    await message.answer(user_info, reply_markup=main_kb.lk_menu())


@router.callback_query(F.data == 'add_balance')
async def p_add_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('<b>Введите сумму пополнения:</b>'
                                     '\n\n<b>Минимальная сумма:</b> 300 рублей ', reply_markup=main_kb.del_last_lk())
    await state.set_state(UkassaPayment.input_value)


@router.callback_query(F.data.startswith('add_fxd_balance_'))
async def p_add_balance(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    print(callback.data)
    amount = callback.data.split('_')[-1]
    g_id = int(callback.data.split('_')[-2])
    hours = callback.data.split('_')[-3]
    await state.set_state(UkassaPayment.input_value)
    uid = callback.from_user.id
    try:
        data = await state.get_data()
        payment_sum = data.get('amount', None)
        if not payment_sum:
            payment_sum = amount
        payment_id, conf_url, amount = await create_payment(int(payment_sum), f"Пополнение баланса на {payment_sum} рублей")
        logger.info(f'{uid} creating invoice')
        if payment_id:
            print("Платеж успешно создан:", payment_id)
            print("Ссылка для оплаты:", conf_url)
            await callback.message.answer(f'Пополнение баланса на <b>{amount}</b> рублей.', reply_markup=main_kb.pay_btns_fxd(payment_id, conf_url, amount, g_id, hours))
            await state.clear()
        else:
            await callback.message.answer('Произошла ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
    except Exception as e:
        logger.error(e)
        await callback.message.answer('Произошла ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
        await state.clear()


@router.message(UkassaPayment.input_value, lambda message: message.text.isdigit() and int(message.text) >= 300)
async def p_buy_ukassa(message: Message, bot: aiogram_bot, state: FSMContext):
    uid = message.from_user.id
    try:
        data = await state.get_data()
        payment_sum = data.get('amount', None)
        if not payment_sum:
            payment_sum = message.text
        payment_id, conf_url, amount = await create_payment(int(payment_sum), f"Пополнение баланса на {payment_sum} рублей")
        logger.info(f'{uid} creating invoice')
        if payment_id:
            print("Платеж успешно создан:", payment_id)
            print("Ссылка для оплаты:", conf_url)
            await message.answer(f'Пополнение баланса на <b>{amount}</b> рублей.',
                                 reply_markup=main_kb.pay_btns(payment_id, conf_url, amount))
            await state.clear()
        else:
            await message.answer('Произошла ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
    except Exception as e:
        logger.error(e)
        await message.answer('Произошла ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
        await state.clear()


@router.callback_query(F.data.startswith('check_pay_status'))
async def p_check_pay_status(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    uid = call.from_user.id
    logger.info(f'{uid} checking payment status')
    if len(call.data.split('_')) == 5:
        g_id = None
    else:
        g_id = int(call.data.split('_')[-3])
        hours = call.data.split('_')[-4]

    pid = call.data.split('_')[-2]
    amount = call.data.split('_')[-1]
    uid = call.from_user.id
    status = await check_payment_status(pid)
    if status == 'CONFIRMED' and g_id is not None:
        await db.top_up_balance(uid, int(amount))
        u_balance = await db.get_user_balance(uid)
        await call.message.edit_text(f'\n<b>Платеж принят.</b>'
                                     f'\nЗачислено: <b>{amount}</b> рублей'
                                     f'\n<b>Баланс:</b> {u_balance} рублей')
        adm_text = f'{username} пополнил баланс на {amount} рублей.'
        await inform_admins(adm_text)
        await db.withdraw_from_balance(uid, int(amount))
        await send_chat_request(hours, call, g_id, state, uid)
    elif status == 'CONFIRMED' and g_id is None:
        await db.top_up_balance(uid, int(amount))
        u_balance = await db.get_user_balance(uid)
        await call.message.edit_text(f'\n<b>Платеж принят.</b>'
                                     f'\nЗачислено: <b>{amount}</b> рублей'
                                     f'\n<b>Баланс:</b> {u_balance} рублей')
        adm_text = f'{username} пополнил баланс на {amount} рублей.'
        await inform_admins(adm_text)
    elif status == 'REJECTED':
        await call.message.edit_text(f'\n<b>Платеж отменен.</b>'
                                     f'\nНа вашей карте недостаточно средств.')
        await state.clear()
        return
    else:
        await call.message.answer('Платеж еще не обработан.')


# @router.message(UkassaPayment.input_value, lambda message: message.text.isdigit() and int(message.text) >= 500)
# async def p_buy_ukassa(message: Message, bot: aiogram_bot, state: FSMContext):
#    env = Env()
#    uk_token = env.str('uk_token')
#    payment_sum = message.text
#    price = LabeledPrice(label=f'Пополнение баланса gcc4bot_bot', amount=int(payment_sum)*100)
#    photo = 'https://i.yapx.ru/W2qAP.png'
#    await bot.send_invoice(chat_id=message.from_user.id,
#                           title='Пополнение баланса',
#                           description=f'Пополнение баланса на {payment_sum} рублей',
#                           provider_token=uk_token,
#                           currency='rub',
#                           photo_url=photo,
#                           photo_width=480,
#                           photo_height=260,
#                           photo_size=416,
#                           is_flexible=False,
#                           prices=[price],
#                          start_parameter='balance-top-up',
#                          payload='some-invoice-payload')
#   await state.clear()


@router.message(UkassaPayment.input_value)
async def process_inv_sum(message: Message):
    await message.answer('Неверная сумма пополнения!'
                         '\nМинимальная сумма пополнения - <b>300 рублей</b>')


@router.pre_checkout_query(lambda query: True)
async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: aiogram_bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message, state: FSMContext):
    uid = message.from_user.id
    print('successssfsdfdfsdsf')
    amount = message.successful_payment.total_amount // 100
    await message.answer(f'Баланс успешно пополнен на {amount} рублей.')
    logger.info(f'{uid} balance update: amount {amount}')
    await db.top_up_balance(uid, amount)
    await state.clear()
    await p_lk(message)

    # if message.successful_payment:
    #     amount = message.successful_payment.total_amount // 100
    #     await message.answer('Оплата прошла успешно!'
    #                          f'\nВаш баланс пополнен на <b>{amount}</b> рублей', parse_mode='HTML')
    #     await payment_action.update_balance(uid, amount)
    #
    #     await asyncio.sleep(1)
    #     user_data = await db.get_user_info(uid)
    #     ref_link = f'https://t.me/MagicComment24_bot?start=ref{uid}'
    #     accounts = ''
    #     commentaries = ''
    #     if user_data['sub_type'] == 'DEMO':
    #         accounts = '1 (демо)'
    #         commentaries = '1'
    #     elif user_data['sub_type'] == 'Подписка на 1 день':
    #         accounts = '1'
    #         commentaries = '7'
    #     elif user_data['sub_type'] == 'Подписка на 7 дней':
    #         accounts = '3'
    #         commentaries = '147'
    #     elif user_data['sub_type'] == 'Подписка на 30 дней':
    #         accounts = '5'
    #         commentaries = '1050'
    #     sub_start = 'Не активна' if user_data['sub_start_date'] is None else user_data['sub_start_date']
    #     sub_end = 'Не активна' if user_data['sub_end_date'] is None else user_data['sub_start_date']
    #     if user_data:
    #         await message.answer(f'<b>ID:</b> {uid}\n'
    #                                       f'<b>Username:</b> @{uname}\n\n'
    #
    #                                       f'<b>Баланс:</b> {user_data["balance"]} рублей\n'
    #                                       f'<b>Уровень подписки:</b> {user_data["sub_type"]}\n'
    #                                       f'<b>Начало подписки:</b> {sub_start}\n'
    #                                       f'<b>Подписка истекает:</b> {sub_end}\n'
    #                                       f'<b>Доступно аккаунтов:</b> {accounts}\n'
    #                                       f'<b>Лимит комментариев:</b> {commentaries}\n\n'
    #                                       f'<b>Статистика:\n</b>'
    #                                       f'Отправлено комментариев: {user_data["comments_sent"]}\n\n'
    #                                       f'<b>Реферальная программа:</b>\n'
    #                                       f'Приглашенных пользователей: 0\n'
    #                                       f'Бонусные дни подписки: 0\n\n'
    #                                       f'<b>Реферальная ссылка:</b> \n{ref_link}\n\n',
    #                                       reply_markup=kb_admin.lk_btns(),
    #                                       parse_mode='HTML')
    #     else:
    #         await message.answer('Произошла ошибка, попробуйте позже',
    #                                       reply_markup=kb_admin.lk_btns(),
    #                                       parse_mode='HTML')
