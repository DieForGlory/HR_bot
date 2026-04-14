from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from hr_bot.keyboards.main_menu import main_menu_kb
from hr_bot.database.models import User
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, user: User = None):
    # Если пользователь новый, используется 'ru'
    lang = user.language_code if user else "ru"
    await message.answer(
        MESSAGES[lang]['main_menu'],
        reply_markup=main_menu_kb(lang)
    )

@router.message(F.text.in_(["📚 FAQ", "📚 Savol-javob"]))
async def cmd_faq(message: Message, user: User):
    lang = user.language_code
    faq_text = (
        "**Зарплата:** 5 и 20 числа каждого месяца.\n"
        "**Отпуск:** необходимо подать заявку за 2 недели."
    ) if lang == 'ru' else "**Oylik:** har oyning 5 va 20 sanalarida.\n**Ta'til:** 2 hafta oldin ariza berish kerak."
    await message.answer(faq_text, parse_mode="Markdown")

@router.message(F.text.in_(["📅 Календарь", "📅 Kalendar"]))
async def cmd_calendar(message: Message):
    await message.answer("Производственный календарь\n(Нерабочие дни выделены скобками []):", reply_markup=await CustomCalendar().start_calendar())