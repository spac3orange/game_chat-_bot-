from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from config import logger
from filters.is_admin import IsAdmin
from keyboards import main_kb
from database import db
from states import Promo
router = Router()


async def check_code(code):
    codes = await db.get_all_promo()
    for c in codes:
        if c["code"] == code:
            return c["value"]
    return False


async def check_code_in_users(uid, code):
    codes = await db.get_user_promo_codes(uid)
    print(codes)
    if code in codes:
        return False
    else:
        return True


async def p_lk(message: Message):
    uid = message.from_user.id
    user_balance = await db.get_user_balance(uid)
    user_info = (f'<b>Ваш ID</b>: {uid}'
                 f'\n<b>Баланс:</b> {user_balance} рублей')
    await message.answer(user_info, reply_markup=main_kb.lk_menu())


@router.callback_query(F.data == 'input_promo')
async def p_input_promo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите промо-код: ', reply_markup=main_kb.del_last_promo())
    await state.set_state(Promo.input_code)


@router.callback_query(F.data == 'del_last_promo')
async def del_l_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.delete()


@router.message(Promo.input_code, lambda message: message.text.isdigit())
async def p_code_applied(message: Message, state: FSMContext):
    uid = message.from_user.id
    code = message.text
    code_value = await check_code(code)
    if code_value:
        code_not_used = await check_code_in_users(uid, code)
        if code_not_used:
            await db.top_up_balance(uid, code_value)
            await message.answer(f'Баланс пополнен на {code_value} рублей')
            await db.add_promo_code_to_user(uid, code)
            await state.clear()
            await p_lk(message)
        else:
            await message.answer('Вы уже использовали этот код.')
    else:
        await message.answer('Промо код указан не верно.')




