import asyncio
import uuid
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, CallbackQuery
from aiogram.types.message import ContentType
from environs import Env
from config import aiogram_bot, logger
from database import db
from keyboards import main_kb
from states import UkassaPayment
from yookassa import Configuration, Payment, Receipt
from utils import inform_admins

router = Router()


async def calculate_price_without_vat(price_with_vat, vat_rate):
    price_without_vat = price_with_vat / (1 + vat_rate)
    return price_without_vat


# Функция для создания платежа
async def create_payment(amount, description, return_url=None):
    try:
        env = Env()
        Configuration.account_id = env.int('uk_shop_id')
        Configuration.secret_key = env.str('uk_api')
        idempotence_key = str(uuid.uuid4())
        print(Configuration.account_id)
        print(Configuration.secret_key)

        return_url = 'https://t.me/Gifdeomes_bot'
        price_wv = await calculate_price_without_vat(amount, 20)
        payment = Payment.create({
            "amount": {
                "value": amount,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": f"{description}",
            "capture": True,
            "receipt": {
                "customer": {
                    "email": "stepusiktwitch@gmail.com"
                },
                "items": [
                    {
                        "description": "Пополнение баланса в Gifdeomes_bot",
                        "quantity": 1,
                        "amount": {
                            "value": amount,
                            "currency": "RUB"
                        },
                        "vat_code": "1"}
                ]
            },
        }, idempotence_key)

        payment_status = payment.status
        receipt_status = payment.receipt_registration
        print(f'status: {payment_status}')
        print(f'receipt_reg: {receipt_status}')
        await asyncio.sleep(3)
        conf_url = payment.confirmation.confirmation_url
        return payment.id, conf_url, amount
    except Exception as e:
        print(e)
        logger.error("Произошла ошибка:", e)
        return None


# Функция для проверки статуса платежа
async def check_payment_status(payment_id):
    try:
        payment = Payment.find_one(payment_id)
        status = payment.status
        rec_status = payment.receipt_registration
        print(f'status: {status}')
        print(f'rec status: {rec_status}')
        return status
    except Exception as e:
        print("Произошла ошибка:", e)
        return None

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
    amount = callback.data.split('_')[-1]
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
            await callback.message.answer(f'Пополнение баланса на <b>{amount}</b> рублей.', reply_markup=main_kb.pay_btns(payment_id, conf_url, amount))
            await state.clear()
        else:
            await callback.message.answer('Произошло ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
    except Exception as e:
        logger.error(e)
        await callback.message.answer('Произошло ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
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
            await message.answer('Произошло ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
    except Exception as e:
        logger.error(e)
        await message.answer('Произошло ошибка при отправке запроса. Пожалуйста, попробуйте позже.')
        await state.clear()


@router.callback_query(F.data.startswith('check_pay_status'))
async def p_check_pay_status(call: CallbackQuery):
    username = call.from_user.username
    uid = call.from_user.id
    logger.info(f'{uid} checking payment status')
    pid = call.data.split('_')[-2]
    amount = call.data.split('_')[-1]
    uid = call.from_user.id
    status = await check_payment_status(pid)
    if status == 'succeeded':
        await db.top_up_balance(uid, int(amount))
        u_balance = await db.get_user_balance(uid)
        await call.message.edit_text(f'\n<b>Платеж принят.</b>'
                                     f'\nЗачислено: <b>{amount}</b> рублей'
                                     f'\n<b>Баланс:</b> {u_balance} рублей')
        adm_text = f'{username} пополнил баланс на {amount} рублей.'
        await inform_admins(adm_text)
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
                         '\nМинимальная сумма пополнения - <b>500 рублей</b>')


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



