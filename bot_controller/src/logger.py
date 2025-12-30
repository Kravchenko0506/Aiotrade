import logging
import sys
from types import FrameType
from typing import Optional

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Intercepts standard logging messages and redirects them to Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Optional[FrameType] = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    Configures Loguru logger and intercepts standard library logging.
    """

    if getattr(setup_logging, "_is_setup", False):
        return
    setup_logging._is_setup = True

    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG",
        colorize=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.INFO)
