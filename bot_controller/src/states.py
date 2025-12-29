from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    """
    Finite State Machine definitions for settings modification.
    """

    waiting_for_rsi = State()
    waiting_for_stoploss = State()
