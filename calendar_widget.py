"""
Календарь с выбором диапазона дат (inline-кнопки).
Состояние зашито в callback_data, отдельное хранилище не нужно.

Формат callback_data:
  cal:<key>:<year>:<month>:<sel>   - показ месяца
  calpick:<key>:<year>:<month>:<day>:<sel>  - тап по дню
  calnoop                          - пустая клетка (ничего не делает)

  key  - для какой функции (report/top/expenses/writeoffs)
  sel  - выбранное начало: "0" если ещё нет, или "YYYY-MM-DD"
"""
import calendar as _cal
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MIN_YEAR = 2000
MAX_YEAR = 2050
WEEK_HEADER = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


def _clamp_month(year, month):
    
    if year < MIN_YEAR:
        return MIN_YEAR, 1
    if year > MAX_YEAR:
        return MAX_YEAR, 12
    return year, month


def build_calendar(key, year, month, sel="0", today=None):
    """Строит клавиатуру календаря на месяц year-month.
    sel - выбранное начало ('0' или 'YYYY-MM-DD'). today - дата для подсветки."""
    year, month = _clamp_month(year, month)
    keyboard = []

    # --- шапка: навигация по году и месяцу ---
    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f"cal:{key}:{year-1}:{month}:{sel}"),
        InlineKeyboardButton("<", callback_data=f"cal:{key}:{year}:{month-1 or 12}:{sel}"
                             if month > 1 else f"cal:{key}:{year-1}:12:{sel}"),
        InlineKeyboardButton(f"{MONTHS_RU[month]} {year}", callback_data="calnoop"),
        InlineKeyboardButton(">", callback_data=f"cal:{key}:{year}:{month+1}:{sel}"
                             if month < 12 else f"cal:{key}:{year+1}:1:{sel}"),
        InlineKeyboardButton(">>", callback_data=f"cal:{key}:{year+1}:{month}:{sel}"),
    ])

    # --- строка дней недели ---
    keyboard.append([InlineKeyboardButton(d, callback_data="calnoop") for d in WEEK_HEADER])

    # --- сетка дней ---
    sel_date = None
    if sel != "0":
        y, mo, d = map(int, sel.split("-"))
        sel_date = date(y, mo, d)

    for week in _cal.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="calnoop"))
                continue
            cur = date(year, month, day)
            label = str(day)
            # пометки: [день] - выбранное начало, (день) - сегодня
            if sel_date and cur == sel_date:
                label = f"[{day}]"
            elif today and cur == today:
                label = f"({day})"
            row.append(InlineKeyboardButton(
                label, callback_data=f"calpick:{key}:{year}:{month}:{day}:{sel}"
            ))
        keyboard.append(row)

    # --- низ: отмена ---
    keyboard.append([InlineKeyboardButton("Отмена", callback_data=key)])
    return InlineKeyboardMarkup(keyboard)


def calendar_intro_text(sel="0"):
    if sel == "0":
        return "Выберите дату начала периода:"
    return f"Начало: {sel}\nТеперь выберите дату конца периода:"
