from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User
from hr_bot.keyboards.main_menu import main_menu_kb, back_kb
from hr_bot.keyboards.inline import get_approval_kb
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from hr_bot.utils.logger import log_action
from hr_bot.utils.hierarchy import get_manager_tg_id
from sqlalchemy import select

router = Router()


class SickLeaveStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_doc = State()


@router.message(F.text.in_(["🏥 Больничный", "🏥 Kasallik varaqasi"]))
async def start_sick_leave(message: Message, state: FSMContext, user: User):
    await state.set_state(SickLeaveStates.waiting_for_date)
    await message.answer("Оформление больничного.", reply_markup=back_kb(user.language_code))
    await message.answer("Выберите дату начала:",
                         reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.message(SickLeaveStates.waiting_for_date, F.text)
async def cancel_sick_date(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))


@router.callback_query(CalCB.filter(), SickLeaveStates.waiting_for_date)
async def process_sick_date_cal(callback: CallbackQuery, callback_data: CalCB, state: FSMContext, user: User):
    selected, date_obj = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        await state.update_data(date=date_obj)
        await state.set_state(SickLeaveStates.waiting_for_doc)
        await callback.message.answer("Загрузите фото справки или PDF-документ:")


@router.message(SickLeaveStates.waiting_for_doc, F.text)
async def back_sick_doc(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(SickLeaveStates.waiting_for_date)
        await message.answer("Выберите дату начала:",
                             reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.message(SickLeaveStates.waiting_for_doc, F.photo | F.document)
async def process_sick_doc(message: Message, state: FSMContext, user: User, bot: Bot):
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    is_photo = bool(message.photo)

    async with async_session() as session:
        new_request = Request(user_id=user.id, type="sick_leave", start_date=data['date'], file_id=file_id)
        session.add(new_request)
        await session.flush()

        await log_action(session, user.id, f"Создана заявка на больничный (ID: {new_request.id})")

        targets = await get_manager_tg_id(session, user)

        caption = f"🏥 Больничный: {user.fullname}\nС {data['date']}"
        kb = get_approval_kb(new_request.id)

        for tg_id in targets:
            if is_photo:
                await bot.send_photo(tg_id, file_id, caption=caption, reply_markup=kb)
            else:
                await bot.send_document(tg_id, file_id, caption=caption, reply_markup=kb)
        await session.commit()

    await state.clear()
    await message.answer("Данные переданы.", reply_markup=main_menu_kb(user.language_code))