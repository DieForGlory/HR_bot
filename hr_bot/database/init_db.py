
import asyncio
from hr_bot.database.engine import engine, async_session
from hr_bot.database.models import Base, User

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        admin = User(
            tg_id=920158086,  # Заменить на реальный ID
            fullname="Plakhotnyi Dmitry",
            phone="+79169782470",
            role="hr",
            is_active=True
        )
        session.add(admin)
        await session.commit()
    print("Database initialized.")


if __name__ == "__main__":
    asyncio.run(init_db())