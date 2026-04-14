from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from hr_bot.database.engine import async_session
from hr_bot.database.models import User, SystemConfig
from sqlalchemy import select
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
router = Router()


@router.message(F.text.in_(["🚀 Онбординг", "🚀 Onboarding"]))
async def start_onboarding(message: Message, user: User):
    async with async_session() as session:
        res = await session.execute(select(SystemConfig).where(SystemConfig.key == "onboarding_text"))
        config_obj = res.scalar_one_or_none()
        text = config_obj.value if config_obj else "Базовый гайд: [ссылка отсутствует]"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺 Карта офиса", callback_data="show_map")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "show_map")
async def send_map(callback: CallbackQuery):
    await callback.message.answer("📍 Наш офис находится на 5 этаже.")
    await callback.answer()


@router.message(Command("edit_onboarding"))
async def cmd_edit_onboarding(message: Message, user: User):
    if user.role != "hr": return
    new_text = message.text.replace("/edit_onboarding", "").strip()
    if not new_text:
        return await message.answer("Отправьте текст после команды. Поддерживается HTML.")

    async with async_session() as session:
        res = await session.execute(select(SystemConfig).where(SystemConfig.key == "onboarding_text"))
        cfg = res.scalar_one_or_none()
        if cfg:
            cfg.value = new_text
        else:
            session.add(SystemConfig(key="onboarding_text", value=new_text))
        await session.commit()
    await message.answer("Раздел онбординга обновлен.")