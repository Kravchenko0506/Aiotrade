from aiogram import Router, types
from aiogram.filters import Command
from api_client import APIClient

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command."""
    await message.answer(
        "Привет! Я контроллер для Freqtrade.\n"
        "Используй /status для проверки состояния бота."
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message, api_client: APIClient):
    """
    Handler for /status command.
    Aiogram automatically injects 'api_client' from workflow data.
    """
    config_data = await api_client.get_status()

    if config_data is None:
        response = (
            "⚠️ **Ошибка подключения**\n" "Не удалось получить данные от Freqtrade API."
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
