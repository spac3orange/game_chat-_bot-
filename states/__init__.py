from aiogram.fsm.state import StatesGroup, State


class AdmMailing(StatesGroup):
    input_message = State()


class UkassaPayment(StatesGroup):
    input_value = State()


class Promo(StatesGroup):
    input_code = State()


class SearchGirls(StatesGroup):
    searching = State()


class EditBot(StatesGroup):
    input_media = State()
    input_maint = State()
    input_gst = State()


class EnterPromo(StatesGroup):
    input_code = State()


class BuyGirl(StatesGroup):
    input_hours = State()
    process_req = State()