from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from hr_bot.database.engine import async_session
from hr_bot.database.models import Survey, SurveyQuestion, SurveyAnswer, User
from sqlalchemy import select
from aiogram.filters import Command

router = Router()


class SurveyStates(StatesGroup):
    answering = State()


@router.message(F.text.in_(["📊 Опросы", "📊 So'rovnomalar"]))
async def list_surveys(message: Message, user: User):
    async with async_session() as session:
        result = await session.execute(select(Survey).where(Survey.is_active == True))
        surveys = result.scalars().all()

    if not surveys:
        return await message.answer("На данный момент активных опросов нет.")

    for s in surveys:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Пройти опрос", callback_data=f"survey_{s.id}")]])
        await message.answer(f"📋 {s.title}\n{s.description}", reply_markup=kb)


@router.callback_query(F.data.startswith("survey_"))
async def start_survey(callback: CallbackQuery, state: FSMContext):
    survey_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id))
        questions = result.scalars().all()

    if not questions:
        return await callback.answer("В этом опросе нет вопросов.")

    await state.update_data(questions=[q.id for q in questions], current_idx=0, survey_id=survey_id, answers=[])
    await state.set_state(SurveyStates.answering)
    await callback.message.answer(f"Вопрос 1: {questions[0].text}")
    await callback.answer()


@router.message(SurveyStates.answering)
async def process_answer(message: Message, state: FSMContext, user: User):
    data = await state.get_data()
    q_ids = data['questions']
    idx = data['current_idx']

    data['answers'].append({'question_id': q_ids[idx], 'answer': message.text})

    if idx + 1 < len(q_ids):
        async with async_session() as session:
            q = await session.get(SurveyQuestion, q_ids[idx + 1])
        await state.update_data(current_idx=idx + 1, answers=data['answers'])
        await message.answer(f"Вопрос {idx + 2}: {q.text}")
    else:
        async with async_session() as session:
            for ans in data['answers']:
                session.add(SurveyAnswer(user_id=user.id, question_id=ans['question_id'], answer=ans['answer']))
            await session.commit()
        await state.clear()
        await message.answer("Спасибо! Ваши ответы записаны.")


class CreateSurveyStates(StatesGroup):
    title = State()
    description = State()
    questions = State()


@router.message(Command("create_survey"))
async def cmd_create_survey(message: Message, user: User, state: FSMContext):
    if user.role != "hr": return
    await state.set_state(CreateSurveyStates.title)
    await message.answer("Введите название опроса:")


@router.message(CreateSurveyStates.title)
async def survey_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(CreateSurveyStates.description)
    await message.answer("Введите описание опроса:")


@router.message(CreateSurveyStates.description)
async def survey_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateSurveyStates.questions)
    await message.answer("Отправьте вопросы, каждый с новой строки:")


@router.message(CreateSurveyStates.questions)
async def survey_qs(message: Message, state: FSMContext, bot: Bot):
    questions_list = [q.strip() for q in message.text.split('\n') if q.strip()]
    data = await state.get_data()

    async with async_session() as session:
        survey = Survey(title=data['title'], description=data['description'])
        session.add(survey)
        await session.flush()

        for text in questions_list:
            session.add(SurveyQuestion(survey_id=survey.id, text=text))

        users_res = await session.execute(select(User).where(User.is_active == True))
        for u in users_res.scalars():
            if u.id == message.from_user.id: continue
            try:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Пройти опрос", callback_data=f"survey_{survey.id}")]])
                await bot.send_message(u.tg_id, f"📊 Новый опрос!\n<b>{survey.title}</b>\n{survey.description}",
                                       reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass

        await session.commit()

    await state.clear()
    await message.answer("Опрос успешно создан и разослан сотрудникам.")


@router.message(Command("survey_results"))
async def cmd_survey_results(message: Message, user: User):
    if user.role != "hr": return
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("Формат: /survey_results <ID_опроса>")

    survey_id = int(parts[1])
    async with async_session() as session:
        res = await session.execute(
            select(SurveyAnswer, User, SurveyQuestion)
            .join(User).join(SurveyQuestion)
            .where(SurveyQuestion.survey_id == survey_id)
        )
        answers = res.all()

    if not answers:
        return await message.answer("Ответов нет.")

    out = [f"Результаты опроса ID {survey_id}:"]
    for ans, usr, q in answers:
        out.append(f"👤 {usr.fullname} | ❓ {q.text} | 💬 {ans.answer}")

    await message.answer("\n".join(out)[:4000])