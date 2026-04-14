from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from hr_bot.database.engine import async_session
from hr_bot.database.models import User


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == event.from_user.id, User.is_active == True)
            )
            user = result.scalar_one_or_none()

        data["user"] = user
        state = data.get("state")
        current_state = await state.get_state() if state else None

        if event.text == "/start" or (current_state and current_state.startswith("RegStates")):
            return await handler(event, data)

        if not user:
            await event.answer("Доступ запрещен. Завершите регистрацию или дождитесь одобрения HR.")
            return

        return await handler(event, data)