from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from loguru import logger


class AdminMiddleware(BaseMiddleware):
    """
    Middleware to restrict access to the bot to a specific administrator.
    """

    def __init__(self, admin_id: int):
        self.admin_id = admin_id

    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.from_user and event.from_user.id == self.admin_id:
            return await handler(event, data)

        if event.from_user:
            logger.warning(
                f"Unauthorized access attempt from user "
                f"{event.from_user.id} (@{event.from_user.username})"
            )
        return None


class ServicesMiddleware(BaseMiddleware):
    """
    Middleware for Dependency Injection.
    Injects services (like APIClient) into handler arguments.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data.update(self.kwargs)
        return await handler(event, data)
