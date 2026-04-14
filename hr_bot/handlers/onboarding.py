from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.models import User
from locales.texts import MESSAGES

router = Router()


@router.message(F.text.in_(["🚀 Онбординг", "🚀 Onboarding"]))
async def start_onboarding(message: Message, user: User):
    welcome_text = (
        "👋 Добро пожаловать в команду!\n\n"
        "Здесь ты найдешь всё необходимое для успешного старта:\n"
        "1. Структура компании\n"
        "2. Правила внутреннего распорядка\n"
        "3. Полезные ссылки и доступы"
    ) if user.language_code == 'ru' else "Jamoaga xush kelibsiz!.."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Гайд новичка", url="https://example.com/handbook")],
        [InlineKeyboardButton(text="🗺 Карта офиса", callback_data="show_map")]
    ])

    await message.answer(welcome_text, reply_markup=kb)


@router.callback_query(F.data == "show_map")
async def send_map(callback: Message):
    await callback.message.answer("📍 Наш офис находится на 5 этаже. Твое место — в отделе аналитики.")
    await callback.answer()