from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User
from sqlalchemy import update, select
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.models import Holiday
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from aiogram.types import CallbackQuery, Message
from hr_bot.utils.logger import log_action

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

        if req.type == "vacation":
            days = (req.end_date - req.start_date).days + 1
            await session.execute(
                update(User).where(User.id == user.id).values(vacation_used=User.vacation_used + days))

        await log_action(session, user.id, f"Заявка {request_id} ({req.type}) одобрена",
                         details=f"Одобрено: tg_id {callback.from_user.id}")
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
        await log_action(session, user.id, f"Заявка {request_id} ({req.type}) отклонена",
                         details=f"Отклонено: tg_id {callback.from_user.id}")
        await session.commit()
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


class HolidayState(StatesGroup):
    managing = State()


@router.message(Command("manage_calendar"))
async def manage_calendar(message: Message, user: User, state: FSMContext):
    if user.role != "hr":
        return
    await state.set_state(HolidayState.managing)
    await message.answer(
        "Управление производственным календарем.\nНажмите на дату для добавления/удаления выходного дня (выделяются скобками []).",
        reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.callback_query(CalCB.filter(), HolidayState.managing)
async def toggle_holiday(callback: CallbackQuery, callback_data: CalCB, state: FSMContext):
    selected, date_obj = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        async with async_session() as session:
            result = await session.execute(select(Holiday).where(Holiday.date == date_obj))
            holiday = result.scalar_one_or_none()

            if holiday:
                await session.delete(holiday)
                status = "Удален из выходных"
            else:
                session.add(Holiday(date=date_obj))
                status = "Добавлен в выходные"
            await session.commit()

        await callback.message.edit_text(
            f"Статус изменен: {date_obj.strftime('%d.%m.%Y')} - {status}",
            reply_markup=await CustomCalendar(user.language_code).start_calendar(date_obj.year, date_obj.month)
        )


@router.message(Command("set_manager"))
async def cmd_set_manager(message: Message, user: User):
    if user.role != "hr": return
    parts = message.text.split()
    if len(parts) != 3:
        return await message.answer("Формат: /set_manager <ID_сотрудника_TG> <ID_руководителя_TG>")

    emp_tg, mgr_tg = int(parts[1]), int(parts[2])
    async with async_session() as session:
        emp_res = await session.execute(select(User).where(User.tg_id == emp_tg))
        mgr_res = await session.execute(select(User).where(User.tg_id == mgr_tg))
        emp, mgr = emp_res.scalar_one_or_none(), mgr_res.scalar_one_or_none()

        if not emp or not mgr:
            return await message.answer("Пользователь не найден.")

        emp.manager_id = mgr.id
        await log_action(session, user.id, "Привязка руководителя", f"Сотрудник: {emp.id}, Руководитель: {mgr.id}")
        await session.commit()

    await message.answer(f"Сотрудник {emp.fullname} привязан к руководителю {mgr.fullname}.")