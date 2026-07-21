"""
db.py
-----
Работа с SQLite. Здесь минимально необходимая структура для MVP:
две таблицы — "tests" (сессия прохождения теста целиком) и
"answers" (каждый отдельный ответ ученика с результатом ИИ-анализа).

Такое разделение важно для защиты перед жюри:
- таблица tests даёт агрегированную статистику (сколько баллов, когда, по какому предмету)
- таблица answers хранит "сырые" данные для будущей аналитики пробелов в знаниях
  (например, чтобы через месяц показать: "у ученика системная проблема с темой Х")
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, date, timedelta

DB_PATH = "data/quiz.db"


def get_connection():
    """
    Открывает соединение с базой (создаёт файл, если его ещё нет).

    Важно: Git не отслеживает пустые папки, поэтому на "чистом" сервере
    (например, при деплое на Streamlit Cloud) папки data может не быть
    вообще — os.makedirs создаёт её на лету при первом обращении,
    иначе sqlite3.connect упадёт с OperationalError.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Создаёт таблицы при первом запуске приложения.
    Вызывается один раз при старте app.py.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            grade INTEGER,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Миграция для баз, созданных ДО добавления поля grade (например,
    # уже задеплоенное приложение на Streamlit Cloud с existing data/quiz.db).
    # Если колонка уже есть — sqlite вернёт ошибку, которую мы просто игнорируем.
    try:
        cur.execute("ALTER TABLE tests ADD COLUMN grade INTEGER")
    except sqlite3.OperationalError:
        pass

    # Поле username связывает тест с зарегистрированным аккаунтом
    # (для гостевых/старых тестов может быть NULL - обратная совместимость).
    try:
        cur.execute("ALTER TABLE tests ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass

    # Флаг диагностического теста (охватывает все предметы разом),
    # чтобы отличать его от обычного теста по одному предмету.
    try:
        cur.execute("ALTER TABLE tests ADD COLUMN is_diagnostic INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            topic TEXT,
            student_answer TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,   -- 0 или 1
            ai_explanation TEXT,           -- объяснение от ИИ-тьютора (NULL если ответ верный)
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
    """)

    # Аккаунты учеников: пароль хранится НЕ в открытом виде, а как хеш
    # с индивидуальной "солью" (salt) для каждого пользователя.
    # Это упрощённая, но не игрушечная схема — pbkdf2_hmac с 100 000
    # итераций является стандартной практикой без сторонних библиотек.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_diagnostic_at TEXT
        )
    """)

    # Миграция для баз, созданных ДО добавления "серии" (streak) -
    # сколько дней подряд ученик занимается хотя бы один раз в день.
    try:
        cur.execute("ALTER TABLE users ADD COLUMN streak_days INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_practice_date TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def save_test_result(student_name: str, subject: str, grade: int, total_questions: int,
                      correct_answers: int, answer_records: list,
                      username: str = None, is_diagnostic: bool = False) -> int:
    """
    Сохраняет результат прохождения теста + все ответы одним пакетом.

    answer_records — список словарей вида:
        {
            "question_text": str,
            "topic": str,
            "student_answer": str,
            "correct_answer": str,
            "is_correct": bool,
            "ai_explanation": str или None
        }

    username — логин зарегистрированного ученика (для связи с аккаунтом
    и картой прогресса). Может быть None для обратной совместимости.
    is_diagnostic — True для сводного диагностического теста по всем
    предметам (в отличие от обычного теста по одному предмету).

    Возвращает id созданной записи в tests (пригодится для истории/дашборда).
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tests (student_name, subject, grade, total_questions, correct_answers,
                            created_at, username, is_diagnostic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_name, subject, grade, total_questions, correct_answers,
          datetime.now().isoformat(timespec="seconds"), username, 1 if is_diagnostic else 0))

    test_id = cur.lastrowid

    for rec in answer_records:
        cur.execute("""
            INSERT INTO answers
                (test_id, question_text, topic, student_answer, correct_answer, is_correct, ai_explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            rec["question_text"],
            rec.get("topic"),
            rec["student_answer"],
            rec["correct_answer"],
            1 if rec["is_correct"] else 0,
            rec.get("ai_explanation"),
        ))

    conn.commit()
    conn.close()

    # Обновляем "серию" (streak) - сколько дней подряд ученик занимается.
    # Делаем это здесь, а не отдельным вызовом в app.py, чтобы streak
    # обновлялся ОДИНАКОВО и для обычного теста, и для диагностики
    # (диагностика сохраняет несколько записей через save_test_result,
    # по одной на предмет - update_streak при этом идемпотентен в рамках
    # одного дня, повторный вызов в тот же день ничего не портит).
    if username:
        update_streak(username)

    return test_id


def update_streak(username: str) -> int:
    """
    Обновляет "серию" дней подряд, когда ученик занимался.
    Логика:
    - Если ученик уже отмечался сегодня - серия не меняется.
    - Если последний раз занимался вчера - серия увеличивается на 1.
    - Если был перерыв (позавчера и раньше) или это первый раз - серия
      начинается заново с 1.
    Возвращает текущее значение серии после обновления.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT streak_days, last_practice_date FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 0

    streak_days, last_date_str = row
    streak_days = streak_days or 0
    today = date.today()

    if last_date_str:
        last_date = date.fromisoformat(last_date_str)
        if last_date == today:
            pass  # уже отмечались сегодня - серия не меняется
        elif last_date == today - timedelta(days=1):
            streak_days += 1
        else:
            streak_days = 1
    else:
        streak_days = 1

    cur.execute(
        "UPDATE users SET streak_days = ?, last_practice_date = ? WHERE username = ?",
        (streak_days, today.isoformat(), username),
    )
    conn.commit()
    conn.close()
    return streak_days


def get_streak(username: str) -> int:
    """
    Возвращает ТЕКУЩУЮ действующую серию дней. Если с последнего занятия
    прошло больше суток (пропущен хотя бы один день), серия считается
    прерванной и отображается как 0, даже если в базе ещё хранится
    старое число - серия сбрасывается автоматически при следующем
    занятии через update_streak(), но для ОТОБРАЖЕНИЯ (до этого момента)
    нам нужно честно показать, что серия уже не действует.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT streak_days, last_practice_date FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[1]:
        return 0

    streak_days, last_date_str = row
    last_date = date.fromisoformat(last_date_str)
    if (date.today() - last_date).days <= 1:
        return streak_days or 0
    return 0


def get_today_answers_count(username: str) -> int:
    """Считает, на сколько вопросов ученик уже ответил СЕГОДНЯ (для 'цели дня')."""
    conn = get_connection()
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("""
        SELECT COUNT(*)
        FROM answers a
        JOIN tests t ON a.test_id = t.id
        WHERE t.username = ? AND date(t.created_at) = ?
    """, (username, today))
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_student_history(student_name: str):
    """
    Возвращает историю всех тестов ученика — пригодится, если на защите
    спросят про 'отслеживание прогресса во времени'.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject, total_questions, correct_answers, created_at
        FROM tests
        WHERE student_name = ?
        ORDER BY created_at DESC
    """, (student_name,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_weak_topics(student_name: str):
    """
    Простейшая аналитика пробелов: считает, по каким темам ученик
    чаще всего ошибается (агрегация по всем его тестам).
    Это можно показать жюри как задел на 'адаптивное обучение'.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.topic,
               SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END) AS wrong_count,
               COUNT(*) AS total_count
        FROM answers a
        JOIN tests t ON a.test_id = t.id
        WHERE t.student_name = ?
        GROUP BY a.topic
        ORDER BY wrong_count DESC
    """, (student_name,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# АККАУНТЫ УЧЕНИКОВ
# ============================================================
# Пароли НИКОГДА не хранятся в открытом виде. Используется
# pbkdf2_hmac (встроен в стандартную библиотеку hashlib, сторонние
# пакеты вроде bcrypt не нужны) с индивидуальной случайной "солью"
# на каждого пользователя - это защищает от атак по радужным таблицам.
# ============================================================

def _hash_password(password: str, salt: str) -> str:
    """Хеширует пароль с солью через pbkdf2_hmac (100 000 итераций)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Регистрирует нового пользователя.
    Возвращает (успех: bool, сообщение: str).
    """
    username = username.strip()
    if not username or not password:
        return False, "Логин и пароль не могут быть пустыми."
    if len(password) < 4:
        return False, "Пароль должен содержать минимум 4 символа."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        conn.close()
        return False, "Пользователь с таким логином уже существует."

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    cur.execute("""
        INSERT INTO users (username, password_hash, salt, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, password_hash, salt, datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    conn.close()
    return True, "Регистрация прошла успешно!"


def authenticate_user(username: str, password: str) -> bool:
    """Проверяет логин и пароль. Возвращает True, если совпадают."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    stored_hash, salt = row
    return _hash_password(password, salt) == stored_hash


def get_last_diagnostic(username: str):
    """
    Возвращает дату последней пройденной диагностики (datetime) или None,
    если ученик ещё ни разу её не проходил.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT last_diagnostic_at FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return None
    return datetime.fromisoformat(row[0])


def mark_diagnostic_completed(username: str):
    """Отмечает, что ученик только что прошёл диагностический тест."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET last_diagnostic_at = ? WHERE username = ?",
        (datetime.now().isoformat(timespec="seconds"), username),
    )
    conn.commit()
    conn.close()


def get_progress_map(username: str):
    """
    Возвращает "карту" прогресса ученика: по каждому предмету и теме -
    сколько было верных и всего ответов за всё время (по всем тестам,
    включая диагностические). Используется для визуализации того, какие
    темы ученик уже "прокачал", а какие ещё требуют внимания.

    Возвращает список кортежей: (subject, topic, correct_count, total_count)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.subject,
               a.topic,
               SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
               COUNT(*) AS total_count
        FROM answers a
        JOIN tests t ON a.test_id = t.id
        WHERE t.username = ?
        GROUP BY t.subject, a.topic
        ORDER BY t.subject, a.topic
    """, (username,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_mistake_bank(username: str):
    """
    "Банк ошибок" - собирает ВСЕ неверные ответы ученика со ВСЕХ его
    тестов (обычных и диагностических), за всё время, в одном месте.

    Ключевая идея: объяснение от ИИ-тьютора УЖЕ сохранено в колонке
    ai_explanation на момент прохождения теста, поэтому здесь не нужно
    заново обращаться к API - просто достаём готовые объяснения из БД.
    Это быстро (без сетевых запросов) и бесплатно (без новых токенов).

    Возвращает список кортежей, отсортированный по предмету и дате:
    (subject, grade, topic, question_text, student_answer,
     correct_answer, ai_explanation, created_at)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.subject, t.grade, a.topic, a.question_text,
               a.student_answer, a.correct_answer, a.ai_explanation, t.created_at
        FROM answers a
        JOIN tests t ON a.test_id = t.id
        WHERE t.username = ? AND a.is_correct = 0
        ORDER BY t.subject, t.created_at DESC
    """, (username,))
    rows = cur.fetchall()
    conn.close()
    return rows
