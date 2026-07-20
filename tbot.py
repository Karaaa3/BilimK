import asyncpg
from datetime import datetime, timedelta, date, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from translations import product_ru, category_ru
from calendar_widget import build_calendar, calendar_intro_text

TOKEN = "8894511817:AAHLqt3MCy-Rril6KMQQa7aKYS_HQZ2oHqA"

DB_CONFIG = {
    "user": "postgres",
    "password": "cvlm391!hakl24@",
    "database": "bot", 
    "host": "localhost",
    "port": 5432
}

db_pool = None
REF_DATE = None  # последняя дата в данных (наше "сегодня")
 
MONTHS_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
 
EXPENSE_RU = {
    "rent": "Аренда", "salary": "Зарплата", "marketing": "Маркетинг",
    "utilities": "Коммуналка", "bank_commission": "Комиссия банка",
}
 
 
async def db_connect(app):
    global db_pool, REF_DATE
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    async with db_pool.acquire() as conn:
        last = await conn.fetchval("SELECT MAX(created_at) FROM orders")
    REF_DATE = last.date()
    print("Подключение к базе установлено. Последняя дата данных:", REF_DATE)
 
 
async def db_close(app):
    if db_pool is not None:
        await db_pool.close()
        print("Соединение с базой закрыто")
 
 
# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================
 
def m(n):
    """Денежный формат: 1234567 -> '1 234 567'."""
    return f"{int(round(float(n))):,}".replace(",", " ")
 
 
def pct(part, whole):
    return round(part / whole * 100) if whole else 0
 
 
def status_word(stock, limit):
    if stock <= 0:
        return "нет"
    if stock < limit * 0.5:
        return "критично"
    if stock < limit:
        return "мало"
    return "норма"
 
 
def back_to(section, label="Назад"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=section)]])
 
 
def period_range(days):
    """Возвращает (начало, конец_исключительно) для последних N дней от REF_DATE."""
    end_d = REF_DATE
    start_d = end_d - timedelta(days=days - 1)
    start = datetime.combine(start_d, time())
    end_excl = datetime.combine(end_d + timedelta(days=1), time())
    return start, end_excl
 
 
def period_label(days):
    return {7: "последние 7 дней", 30: "последние 30 дней", 365: "последний год"}.get(days, f"{days} дней")
 
 
def build_buttons(items, label_fn, prefix, per_row=2, back="warehouse"):
    """Универсальная сетка кнопок. items с полями id и name."""
    buttons = []
    row = []
    for it in items:
        row.append(InlineKeyboardButton(label_fn(it["name"]), callback_data=f"{prefix}:{it['id']}"))
        if len(row) == per_row:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Назад", callback_data=back)])
    return InlineKeyboardMarkup(buttons)
 
 
def period_menu(key, title):
    buttons = [
        [InlineKeyboardButton("Последние 7 дней", callback_data=f"{key}_p:7")],
        [InlineKeyboardButton("Последние 30 дней", callback_data=f"{key}_p:30")],
        [InlineKeyboardButton("Последний год", callback_data=f"{key}_p:365")],
        [InlineKeyboardButton("Выбрать даты", callback_data=f"{key}_cal")],
        [InlineKeyboardButton("Назад", callback_data="finance")],
    ]
    return f"{title}\n\nВыберите период:", InlineKeyboardMarkup(buttons)
 
 
# ============================================================
#  ЭКРАНЫ МЕНЮ
# ============================================================
 
def menu_screen():
    keyboard = [
        [InlineKeyboardButton("Склад", callback_data="warehouse")],
        [InlineKeyboardButton("Финансы", callback_data="finance")],
    ]
    return "Главное меню\n\nВыберите раздел:", InlineKeyboardMarkup(keyboard)
 
 
def warehouse_screen():
    keyboard = [
        [InlineKeyboardButton("Остатки", callback_data="stock")],
        [InlineKeyboardButton("Закупки", callback_data="restock")],
        [InlineKeyboardButton("Категории", callback_data="categories")],
        [InlineKeyboardButton("Стоимость склада", callback_data="stock_value")],
        [InlineKeyboardButton("Назад", callback_data="menu")],
    ]
    return "Склад\n\nВыберите действие:", InlineKeyboardMarkup(keyboard)
 
 
def finance_screen():
    keyboard = [
        [InlineKeyboardButton("Отчёт за период", callback_data="report")],
        [InlineKeyboardButton("Топ продаж", callback_data="top")],
        [InlineKeyboardButton("Расходы", callback_data="expenses")],
        [InlineKeyboardButton("Списания", callback_data="writeoffs")],
        [InlineKeyboardButton("Назад", callback_data="menu")],
    ]
    return "Финансы\n\nВыберите действие:", InlineKeyboardMarkup(keyboard)
 
 
# ============================================================
#  СКЛАД: ЧТО ЗАКУПИТЬ
# ============================================================
 
async def restock_screen():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT name, stock_kg, min_kg, start_kg
            FROM products WHERE stock_kg < min_kg
            ORDER BY stock_kg / min_kg ASC
            """
        )
    if not rows:
        return "Что закупить\n\nВсё в порядке, ни один товар не ниже лимита.", back_to("warehouse")
 
    lines = [f"Что закупить ({len(rows)} позиций)", ""]
    for r in rows:
        stock = float(r["stock_kg"]); limit = float(r["min_kg"]); start = float(r["start_kg"])
        lines.append(f"{product_ru(r['name'])} ({status_word(stock, limit)})")
        lines.append(f"   Сейчас: {stock:g} кг | Лимит: {limit:g} кг")
        lines.append(f"   Докупить: минимум {round(limit-stock,1):g} кг, лучше {round(start-stock,1):g} кг")
        lines.append("")
    return "\n".join(lines), back_to("warehouse")
 
 
# ============================================================
#  СКЛАД: ОСТАТКИ
# ============================================================
 
async def stock_categories_screen():
    async with db_pool.acquire() as conn:
        cats = await conn.fetch("SELECT id, name FROM categories ORDER BY id")
    kb = build_buttons(cats, category_ru, "stock_cat", back="warehouse")
    return "Остатки\n\nВыберите категорию:", kb
 
 
async def stock_list_screen(cat_id):
    async with db_pool.acquire() as conn:
        cat = await conn.fetchrow("SELECT name FROM categories WHERE id = $1", cat_id)
        rows = await conn.fetch(
            "SELECT name, stock_kg, min_kg FROM products WHERE category_id = $1", cat_id
        )
    items = sorted(rows, key=lambda r: product_ru(r["name"]))
    lines = [f"Остатки - {category_ru(cat['name'])}", ""]
    for r in items:
        stock = float(r["stock_kg"]); limit = float(r["min_kg"])
        lines.append(f"{product_ru(r['name'])} - {stock:g} кг ({status_word(stock, limit)})")
    return "\n".join(lines), back_to("stock")
 
 
# ============================================================
#  СКЛАД: КАТЕГОРИИ (категория -> товар -> карточка)
# ============================================================
 
async def categories_screen():
    async with db_pool.acquire() as conn:
        cats = await conn.fetch("SELECT id, name FROM categories ORDER BY id")
    kb = build_buttons(cats, category_ru, "cat", back="warehouse")
    return "Категории\n\nВыберите категорию:", kb
 
 
async def category_products_screen(cat_id):
    async with db_pool.acquire() as conn:
        cat = await conn.fetchrow("SELECT name FROM categories WHERE id = $1", cat_id)
        rows = await conn.fetch("SELECT id, name FROM products WHERE category_id = $1", cat_id)
    items = sorted(rows, key=lambda r: product_ru(r["name"]))
    kb = build_buttons(items, product_ru, "prod", back="categories")
    return f"{category_ru(cat['name'])}\n\nВыберите товар:", kb
 
 
async def product_card_screen(prod_id):
    async with db_pool.acquire() as conn:
        p = await conn.fetchrow(
            """
            SELECT p.name, p.stock_kg, p.min_kg, p.buy_price, p.sell_price,
                   p.category_id, c.name AS cat_name
            FROM products p JOIN categories c ON c.id = p.category_id
            WHERE p.id = $1
            """,
            prod_id,
        )
    stock = float(p["stock_kg"]); limit = float(p["min_kg"])
    lines = [
        f"{product_ru(p['name'])} ({p['name']})",
        "",
        f"Остаток: {stock:g} кг ({status_word(stock, limit)})",
        f"Лимит: {limit:g} кг",
        f"Цена закупки: {p['buy_price']} тг/кг",
        f"Цена продажи: {p['sell_price']} тг/кг",
        f"Категория: {category_ru(p['cat_name'])}",
    ]
    return "\n".join(lines), back_to(f"cat:{p['category_id']}")
 
 
# ============================================================
#  СКЛАД: СТОИМОСТЬ СКЛАДА
# ============================================================
 
async def stock_value_screen():
    async with db_pool.acquire() as conn:
        total = await conn.fetchval("SELECT COALESCE(SUM(stock_kg*buy_price),0) FROM products")
        cats = await conn.fetch(
            """
            SELECT c.id, c.name, COALESCE(SUM(p.stock_kg*p.buy_price),0) AS val
            FROM categories c LEFT JOIN products p ON p.category_id = c.id
            GROUP BY c.id, c.name ORDER BY val DESC
            """
        )
    lines = [f"Стоимость склада: {m(total)} тг", "(по цене закупки)", ""]
    for c in cats:
        lines.append(f"{category_ru(c['name'])}: {m(c['val'])} тг")
 
    # кнопки категорий для детализации
    buttons = []
    row = []
    for c in cats:
        row.append(InlineKeyboardButton(category_ru(c["name"]), callback_data=f"sv_cat:{c['id']}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Назад", callback_data="warehouse")])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)
 
 
async def stock_value_category_screen(cat_id):
    async with db_pool.acquire() as conn:
        cat = await conn.fetchrow("SELECT name FROM categories WHERE id = $1", cat_id)
        rows = await conn.fetch(
            """
            SELECT name, stock_kg, buy_price, (stock_kg*buy_price) AS val
            FROM products WHERE category_id = $1 ORDER BY val DESC
            """,
            cat_id,
        )
    total = sum(float(r["val"]) for r in rows)
    lines = [f"Стоимость - {category_ru(cat['name'])}: {m(total)} тг", ""]
    for r in rows:
        lines.append(f"{product_ru(r['name'])}: {m(r['val'])} тг ({float(r['stock_kg']):g} кг)")
    return "\n".join(lines), back_to("stock_value")
 
 
# ============================================================
#  ФИНАНСЫ: общие расчёты
# ============================================================
 
async def fin_summary(conn, start, end):
    row = await conn.fetchrow(
        """
        SELECT
          COALESCE(SUM(oi.amount),0) AS revenue,
          COALESCE(SUM(oi.cost),0)   AS cogs,
          COALESCE(SUM(CASE WHEN o.payment_method='cash' THEN oi.amount ELSE 0 END),0) AS cash_rev,
          COALESCE(SUM(CASE WHEN o.payment_method='card' THEN oi.amount ELSE 0 END),0) AS card_rev
        FROM order_items oi JOIN orders o ON o.id = oi.order_id
        WHERE o.created_at >= $1 AND o.created_at < $2
        """,
        start, end,
    )
    spoil = await conn.fetchval(
        "SELECT COALESCE(SUM(cost),0) FROM write_offs WHERE created_at >= $1 AND created_at < $2",
        start, end,
    )
    exp = await conn.fetchval(
        "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE created_at >= $1 AND created_at < $2",
        start, end,
    )
    return dict(
        revenue=float(row["revenue"]), cogs=float(row["cogs"]),
        cash=float(row["cash_rev"]), card=float(row["card_rev"]),
        spoil=float(spoil), exp=float(exp),
    )
 
 
async def fin_breakdown(conn, start, end, unit):
    """Разбивка по дням ('day') или месяцам ('month'). unit из белого списка."""
    sales = await conn.fetch(
        f"""
        SELECT date_trunc('{unit}', o.created_at) AS k,
               SUM(oi.amount) AS rev, SUM(oi.cost) AS cogs
        FROM order_items oi JOIN orders o ON o.id = oi.order_id
        WHERE o.created_at >= $1 AND o.created_at < $2
        GROUP BY k
        """,
        start, end,
    )
    spoil = await conn.fetch(
        f"SELECT date_trunc('{unit}', created_at) AS k, SUM(cost) AS c "
        f"FROM write_offs WHERE created_at >= $1 AND created_at < $2 GROUP BY k",
        start, end,
    )
    exp = await conn.fetch(
        f"SELECT date_trunc('{unit}', created_at) AS k, SUM(amount) AS c "
        f"FROM expenses WHERE created_at >= $1 AND created_at < $2 GROUP BY k",
        start, end,
    )
    spoil_map = {r["k"]: float(r["c"]) for r in spoil}
    exp_map = {r["k"]: float(r["c"]) for r in exp}
    out = []
    for r in sales:
        k = r["k"]
        rev = float(r["rev"]); cogs = float(r["cogs"])
        profit = rev - cogs - spoil_map.get(k, 0) - exp_map.get(k, 0)
        out.append((k, rev, profit))
    out.sort(key=lambda x: x[0], reverse=True)
    return out
 
 
# ============================================================
#  ФИНАНСЫ: ОТЧЁТ ЗА ПЕРИОД
# ============================================================
 
def ymd(d):
    return d.strftime("%Y%m%d")
 
 
def parse_ymd(s):
    return datetime.strptime(s, "%Y%m%d").date()
 
 
def range_from_dates(d1, d2):
    """Из двух дат делает (начало, конец_искл, подпись). Авто-разворот если перепутаны."""
    if d1 > d2:
        d1, d2 = d2, d1
    start = datetime.combine(d1, time())
    end_excl = datetime.combine(d2 + timedelta(days=1), time())
    label = f"{d1.strftime('%d.%m.%Y')} - {d2.strftime('%d.%m.%Y')}"
    return start, end_excl, label
 
 
async def run_finance(key, start, end, label):
    """Вызывает нужную финансовую функцию по ключу."""
    if key == "report":
        return await report_screen(start, end, label)
    if key == "top":
        return await top_screen(start, end, label)
    if key == "expenses":
        return await expenses_screen(start, end, label)
    if key == "writeoffs":
        return await writeoffs_screen(start, end, label)
    return "Неизвестная команда.", back_to("finance")
 
 
async def report_screen(start, end, label):
    span = (end - start).days
    unit = "month" if span > 90 else "day"
    async with db_pool.acquire() as conn:
        s = await fin_summary(conn, start, end)
        bd = await fin_breakdown(conn, start, end, unit)
 
    if s["revenue"] == 0 and not bd:
        return f"Отчёт - {label}\n\nЗа этот период данных нет.", back_to("report")
 
    net = s["revenue"] - s["cogs"] - s["spoil"] - s["exp"]
    lines = [
        f"Отчёт - {label}",
        "",
        f"Выручка: {m(s['revenue'])} тг",
        f"   Наличными: {m(s['cash'])} ({pct(s['cash'], s['revenue'])}%)",
        f"   Картой: {m(s['card'])} ({pct(s['card'], s['revenue'])}%)",
        f"Себестоимость: {m(s['cogs'])} тг",
        f"Порча (списано): {m(s['spoil'])} тг",
        f"Расходы: {m(s['exp'])} тг",
        "-----------------------------",
        f"Чистая прибыль: {m(net)} тг",
        "",
        "По месяцам:" if unit == "month" else "По дням:",
    ]
    for k, rev, profit in bd:
        if unit == "month":
            dl = f"{MONTHS_RU[k.month]} {k.year}"
        else:
            dl = f"{k.day:02d}.{k.month:02d}"
        lines.append(f"{dl}: выручка {m(rev)}, прибыль {m(profit)}")
    return "\n".join(lines), back_to("report")
 
 
# ============================================================
#  ФИНАНСЫ: ТОП ПРОДАЖ
# ============================================================
 
async def top_screen(start, end, label):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT oi.product_id, p.name,
                   SUM(oi.weight_kg)              AS kg,
                   SUM(oi.amount)                 AS revenue,
                   SUM(oi.amount) - SUM(oi.cost)  AS profit
            FROM order_items oi
            JOIN orders o   ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE o.created_at >= $1 AND o.created_at < $2
            GROUP BY oi.product_id, p.name
            ORDER BY profit DESC
            LIMIT 10
            """,
            start, end,
        )
    if not rows:
        return f"Топ продаж - {label}\n\nЗа этот период данных нет.", back_to("top")
    lines = [f"Топ продаж (по чистой прибыли) - {label}", ""]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"{i}. {product_ru(r['name'])} - прибыль {m(r['profit'])} тг "
            f"({float(r['kg']):g} кг, выручка {m(r['revenue'])} тг)"
        )
    return "\n".join(lines), back_to("top")
 
 
# ============================================================
#  ФИНАНСЫ: РАСХОДЫ
# ============================================================
 
async def expenses_screen(start, end, label):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT category, SUM(amount) AS total
            FROM expenses WHERE created_at >= $1 AND created_at < $2
            GROUP BY category ORDER BY total DESC
            """,
            start, end,
        )
    if not rows:
        return f"Расходы - {label}\n\nЗа этот период данных нет.", back_to("expenses")
    total = sum(float(r["total"]) for r in rows)
    lines = [f"Расходы - {label}", ""]
    for r in rows:
        lines.append(f"{EXPENSE_RU.get(r['category'], r['category'])}: {m(r['total'])} тг")
    lines.append("-----------------------------")
    lines.append(f"Итого: {m(total)} тг")
    return "\n".join(lines), back_to("expenses")
 
 
# ============================================================
#  ФИНАНСЫ: СПИСАНИЯ
# ============================================================
 
async def writeoffs_screen(start, end, label, page=0):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.name, SUM(w.weight_kg) AS kg, SUM(w.cost) AS cost
            FROM write_offs w JOIN products p ON p.id = w.product_id
            WHERE w.created_at >= $1 AND w.created_at < $2
            GROUP BY p.name ORDER BY cost DESC
            """,
            start, end,
        )
    if not rows:
        return f"Списания - {label}\n\nЗа этот период данных нет.", back_to("writeoffs")
 
    total = sum(float(r["cost"]) for r in rows)
    per_page = 15
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    chunk = rows[page * per_page:(page + 1) * per_page]
 
    lines = [f"Списания - {label}", ""]
    for r in chunk:
        lines.append(f"{product_ru(r['name'])}: {float(r['kg']):g} кг ({m(r['cost'])} тг)")
    lines.append("-----------------------------")
    lines.append(f"Итого списано: {m(total)} тг  (всего {len(rows)} позиций)")
 
    # для листания зашиваем диапазон дат в callback
    d1 = start.date()
    d2 = (end - timedelta(days=1)).date()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("Предыдущая страница", callback_data=f"wopg:{ymd(d1)}:{ymd(d2)}:{page-1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("Следующая  страница", callback_data=f"wopg:{ymd(d1)}:{ymd(d2)}:{page+1}"))
 
    keyboard = []
    if nav:
        keyboard.append(nav)
        keyboard.append([InlineKeyboardButton(f"Страница {page+1}/{pages}", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="writeoffs")])
    return "\n".join(lines), InlineKeyboardMarkup(keyboard)
 
 
# ============================================================
#  ОБРАБОТЧИКИ
# ============================================================
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Меню", callback_data="menu")]])
    await update.message.reply_text(
        "Добро пожаловать в X2POS бот!\n"
        "Нажмите кнопку, чтобы открыть меню:",
        reply_markup=keyboard,
    )
 
 
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
 
    # --- меню ---
    if data == "menu":
        text, kb = menu_screen()
    elif data == "warehouse":
        text, kb = warehouse_screen()
    elif data == "finance":
        text, kb = finance_screen()
 
    # --- склад ---
    elif data == "restock":
        text, kb = await restock_screen()
    elif data == "stock":
        text, kb = await stock_categories_screen()
    elif data.startswith("stock_cat:"):
        text, kb = await stock_list_screen(int(data.split(":")[1]))
    elif data == "categories":
        text, kb = await categories_screen()
    elif data.startswith("cat:"):
        text, kb = await category_products_screen(int(data.split(":")[1]))
    elif data.startswith("prod:"):
        text, kb = await product_card_screen(int(data.split(":")[1]))
    elif data == "stock_value":
        text, kb = await stock_value_screen()
    elif data.startswith("sv_cat:"):
        text, kb = await stock_value_category_screen(int(data.split(":")[1]))
 
    # --- финансы: меню периода ---
    elif data == "report":
        text, kb = period_menu("report", "Отчёт за период")
    elif data == "top":
        text, kb = period_menu("top", "Топ продаж")
    elif data == "expenses":
        text, kb = period_menu("expenses", "Расходы")
    elif data == "writeoffs":
        text, kb = period_menu("writeoffs", "Списания")
 
    # --- финансы: выбран период ---
    elif "_p:" in data:
        key, n = data.split("_p:")
        n = int(n)
        start, end = period_range(n)
        text, kb = await run_finance(key, start, end, period_label(n))
 
    # --- финансы: открыть календарь ---
    elif data.endswith("_cal"):
        key = data[:-4]
        text = calendar_intro_text("0")
        kb = build_calendar(key, REF_DATE.year, REF_DATE.month, sel="0", today=date.today())
 
    # --- календарь: листание месяцев/годов ---
    elif data.startswith("cal:"):
        _, key, y, mo, sel = data.split(":")
        text = calendar_intro_text(sel)
        kb = build_calendar(key, int(y), int(mo), sel=sel, today=date.today())
 
    # --- календарь: тап по дню ---
    elif data.startswith("calpick:"):
        _, key, y, mo, d, sel = data.split(":")
        picked = date(int(y), int(mo), int(d))
        if sel == "0":
            sel_str = picked.strftime("%Y-%m-%d")
            text = calendar_intro_text(sel_str)
            kb = build_calendar(key, int(y), int(mo), sel=sel_str, today=date.today())
        else:
            ys, ms, ds = map(int, sel.split("-"))
            start, end, label = range_from_dates(date(ys, ms, ds), picked)
            text, kb = await run_finance(key, start, end, label)
 
    # --- календарь: пустая клетка ---
    elif data == "calnoop":
        return
 
    # --- списания: листание страниц (диапазон зашит в callback) ---
    elif data.startswith("wopg:"):
        _, d1s, d2s, page_s = data.split(":")
        start, end, label = range_from_dates(parse_ymd(d1s), parse_ymd(d2s))
        text, kb = await writeoffs_screen(start, end, label, int(page_s))
 
    # --- пустая кнопка-счётчик ---
    elif data == "noop":
        return
 
    else:
        text, kb = "Неизвестная команда.", back_to("menu")
 
    await query.edit_message_text(text, reply_markup=kb)
 
 
if __name__ == "__main__":
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(db_connect)
        .post_shutdown(db_close)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    print("Бот запущен. Откройте Telegram и напишите /start")
    app.run_polling()
 