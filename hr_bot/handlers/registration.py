import re
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from aiogram_calendar import DialogCalendar, DialogCalendarCallback

from hr_bot.database.engine import async_session
from hr_bot.database.models import User, Department
from hr_bot.keyboards.inline import get_reg_approval_kb
from hr_bot.keyboards.main_menu import main_menu_kb
from hr_bot.locales.texts import MESSAGES

router = Router()


class RegStates(StatesGroup):
    language = State()
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

    await state.set_state(RegStates.language)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇿 O'zbekcha")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Выберите язык / Tilni tanlang:", reply_markup=kb)


@router.message(RegStates.language)
async def reg_lang(message: Message, state: FSMContext):
    lang_code = "uz" if "uz" in message.text.lower() else "ru"
    await state.update_data(language_code=lang_code)
    await state.set_state(RegStates.fullname)

    text = "Введите ФИО. Ожидается 3 слова. При отсутствии отчества будет подставлено 'XXX'." if lang_code == 'ru' else "F.I.O kiriting. 3 ta so'z kutilmoqda."
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(RegStates.fullname)
async def reg_name(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) < 2: return await message.answer("Ошибка. Требуется минимум Фамилия и Имя.")
    fullname = f"{parts[0]} {parts[1]} {parts[2] if len(parts) > 2 else 'XXX'}"
    await state.update_data(fullname=fullname)

    async with async_session() as session:
        depts = await session.execute(select(Department).where(Department.parent_id.is_(None)))
        dept_list = depts.scalars().all()

    if not dept_list:
        await state.set_state(RegStates.department)
        return await message.answer("Введите ID отдела текстом (база пуста):")

    kb = InlineKeyboardBuilder()
    for d in dept_list:
        kb.button(text=d.name, callback_data=f"dnav_{d.id}")
    kb.adjust(1)

    await state.set_state(RegStates.department)
    await message.answer("Выберите корневое подразделение:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("dnav_"), RegStates.department)
async def reg_dept_nav_cb(callback: CallbackQuery, state: FSMContext):
    dept_id = int(callback.data.split("_")[1])

    async with async_session() as session:
        children_res = await session.execute(select(Department).where(Department.parent_id == dept_id))
        children = children_res.scalars().all()

        current_dept = await session.get(Department, dept_id)

    if not children:
        await state.update_data(department_id=dept_id)
        await state.set_state(RegStates.position)
        await callback.message.edit_text(f"Подразделение: {current_dept.name}\nУкажите должность:")
        return await callback.answer()

    kb = InlineKeyboardBuilder()
    kb.button(text=f"Выбрать: {current_dept.name} (Руководитель)", callback_data=f"dsel_{dept_id}")
    for child in children:
        kb.button(text=child.name, callback_data=f"dnav_{child.id}")
    kb.adjust(1)

    await callback.message.edit_text(
        f"Текущий уровень: {current_dept.name}\nВыберите вложенный отдел или подтвердите выбор текущего уровня.",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dsel_"), RegStates.department)
async def reg_dept_sel_cb(callback: CallbackQuery, state: FSMContext):
    dept_id = int(callback.data.split("_")[1])
    await state.update_data(department_id=dept_id)
    await state.set_state(RegStates.position)

    async with async_session() as session:
        dept = await session.get(Department, dept_id)

    await callback.message.edit_text(f"Подразделение: {dept.name if dept else dept_id}\nУкажите должность:")
    await callback.answer()


@router.message(RegStates.department)
async def reg_dept_text(message: Message, state: FSMContext):
    try:
        await state.update_data(department_id=int(message.text))
    except ValueError:
        return await message.answer("Ожидается числовой ID отдела.")
    await state.set_state(RegStates.position)
    await message.answer("Укажите должность:")


@router.message(RegStates.position)
async def reg_pos(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    await state.set_state(RegStates.phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Отправьте контакт или введите номер вручную (РФ/РУз):", reply_markup=kb)


@router.message(RegStates.phone, F.contact | F.text)
async def reg_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith('+'): phone = '+' + phone
    else:
        phone_clean = re.sub(r'\D', '', message.text)
        is_ru = (phone_clean.startswith(('7', '8')) and len(phone_clean) == 11)
        is_uz = (phone_clean.startswith('998') and len(phone_clean) == 12)

        if not (is_ru or is_uz):
            return await message.answer("Ошибка формата. Ожидается номер РФ (+7...) или РУз (+998...).")
        phone = f"+{phone_clean}" if not phone_clean.startswith('8') else f"+7{phone_clean[1:]}"

    await state.update_data(phone=phone)
    await state.set_state(RegStates.birth_date)

    data = await state.get_data()
    locale = 'ru_RU' if data.get('language_code') == 'ru' else 'uz_UZ'

    await message.answer(
        "Выберите дату рождения:" if locale == 'ru_RU' else "Tug'ilgan sanani tanlang:",
        reply_markup=await DialogCalendar(locale=locale).start_calendar()
    )


@router.callback_query(DialogCalendarCallback.filter(), RegStates.birth_date)
async def process_calendar(callback_query: CallbackQuery, callback_data: DialogCalendarCallback, state: FSMContext):
    data = await state.get_data()
    locale = 'ru_RU' if data.get('language_code') == 'ru' else 'uz_UZ'

    selected, date_obj = await DialogCalendar(locale=locale).process_selection(callback_query, callback_data)

    if selected:
        await callback_query.message.delete()
        await state.update_data(birth_date=date_obj.strftime("%d.%m.%Y"))
        await state.set_state(RegStates.car_info)

        text = "Укажите номер и марку авто (или 'нет'):" if locale == 'ru_RU' else "Avtomobil raqami va rusumini kiriting (yoki 'yoq'):"
        await callback_query.message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(RegStates.car_info)
async def reg_car(message: Message, state: FSMContext):
    await state.update_data(car_info=message.text)
    await state.set_state(RegStates.face_id_photo)
    await message.answer("Загрузите фото для Face ID (только JPG/PNG):")


@router.message(RegStates.face_id_photo, F.photo | F.document.mime_type.in_(["image/jpeg", "image/png"]))
async def reg_photo(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id if message.photo else message.document.file_id
    data = await state.get_data()

    async with async_session() as session:
        dept_id = data.get('department_id')
        dept_name = "Не указан"
        if dept_id:
            dept = await session.get(Department, dept_id)
            if dept:
                dept_name = dept.name

        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        db_user = result.scalars().first()

        if db_user:
            db_user.fullname = data['fullname']
            db_user.username = message.from_user.username
            db_user.department_id = dept_id
            db_user.position = data['position']
            db_user.phone = data['phone']
            db_user.birth_date = data['birth_date']
            db_user.car_info = data['car_info']
            db_user.face_id_photo = photo_id
            db_user.language_code = data.get('language_code', 'ru')
            db_user.is_active = False
        else:
            db_user = User(
                tg_id=message.from_user.id,
                fullname=data['fullname'],
                username=message.from_user.username,
                department_id=dept_id,
                position=data['position'],
                phone=data['phone'],
                birth_date=data['birth_date'],
                car_info=data['car_info'],
                face_id_photo=photo_id,
                language_code=data.get('language_code', 'ru'),
                is_active=False
            )
            session.add(db_user)

        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            return await message.answer("Ошибка: этот номер телефона уже привязан к другому аккаунту.")

        hrs = await session.execute(select(User).where(User.role == "hr"))
        caption = f"📝 Новая заявка:\nФИО: {data['fullname']}\nОтдел: {dept_name}\nТел: {data['phone']}\nДР: {data['birth_date']}"

        for hr in hrs.scalars():
            if message.photo:
                await bot.send_photo(hr.tg_id, photo_id, caption=caption,
                                     reply_markup=get_reg_approval_kb(db_user.tg_id))
            else:
                await bot.send_document(hr.tg_id, photo_id, caption=caption,
                                        reply_markup=get_reg_approval_kb(db_user.tg_id))
        await session.commit()

    await state.clear()
    text = "Анкета отправлена на проверку." if data.get('language_code') == 'ru' else "Anketa tekshirishga yuborildi."
    await message.answer(text)


@router.message(RegStates.face_id_photo)
async def invalid_reg_photo(message: Message):
    await message.answer("Ошибка: формат не поддерживается. Принимаются только файлы форматов JPG или PNG.")