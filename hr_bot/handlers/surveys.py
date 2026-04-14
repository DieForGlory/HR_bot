from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.engine import async_session
from database.models import Survey, SurveyQuestion, SurveyAnswer, User
from sqlalchemy import select

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
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пройти опрос", callback_data=f"survey_{s.id}")]
        ])
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

    # Сохраняем текущий ответ
    data['answers'].append({'question_id': q_ids[idx], 'answer': message.text})

    if idx + 1 < len(q_ids):
        # Следующий вопрос
        async with async_session() as session:
            q = await session.get(SurveyQuestion, q_ids[idx + 1])
        await state.update_data(current_idx=idx + 1, answers=data['answers'])
        await message.answer(f"Вопрос {idx + 2}: {q.text}")
    else:
        # Сохранение всех ответов в БД
        async with async_session() as session:
            for ans in data['answers']:
                session.add(SurveyAnswer(user_id=user.id, question_id=ans['question_id'], answer=ans['answer']))
            await session.commit()

        await state.clear()
        await message.answer("Спасибо! Ваши ответы записаны.")