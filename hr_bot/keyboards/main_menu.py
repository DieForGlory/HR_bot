from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from locales.texts import MESSAGES

def main_menu_kb(lang: str):
    m = MESSAGES[lang]
    kb = [
        [KeyboardButton(text=m['vacation']), KeyboardButton(text=m['day_off'])],
        [KeyboardButton(text=m['sick_leave']), KeyboardButton(text=m['certificates'])],
        [KeyboardButton(text="🚀 Онбординг"), KeyboardButton(text="📊 Опросы")],  # Новое
        [KeyboardButton(text=m['question_hr']), KeyboardButton(text=m['faq'])],
        [KeyboardButton(text=m['calendar'])]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def back_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=MESSAGES[lang]['back'])]],
        resize_keyboard=True
    )