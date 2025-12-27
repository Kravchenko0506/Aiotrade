import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from api_client import APIClient
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    ),
    level="INFO",
)
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/bot_controller.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level="DEBUG",
)


async def main() -> None:
    """
    Entry point for Telegram Bot Controller.
    Initializes bot, dispatcher, API client and starts polling.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    api_url = os.getenv("FREQTRADE_API_URL")
    api_user = os.getenv("FREQTRADE_API_USERNAME", "freqtrader")
    api_pass = os.getenv("FREQTRADE_API_PASSWORD")

    if not bot_token:
        logger.critical("TELEGRAM_BOT_TOKEN missing in environment")
        sys.exit(1)

    if not api_url or not api_pass:
        logger.critical("FREQTRADE_API_URL or password missing")
        sys.exit(1)

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    client = APIClient(base_url=api_url, username=api_user, password=api_pass)

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Handler for /start command."""
        await message.answer(
            "Привет! Я контроллер для Freqtrade.\n"
            "Используй /status для проверки состояния бота."
        )

    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        """Handler for /status command."""
        config_data = await client.get_status()

        if config_data is None:
            response = (
                "⚠️ **Ошибка подключения**\n"
                "Не удалось получить данные от Freqtrade API."
            )
        elif not config_data or "state" not in config_data:
            response = (
                "⚠️ **API вернул некорректный ответ**\n"
                "Проверьте версию Freqtrade и доступность эндпоинта."
            )
        else:
            state = config_data.get("state", "unknown")
            strategy = config_data.get("strategy", "N/A")
            stake_currency = config_data.get("stake_currency", "N/A")

            response = (
                f"🤖 **Состояние:** {state}\n"
                f"📊 **Стратегия:** {strategy}\n"
                f"💰 **Валюта:** {stake_currency}\n"
                f"✅ Связь с API установлена."
            )

        await message.answer(response, parse_mode="Markdown")

    logger.info("Starting Telegram bot polling loop")
    try:
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
