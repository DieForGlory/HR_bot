from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from hr_bot.keyboards.main_menu import main_menu_kb
from hr_bot.database.models import User
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar
from hr_bot.database.engine import async_session
from hr_bot.utils.logger import log_action

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User = None):
    lang = user.language_code if user else "ru"
    await message.answer(MESSAGES[lang]['main_menu'], reply_markup=main_menu_kb(lang))


@router.message(F.text.in_(["📚 FAQ", "📚 Savol-javob"]))
async def cmd_faq(message: Message, user: User):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Когда зарплата?" if user.language_code == 'ru' else "Qachon oylik?",
                              callback_data="faq_salary")],
        [InlineKeyboardButton(
            text="Сколько дней отпуска осталось?" if user.language_code == 'ru' else "Ta'til qoldig'i?",
            callback_data="faq_vacation")]
    ])
    async with async_session() as session:
        await log_action(session, user.id, "Открыл FAQ")
        await session.commit()
    await message.answer("Раздел FAQ:" if user.language_code == 'ru' else "FAQ bo'limi:", reply_markup=kb)


@router.callback_query(F.data.startswith("faq_"))
async def process_faq(callback: CallbackQuery, user: User):
    if callback.data == "faq_salary":
        text = "Зарплата: 5 и 20 числа каждого месяца." if user.language_code == 'ru' else "Oylik: har oyning 5 va 20 sanalarida."
    elif callback.data == "faq_vacation":
        remain = user.vacation_total - user.vacation_used
        text = f"Остаток отпуска: {remain} дней." if user.language_code == 'ru' else f"Ta'til qoldig'i: {remain} kun."

    await callback.message.answer(text)
    await callback.answer()


@router.message(F.text.in_(["📅 Календарь", "📅 Kalendar"]))
async def cmd_calendar(message: Message, user: User):
    await message.answer("Производственный календарь\n(Нерабочие дни выделены скобками []):",
                         reply_markup=await CustomCalendar(user.language_code).start_calendar())