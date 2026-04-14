from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from hr_bot.database.engine import async_session
from hr_bot.database.models import User
from hr_bot.locales.texts import MESSAGES
from hr_bot.keyboards.main_menu import main_menu_kb, back_kb
router = Router()

class HRQuestion(StatesGroup):
    waiting_for_text = State()

@router.message(F.text.in_(["❓ Вопрос HR", "❓ HRga savol"]))
async def ask_hr(message: Message, state: FSMContext, user: User):
    await state.set_state(HRQuestion.waiting_for_text)
    await message.answer("Введите ваш вопрос:", reply_markup=back_kb(user.language_code))

@router.message(HRQuestion.waiting_for_text)
async def forward_to_hr(message: Message, state: FSMContext, user: User, bot: Bot):
    if message.text == MESSAGES[user.language_code]['back']:
        await state.clear()
        return await message.answer(MESSAGES[user.language_code]['main_menu'], reply_markup=main_menu_kb(user.language_code))

    async with async_session() as session:
        hrs = await session.execute(select(User).where(User.role == "hr"))
        for hr in hrs.scalars():
            await bot.send_message(
                hr.tg_id,
                f"✉️ Вопрос от {user.fullname} (@{message.from_user.username}):\n\n{message.text}"
            )
    await state.clear()
    await message.answer("Ваш вопрос передан.", reply_markup=main_menu_kb(user.language_code))