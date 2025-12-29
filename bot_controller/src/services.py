import json
import os
from pathlib import Path
from typing import Any, Dict

from loguru import logger

SHARED_DATA_DIR = Path("/app/shared_data")
PARAMS_FILE = SHARED_DATA_DIR / "strategy_params.json"


def load_params() -> Dict[str, Any]:
    """
    Loads strategy parameters from the shared JSON file.
    Returns default values if file is missing or corrupted.
    """
    if not PARAMS_FILE.exists():
        logger.warning(f"Params file not found at {PARAMS_FILE}. Using empty dict.")
        return {}

    try:
        with open(PARAMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load parameters: {e}")
        return {}


def save_params(params: Dict[str, Any]) -> bool:
    """
    Safely saves strategy parameters to the shared JSON file.
    Uses atomic write pattern (write to temp file, then rename).
    """
    temp_file = PARAMS_FILE.with_suffix(".tmp")
    try:
        PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, PARAMS_FILE)
        logger.info(f"Successfully saved new parameters to {PARAMS_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to save parameters safely: {e}")
        if temp_file.exists():
            temp_file.unlink()
        return False
