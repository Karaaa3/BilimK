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

import os
import sqlite3
from datetime import datetime

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

    conn.commit()
    conn.close()


def save_test_result(student_name: str, subject: str, grade: int, total_questions: int,
                      correct_answers: int, answer_records: list) -> int:
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

    Возвращает id созданной записи в tests (пригодится для истории/дашборда).
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tests (student_name, subject, grade, total_questions, correct_answers, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_name, subject, grade, total_questions, correct_answers,
          datetime.now().isoformat(timespec="seconds")))

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
    return test_id


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
