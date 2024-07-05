import random

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import main_kb
from states import ProcRev
from utils import inform_admins

router = Router()
router.message.filter(
)


async def generate_random_id():
    random_id = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    return random_id


async def send_rev_notif(message: Message, g_id):
    await message.answer('Пожалуйста оставьте отзыв о девушке: ', reply_markup=main_kb.rev_menu(g_id))


@router.callback_query(F.data.startswith('revs_'))
async def get_revs(call: CallbackQuery):
    await call.answer()
    g_id = int(call.data.split('_')[-1])
    revs = await db.get_reviews_for_g_id(g_id)
    if revs:
        for rev in revs:
            from_user = rev['from_username']
            date = rev['date']
            text = rev['rev_text']
            await call.message.answer(f'<b>От кого:</b> {from_user}'
                                      f'\n<b>Дата:</b> {date}'
                                      f'\n<b>Отзыв:</b> {text}')
    else:
        await call.message.answer('Отзывы не найдены.')


@router.callback_query(F.data.startswith('create_rev_'))
async def p_create_rev(callback: CallbackQuery, state: FSMContext):
    g_id = callback.data.split('_')[-1]
    await callback.message.answer('Введите текст отзыва: ')
    await state.set_state(ProcRev.input_rev)
    await state.update_data(g_id=g_id)


@router.message(ProcRev.input_rev)
async def p_proc_rev(message: Message, state: FSMContext):
    rev_id = await generate_random_id()
    username = message.from_user.username
    data = await state.get_data()
    review = message.text
    await db.add_review(g_id=int(data['g_id']), rev_id=int(rev_id), from_username=username, rev_text=review)
    await message.answer('Отзыв добавлен.')
    adm_text = (f'Пользователь @{message.from_user.username} оставил отзыв девушке {data['g_id']}.'
                f'\n\n.')
    adm_rpmkup = main_kb.adm_del_rev(rev_id)
    await inform_admins(adm_text, reply_markup=adm_rpmkup)
    await state.clear()


@router.callback_query(F.data == 'pass_rev')
async def p_pass_rev(callback: CallbackQuery):
    pass
