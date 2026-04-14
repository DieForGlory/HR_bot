import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from hr_bot.config import config
from hr_bot.handlers import common, requests, sick_leave, admin, vacation, hr_chat, certificates, onboarding, surveys, registration
from hr_bot.middlewares.auth import AuthMiddleware
from hr_bot.database.engine import engine
from hr_bot.database.models import Base


# Ваш SSL PATCH
_orig_connector_init = aiohttp.TCPConnector.__init__
def _patched_connector_init(self, *args, **kwargs):
    kwargs['ssl'] = False
    _orig_connector_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = _patched_connector_init

async def main():
    logging.basicConfig(level=logging.INFO)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher()
    auth_mw = AuthMiddleware()
    dp.message.outer_middleware(auth_mw)
    dp.callback_query.outer_middleware(auth_mw)
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(requests.router)
    dp.include_router(sick_leave.router)
    dp.include_router(vacation.router)
    dp.include_router(hr_chat.router)
    dp.include_router(certificates.router)
    dp.include_router(onboarding.router)
    dp.include_router(surveys.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass