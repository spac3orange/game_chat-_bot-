import hashlib
import http.client
import json
import random
import string
from datetime import datetime, timedelta

from aiogram import Router
from environs import Env

from config import logger

router = Router()
env = Env()
t_token = env('t_api')
t_password = env('t_pass')
terminal_key = env.str('t_key')


async def calculate_price_without_vat(price_with_vat, vat_rate):
    price_without_vat = price_with_vat / (1 + vat_rate)
    return price_without_vat


async def create_payment(amount: int, hours):
    try:
        return_url = 'https://t.me/Gifdeomes_bot'
        price_wv = await calculate_price_without_vat(amount, 20)
        invoice_number = ''.join(random.choices(string.digits, k=15))
        due_date = (datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d')
        invoice_date = datetime.now().strftime('%Y-%m-%d')

        # Корневые параметры для токена
        params = {
            "TerminalKey": terminal_key,
            "Amount": amount * 100,  # Сумма в копейках
            "OrderId": invoice_number,
            "Description": "Платеж за товар",
            "Password": t_password
        }

        # Сортируем параметры по ключу и конкатенируем их значения
        sorted_values = ''.join(str(params[k]) for k in sorted(params.keys()))

        # Вычисляем SHA-256 хеш
        token = hashlib.sha256(sorted_values.encode('utf-8')).hexdigest()

        conn = http.client.HTTPSConnection("securepay.tinkoff.ru")
        payload = json.dumps({
            "TerminalKey": terminal_key,
            "Amount": amount * 100,
            "OrderId": invoice_number,
            "Description": "Платеж за товар",
            "Token": token,

            "Receipt": {
                "Email": "stepdronpro@gmail.com",
                "Phone": "+79031234555",
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": "Оплата чата",
                        "Price": amount * 100,
                        "Quantity": 1,
                        "Amount": amount * 100,
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
        print(f'Payment ID: {payment_id}')
        return payment_id

    except Exception as e:
        print(e)
        logger.error("Произошла ошибка:", e)


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

    except Exception as e:
        print("Произошла ошибка:", e)
        return None


# pay_id = asyncio.run(create_payment(100, 1))

# asyncio.run(check_payment_status(pay_id))
# "Status":"NEW", "Status":"CONFIRMED", "Status":"REJECTED"
