from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_approval_kb(request_id: int):
    kb = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{request_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_reg_approval_kb(tg_id: int):
    kb = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"reg_approve_{tg_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reg_reject_{tg_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)