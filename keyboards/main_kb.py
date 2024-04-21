from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import config_aiogram
from environs import Env

def start_btns(uid):
    admins = config_aiogram.admin_id
    kb_builder = InlineKeyboardBuilder()
    if str(uid) in admins:
        kb_builder.button(text='Выбрать игру', callback_data='select_game')
        kb_builder.button(text='Личный кабинет', callback_data='user_lk')
        kb_builder.button(text='Админ панель', callback_data='admin_panel')
    else:
        kb_builder.button(text='Выбрать игру', callback_data='select_game')
        kb_builder.button(text='Личный кабинет', callback_data='user_lk')

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
    kb_builder.button(text='Подтвердить', callback_data=f'buy_girl_{g_id}_{price}')
    kb_builder.button(text='Отмена', callback_data=f'cancel_buy_girl')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def buy_girl_fxd(g_id, price):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Купить доступ', callback_data=f'add_fxd_balance_{g_id}_{price}')
    kb_builder.button(text='Отмена', callback_data=f'cancel_buy_girl')

    kb_builder.adjust(1)
    return kb_builder.as_markup(resize_keyboard=True)


def pay_btns(pid, conf_url, amount):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text='Оплатить', url=conf_url)
    kb_builder.button(text='Проверить статус', callback_data=f'check_pay_status_{pid}_{amount}')

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

