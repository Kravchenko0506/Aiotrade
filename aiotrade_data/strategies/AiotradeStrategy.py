import json
import logging
from pathlib import Path
from typing import Any  # добавили

import pandas as pd
import pandas_ta as pta
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class AiotradeStrategy(IStrategy):

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
        return "2.0-JSON"

    def bot_loop_start(self, **kwargs: Any) -> None:
        self._load_dynamic_params()

    def _load_dynamic_params(self) -> None:
        try:
            file_path = Path(self.config["user_data_dir"]) / "strategy_params.json"

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    new_params = json.load(f)

                self.params.update(new_params)

                self.stoploss = float(new_params.get("stoploss", -0.10))
                self.trailing_stop = bool(new_params.get("trailing_stop", True))
                self.trailing_stop_positive = float(
                    new_params.get("trailing_stop_positive", 0.01)
                )
                self.trailing_stop_positive_offset = float(
                    new_params.get("trailing_stop_positive_offset", 0.02)
                )
            else:
                logger.warning("strategy_params.json not found! Using defaults.")

        except Exception as e:
            logger.error(f"Failed to load dynamic params: {e}")

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict
    ) -> pd.DataFrame:
        period = int(self.params.get("rsi_period", 14))
        dataframe["rsi"] = pta.rsi(dataframe["close"], length=period)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)

        return dataframe

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict
    ) -> pd.DataFrame:
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
        rsi_sell_level = float(self.params.get("rsi_sell", 70))

        dataframe.loc[
            ((dataframe["rsi"] > rsi_sell_level) & (dataframe["volume"] > 0)),
            "exit_long",
        ] = 1
        return dataframe
