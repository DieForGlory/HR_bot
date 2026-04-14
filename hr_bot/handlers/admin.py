from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User
from sqlalchemy import update, select

router = Router()

@router.callback_query(F.data.startswith("approve_"))
async def approve_request(callback: CallbackQuery, bot: Bot):
    request_id = int(callback.data.split("_")[1])

    async with async_session() as session:
        result = await session.execute(
            select(Request, User).join(User).where(Request.id == request_id)
        )
        data = result.first()
        if not data: return

        req, user = data
        await session.execute(update(Request).where(Request.id == request_id).values(status="approved"))
        await session.commit()

    await bot.send_message(user.tg_id, f"✅ Ваша заявка на {req.type} ({req.start_date}) одобрена!")
    await callback.message.edit_text(callback.message.text + "\n\n✅ Статус: Одобрено")

@router.callback_query(F.data.startswith("reject_"))
async def reject_request(callback: CallbackQuery, bot: Bot):
    request_id = int(callback.data.split("_")[1])

    async with async_session() as session:
        result = await session.execute(select(Request, User).join(User).where(Request.id == request_id))
        data = result.first()
        if not data: return

        req, user = data
        await session.execute(update(Request).where(Request.id == request_id).values(status="rejected"))
        await session.commit()

    await bot.send_message(user.tg_id, f"❌ Ваша заявка на {req.type} ({req.start_date}) отклонена.")
    await callback.message.edit_text(callback.message.text + "\n\n❌ Статус: Отклонено")

@router.callback_query(F.data.startswith("reg_approve_"))
async def approve_reg(callback: CallbackQuery, bot: Bot):
    user_tg_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == user_tg_id).values(is_active=True)
        )
        await session.commit()

    await bot.send_message(user_tg_id, "🎉 Ваша регистрация одобрена! Теперь вам доступно основное меню. Используйте /start.")
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ Одобрено")


@router.callback_query(F.data.startswith("reg_reject_"))
async def reject_reg(callback: CallbackQuery, bot: Bot):
    user_tg_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == user_tg_id).values(is_active=False)
        )
        await session.commit()

    await bot.send_message(user_tg_id, "❌ Ваша заявка на регистрацию отклонена.")
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ Отклонено")