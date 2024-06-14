from config import logger, aiogram_bot, config_aiogram


async def inform_admins(msg_text: str, reply_markup=None) -> None:
    admin_list = config_aiogram.admin_id
    if reply_markup:
        if isinstance(admin_list, list):
            for admin_id in admin_list:
                try:
                    await aiogram_bot.send_message(admin_id, text=msg_text, reply_markup=reply_markup)
                except Exception as e:
                    logger.error(e)
                    continue
        else:
            await aiogram_bot.send_chat_action(admin_list, text=msg_text)
    else:
        if isinstance(admin_list, list):
            for admin_id in admin_list:
                try:
                    await aiogram_bot.send_message(admin_id, text=msg_text)
                except Exception as e:
                    logger.error(e)
                    continue
        else:
            await aiogram_bot.send_chat_action(admin_list, text=msg_text)
