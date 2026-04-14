from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.engine import async_session
from database.models import Request, User
from locales.texts import MESSAGES
from keyboards.main_menu import main_menu_kb, back_kb
from keyboards.inline import get_approval_kb
from sqlalchemy import select
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()

class DayOffStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_comment = State()

@router.message(F.text.in_(["⏰ Отгул", "⏰ Dam olish kuni"]))
async def start_day_off(message: Message, state: FSMContext, user: User):
    await state.set_state(DayOffStates.waiting_for_date)
    await message.answer("Оформление отгула.", reply_markup=back_kb(user.language_code))
    await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())

@router.message(DayOffStates.waiting_for_date, F.text)
async def cancel_date(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))

@router.callback_query(SimpleCalendarCallback.filter(), DayOffStates.waiting_for_date)
async def process_date_cal(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(date=date.date())
        await state.set_state(DayOffStates.waiting_for_comment)
        await callback.message.answer("Укажите причину:")

@router.message(DayOffStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext, user: User, bot: Bot):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(DayOffStates.waiting_for_date)
        return await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())

    data = await state.get_data()
    async with async_session() as session:
        new_request = Request(user_id=user.id, type="day_off", start_date=data['date'], comment=message.text)
        session.add(new_request)
        await session.flush()

        hrs = await session.execute(select(User).where(User.role == "hr"))
        for hr in hrs.scalars():
            await bot.send_message(
                hr.tg_id,
                f"🚀 Запрос: ОТГУЛ\nОт: {user.fullname}\nДата: {data['date']}\nПричина: {message.text}",
                reply_markup=get_approval_kb(new_request.id)
            )
        await session.commit()

    await state.clear()
    await message.answer(MESSAGES[user.language_code]['request_sent'], reply_markup=main_menu_kb(user.language_code))