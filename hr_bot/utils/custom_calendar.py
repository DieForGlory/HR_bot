import calendar
from datetime import date, timedelta
from aiogram.types import InlineKeyboardMarkup, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from hr_bot.database.engine import async_session
from hr_bot.database.models import Holiday
from sqlalchemy import select


class CalCB(CallbackData, prefix="ccal"):
    act: str
    y: int
    m: int
    d: int


class CustomCalendar:
    def __init__(self):
        self.months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    async def start_calendar(self, year: int = None, month: int = None) -> InlineKeyboardMarkup:
        today = date.today()
        return await self._get_days_kb(year or today.year, month or today.month)

    async def _get_days_kb(self, year: int, month: int) -> InlineKeyboardMarkup:
        async with async_session() as session:
            result = await session.execute(
                select(Holiday.date).where(
                    Holiday.date >= date(year, month, 1),
                    Holiday.date <= date(year, month, calendar.monthrange(year, month)[1])
                )
            )
            holidays = {row[0] for row in result.all()}

        b = InlineKeyboardBuilder()
        b.button(text="<", callback_data=CalCB(act="p_m", y=year, m=month, d=1))
        b.button(text=f"{self.months[month - 1]} {year}", callback_data=CalCB(act="s_m", y=year, m=month, d=1))
        b.button(text=">", callback_data=CalCB(act="n_m", y=year, m=month, d=1))

        for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
            b.button(text=day, callback_data=CalCB(act="ig", y=0, m=0, d=0))

        for week in calendar.monthcalendar(year, month):
            for day in week:
                if day == 0:
                    b.button(text=" ", callback_data=CalCB(act="ig", y=0, m=0, d=0))
                else:
                    is_holiday = date(year, month, day) in holidays
                    text_display = f"[{day}]" if is_holiday else str(day)
                    b.button(text=text_display, callback_data=CalCB(act="day", y=year, m=month, d=day))
        b.adjust(3, 7, 7, 7, 7, 7, 7)
        return b.as_markup()

    def _get_months_kb(self, year: int) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text=f"Год: {year}", callback_data=CalCB(act="s_y", y=year, m=1, d=1))
        for i, mo in enumerate(self.months, 1):
            b.button(text=mo, callback_data=CalCB(act="set_m", y=year, m=i, d=1))
        b.adjust(1, 3, 3, 3, 3)
        return b.as_markup()

    def _get_years_kb(self, year: int) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        start = year - (year % 12)
        b.button(text="<", callback_data=CalCB(act="p_y", y=start - 12, m=1, d=1))
        b.button(text="Период", callback_data=CalCB(act="ig", y=0, m=0, d=0))
        b.button(text=">", callback_data=CalCB(act="n_y", y=start + 12, m=1, d=1))
        for i in range(12):
            y = start + i
            b.button(text=str(y), callback_data=CalCB(act="set_y", y=y, m=1, d=1))
        b.adjust(3, 3, 3, 3, 3)
        return b.as_markup()

    async def process_selection(self, call: CallbackQuery, data: CalCB) -> tuple[bool, date | None]:
        act = data.act
        if act == "ig":
            await call.answer()
            return False, None
        if act == "day":
            return True, date(data.y, data.m, data.d)

        if act == "p_m":
            d = date(data.y, data.m, 1) - timedelta(days=1)
            await call.message.edit_reply_markup(reply_markup=await self._get_days_kb(d.year, d.month))
        elif act == "n_m":
            d = date(data.y, data.m, calendar.monthrange(data.y, data.m)[1]) + timedelta(days=1)
            await call.message.edit_reply_markup(reply_markup=await self._get_days_kb(d.year, d.month))
        elif act == "s_m":
            await call.message.edit_reply_markup(reply_markup=self._get_months_kb(data.y))
        elif act == "set_m":
            await call.message.edit_reply_markup(reply_markup=await self._get_days_kb(data.y, data.m))
        elif act == "s_y":
            await call.message.edit_reply_markup(reply_markup=self._get_years_kb(data.y))
        elif act in ["set_y", "p_y", "n_y"]:
            if act == "set_y":
                await call.message.edit_reply_markup(reply_markup=self._get_months_kb(data.y))
            else:
                await call.message.edit_reply_markup(reply_markup=self._get_years_kb(data.y))
        return False, None