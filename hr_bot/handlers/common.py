from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from hr_bot.keyboards.main_menu import main_menu_kb
from hr_bot.database.models import User, Request
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from hr_bot.database.engine import async_session
from hr_bot.utils.logger import log_action
from sqlalchemy import update, select

router = Router()


class ProfileStates(StatesGroup):
    waiting_for_car = State()
    waiting_for_phone = State()
    waiting_for_photo = State()


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


@router.message(Command("language"))
async def cmd_language(message: Message, user: User):
    new_lang = "uz" if user.language_code == "ru" else "ru"
    async with async_session() as session:
        await session.execute(update(User).where(User.id == user.id).values(language_code=new_lang))
        await log_action(session, user.id, f"Изменил язык на {new_lang}")
        await session.commit()

    text = "Язык изменен на Русский." if new_lang == "ru" else "Til O'zbekchaga o'zgartirildi."
    await message.answer(text, reply_markup=main_menu_kb(new_lang))


@router.message(Command("history"))
async def cmd_history(message: Message, user: User):
    async with async_session() as session:
        res = await session.execute(
            select(Request).where(Request.user_id == user.id).order_by(Request.id.desc()).limit(10))
        reqs = res.scalars().all()
        await log_action(session, user.id, "Запрос истории заявок")
        await session.commit()

    if not reqs:
        return await message.answer("История пуста." if user.language_code == 'ru' else "Tarix bo'sh.")

    lines = []
    for r in reqs:
        date_str = r.start_date.strftime('%d.%m.%Y')
        lines.append(f"[{r.id}] {r.type.upper()} | {date_str} | Статус: {r.status}")

    await message.answer("\n".join(lines))


@router.message(Command("profile"))
async def cmd_profile(message: Message, user: User):
    text = f"👤 Ваш профиль:\nФИО: {user.fullname}\nОтдел: {user.department}\nТелефон: {user.phone}\nАвто: {user.car_info}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Изменить авто", callback_data="edit_car")],
        [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_phone")],
        [InlineKeyboardButton(text="📸 Обновить Face ID", callback_data="edit_photo")]
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("edit_"))
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    if action == "car":
        await state.set_state(ProfileStates.waiting_for_car)
        await callback.message.answer("Введите новые данные автомобиля (марка, госномер):")
    elif action == "phone":
        await state.set_state(ProfileStates.waiting_for_phone)
        await callback.message.answer("Введите новый номер телефона:")
    elif action == "photo":
        await state.set_state(ProfileStates.waiting_for_photo)
        await callback.message.answer("Загрузите новое фото:")
    await callback.answer()


@router.message(ProfileStates.waiting_for_car)
async def save_car(message: Message, state: FSMContext, user: User):
    async with async_session() as session:
        await session.execute(update(User).where(User.id == user.id).values(car_info=message.text))
        await log_action(session, user.id, "Обновлен автомобиль")
        await session.commit()
    await state.clear()
    await message.answer("Данные автомобиля обновлены.")


@router.message(ProfileStates.waiting_for_phone)
async def save_phone(message: Message, state: FSMContext, user: User):
    async with async_session() as session:
        await session.execute(update(User).where(User.id == user.id).values(phone=message.text))
        await log_action(session, user.id, "Обновлен телефон")
        await session.commit()
    await state.clear()
    await message.answer("Номер телефона обновлен.")


@router.message(ProfileStates.waiting_for_photo, F.photo)
async def save_photo(message: Message, state: FSMContext, user: User):
    photo_id = message.photo[-1].file_id
    async with async_session() as session:
        await session.execute(update(User).where(User.id == user.id).values(face_id_photo=photo_id))
        await log_action(session, user.id, "Обновлено фото Face ID")
        await session.commit()
    await state.clear()
    await message.answer("Фото Face ID обновлено.")


@router.callback_query(CalCB.filter(), default_state)
async def process_generic_calendar(callback: CallbackQuery, callback_data: CalCB, user: User):
    selected, _ = await CustomCalendar(user.language_code).process_selection(callback, callback_data)
    if selected:
        msg = "Для управления используйте /manage_calendar" if user.role == "hr" else "Просмотр календаря"
        await callback.answer(msg)