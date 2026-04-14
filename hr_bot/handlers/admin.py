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
from hr_bot.database.models import Department

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
async def toggle_holiday(callback: CallbackQuery, callback_data: CalCB, state: FSMContext, user: User):
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


@router.message(Command("add_dept"))
async def cmd_add_dept(message: Message, user: User):
    if user.role != "hr": return
    name = message.text.replace("/add_dept", "").strip()
    if not name: return await message.answer("Формат: /add_dept <Название>")
    async with async_session() as session:
        session.add(Department(name=name))
        await log_action(session, user.id, f"Создано подразделение: {name}")
        await session.commit()
    await message.answer("Подразделение создано.")


@router.message(Command("link_dept"))
async def cmd_link_dept(message: Message, user: User):
    if user.role != "hr": return
    try:
        parts = message.text.split()
        child_id, parent_id = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return await message.answer("Формат: /link_dept <ID_Дочернего> <ID_Родительского>")

    async with async_session() as session:
        await session.execute(update(Department).where(Department.id == child_id).values(parent_id=parent_id))
        await log_action(session, user.id, f"Подразделение {child_id} подчинено {parent_id}")
        await session.commit()
    await message.answer("Связь иерархии установлена.")


@router.message(Command("set_head"))
async def cmd_set_head(message: Message, user: User):
    if user.role != "hr": return
    try:
        parts = message.text.split()
        dept_id, tg_id = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return await message.answer("Формат: /set_head <ID_Подразделения> <TG_ID_Руководителя>")

    async with async_session() as session:
        target_user = await session.execute(select(User).where(User.tg_id == tg_id))
        usr = target_user.scalar_one_or_none()
        if not usr: return await message.answer("Пользователь не найден.")

        await session.execute(update(Department).where(Department.id == dept_id).values(head_id=usr.id))
        await session.execute(update(User).where(User.id == usr.id).values(department_id=dept_id))
        await log_action(session, user.id, f"Пользователь {usr.id} назначен главой отдела {dept_id}")
        await session.commit()
    await message.answer("Руководитель назначен.")


@router.message(Command("structure"))
async def cmd_structure(message: Message, user: User):
    if user.role != "hr": return
    async with async_session() as session:
        depts = await session.execute(select(Department))
        dept_list = depts.scalars().all()
        users_res = await session.execute(select(User))
        users = {u.id: u for u in users_res.scalars().all()}

    out = []
    for d in dept_list:
        head_name = users[d.head_id].fullname if d.head_id and d.head_id in users else "Отсутствует"
        parent = f" | Родитель: {d.parent_id}" if d.parent_id else " | (Корневое)"
        out.append(f"[ID: {d.id}] {d.name} | Глава: {head_name}{parent}")
    await message.answer("\n".join(out) if out else "Структура не задана.")


@router.message(Command("admin_help"))
async def cmd_admin_help(message: Message, user: User):
    if user.role != "hr":
        return

    help_text = (
        "🛠 **Панель команд администратора (HR)**\n\n"
        "**Организационная структура:**\n"
        "• `/users` — Получить список всех сотрудников и их TG ID (нажми на ID для копирования).\n"
        "• `/add_dept <Название>` — Создать новое подразделение.\n"
        "• `/link_dept <ID_Дочернего> <ID_Родительского>` — Установить подчинение отделов.\n"
        "• `/set_head <ID_Подразделения> <TG_ID_Руководителя>` — Назначить руководителя отдела.\n"
        "• `/structure` — Показать текущее дерево подразделений и руководителей.\n"
        "• `/set_manager <ID_сотрудника_TG> <ID_руководителя_TG>` — Персональная привязка сотрудника к руководителю (вне структуры).\n\n"
        "**Управление контентом:**\n"
        "• `/manage_calendar` — Открыть редактор производственного календаря.\n"
        "• `/edit_onboarding <Текст>` — Изменить приветственный текст раздела 'Онбординг' (поддерживает HTML).\n\n"
        "**Опросы:**\n"
        "• `/create_survey` — Запустить мастер создания нового опроса.\n"
        "• `/survey_results <ID_опроса>` — Выгрузить ответы сотрудников по конкретному опросу."
    )

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("users"))
async def cmd_users(message: Message, user: User):
    if user.role != "hr":
        return

    async with async_session() as session:
        res = await session.execute(select(User).where(User.is_active == True))
        users = res.scalars().all()

    if not users:
        return await message.answer("Нет активных сотрудников.")

    lines = ["👥 <b>Список сотрудников:</b>\n"]
    for u in users:
        dept = f"Отдел ID: {u.department_id}" if u.department_id else "Без отдела"
        # Тег <code> позволяет скопировать ID по клику в Telegram
        lines.append(f"• {u.fullname} | {dept} | TG ID: <code>{u.tg_id}</code>")

    text = "\n".join(lines)

    # Разбивка сообщения, если текст превышает лимит Telegram (4096 символов)
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await message.answer(text[x:x + 4000], parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")