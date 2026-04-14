from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.engine import async_session
from database.models import Request, User as DBUser
from keyboards.main_menu import main_menu_kb, back_kb
from keyboards.inline import get_approval_kb
from locales.texts import MESSAGES
from sqlalchemy import select
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()

class VacationStates(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()

@router.message(F.text.in_(["📄 Отпуск", "📄 Ta'til"]))
async def start_vacation(message: Message, state: FSMContext, user: DBUser):
    await state.set_state(VacationStates.waiting_for_start)
    await message.answer("Оформление отпуска.", reply_markup=back_kb(user.language_code))
    await message.answer("Выберите дату начала:", reply_markup=await SimpleCalendar().start_calendar())

@router.message(VacationStates.waiting_for_start, F.text)
async def cancel_vac_start(message: Message, state: FSMContext, user: DBUser):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))

@router.callback_query(SimpleCalendarCallback.filter(), VacationStates.waiting_for_start)
async def process_vac_start_cal(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(start_date=date.date())
        await state.set_state(VacationStates.waiting_for_end)
        await callback.message.answer("Выберите дату окончания:", reply_markup=await SimpleCalendar().start_calendar())

@router.message(VacationStates.waiting_for_end, F.text)
async def back_vac_end(message: Message, state: FSMContext, user: DBUser):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(VacationStates.waiting_for_start)
        await message.answer("Выберите дату начала:", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(SimpleCalendarCallback.filter(), VacationStates.waiting_for_end)
async def process_vac_end_cal(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext, user: DBUser, bot: Bot):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        data = await state.get_data()
        start_date = data['start_date']
        end_date = date.date()

        if end_date <= start_date:
            await callback.message.answer("Ошибка: Дата окончания должна быть позже даты начала.\nВыберите заново:", reply_markup=await SimpleCalendar().start_calendar())
            return

        async with async_session() as session:
            new_req = Request(user_id=user.id, type="vacation", start_date=start_date, end_date=end_date)
            session.add(new_req)
            await session.flush()

            hrs = await session.execute(select(DBUser).where(DBUser.role == "hr"))
            for hr in hrs.scalars():
                await bot.send_message(
                    hr.tg_id,
                    f"🚀 Заявка: ОТПУСК\nОт: {user.fullname}\nПериод: {start_date} - {end_date}",
                    reply_markup=get_approval_kb(new_req.id)
                )
            await session.commit()

        await state.clear()
        await callback.message.answer(MESSAGES[user.language_code]['request_sent'], reply_markup=main_menu_kb(user.language_code))