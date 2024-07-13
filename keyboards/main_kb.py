from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import config_aiogram
from environs import Env
import uuid
import base64


def encode_payment_id_base64(payment_id: str) -> str:
    # Преобразование UUID в байты
    payment_id_bytes = uuid.UUID(payment_id).bytes
    # Кодирование в Base64
    encoded_id = base64.urlsafe_b64encode(payment_id_bytes).decode('utf-8').rstrip('=')
    return encoded_id


def decode_payment_id_base64(encoded_id: str) -> str:
    # Декодирование из Base64
    decoded_id_bytes = base64.urlsafe_b64decode(encoded_id + '==')
    decoded_payment_id = str(uuid.UUID(bytes=decoded_id_bytes))
    return decoded_payment_id


def start_btns(uid):
    admins = config_aiogram.admin_id
    kb_builder = InlineKeyboardBuilder()
    if str(uid) in admins:
        kb_builder.button(text='Выбрать игру', callback_data='select_game')
        kb_builder.button(text='Личный кабинет', callback_data='user_lk')
        kb_builder.button(text='Админ панель', callback_data='admin_panel')
        kb_builder.button(text='Тех. Поддержка', url='https://t.me/egirlforyou')
    else:
        kb_builder.button(text='Выбрать игру', callback_data='select_game')
        kb_builder.button(text='Личный кабинет', callback_data='user_lk')
        kb_builder.button(text='Тех. Поддержка', url='https://t.me/egirlforyou')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def game_menu():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='CS 2', callback_data='game_cs2')
    kb_builder.button(text='DOTA 2', callback_data='game_dota2')
    kb_builder.button(text='VALORANT', callback_data='game_val')
    kb_builder.button(text='APEX', callback_data='game_apex')
    kb_builder.button(text='Общение', callback_data='game_talk')
    kb_builder.button(text='Назад', callback_data='back_to_main')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def lk_menu():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Пополнить баланс', callback_data='add_balance')
    kb_builder.button(text='Ввести промо-код', callback_data='input_promo')
    kb_builder.button(text='Назад', callback_data='back_to_main')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def adm_p_menu():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Рассылка', callback_data='adm_mailing')
    kb_builder.button(text='Пользователи', callback_data='adm_get_users')
    kb_builder.button(text='Редактировать описания', callback_data='adm_edit_descriptions')
    kb_builder.button(text='Промо-коды', callback_data='edit_promo_codes')
    kb_builder.button(text='Отзывы', callback_data='edit_reviews')
    kb_builder.button(text='Назад', callback_data='back_to_main')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def sub_menu():
    kb_builder = InlineKeyboardBuilder()
    env = Env()
    kb_builder.button(text='Подписаться', url=env.str('channel_url'))
    kb_builder.button(text='Проверить подписку', callback_data='check_sub')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def bg_menu(g_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Оплатить', callback_data=f'bg_buy_{g_id}')
    kb_builder.button(text='Отзывы', callback_data=f'revs_{g_id}')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def g_intr_menu(g_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Подробнее', callback_data=f'g_intr_menu_{g_id}')
    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def sg_btn():
    buttons = [
        [KeyboardButton(text='Остановить поиск', callback_data='stop')]
    ]
    kb_markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return kb_markup


def buy_girl(g_id, price):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Подтвердить', callback_data=f'complete_buy_girl_{g_id}_{price}')
    kb_builder.button(text='Отмена', callback_data=f'cancel_buy_girl')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def buy_girl_fxd(g_id, price, hours):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Купить доступ', callback_data=f'add_fxd_balance_{hours}_{g_id}_{price}')
    kb_builder.button(text='Отмена', callback_data=f'cancel_buy_girl')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def pay_btns(pid, conf_url, amount):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Оплатить', url=conf_url)
    kb_builder.button(text='Проверить статус', callback_data=f'check_pay_status_{pid}_{amount}')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def pay_btns_fxd(pid, conf_url, amount, g_id, hours):
    kb_builder = InlineKeyboardBuilder()
    encoded_id = encode_payment_id_base64(pid)
    kb_builder.button(text='Оплатить', url=conf_url)
    kb_builder.button(text='Проверить статус', callback_data=f'check_pay_status_{hours}_{g_id}_{encoded_id}_{amount}')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def edit_promo_codes():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Добавить', callback_data='add_promo_code')
    kb_builder.button(text='Удалить', callback_data='rm_promo_code')
    kb_builder.button(text='Назад', callback_data=f'del_last_promo')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def del_promo_codes(codes):
    kb_builder = InlineKeyboardBuilder()
    for code in codes:
        kb_builder.button(text=code["code"], callback_data=f'del_code_{code["code"]}')
    kb_builder.button(text='Назад', callback_data='del_last_promo')
    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def del_last_lk():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Назад', callback_data='user_lk')
    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def del_last_promo():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Отменить', callback_data='del_last_promo')
    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def rev_menu(g_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Написать', callback_data=f'create_rev_{g_id}')
    kb_builder.button(text='Отказаться', callback_data='pass_rev')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def chat_menu(user_1_id, hours):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Принять', callback_data=f'accept_{hours}_{user_1_id}')
    kb_builder.button(text='Отменить', callback_data=f'decline_{user_1_id}')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def edit_revs_menu(g_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Отзывы', callback_data=f'adm_edit_revs_{g_id}')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def adm_del_rev(rev_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Удалить', callback_data=f'adm_del_rev_{rev_id}')

    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


# def web_q(g_price, message_id, g_id):
#     kb_builder = InlineKeyboardBuilder()
#     kb_builder.button(text='Да', callback_data=f'web_q_y_{message_id}_{g_price}_{g_id}')
#     kb_builder.button(text='Нет', callback_data=f'web_q_n_{message_id}_{g_price}_{g_id}')
#     kb_builder.adjust(2)
#     return kb_builder.as_markup(resize_keyboard=True)
#
#
# def alone_q(g_price, message_id, g_id):
#     kb_builder = InlineKeyboardBuilder()
#     kb_builder.button(text='Да', callback_data=f'complete_buy_girl_{message_id}_{g_price}_{g_id}')
#     kb_builder.button(text='Нет', callback_data=f'alone_q_n_{message_id}_{g_price}_{g_id}')
#     kb_builder.adjust(2)
#     return kb_builder.as_markup(resize_keyboard=True)


def create_services_keyboard(services=None, g_id=None, h_price=None):
    kb_builder = InlineKeyboardBuilder()
    if services:
        for service in services:
            print(service)
            button_text = f"{service['service_name']}"
            callback_data = f"u_add_service_{service['s_id']}_{service['price']}_{g_id}"  # Уникальный идентификатор услуги
            kb_builder.button(text=button_text, callback_data=callback_data)
        kb_builder.button(text='Отзывы', callback_data=f'revs_{g_id}')
        kb_builder.button(text='Оплатить', callback_data=f'complete_buy_girl_{h_price}_{g_id}')
        kb_builder.adjust(2)
        return kb_builder.as_markup(resize_keyboard=True)
    else:
        kb_builder.button(text='Отзывы', callback_data=f'revs_{g_id}')
        kb_builder.button(text='Оплатить', callback_data=f'cbg_noserv_{h_price}_{g_id}')
        kb_builder.adjust(2)
        return kb_builder.as_markup(resize_keyboard=True)


def create_add_services_keyboard(g_id, services, ttl_price, h_price, ttl_hours):
    kb_builder = InlineKeyboardBuilder()
    for service in services:
        button_text = f"{service['service_name']}"
        callback_data = f"u_add_service_{service['s_id']}_{service['price']}_{g_id}"  # Уникальный идентификатор услуги
        kb_builder.button(text=button_text, callback_data=callback_data)
    kb_builder.button(text='Отзывы', callback_data=f'revs_{g_id}')
    kb_builder.button(text='Оплатить', callback_data=f'complete_buy_girl_{ttl_hours}_{h_price}_{g_id}_{ttl_price}')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def u_choose_serv(s_name, s_price, g_id):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Добавить', callback_data=f'bg_add_serv_{s_name}_{s_price}_{g_id}')
    kb_builder.button(text='Назад', callback_data=f'back_to_add_serv_{g_id}')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def u_webcam_req():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Да', callback_data=f'webcam_req_y_')
    kb_builder.button(text='Нет', callback_data=f'webcam_req_n_')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)


def additional_part_req():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Да', callback_data=f'add_part_req_y_')
    kb_builder.button(text='Нет', callback_data=f'add_part_req_n_')
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)