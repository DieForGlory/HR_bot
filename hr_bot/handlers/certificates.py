from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import Request, User
from hr_bot.locales.texts import MESSAGES
from hr_bot.keyboards.main_menu import main_menu_kb
from sqlalchemy import select
from datetime import datetime

router = Router()


class CertStates(StatesGroup):
    waiting_for_type = State()


@router.message(F.text.in_(["💰 Справки", "💰 Ma'lumotnomalar"]))
async def start_cert(message: Message, state: FSMContext, user: User):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Справка о доходах"), KeyboardButton(text="С места работы")],
        [KeyboardButton(text=MESSAGES[user.language_code]['back'])]
    ], resize_keyboard=True)
    await state.set_state(CertStates.waiting_for_type)
    await message.answer("Выберите тип справки:", reply_markup=kb)


@router.message(CertStates.waiting_for_type)
async def process_cert(message: Message, state: FSMContext, user: User, bot: Bot):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        return await message.answer(MESSAGES[user.language_code]['main_menu'],
                                    reply_markup=main_menu_kb(user.language_code))

    async with async_session() as session:
        new_req = Request(user_id=user.id, type="certificate", start_date=datetime.now().date(), comment=message.text)
        session.add(new_req)
        await session.flush()

        hrs = await session.execute(select(User).where(User.role == "hr"))
        for hr in hrs.scalars():
            await bot.send_message(hr.tg_id, f"💰 Запрос справки ({message.text}) от {user.fullname}")
        await session.commit()

    await state.clear()
    await message.answer("Запрос принят.", reply_markup=main_menu_kb(user.language_code))