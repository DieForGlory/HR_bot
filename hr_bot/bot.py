import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from config import config
from handlers import common, requests, sick_leave, admin, vacation, hr_chat, certificates, onboarding, surveys,registration # Добавлены onboarding и surveys
from middlewares.auth import AuthMiddleware
from database.engine import engine
from database.models import Base



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

    dp.message.outer_middleware(AuthMiddleware())

    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(requests.router)
    dp.include_router(sick_leave.router)
    dp.include_router(vacation.router)
    dp.include_router(hr_chat.router)
    dp.include_router(certificates.router)
    dp.include_router(onboarding.router) # Новый
    dp.include_router(surveys.router)    # Новый

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass