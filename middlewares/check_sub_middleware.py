import asyncio
from typing import Any, Callable, Dict, Awaitable, Union
from aiogram import BaseMiddleware
from environs import Env
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import aiogram_bot
from config import logger
from keyboards import main_kb


class CheckSubMiddleware(BaseMiddleware):
    def __init__(self):
        env = Env()
        self.channel_id = env.int('channel_id')
        self.bot = aiogram_bot

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        try:
            chat_member = await self.bot.get_chat_member(chat_id=self.channel_id, user_id=user_id)
            if chat_member.status not in ['creator', 'administrator', 'member']:
                # Если пользователь не является участником канала, отправляем сообщение и прерываем обработку
                await aiogram_bot.send_message(user_id, text="Вы должны быть участником нашего <a href='@ru_emarket'>канала</a> для доступа к боту."
                                               "\n\nПожалуйста, подпишитесь на канал и попробуйте еще раз.",
                                               reply_markup=main_kb.sub_menu())
                return
        except Exception as e:
            # Если бот не имеет доступа к информации о пользователе или к каналу
            logger.error(e)
            await event.answer("Произошла ошибка при проверке вашей подписки.")
            return

        # Если пользователь является участником канала, продолжаем обработку события
        return await handler(event, data)

