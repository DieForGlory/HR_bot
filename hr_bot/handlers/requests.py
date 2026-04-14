from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User
from hr_bot.locales.texts import MESSAGES
from hr_bot.keyboards.main_menu import main_menu_kb, back_kb
from hr_bot.keyboards.inline import get_approval_kb
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from hr_bot.utils.logger import log_action
from hr_bot.utils.hierarchy import get_manager_tg_id
from sqlalchemy import select

router = Router()


class DayOffStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


@router.message(F.text.in_(["⏰ Отгул", "⏰ Dam olish kuni"]))
async def start_day_off(message: Message, state: FSMContext, user: User):
    await state.set_state(DayOffStates.waiting_for_date)
    await message.answer("Оформление отгула.", reply_markup=back_kb(user.language_code))
    await message.answer("Выберите дату:", reply_markup=await CustomCalendar(user.language_code).start_calendar())


@router.message(DayOffStates.waiting_for_date, F.text)
async def cancel_date(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))


@router.callback_query(CalCB.filter(), DayOffStates.waiting_for_date)
async def process_date_cal(callback: CallbackQuery, callback_data: CalCB, state: FSMContext, user: User):
    selected, date_obj = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        await state.update_data(date=date_obj)
        await state.set_state(DayOffStates.waiting_for_comment)
        await callback.message.answer("Укажите причину:")


@router.message(DayOffStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext, user: User):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.set_state(DayOffStates.waiting_for_date)
        return await message.answer("Выберите дату:",
                                    reply_markup=await CustomCalendar(user.language_code).start_calendar())

    await state.update_data(comment=message.text)
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="dayoff_confirm"),
         InlineKeyboardButton(text="❌ Отменить", callback_data="dayoff_cancel")]
    ])
    await state.set_state(DayOffStates.waiting_for_confirmation)
    await message.answer(f"Подтверждение:\nДата: {data['date']}\nПричина: {data['comment']}", reply_markup=kb)


@router.callback_query(F.data == "dayoff_confirm", DayOffStates.waiting_for_confirmation)
async def confirm_dayoff(callback: CallbackQuery, state: FSMContext, user: User, bot: Bot):
    data = await state.get_data()
    async with async_session() as session:
        new_request = Request(user_id=user.id, type="day_off", start_date=data['date'], comment=data['comment'])
        session.add(new_request)
        await session.flush()

        await log_action(session, user.id, f"Создана заявка на отгул (ID: {new_request.id})")

        targets = await get_manager_tg_id(session, user)

        for tg_id in targets:
            await bot.send_message(
                tg_id,
                f"🚀 Запрос: ОТГУЛ\nОт: {user.fullname}\nДата: {data['date']}\nПричина: {data['comment']}",
                reply_markup=get_approval_kb(new_request.id)
            )
        await session.commit()

    await state.clear()
    await callback.message.edit_text(MESSAGES[user.language_code]['request_sent'])


@router.callback_query(F.data == "dayoff_cancel", DayOffStates.waiting_for_confirmation)
async def cancel_dayoff(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    await callback.message.edit_text("Заявка отменена." if user.language_code == 'ru' else "Ariza bekor qilindi.")
    await callback.message.answer(MESSAGES[user.language_code]['main_menu'],
                                  reply_markup=main_menu_kb(user.language_code))