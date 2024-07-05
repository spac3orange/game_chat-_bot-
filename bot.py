import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import aiogram_bot
from config.logger import logger
from keyboards import set_commands_menu
from database import db
from handlers import start, game_menu, unknown_command, user_lk, pop_up_commands, search_engine, reviews
from handlers.admin_panel import edit_descriptions, panel_menu, edit_revs
from handlers.payment import ukassa, promo_code
from middlewares import CheckSubMiddleware


async def start_params() -> None:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(game_menu.router)
    dp.include_router(user_lk.router)
    dp.include_router(panel_menu.router)
    dp.include_router(edit_descriptions.router)
    dp.include_router(pop_up_commands.router)
    dp.include_router(ukassa.router)
    dp.include_router(promo_code.router)
    dp.include_router(search_engine.router)
    dp.include_router(reviews.router)
    dp.include_router(edit_revs.router)
    dp.include_router(unknown_command.router)

    dp.message.middleware(CheckSubMiddleware())
    dp.callback_query.middleware(CheckSubMiddleware())

    logger.info('Bot started')

    # Регистрируем меню команд
    await set_commands_menu(aiogram_bot)

    # инициализирем БД
    await db.db_start()

    # Пропускаем накопившиеся апдейты и запускаем polling
    await aiogram_bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(aiogram_bot)


async def main():
    task1 = asyncio.create_task(start_params())
    await asyncio.gather(task1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning('Bot stopped')
    except Exception as e:
        logger.error(e)
