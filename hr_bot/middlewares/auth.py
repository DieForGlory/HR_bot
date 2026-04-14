from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy import select
from hr_bot.database.engine import async_session
from hr_bot.database.models import User

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]):
        user_id = data["event_from_user"].id

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()

        data["user"] = user
        state = data.get("state")
        current_state = await state.get_state() if state else None

        is_start = isinstance(event, Message) and event.text == "/start"

        if is_start or (current_state and current_state.startswith("RegStates")):
            return await handler(event, data)

        if not user:
            if isinstance(event, Message):
                await event.answer("Доступ запрещен. Завершите регистрацию или дождитесь одобрения HR.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен. Ожидайте одобрения.", show_alert=True)
            return

        return await handler(event, data)