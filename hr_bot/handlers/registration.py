import re
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import User
from hr_bot.keyboards.inline import get_reg_approval_kb
from hr_bot.keyboards.main_menu import main_menu_kb
from hr_bot.locales.texts import MESSAGES
from hr_bot.utils.custom_calendar import CustomCalendar, CalCB
from sqlalchemy import select

router = Router()

class RegStates(StatesGroup):
    fullname = State()
    department = State()
    position = State()
    phone = State()
    birth_date = State()
    car_info = State()
    face_id_photo = State()

@router.message(CommandStart())
async def reg_start(message: Message, state: FSMContext, user: User = None):
    if user and user.is_active:
        lang = user.language_code
        return await message.answer(MESSAGES[lang]['main_menu'], reply_markup=main_menu_kb(lang))

    await state.set_state(RegStates.fullname)
    await message.answer(
        "Введите ФИО. Ожидается 3 слова. При отсутствии отчества будет подставлено 'XXX'.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(RegStates.fullname)
async def reg_name(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) < 2:
        return await message.answer("Ошибка. Требуется минимум Фамилия и Имя.")

    fullname = f"{parts[0]} {parts[1]} {parts[2] if len(parts) > 2 else 'XXX'}"
    await state.update_data(fullname=fullname)
    await state.set_state(RegStates.department)
    await message.answer("Укажите Управление/Отдел:")

@router.message(RegStates.department)
async def reg_dept(message: Message, state: FSMContext):
    await state.update_data(department=message.text)
    await state.set_state(RegStates.position)
    await message.answer("Укажите должность:")

@router.message(RegStates.position)
async def reg_pos(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    await state.set_state(RegStates.phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Отправьте контакт или введите номер вручную (РФ/РУз):", reply_markup=kb)

@router.message(RegStates.phone, F.contact | F.text)
async def reg_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
    else:
        phone_clean = re.sub(r'\D', '', message.text)
        is_ru = (phone_clean.startswith(('7', '8')) and len(phone_clean) == 11)
        is_uz = (phone_clean.startswith('998') and len(phone_clean) == 12)

        if not (is_ru or is_uz):
            return await message.answer("Ошибка формата. Ожидается номер РФ (+7...) или РУз (+998...).")

        phone = f"+{phone_clean}" if not phone_clean.startswith('8') else f"+7{phone_clean[1:]}"

    await state.update_data(phone=phone)
    await state.set_state(RegStates.birth_date)
    await message.answer("Выберите дату рождения:", reply_markup=await CustomCalendar().start_calendar())

@router.callback_query(CalCB.filter(), RegStates.birth_date)
async def process_calendar(callback_query: CallbackQuery, callback_data: CalCB, state: FSMContext):
    selected, date_obj = await CustomCalendar().process_selection(callback_query, callback_data)
    if selected:
        await state.update_data(birth_date=date_obj.strftime("%d.%m.%Y"))
        await state.set_state(RegStates.car_info)
        await callback_query.message.answer("Укажите номер и марку авто (или 'нет'):", reply_markup=ReplyKeyboardRemove())

@router.message(RegStates.car_info)
async def reg_car(message: Message, state: FSMContext):
    await state.update_data(car_info=message.text)
    await state.set_state(RegStates.face_id_photo)
    await message.answer("Загрузите фото для Face ID:")

@router.message(RegStates.face_id_photo, F.photo)
async def reg_photo(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    async with async_session() as session:
        new_user = User(
            tg_id=message.from_user.id,
            fullname=data['fullname'],
            username=message.from_user.username,
            department=data['department'],
            position=data['position'],
            phone=data['phone'],
            birth_date=data['birth_date'],
            car_info=data['car_info'],
            face_id_photo=photo_id,
            is_active=False
        )
        session.add(new_user)
        await session.flush()

        hrs = await session.execute(select(User).where(User.role == "hr"))
        for hr in hrs.scalars():
            await bot.send_photo(
                hr.tg_id,
                photo_id,
                caption=f"📝 Новая заявка:\nФИО: {data['fullname']}\nОтдел: {data['department']}\nТел: {data['phone']}\nДР: {data['birth_date']}",
                reply_markup=get_reg_approval_kb(new_user.tg_id)
            )
        await session.commit()

    await state.clear()
    await message.answer("Анкета отправлена на проверку.")