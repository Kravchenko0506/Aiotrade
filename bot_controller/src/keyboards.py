from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """
    Generates the main control menu with inline buttons.
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📊 Статус", callback_data="cb_status"))

    builder.row(
        InlineKeyboardButton(text="▶️ Старт", callback_data="cb_start"),
        InlineKeyboardButton(text="⏹ Стоп", callback_data="cb_stop"),
    )

    builder.row(InlineKeyboardButton(text="⚙️ Настройки", callback_data="cb_settings"))

    return builder.as_markup()


def get_settings_menu() -> InlineKeyboardMarkup:
    """
    Generates the settings sub-menu.
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📝 Изменить RSI", callback_data="set_rsi"),
        InlineKeyboardButton(text="📉 Изменить Stoploss", callback_data="set_stoploss"),
    )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="cb_main_menu"))

    return builder.as_markup()
