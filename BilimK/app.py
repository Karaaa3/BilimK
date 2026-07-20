"""
app.py
------
Главный файл Streamlit-приложения.

СЦЕНАРИЙ РАБОТЫ ПРИЛОЖЕНИЯ (обновлённая версия с аккаунтами):
1. Ученик регистрируется или входит в свой аккаунт (логин/пароль).
2. При первом входе (или если прошло 7+ дней с последней диагностики)
   приложение предлагает пройти ДИАГНОСТИЧЕСКИЙ тест — по одному вопросу
   из КАЖДОГО предмета выбранного класса. Это даёт стартовую "карту"
   сильных и слабых сторон ученика по всем предметам сразу.
3. Ученик может в любой момент пройти обычный тест по одному предмету.
4. По каждому неправильному ответу ИИ-тьютор (ai_tutor.py) объясняет
   ошибку, а в конце строит персональный план обучения с реальными
   образовательными ресурсами.
5. Раздел "Мой прогресс" показывает карту освоенных и слабых тем
   по всем предметам на основе истории ВСЕХ пройденных тестов.

Вся "умная" логика вынесена в отдельные модули (db.py, ai_tutor.py,
questions.py) — интерфейс не завязан намертво на конкретного
LLM-провайдера или структуру БД.
"""

import concurrent.futures
from datetime import datetime

import pandas as pd
import streamlit as st

import ai_tutor
import db
from questions import get_grades, get_questions, get_subjects

st.set_page_config(page_title="Тьютор для сельских школ", page_icon="📘")
db.init_db()  # создаёт/мигрирует таблицы - безопасно вызывать при каждом запуске


# ============================================================
# ОБЩАЯ ЛОГИКА ПРОВЕРКИ ОТВЕТОВ (используется и обычным тестом,
# и диагностикой - вынесена в одну функцию, чтобы не дублировать код)
# ============================================================

def grade_and_explain(questions: list, user_answers: list):
    """
    Проверяет ответы ученика и параллельно запрашивает у ИИ-тьютора
    объяснения для неверных ответов (см. комментарии в ai_tutor.py
    про ускорение через ThreadPoolExecutor).

    Каждый элемент questions должен содержать ключи:
    question, options, correct_index, topic, и опционально subject
    (нужен для диагностики, где вопросы из разных предметов вперемешку).

    Возвращает: (answer_records, correct_count, wrong_topics)
    """
    answer_records = []
    correct_count = 0
    wrong_topics = []
    wrong_items = []

    for q, user_choice in zip(questions, user_answers):
        correct_option = q["options"][q["correct_index"]]
        is_correct = (user_choice == correct_option)

        answer_records.append({
            "question_text": q["question"],
            "topic": q["topic"],
            "subject": q.get("subject"),
            "student_answer": user_choice,
            "correct_answer": correct_option,
            "is_correct": is_correct,
            "ai_explanation": None,
        })

        if is_correct:
            correct_count += 1
        else:
            wrong_topics.append(q["topic"])
            wrong_items.append((len(answer_records) - 1, q, user_choice, correct_option))

    if wrong_items:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(wrong_items)) as executor:
            futures = {
                executor.submit(
                    ai_tutor.get_ai_explanation,
                    question_text=q["question"],
                    topic=q["topic"],
                    student_answer=user_choice,
                    correct_answer=correct_option,
                ): idx
                for idx, q, user_choice, correct_option in wrong_items
            }
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                answer_records[idx]["ai_explanation"] = future.result()

    return answer_records, correct_count, wrong_topics


def render_answer_review(answer_records: list):
    """Отрисовывает разбор каждого вопроса - используется и тестом, и диагностикой."""
    for i, rec in enumerate(answer_records):
        label_prefix = f"{rec['subject']}: " if rec.get("subject") else ""
        if rec["is_correct"]:
            with st.expander(f"✅ {label_prefix}Вопрос {i + 1} — верно", expanded=False):
                st.write(rec["question_text"])
        else:
            with st.expander(f"❌ {label_prefix}Вопрос {i + 1} — есть над чем поработать", expanded=True):
                st.write(f"**Вопрос:** {rec['question_text']}")
                st.write(f"Ваш ответ: _{rec['student_answer']}_")
                st.write(f"Правильный ответ: **{rec['correct_answer']}**")
                st.markdown("---")
                st.markdown(f"🧑‍🏫 **Объяснение тьютора:**\n\n{rec['ai_explanation']}")


# ============================================================
# ЭКРАН ВХОДА / РЕГИСТРАЦИИ
# ============================================================

if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.username:
    st.title("📘 Персональный ИИ-тьютор")
    st.caption("Войдите в аккаунт, чтобы сохранять свой прогресс между занятиями")

    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input("Логин", key="login_username")
            login_password = st.text_input("Пароль", type="password", key="login_password")
            login_submitted = st.form_submit_button("Войти")

        if login_submitted:
            if db.authenticate_user(login_username, login_password):
                st.session_state.username = login_username.strip()
                st.rerun()
            else:
                st.error("Неверный логин или пароль.")

    with tab_register:
        with st.form("register_form"):
            reg_username = st.text_input("Придумайте логин", key="reg_username")
            reg_password = st.text_input("Придумайте пароль (от 4 символов)", type="password", key="reg_password")
            reg_submitted = st.form_submit_button("Зарегистрироваться")

        if reg_submitted:
            ok, message = db.register_user(reg_username, reg_password)
            if ok:
                st.success(f"{message} Теперь войдите во вкладке «Вход».")
            else:
                st.error(message)

    st.stop()  # дальше приложение не выполняется, пока пользователь не вошёл


# ============================================================
# ПОЛЬЗОВАТЕЛЬ ВОШЁЛ - ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================

username = st.session_state.username

for key, default in [
    ("test_started", False), ("test_finished", False), ("results", None),
    ("diag_started", False), ("diag_finished", False), ("diag_results", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.write(f"👋 Привет, **{username}**!")
    if st.button("Выйти", width='stretch'):
        st.session_state.username = None
        st.rerun()

    st.divider()
    page = st.radio(
        "Что хотите сделать?",
        ["Пройти тест", "Диагностика по всем предметам", "Мой прогресс"],
    )

st.title("📘 Персональный ИИ-тьютор")

# Баннер-напоминание о диагностике: при первом входе или если прошло 7+ дней
last_diag = db.get_last_diagnostic(username)
if last_diag is None:
    st.info(
        "👋 Вы ещё не проходили общую диагностику. Рекомендуем начать с неё — "
        "выберите «Диагностика по всем предметам» в меню слева, чтобы сразу "
        "увидеть карту своих сильных и слабых сторон по всем предметам."
    )
elif (datetime.now() - last_diag).days >= 7:
    st.info(
        f"📅 С последней диагностики прошло {(datetime.now() - last_diag).days} дн. "
        "Рекомендуем пройти её снова, чтобы отследить прогресс за неделю."
    )


# ============================================================
# СТРАНИЦА 1: ОБЫЧНЫЙ ТЕСТ ПО ОДНОМУ ПРЕДМЕТУ
# ============================================================

if page == "Пройти тест":
    with st.sidebar:
        st.header("Настройки теста")
        grade = st.selectbox("Выберите класс", get_grades(), format_func=lambda g: f"{g} класс")
        subject = st.selectbox("Выберите предмет", get_subjects())

        if st.button("▶️ Начать тест", width='stretch'):
            st.session_state.test_started = True
            st.session_state.test_finished = False
            st.session_state.results = None
            st.session_state.current_subject = subject
            st.session_state.current_grade = grade

    if st.session_state.test_started and not st.session_state.test_finished:
        subject = st.session_state.current_subject
        grade = st.session_state.current_grade
        questions = get_questions(subject, grade)

        st.subheader(f"Тест по предмету: {subject} ({grade} класс)")
        st.write(f"Вопросов в тесте: {len(questions)}")

        if not questions:
            st.warning("Для этого предмета пока нет вопросов на выбранный класс.")
            st.stop()

        with st.form("quiz_form"):
            user_answers = []
            for i, q in enumerate(questions):
                choice = st.radio(f"**{i + 1}. {q['question']}**", q["options"], index=None, key=f"q_{i}")
                user_answers.append(choice)
            submitted = st.form_submit_button("✅ Завершить тест")

        if submitted:
            if any(a is None for a in user_answers):
                st.warning("Пожалуйста, ответьте на все вопросы перед завершением теста.")
            else:
                with st.spinner("ИИ-тьютор анализирует ваши ответы..."):
                    answer_records, correct_count, wrong_topics = grade_and_explain(questions, user_answers)

                    db.save_test_result(
                        student_name=username, subject=subject, grade=grade,
                        total_questions=len(questions), correct_answers=correct_count,
                        answer_records=answer_records, username=username,
                    )

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        future_summary = executor.submit(ai_tutor.get_summary_feedback, subject, wrong_topics)
                        future_plan = executor.submit(ai_tutor.get_learning_plan, subject, wrong_topics)
                        summary = future_summary.result()
                        learning_plan = future_plan.result()

                st.session_state.results = {
                    "correct_count": correct_count, "total": len(questions),
                    "answer_records": answer_records, "summary": summary, "learning_plan": learning_plan,
                }
                st.session_state.test_finished = True
                st.rerun()

    if st.session_state.test_finished and st.session_state.results:
        results = st.session_state.results
        st.subheader("📊 Результат теста")
        st.metric("Правильных ответов", f"{results['correct_count']} / {results['total']}")
        st.info(f"**Общая рекомендация:** {results['summary']}")
        st.subheader("📚 Персональный план обучения")
        st.markdown(results["learning_plan"])
        st.subheader("🔍 Разбор ответов")
        render_answer_review(results["answer_records"])

        if st.button("🔁 Пройти другой тест"):
            st.session_state.test_started = False
            st.session_state.test_finished = False
            st.session_state.results = None
            st.rerun()

    if not st.session_state.test_started and not st.session_state.test_finished:
        st.write("👈 Выберите класс и предмет слева, затем нажмите **«Начать тест»**.")


# ============================================================
# СТРАНИЦА 2: ДИАГНОСТИКА ПО ВСЕМ ПРЕДМЕТАМ
# ============================================================

elif page == "Диагностика по всем предметам":
    with st.sidebar:
        st.header("Диагностика")
        diag_grade = st.selectbox("Ваш класс", get_grades(), format_func=lambda g: f"{g} класс", key="diag_grade")
        if st.button("▶️ Начать диагностику", width='stretch'):
            st.session_state.diag_started = True
            st.session_state.diag_finished = False
            st.session_state.diag_results = None
            st.session_state.current_diag_grade = diag_grade

    if st.session_state.diag_started and not st.session_state.diag_finished:
        grade = st.session_state.current_diag_grade
        # По одному (первому) вопросу из КАЖДОГО предмета этого класса
        diag_questions = []
        for subject in get_subjects():
            subject_qs = get_questions(subject, grade)
            if subject_qs:
                q = dict(subject_qs[0])
                q["subject"] = subject
                diag_questions.append(q)

        st.subheader(f"Диагностический тест — {grade} класс, все предметы")
        st.caption(f"{len(diag_questions)} вопросов — по одному из каждого предмета")

        with st.form("diag_form"):
            user_answers = []
            for i, q in enumerate(diag_questions):
                choice = st.radio(f"**{i + 1}. [{q['subject']}] {q['question']}**",
                                    q["options"], index=None, key=f"diag_q_{i}")
                user_answers.append(choice)
            submitted = st.form_submit_button("✅ Завершить диагностику")

        if submitted:
            if any(a is None for a in user_answers):
                st.warning("Пожалуйста, ответьте на все вопросы.")
            else:
                with st.spinner("ИИ-тьютор анализирует результаты диагностики..."):
                    answer_records, correct_count, wrong_topics = grade_and_explain(diag_questions, user_answers)

                    # Сохраняем отдельной записью в tests для КАЖДОГО предмета -
                    # так карта прогресса потом сможет корректно сгруппировать
                    # результаты именно по предметам, а не одной общей строкой.
                    by_subject = {}
                    for rec in answer_records:
                        by_subject.setdefault(rec["subject"], []).append(rec)

                    for subject, recs in by_subject.items():
                        db.save_test_result(
                            student_name=username, subject=subject, grade=grade,
                            total_questions=len(recs),
                            correct_answers=sum(1 for r in recs if r["is_correct"]),
                            answer_records=recs, username=username, is_diagnostic=True,
                        )
                    db.mark_diagnostic_completed(username)

                    # Общий план обучения по всем слабым темам сразу (с указанием предмета)
                    labeled_wrong_topics = [
                        f"{rec['subject']}: {rec['topic']}"
                        for rec in answer_records if not rec["is_correct"]
                    ]
                    learning_plan = ai_tutor.get_learning_plan("несколько предметов сразу", labeled_wrong_topics)

                st.session_state.diag_results = {
                    "correct_count": correct_count, "total": len(diag_questions),
                    "answer_records": answer_records, "learning_plan": learning_plan,
                }
                st.session_state.diag_finished = True
                st.rerun()

    if st.session_state.diag_finished and st.session_state.diag_results:
        results = st.session_state.diag_results
        st.subheader("📊 Результат диагностики")
        st.metric("Правильных ответов", f"{results['correct_count']} / {results['total']}")
        st.subheader("📚 Общий план обучения по итогам диагностики")
        st.markdown(results["learning_plan"])
        st.subheader("🔍 Разбор по предметам")
        render_answer_review(results["answer_records"])

        if st.button("🔁 Пройти диагностику заново"):
            st.session_state.diag_started = False
            st.session_state.diag_finished = False
            st.session_state.diag_results = None
            st.rerun()

    if not st.session_state.diag_started and not st.session_state.diag_finished:
        st.write("👈 Выберите класс слева и нажмите **«Начать диагностику»** — "
                    "это займёт всего пару минут и покажет карту по всем предметам сразу.")


# ============================================================
# СТРАНИЦА 3: МОЯ КАРТА ПРОГРЕССА
# ============================================================

elif page == "Мой прогресс":
    st.subheader("🗺️ Карта прогресса")

    progress_rows = db.get_progress_map(username)

    if not progress_rows:
        st.write(
            "Пока нет данных о прогрессе — пройдите хотя бы один тест "
            "или диагностику, и здесь появится карта ваших тем."
        )
    else:
        df = pd.DataFrame(progress_rows, columns=["Предмет", "Тема", "Верно", "Всего"])
        df["Процент"] = (df["Верно"] / df["Всего"] * 100).round(0).astype(int)

        def status_emoji(pct):
            if pct >= 70:
                return "✅ Освоено"
            elif pct >= 40:
                return "⚠️ Нужно повторить"
            return "❌ Слабое место"

        df["Статус"] = df["Процент"].apply(status_emoji)

        for subject in df["Предмет"].unique():
            st.markdown(f"### {subject}")
            subject_df = df[df["Предмет"] == subject][["Тема", "Верно", "Всего", "Процент", "Статус"]]
            st.dataframe(
                subject_df.style.background_gradient(subset=["Процент"], cmap="RdYlGn", vmin=0, vmax=100),
                width='stretch', hide_index=True,
            )

        weak_count = (df["Процент"] < 40).sum()
        if weak_count > 0:
            st.warning(f"⚠️ Слабых мест сейчас: {weak_count}. Пройдите тест по этим темам ещё раз, чтобы закрыть пробелы.")
        else:
            st.success("🎉 Явных слабых мест не найдено — отличная работа!")
