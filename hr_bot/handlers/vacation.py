from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User as DBUser
from hr_bot.keyboards.main_menu import main_menu_kb, back_kb
from hr_bot.keyboards.inline import get_approval_kb
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from hr_bot.utils.logger import log_action
from sqlalchemy import select

router = Router()


class VacationStates(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()


@router.message(F.text.in_(["📄 Отпуск", "📄 Ta'til"]))
async def start_vacation(message: Message, user: DBUser):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подать заявку" if user.language_code == 'ru' else "Ariza berish",
                              callback_data="vac_apply")],
        [InlineKeyboardButton(text="Мои заявки" if user.language_code == 'ru' else "Mening arizalarim",
                              callback_data="vac_history")]
    ])
    await message.answer("Управление отпусками:" if user.language_code == 'ru' else "Ta'tillarni boshqarish:",
                         reply_markup=kb)


@router.callback_query(F.data == "vac_history")
async def vac_history(callback: CallbackQuery, user: DBUser):
    async with async_session() as session:
        await log_action(session, user.id, "Просмотр истории отпусков")
        res = await session.execute(select(Request).where(Request.user_id == user.id, Request.type == "vacation"))
        reqs = res.scalars().all()
        await session.commit()

    if not reqs:
        await callback.message.answer("Заявки отсутствуют." if user.language_code == 'ru' else "Arizalar yo'q.")
    else:
        msg = "\n".join([f"📅 {r.start_date} - {r.end_date} | Статус: {r.status}" for r in reqs])
        await callback.message.answer(msg)
    await callback.answer()


@router.callback_query(F.data == "vac_apply")
async def vac_apply(callback: CallbackQuery, state: FSMContext, user: DBUser):
    remain = user.vacation_total - user.vacation_used
    if remain <= 0:
        return await callback.message.answer(
            "Отказ: Лимит дней отпуска исчерпан." if user.language_code == 'ru' else "Rad etildi: Ta'til kunlari tugagan.")

    await state.set_state(VacationStates.waiting_for_start)
    await callback.message.answer("Оформление отпуска.", reply_markup=back_kb(user.language_code))
    await callback.message.answer("Выберите дату начала:",
                                  reply_markup=await CustomCalendar(user.language_code).start_calendar())
    await callback.answer()


@router.message(VacationStates.waiting_for_start, F.text)
async def cancel_vac_start(message: Message, state: FSMContext, user: DBUser):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))


@router.callback_query(CalCB.filter(), VacationStates.waiting_for_start)
async def process_vac_start_cal(callback: CallbackQuery, callback_data: CalCB, state: FSMContext, user: DBUser):
    selected, date_obj = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        await state.update_data(start_date=date_obj)
        await state.set_state(VacationStates.waiting_for_end)
        await callback.message.answer("Выберите дату окончания:",
                                      reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.message(VacationStates.waiting_for_end, F.text)
async def back_vac_end(message: Message, state: FSMContext, user: DBUser):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(VacationStates.waiting_for_start)
        await message.answer("Выберите дату начала:",
                             reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.callback_query(CalCB.filter(), VacationStates.waiting_for_end)
async def process_vac_end_cal(callback: CallbackQuery, callback_data: CalCB, state: FSMContext, user: DBUser, bot: Bot):
    selected, date_obj = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        data = await state.get_data()
        start_date = data['start_date']
        end_date = date_obj

        if end_date <= start_date:
            await callback.message.answer("Ошибка: Дата окончания должна быть позже даты начала.\nВыберите заново:",
                                          reply_markup=await CustomCalendar(user.language_code).start_calendar())
            return

        async with async_session() as session:
            new_req = Request(user_id=user.id, type="vacation", start_date=start_date, end_date=end_date)
            session.add(new_req)
            await session.flush()

            await log_action(session, user.id, f"Создана заявка на отпуск (ID: {new_req.id})")

            # Маршрутизация Руководителю, если назначен. Иначе — HR.
            targets = []
            if user.manager_id:
                mgr = await session.get(DBUser, user.manager_id)
                if mgr: targets.append(mgr.tg_id)

            if not targets:
                hrs = await session.execute(select(DBUser).where(DBUser.role == "hr"))
                targets = [hr.tg_id for hr in hrs.scalars()]

            for tg_id in targets:
                await bot.send_message(tg_id,
                                       f"🚀 Заявка: ОТПУСК\nОт: {user.fullname}\nПериод: {start_date} - {end_date}",
                                       reply_markup=get_approval_kb(new_req.id))
            await session.commit()

        await state.clear()
        await callback.message.answer(MESSAGES[user.language_code]['request_sent'],
                                      reply_markup=main_menu_kb(user.language_code))