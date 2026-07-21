"""
app.py
------
Главный файл Streamlit-приложения.

СЦЕНАРИЙ РАБОТЫ ПРИЛОЖЕНИЯ (с аккаунтами и двумя языками интерфейса):
1. Ученик выбирает язык интерфейса (русский/казахский) и регистрируется
   или входит в свой аккаунт.
2. Язык интерфейса определяет СТРУКТУРУ ПРЕДМЕТОВ (тип школы):
   - RU -> "Русский язык" и "Русская литература" отдельно,
     "Қазақ тілі мен әдебиеті" вместе (структура русской школы).
   - KZ -> "Қазақ тілі" и "Қазақ әдебиеті" отдельно,
     "Орыс тілі мен әдебиеті" вместе (структура казахской школы).
   Вопросы по "предметным" дисциплинам (Алгебра, Физика, История и т.д.)
   показываются на выбранном языке интерфейса; языковые/литературные
   предметы всегда на своём фиксированном языке (см. questions.py).
3. При первом входе (или если прошло 7+ дней с последней диагностики)
   приложение предлагает пройти ДИАГНОСТИЧЕСКИЙ тест по всем предметам.
4. Ученик может в любой момент пройти обычный тест по одному предмету.
5. По каждому неправильному ответу ИИ-тьютор объясняет ошибку НА ТОМ ЖЕ
   ЯЗЫКЕ, что и вопрос, а в конце строит план обучения с реальными
   образовательными ресурсами.
6. "Мой прогресс" и "Банк ошибок" показывают карту освоенных/слабых тем
   и накопленные ошибки по истории всех пройденных тестов.
"""

import concurrent.futures
import random
from datetime import datetime

import pandas as pd
import streamlit as st

import ai_tutor
import branding
import db
from questions import get_grades, get_questions, get_subjects
from translations import t

st.set_page_config(page_title="BilimK", page_icon="🏔")
db.init_db()  # создаёт/мигрирует таблицы - безопасно вызывать при каждом запуске
st.markdown(branding.inject_custom_css(), unsafe_allow_html=True)

if "lang" not in st.session_state:
    st.session_state.lang = "ru"


def shuffle_questions(questions: list) -> list:
    """
    Перемешивает порядок вопросов И порядок вариантов ответа внутри
    каждого вопроса, чтобы повторное прохождение теста не выглядело
    буквально идентичным. Возвращает НОВЫЙ список с пересчитанным
    correct_index под новый порядок вариантов.
    """
    shuffled = []
    for q in random.sample(questions, len(questions)):
        correct_text = q["options"][q["correct_index"]]
        new_options = q["options"][:]
        random.shuffle(new_options)
        new_q = dict(q)
        new_q["options"] = new_options
        new_q["correct_index"] = new_options.index(correct_text)
        shuffled.append(new_q)
    return shuffled


def grade_and_explain(questions: list, user_answers: list, lang: str):
    """
    Проверяет ответы ученика и параллельно запрашивает у ИИ-тьютора
    объяснения для неверных ответов - НА ЯЗЫКЕ lang, чтобы объяснение
    совпадало с языком самого вопроса.

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
                    lang=lang,
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
        prefix = f"[{rec['subject']}] " if rec.get("subject") else ""
        if rec["is_correct"]:
            with st.expander(t("correct_expander", prefix=prefix, num=i + 1), expanded=False):
                st.write(rec["question_text"])
        else:
            with st.expander(t("wrong_expander", prefix=prefix, num=i + 1), expanded=True):
                st.write(t("question_label", text=rec["question_text"]))
                st.write(t("your_answer_label", answer=rec["student_answer"]))
                st.write(t("correct_answer_label", answer=rec["correct_answer"]))
                st.markdown("---")
                st.markdown(t("tutor_explanation_label", explanation=rec["ai_explanation"]))


# ============================================================
# ЭКРАН ВХОДА / РЕГИСТРАЦИИ (+ выбор языка интерфейса)
# ============================================================

if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.username:
    lang_choice = st.radio(
        t("language_selector_label"), ["Русский", "Қазақша"],
        index=0 if st.session_state.lang == "ru" else 1, horizontal=True,
        key="lang_selector",
    )
    st.session_state.lang = "ru" if lang_choice == "Русский" else "kz"

    col_logo, col_header = st.columns([1, 4])
    with col_logo:
        st.image("assets/logo.png", width=110)
    with col_header:
        st.markdown(
            branding.render_header(t("app_title"), t("app_tagline"), t("app_subtitle")),
            unsafe_allow_html=True,
        )
    st.caption(t("login_caption"))

    tab_login, tab_register = st.tabs([t("tab_login"), t("tab_register")])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input(t("login_field"), key="login_username")
            login_password = st.text_input(t("password_field"), type="password", key="login_password")
            login_submitted = st.form_submit_button(t("login_button"))

        if login_submitted:
            if db.authenticate_user(login_username, login_password):
                st.session_state.username = login_username.strip()
                st.rerun()
            else:
                st.error(t("login_error"))

    with tab_register:
        with st.form("register_form"):
            reg_username = st.text_input(t("register_login_field"), key="reg_username")
            reg_password = st.text_input(t("register_password_field"), type="password", key="reg_password")
            reg_submitted = st.form_submit_button(t("register_button"))

        if reg_submitted:
            ok, message = db.register_user(reg_username, reg_password)
            if ok:
                st.success(f"{message} {t('register_success_suffix')}")
            else:
                st.error(message)

    st.stop()  # дальше приложение не выполняется, пока пользователь не вошёл


# ============================================================
# ПОЛЬЗОВАТЕЛЬ ВОШЁЛ - ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================

username = st.session_state.username
lang = st.session_state.lang

for key, default in [
    ("test_started", False), ("test_finished", False), ("results", None),
    ("diag_started", False), ("diag_finished", False), ("diag_results", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.markdown(
        f'<div style="text-align:center; padding: 6px 0 14px 0;">'
        f'<span style="font-size:1.6rem;">🏔</span> '
        f'<span style="font-size:1.3rem; font-weight:800; color:{branding.NAVY};">BilimK</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        t("menu_label"),
        [t("page_test"), t("page_diagnostic"), t("page_progress"), t("page_mistakes")],
    )

    st.divider()
    st.write(t("greeting", username=username))
    if st.button(t("logout_button"), width='stretch'):
        st.session_state.username = None
        st.rerun()

st.markdown(
    branding.render_header(t("app_title"), t("app_tagline"), t("app_subtitle")),
    unsafe_allow_html=True,
)

# ============================================================
# ДАШБОРД: показывается на любой странице сверху - для новых учеников
# (ещё нет данных о прогрессе) показываем логотип и мотивирующую цитату,
# для вернувшихся - карточки с рекомендацией на сегодня, серией и
# общим прогрессом. Это решает жалобу "главная страница выглядит пустой".
# ============================================================

progress_rows = db.get_progress_map(username)

if not progress_rows:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.image("assets/logo.png", width=140)
        st.markdown(
            f'<div class="bilimk-quote">{t("new_user_quote")}</div>',
            unsafe_allow_html=True,
        )
    st.info(t("start_diagnostic_cta"))
else:
    dashboard_df = pd.DataFrame(progress_rows, columns=["subject", "topic", "correct", "total"])
    dashboard_df["pct"] = dashboard_df["correct"] / dashboard_df["total"] * 100
    overall_pct = round(dashboard_df["pct"].mean())
    weakest = dashboard_df.sort_values("pct").iloc[0]
    streak_days = db.get_streak(username)
    today_answered = db.get_today_answers_count(username)
    daily_goal = 10

    st.write(t("dashboard_welcome", username=username))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f'<div class="bilimk-card">'
            f'<b>{t("dashboard_recommended")}</b><br>📚 {weakest["subject"]}'
            f'{branding.render_mini_progress(round(weakest["pct"]))}'
            f'<span style="font-size:0.82rem; color:{branding.NAVY};">{round(weakest["pct"])}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="bilimk-card" style="text-align:center;">'
            f'{t("dashboard_daily_goal")}<br>'
            f'<span style="font-size:1.25rem; font-weight:700; color:{branding.NAVY};">'
            f'{t("dashboard_daily_goal_progress", done=today_answered, goal=daily_goal)}</span><br><br>'
            f'{branding.render_streak_badge(streak_days, t("dashboard_streak"))}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="bilimk-card" style="text-align:center;">'
            f'{t("dashboard_overall_progress")}<br>'
            f'<span style="font-size:1.9rem; font-weight:800; color:{branding.TEAL};">{overall_pct}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# Баннер-напоминание о диагностике: при первом входе или если прошло 7+ дней
last_diag = db.get_last_diagnostic(username)
if last_diag is None:
    st.info(t("diag_never_done", page_diagnostic=t("page_diagnostic")))
elif (datetime.now() - last_diag).days >= 7:
    st.info(t("diag_week_passed", days=(datetime.now() - last_diag).days))


# ============================================================
# СТРАНИЦА 1: ОБЫЧНЫЙ ТЕСТ ПО ОДНОМУ ПРЕДМЕТУ
# ============================================================

if page == t("page_test"):
    with st.sidebar:
        st.header(t("settings_header"))
        grade = st.selectbox(t("grade_label"), get_grades(), format_func=lambda g: t("grade_format", grade=g))
        subject = st.selectbox(t("subject_label"), get_subjects(lang))

        if st.button(t("start_test_button"), width='stretch'):
            st.session_state.test_started = True
            st.session_state.test_finished = False
            st.session_state.results = None
            st.session_state.current_subject = subject
            st.session_state.current_grade = grade
            # Перемешиваем ОДИН РАЗ при старте и фиксируем в сессии -
            # иначе порядок вопросов/вариантов "плыл" бы при каждом
            # клике (Streamlit пересчитывает весь скрипт заново
            # на любое взаимодействие, включая выбор ответа).
            st.session_state.current_questions = shuffle_questions(get_questions(subject, grade, lang))

    if st.session_state.test_started and not st.session_state.test_finished:
        subject = st.session_state.current_subject
        grade = st.session_state.current_grade
        questions = st.session_state.current_questions

        st.subheader(t("test_subheader", subject=subject, grade=grade))
        st.write(t("questions_count", count=len(questions)))

        if not questions:
            st.warning(t("no_questions_warning"))
            st.stop()

        with st.form("quiz_form"):
            user_answers = []
            for i, q in enumerate(questions):
                choice = st.radio(f"**{i + 1}. {q['question']}**", q["options"], index=None, key=f"q_{i}")
                user_answers.append(choice)
            submitted = st.form_submit_button(t("finish_test_button"))

        if submitted:
            if any(a is None for a in user_answers):
                st.warning(t("answer_all_warning"))
            else:
                with st.spinner(t("ai_spinner")):
                    answer_records, correct_count, wrong_topics = grade_and_explain(questions, user_answers, lang)

                    db.save_test_result(
                        student_name=username, subject=subject, grade=grade,
                        total_questions=len(questions), correct_answers=correct_count,
                        answer_records=answer_records, username=username,
                    )

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        future_summary = executor.submit(ai_tutor.get_summary_feedback, subject, wrong_topics, lang)
                        future_plan = executor.submit(ai_tutor.get_learning_plan, subject, wrong_topics, lang)
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
        st.subheader(t("result_subheader"))
        st.metric(t("correct_answers_metric"), f"{results['correct_count']} / {results['total']}")
        st.info(t("summary_label", summary=results["summary"]))
        st.subheader(t("plan_subheader"))
        st.markdown(results["learning_plan"])
        st.subheader(t("review_subheader"))
        render_answer_review(results["answer_records"])

        if st.button(t("retry_test_button")):
            st.session_state.test_started = False
            st.session_state.test_finished = False
            st.session_state.results = None
            st.rerun()

    if not st.session_state.test_started and not st.session_state.test_finished:
        st.write(t("test_idle_hint"))


# ============================================================
# СТРАНИЦА 2: ДИАГНОСТИКА ПО ВСЕМ ПРЕДМЕТАМ
# ============================================================

elif page == t("page_diagnostic"):
    with st.sidebar:
        st.header(t("diag_header"))
        diag_grade = st.selectbox(t("diag_grade_label"), get_grades(),
                                     format_func=lambda g: t("grade_format", grade=g), key="diag_grade")
        if st.button(t("start_diag_button"), width='stretch'):
            st.session_state.diag_started = True
            st.session_state.diag_finished = False
            st.session_state.diag_results = None
            st.session_state.current_diag_grade = diag_grade

            # По одному СЛУЧАЙНОМУ вопросу из КАЖДОГО предмета -
            # выбирается один раз здесь, при старте, и фиксируется
            # в сессии, чтобы не менялся при каждом клике по радио-кнопке.
            diag_questions = []
            for subj in get_subjects(lang):
                subject_qs = get_questions(subj, diag_grade, lang)
                if subject_qs:
                    q = dict(random.choice(subject_qs))
                    q["subject"] = subj
                    diag_questions.append(q)
            st.session_state.diag_questions = shuffle_questions(diag_questions)

    if st.session_state.diag_started and not st.session_state.diag_finished:
        grade = st.session_state.current_diag_grade
        diag_questions = st.session_state.diag_questions

        st.subheader(t("diag_subheader", grade=grade))
        st.caption(t("diag_caption", count=len(diag_questions)))

        with st.form("diag_form"):
            user_answers = []
            for i, q in enumerate(diag_questions):
                choice = st.radio(f"**{i + 1}. [{q['subject']}] {q['question']}**",
                                    q["options"], index=None, key=f"diag_q_{i}")
                user_answers.append(choice)
            submitted = st.form_submit_button(t("finish_diag_button"))

        if submitted:
            if any(a is None for a in user_answers):
                st.warning(t("answer_all_diag_warning"))
            else:
                with st.spinner(t("diag_spinner")):
                    answer_records, correct_count, wrong_topics = grade_and_explain(diag_questions, user_answers, lang)

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
                    learning_plan = ai_tutor.get_learning_plan(
                        "несколько предметов сразу", labeled_wrong_topics, lang
                    )

                st.session_state.diag_results = {
                    "correct_count": correct_count, "total": len(diag_questions),
                    "answer_records": answer_records, "learning_plan": learning_plan,
                }
                st.session_state.diag_finished = True
                st.rerun()

    if st.session_state.diag_finished and st.session_state.diag_results:
        results = st.session_state.diag_results
        st.subheader(t("diag_result_subheader"))
        st.metric(t("correct_answers_metric"), f"{results['correct_count']} / {results['total']}")
        st.subheader(t("diag_plan_subheader"))
        st.markdown(results["learning_plan"])
        st.subheader(t("diag_review_subheader"))
        render_answer_review(results["answer_records"])

        if st.button(t("retry_diag_button")):
            st.session_state.diag_started = False
            st.session_state.diag_finished = False
            st.session_state.diag_results = None
            st.rerun()

    if not st.session_state.diag_started and not st.session_state.diag_finished:
        st.write(t("diag_idle_hint"))


# ============================================================
# СТРАНИЦА 3: МОЯ КАРТА ПРОГРЕССА
# ============================================================

elif page == t("page_progress"):
    st.subheader(t("progress_subheader"))

    progress_rows = db.get_progress_map(username)

    if not progress_rows:
        st.write(t("progress_empty"))
    else:
        col_subject, col_topic, col_correct, col_total = (
            t("col_subject"), t("col_topic"), t("col_correct"), t("col_total")
        )
        col_percent, col_status = t("col_percent"), t("col_status")

        df = pd.DataFrame(progress_rows, columns=[col_subject, col_topic, col_correct, col_total])
        df[col_percent] = (df[col_correct] / df[col_total] * 100).round(0).astype(int)

        # "Восхождение на гору" - буквальная визуализация общего прогресса,
        # используя фирменный мотив BilimK (гора с флагом на вершине).
        overall_pct = round(df[col_percent].mean())
        col_climb, col_climb_label = st.columns([1, 1])
        with col_climb:
            st.markdown(branding.render_mountain_climb(overall_pct), unsafe_allow_html=True)
        with col_climb_label:
            st.markdown(
                f'<div style="padding-top:40px;">'
                f'<span style="font-size:2rem; font-weight:800; color:{branding.TEAL};">{overall_pct}%</span><br>'
                f'<span style="color:{branding.NAVY};">{t("dashboard_overall_progress")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        def status_label(pct):
            if pct >= 70:
                return t("status_mastered")
            elif pct >= 40:
                return t("status_review")
            return t("status_weak")

        df[col_status] = df[col_percent].apply(status_label)

        def highlight_percent(row):
            """
            Раскрашивает строку таблицы вручную по проценту освоения темы.
            Специально НЕ используем Styler.background_gradient(), потому
            что он требует matplotlib - лишнюю тяжёлую зависимость, которой
            может не оказаться на сервере (именно это вызвало ImportError
            на Streamlit Cloud). Простая раскраска по порогам не требует
            вообще никаких дополнительных библиотек.

            ВАЖНО: явно задаём color: black - иначе в тёмной теме Streamlit
            текст остаётся светлым по умолчанию и на светлом фоне ячейки
            становится практически нечитаемым.
            """
            pct = row[col_percent]
            if pct >= 70:
                style = "background-color: #d4edda; color: black"  # мягкий зелёный
            elif pct >= 40:
                style = "background-color: #fff3cd; color: black"  # мягкий жёлтый
            else:
                style = "background-color: #f8d7da; color: black"  # мягкий красный
            return [style] * len(row)

        for subject in df[col_subject].unique():
            st.markdown(f"### {subject}")
            subject_df = df[df[col_subject] == subject][[col_topic, col_correct, col_total, col_percent, col_status]]
            st.dataframe(
                subject_df.style.apply(highlight_percent, axis=1),
                width='stretch', hide_index=True,
            )

        weak_count = (df[col_percent] < 40).sum()
        if weak_count > 0:
            st.warning(t("weak_topics_warning", count=weak_count))
        else:
            st.success(t("no_weak_topics"))


# ============================================================
# СТРАНИЦА 4: БАНК ОШИБОК
# ============================================================
# Идея: ученик сдаёт тесты по разным предметам в разное время,
# и вместо того чтобы вручную выписывать себе, где он ошибся,
# приложение само копит ВСЕ его ошибки в одном месте - с уже готовым
# объяснением от ИИ-тьютора (оно сохранено ещё в момент прохождения
# теста, поэтому здесь ничего заново не генерируется).

elif page == t("page_mistakes"):
    st.subheader(t("mistakes_subheader"))
    st.caption(t("mistakes_caption"))

    mistakes = db.get_mistake_bank(username)

    if not mistakes:
        st.write(t("mistakes_empty"))
    else:
        # Сводка тремя карточками: всего ошибок, слабых тем, исправлено.
        # "Исправлено" - темы, где раньше были ошибки, а сейчас (по карте
        # прогресса) освоенность уже >=70% - то есть ученик закрыл пробел.
        progress_rows_for_stats = db.get_progress_map(username)
        progress_by_topic = {(s, tp): (c / tt * 100 if tt else 0) for s, tp, c, tt in progress_rows_for_stats}

        mistake_topics = {(row[0], row[2]) for row in mistakes}  # (subject, topic)
        weak_topics_count = sum(1 for key, pct in progress_by_topic.items() if pct < 40)
        fixed_count = sum(1 for key in mistake_topics if progress_by_topic.get(key, 0) >= 70)

        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.markdown(
                branding.render_stat_card("⚠️", len(mistakes), t("stat_total_mistakes"), branding.NAVY),
                unsafe_allow_html=True,
            )
        with stat_col2:
            st.markdown(
                branding.render_stat_card("📚", weak_topics_count, t("stat_weak_topics"), "#C0392B"),
                unsafe_allow_html=True,
            )
        with stat_col3:
            st.markdown(
                branding.render_stat_card("✅", fixed_count, t("stat_fixed_topics"), branding.TEAL),
                unsafe_allow_html=True,
            )
        st.write("")

        # Сводка: по каким темам ошибок больше всего
        topic_counts = {}
        for row in mistakes:
            subject, grade, topic, *_ = row
            key = (subject, topic)
            topic_counts[key] = topic_counts.get(key, 0) + 1

        top_weak = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        st.markdown(t("top_weak_label"))
        for (subject, topic), count in top_weak:
            st.write(t("top_weak_item", subject=subject, topic=topic, count=count))

        st.divider()

        # Группируем подробный список по предметам, свежие ошибки сверху
        subjects_with_mistakes = []
        for row in mistakes:
            if row[0] not in subjects_with_mistakes:
                subjects_with_mistakes.append(row[0])

        all_subjects_label = t("all_subjects_option")
        selected_subject = st.selectbox(t("filter_by_subject"), [all_subjects_label] + subjects_with_mistakes)

        for subject, grade, topic, question_text, student_answer, correct_answer, ai_explanation, created_at in mistakes:
            if selected_subject != all_subjects_label and subject != selected_subject:
                continue

            date_str = created_at.split("T")[0] if created_at else ""
            with st.expander(t("mistake_expander", subject=subject, grade=grade, topic=topic, date=date_str)):
                st.write(t("question_label", text=question_text))
                st.write(t("your_answer_label", answer=student_answer))
                st.write(t("correct_answer_label", answer=correct_answer))
                if ai_explanation:
                    st.markdown("---")
                    st.markdown(t("tutor_explanation_label", explanation=ai_explanation))
