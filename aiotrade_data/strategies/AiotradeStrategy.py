import json
from pathlib import Path
from typing import Any

import pandas as pd
import pandas_ta as pta
from freqtrade.strategy import IStrategy
from loguru import logger
from pydantic import BaseModel, Field, ValidationError


class StrategyParams(BaseModel):
    """Data model for dynamic strategy parameters validation."""

    rsi_period: int = Field(default=14, ge=2, le=100)
    rsi_buy: int = Field(default=30, ge=1, le=99)
    rsi_sell: int = Field(default=70, ge=1, le=99)
    stoploss: float = Field(default=-0.10, lt=0.0, ge=-1.0)
    trailing_stop: bool = Field(default=True)
    trailing_stop_positive: float = Field(default=0.01, ge=0.0)
    trailing_stop_positive_offset: float = Field(default=0.02, ge=0.0)


class AiotradeStrategy(IStrategy):
    """
    Aiotrade Strategy implementation for Freqtrade.

    Uses RSI and EMA indicators for entry/exit signals.
    Supports dynamic parameter reloading from a JSON file without restarting the bot.

    """

    minimal_roi = {"0": 100}
    timeframe = "15m"
    params = {
        "rsi_period": 14,
        "rsi_buy": 30,
        "rsi_sell": 70,
        "stoploss": -0.10,
        "trailing_stop": True,
    }

    def version(self) -> str:
        """Returns the strategy version."""
        return "2.1-Pydantic"

    def __init__(self, config: dict) -> None:
        """Initialize the strategy."""
        super().__init__(config)
        self._last_params_mtime = 0.0

    def bot_loop_start(self, **kwargs: Any) -> None:
        """
        Called at the start of each bot iteration.
        Used here to reload dynamic parameters.

        """
        self._load_dynamic_params()

    def _load_dynamic_params(self) -> None:
        """
        Loads strategy parameters from 'strategy_params.json' if the file has changed.

        Updates the strategy's 'params' dictionary and specific attributes like stoploss
        and trailing_stop settings based on the validated JSON data.

        Raises:
            ValidationError: If JSON data does not match the StrategyParams schema.
            Exception: For other file reading or parsing errors.
        """
        try:
            file_path = Path(self.config["user_data_dir"]) / "strategy_params.json"
            if not file_path.exists():
                if self._last_params_mtime != -1:
                    logger.warning(f"Params file not found at {file_path}")
                    self._last_params_mtime = -1
                return

            current_mtime = file_path.stat().st_mtime
            if current_mtime == self._last_params_mtime:
                return

            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            validated = StrategyParams(**raw_data)
            new_params = validated.dict()
            self.params.update(new_params)
            self.stoploss = validated.stoploss
            self.trailing_stop = validated.trailing_stop
            self.trailing_stop_positive = validated.trailing_stop_positive
            self.trailing_stop_positive_offset = validated.trailing_stop_positive_offset

            self._last_params_mtime = current_mtime
            logger.info("Strategy params updated successfully")

        except ValidationError as e:
            logger.error(f"Validation error loading strategy params: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading strategy params: {e}")

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict
    ) -> pd.DataFrame:
        """Calculate technical indicators."""
        period = int(self.params.get("rsi_period", 14))
        dataframe["rsi"] = pta.rsi(dataframe["close"], length=period)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)
        return dataframe

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict
    ) -> pd.DataFrame:
        """Determine entry points based on indicators."""
        rsi_buy_level = float(self.params.get("rsi_buy", 30))
        dataframe.loc[
            (
                (dataframe["rsi"] < rsi_buy_level)
                & (dataframe["close"] > dataframe["ema_200"])
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(
        self, dataframe: pd.DataFrame, metadata: dict
    ) -> pd.DataFrame:
        """Determine exit points based on indicators."""
        rsi_sell_level = float(self.params.get("rsi_sell", 70))
        dataframe.loc[
            ((dataframe["rsi"] > rsi_sell_level) & (dataframe["volume"] > 0)),
            "exit_long",
        ] = 1
        return dataframe
