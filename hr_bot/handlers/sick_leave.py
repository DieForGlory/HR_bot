from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.engine import async_session
from database.models import Request, User
from keyboards.main_menu import main_menu_kb, back_kb
from keyboards.inline import get_approval_kb
from locales.texts import MESSAGES
from sqlalchemy import select
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()

class SickLeaveStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_doc = State()

@router.message(F.text.in_(["🏥 Больничный", "🏥 Kasallik varaqasi"]))
async def start_sick_leave(message: Message, state: FSMContext, user: User):
    await state.set_state(SickLeaveStates.waiting_for_date)
    await message.answer("Оформление больничного.", reply_markup=back_kb(user.language_code))
    await message.answer("Выберите дату начала:", reply_markup=await SimpleCalendar().start_calendar())

@router.message(SickLeaveStates.waiting_for_date, F.text)
async def cancel_sick_date(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))

@router.callback_query(SimpleCalendarCallback.filter(), SickLeaveStates.waiting_for_date)
async def process_sick_date_cal(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(date=date.date())
        await state.set_state(SickLeaveStates.waiting_for_doc)
        await callback.message.answer("Загрузите фото справки или PDF-документ:")

@router.message(SickLeaveStates.waiting_for_doc, F.text)
async def back_sick_doc(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(SickLeaveStates.waiting_for_date)
        await message.answer("Выберите дату начала:", reply_markup=await SimpleCalendar().start_calendar())

@router.message(SickLeaveStates.waiting_for_doc, F.photo | F.document)
async def process_sick_doc(message: Message, state: FSMContext, user: User, bot: Bot):
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    is_photo = bool(message.photo)

    async with async_session() as session:
        new_request = Request(
            user_id=user.id,
            type="sick_leave",
            start_date=data['date'],
            file_id=file_id
        )
        session.add(new_request)
        await session.flush()

        hrs = await session.execute(select(User).where(User.role == "hr"))
        caption = f"🏥 Больничный: {user.fullname}\nС {data['date']}"
        kb = get_approval_kb(new_request.id)

        for hr in hrs.scalars():
            if is_photo:
                await bot.send_photo(hr.tg_id, file_id, caption=caption, reply_markup=kb)
            else:
                await bot.send_document(hr.tg_id, file_id, caption=caption, reply_markup=kb)
        await session.commit()

    await state.clear()
    await message.answer("Данные переданы.", reply_markup=main_menu_kb(user.language_code))