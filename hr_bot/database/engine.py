from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from hr_bot.config import config


engine = create_async_engine(config.database_url.get_secret_value(), echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session