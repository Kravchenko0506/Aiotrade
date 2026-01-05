from middlewares import ServicesMiddleware
import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, types
from api_client import APIClient
from dotenv import load_dotenv
from handlers import router
from logger import setup_logging
from loguru import logger
from middlewares import AdminMiddleware

load_dotenv()

setup_logging()


async def main() -> None:
    """
    Entry point for Telegram Bot Controller.
    Initializes bot, dispatcher, API client and starts polling.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id_raw = os.getenv("ADMIN_ID")
    api_url = os.getenv("FREQTRADE_API_URL")
    api_user = os.getenv("FREQTRADE_API_USERNAME")
    api_pass = os.getenv("FREQTRADE_API_PASSWORD")

    if not bot_token or not admin_id_raw:
        logger.critical("TELEGRAM_BOT_TOKEN or ADMIN_ID missing in environment")
        sys.exit(1)

    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        logger.critical("ADMIN_ID must be an integer")
        sys.exit(1)

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(AdminMiddleware(admin_id))

    client = APIClient(base_url=api_url, username=api_user, password=api_pass)
    dp.update.middleware(ServicesMiddleware(api_client=client))
    dp.include_router(router)
    logger.info("Starting Telegram bot polling loop")
    try:
        await bot.set_my_commands(
            [
                types.BotCommand(command="start", description="🏠 Главное меню"),
                types.BotCommand(
                    command="reload", description="🔄 Перезагрузить конфиг"
                ),
            ],
            scope=types.BotCommandScopeAllPrivateChats(),
        )
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"Critical error during polling: {e}")
    finally:
        await client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Bot interrupted by user")
    except Exception:
        logger.exception("Fatal unhandled exception")
