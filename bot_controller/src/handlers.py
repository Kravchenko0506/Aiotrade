import asyncio
import datetime
from typing import Callable, Any

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from api_client import APIClient
from keyboards import get_main_menu, get_settings_menu
from services import load_params, save_params
from states import SettingsStates

router = Router()


async def _get_status_text(api_client: APIClient) -> str:
    """
    Function to fetch status and format.
    Shared between button and command handlers.
    """
    now = datetime.datetime.now().strftime("%H:%M:%S")

    config_data, balance_data, daily_data, trades_data = await asyncio.gather(
        api_client.get_status(),
        api_client.get_balance(),
        api_client.get_daily_profit(),
        api_client.get_trades(),
    )

    if config_data is None:
        return (
            f"⚠️ **Ошибка подключения**\n"
            f"🕒 `{now}`\n"
            "Не удалось связаться с Freqtrade API."
        )

    if not config_data or "state" not in config_data:
        return f"⚠️ **Ошибка данных**\n" f"🕒 `{now}`\n" "API вернул некорректный ответ."

    bot_state = config_data.get("state", "unknown")
    strategy = config_data.get("strategy", "N/A")
    status_emoji = "🟢" if bot_state == "running" else "🔴"

    total_balance = "N/A"
    currency = "USDT"
    if balance_data and "total" in balance_data:
        try:
            total_balance = f"{balance_data['total']:.2f}"
            currency = balance_data.get("currency", "USDT")
        except (ValueError, TypeError):
            pass

    daily_profit = "N/A"
    daily_pct = "N/A"
    if daily_data and "data" in daily_data and len(daily_data["data"]) > 0:
        today = daily_data["data"][-1]
        try:
            profit_abs = today.get("abs_profit", 0.0)
            profit_pct = today.get("rel_profit", 0.0) * 100  # Convert to %
            daily_profit = f"{profit_abs:.2f}"
            daily_pct = f"{profit_pct:.2f}%"
        except (ValueError, TypeError):
            pass

    active_trades = 0
    if isinstance(trades_data, list):
        active_trades = len(trades_data)

    return (
        f"{status_emoji} **Состояние:** `{bot_state}`\n"
        f"📊 **Стратегия:** `{strategy}`\n"
        f"💰 **Баланс:** `{total_balance} {currency}`\n"
        f"📈 **Профит (24ч):** `{daily_profit} {currency}` ({daily_pct})\n"
        f"⚡ **Активные сделки:** `{active_trades}`\n"
        f"🕒 Обновлено: `{now}`"
    )


@router.message(Command("start"))
@router.message(Command("menu"))
async def cmd_start(message: types.Message):
    """
    Handler for /start and /menu commands.
    """
    await message.answer(
        "👋 **Панель управления Freqtrade**\n\n" "Выберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
    )


@router.message(Command("reload"))
async def cmd_reload(message: types.Message, api_client: APIClient):
    """Manual config reload."""
    status_msg = await message.answer("🔄 Перезагрузка конфига...")
    success = await api_client.reload_config()

    if success:
        await status_msg.edit_text("✅ Конфигурация успешно перезагружена!")
    else:
        await status_msg.edit_text("❌ Ошибка перезагрузки (ядро недоступно).")


@router.callback_query(F.data == "cb_main_menu")
async def cb_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "👋 **Панель управления Freqtrade**\n\n" "Выберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "cb_status")
async def cb_status(callback: types.CallbackQuery, api_client: APIClient):
    """Updates the message with current bot status."""
    await callback.answer("Обновляю статус...")
    text = await _get_status_text(api_client)

    try:
        await callback.message.edit_text(
            text, reply_markup=get_main_menu(), parse_mode="Markdown"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "cb_start")
async def cb_start(callback: types.CallbackQuery, api_client: APIClient):
    """Start command."""
    success = await api_client.start()
    if success:
        await callback.answer("🚀 Бот запускается...", show_alert=True)
        await cb_status(callback, api_client)
    else:
        await callback.answer("❌ Ошибка запуска!", show_alert=True)


@router.callback_query(F.data == "cb_stop")
async def cb_stop(callback: types.CallbackQuery, api_client: APIClient):
    """Stop command."""
    success = await api_client.stop()
    if success:
        await callback.answer("🛑 Бот останавливается...", show_alert=True)
        await cb_status(callback, api_client)
    else:
        await callback.answer("❌ Ошибка остановки!", show_alert=True)


@router.callback_query(F.data == "cb_settings")
async def cb_settings(callback: types.CallbackQuery):
    """Show settings menu with current values."""
    await callback.answer()
    params = await asyncio.to_thread(load_params)

    rsi_buy = params.get("rsi_buy", 30)
    stoploss = params.get("stoploss", -0.10)

    text = (
        "⚙️ **Настройки стратегии**\n\n"
        f"🔹 **RSI Buy:** `{rsi_buy}`\n"
        f"🔹 **Stoploss:** `{stoploss}`\n\n"
        "👇 Нажмите кнопку, чтобы изменить значение."
    )

    await callback.message.edit_text(
        text, reply_markup=get_settings_menu(), parse_mode="Markdown"
    )


async def _update_param(
    message: types.Message,
    state: FSMContext,
    api_client: APIClient,
    param_name: str,
    validator: Callable[[str], Any],
    error_msg: str,
) -> None:
    """Universal handler for parameter updates."""
    try:
        new_value = validator(message.text)

        params = await asyncio.to_thread(load_params)
        params[param_name] = new_value
        success = await asyncio.to_thread(save_params, params)

        if not success:
            await message.answer("❌ Ошибка записи файла параметров.")
            return

        reload_ok = await api_client.reload_config()
        if reload_ok:
            await message.answer(
                f"✅ **{param_name} изменен на {new_value}**",
                reply_markup=get_settings_menu(),
                parse_mode="Markdown",
            )
        else:
            await message.answer("⚠️ Параметр сохранен, но не применен (бот недоступен)")

    except ValueError:
        await message.answer(error_msg)
        return

    await state.clear()


def validate_rsi(text: str) -> int:
    value = int(text)
    if not (1 <= value <= 99):
        raise ValueError
    return value


def validate_stoploss(text: str) -> float:
    value = float(text)
    if not (-1.0 <= value <= 0.0):
        raise ValueError
    return value


@router.callback_query(F.data == "set_rsi")
async def start_set_rsi(callback: types.CallbackQuery, state: FSMContext):
    """Enter RSI edit mode."""
    await callback.answer()
    await state.set_state(SettingsStates.waiting_for_rsi)
    await callback.message.answer(
        "✍️ **Введите новое значение RSI Buy**\n"
        "(Целое число от 1 до 100, например: `40`)"
    )


@router.message(SettingsStates.waiting_for_rsi)
async def process_rsi_input(
    message: types.Message, state: FSMContext, api_client: APIClient
):
    await _update_param(
        message,
        state,
        api_client,
        param_name="rsi_buy",
        validator=validate_rsi,
        error_msg="⚠️ Введите целое число от 1 до 99",
    )


@router.callback_query(F.data == "set_stoploss")
async def start_set_stoploss(callback: types.CallbackQuery, state: FSMContext):
    """Enter Stoploss edit mode."""
    await callback.answer()
    await state.set_state(SettingsStates.waiting_for_stoploss)
    await callback.message.answer(
        "✍️ **Введите новое значение Stoploss**\n"
        "(Отрицательное дробное число, например: `-0.15` для 15%)"
    )


@router.message(SettingsStates.waiting_for_stoploss)
async def process_stoploss_input(
    message: types.Message, state: FSMContext, api_client: APIClient
):
    await _update_param(
        message,
        state,
        api_client,
        param_name="stoploss",
        validator=validate_stoploss,
        error_msg="⚠️ Введите число от -1.0 до 0.0 (например -0.1)",
    )
