"""
app.py
------
Главный файл Streamlit-приложения. Отвечает только за интерфейс и
сценарий прохождения теста. Вся "умная" логика вынесена в отдельные
модули (db.py, ai_tutor.py, questions.py) — это осознанное архитектурное
решение, которое стоит подчеркнуть на защите: интерфейс не завязан
намертво на конкретного LLM-провайдера или структуру БД.

СЦЕНАРИЙ РАБОТЫ ПРИЛОЖЕНИЯ:
1. Ученик вводит имя и выбирает предмет.
2. Отвечает на несколько вопросов пробного теста (радио-кнопки).
3. По кнопке "Завершить тест" приложение:
   a. Считает баллы.
   b. Для КАЖДОГО неправильного ответа вызывает ИИ-тьютора (ai_tutor.py),
      который объясняет ошибку и путь к правильному решению.
   c. Сохраняет весь результат в SQLite (db.py).
   d. Показывает ученику результат и персональные объяснения.
"""

import concurrent.futures

import streamlit as st

import db
import ai_tutor
from questions import get_subjects, get_grades, get_questions

# --- Инициализация ---
st.set_page_config(page_title="Тьютор для сельских школ", page_icon="📘")
db.init_db()  # создаёт таблицы, если их ещё нет (безопасно вызывать при каждом запуске)

# session_state используется, чтобы Streamlit не терял ответы ученика
# при перерисовке страницы (Streamlit перезапускает скрипт на каждое взаимодействие)
if "test_started" not in st.session_state:
    st.session_state.test_started = False
if "test_finished" not in st.session_state:
    st.session_state.test_finished = False
if "results" not in st.session_state:
    st.session_state.results = None


st.title("📘 Персональный ИИ-тьютор")
st.caption("Пробный тест + разбор ошибок для учеников 8–12 классов")


# ---------- ШАГ 1: выбор ученика и предмета ----------
with st.sidebar:
    st.header("Настройки теста")
    student_name = st.text_input("Введите ваше имя", value="Ученик")
    grade = st.selectbox(
        "Выберите класс",
        get_grades(),
        format_func=lambda g: f"{g} класс",
    )
    subject = st.selectbox("Выберите предмет", get_subjects())

    if st.button("▶️ Начать тест", use_container_width=True):
        st.session_state.test_started = True
        st.session_state.test_finished = False
        st.session_state.results = None
        st.session_state.current_subject = subject
        st.session_state.current_grade = grade
        st.session_state.current_student = student_name


# ---------- ШАГ 2: прохождение теста ----------
if st.session_state.test_started and not st.session_state.test_finished:
    subject = st.session_state.current_subject
    grade = st.session_state.current_grade
    student_name = st.session_state.current_student
    questions = get_questions(subject, grade)

    st.subheader(f"Тест по предмету: {subject} ({grade} класс)")
    st.write(f"Вопросов в тесте: {len(questions)}")

    if not questions:
        st.warning(
            "Для этого предмета пока нет вопросов на выбранный класс. "
            "Попробуйте выбрать другой класс или предмет."
        )
        st.stop()

    # Собираем ответы ученика в форму, чтобы не дёргать API на каждый клик,
    # а обработать всё одним пакетом после нажатия "Завершить тест"
    with st.form("quiz_form"):
        user_answers = []
        for i, q in enumerate(questions):
            choice = st.radio(
                label=f"**{i + 1}. {q['question']}**",
                options=q["options"],
                index=None,
                key=f"q_{i}",
            )
            user_answers.append(choice)

        submitted = st.form_submit_button("✅ Завершить тест")

    if submitted:
        if any(a is None for a in user_answers):
            st.warning("Пожалуйста, ответьте на все вопросы перед завершением теста.")
        else:
            with st.spinner("ИИ-тьютор анализирует ваши ответы..."):
                # --- УСКОРЕНИЕ ---
                # Раньше объяснение для каждого неверного ответа запрашивалось
                # ПО ОЧЕРЕДИ (сначала вопрос 1, дождались ответа, потом вопрос 2
                # и т.д.), и время ожидания складывалось линейно: 3 ошибки —
                # это 3 полных цикла ожидания подряд.
                #
                # Теперь используем ThreadPoolExecutor: все запросы к API
                # отправляются ОДНОВРЕМЕННО, а мы просто ждём, пока ответит
                # самый медленный из них. Для теста с 3 ошибками это может
                # ускорить итоговое время в 2-3 раза.
                answer_records = []
                correct_count = 0
                wrong_topics = []
                wrong_items = []  # (индекс в answer_records, вопрос, ответ ученика, правильный ответ)

                # Проход 1: считаем баллы и сразу собираем список того,
                # что нужно объяснить (без вызова API — это быстро)
                for q, user_choice in zip(questions, user_answers):
                    correct_option = q["options"][q["correct_index"]]
                    is_correct = (user_choice == correct_option)

                    answer_records.append({
                        "question_text": q["question"],
                        "topic": q["topic"],
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

                # Проход 2: параллельно запрашиваем объяснения только для
                # неверных ответов (ИИ вызывается только там, где реально нужен)
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

                # Сохраняем результат теста в SQLite
                db.save_test_result(
                    student_name=student_name,
                    subject=subject,
                    grade=grade,
                    total_questions=len(questions),
                    correct_answers=correct_count,
                    answer_records=answer_records,
                )

                # Резюме и план обучения тоже не зависят друг от друга —
                # запускаем их параллельно вместо ожидания по очереди
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_summary = executor.submit(ai_tutor.get_summary_feedback, subject, wrong_topics)
                    future_plan = executor.submit(ai_tutor.get_learning_plan, subject, wrong_topics)
                    summary = future_summary.result()
                    learning_plan = future_plan.result()

            st.session_state.results = {
                "correct_count": correct_count,
                "total": len(questions),
                "answer_records": answer_records,
                "summary": summary,
                "learning_plan": learning_plan,
            }
            st.session_state.test_finished = True
            st.rerun()


# ---------- ШАГ 3: показ результатов и объяснений ----------
if st.session_state.test_finished and st.session_state.results:
    results = st.session_state.results

    st.subheader("📊 Результат теста")
    st.metric("Правильных ответов", f"{results['correct_count']} / {results['total']}")

    st.info(f"**Общая рекомендация:** {results['summary']}")

    st.subheader("📚 Персональный план обучения")
    st.markdown(results["learning_plan"])

    st.subheader("🔍 Разбор ответов")
    for i, rec in enumerate(results["answer_records"]):
        if rec["is_correct"]:
            with st.expander(f"✅ Вопрос {i + 1} — верно", expanded=False):
                st.write(rec["question_text"])
        else:
            with st.expander(f"❌ Вопрос {i + 1} — есть над чем поработать", expanded=True):
                st.write(f"**Вопрос:** {rec['question_text']}")
                st.write(f"Ваш ответ: _{rec['student_answer']}_")
                st.write(f"Правильный ответ: **{rec['correct_answer']}**")
                st.markdown("---")
                st.markdown(f"🧑‍🏫 **Объяснение тьютора:**\n\n{rec['ai_explanation']}")

    if st.button("🔁 Пройти другой тест"):
        st.session_state.test_started = False
        st.session_state.test_finished = False
        st.session_state.results = None
        st.rerun()


# ---------- Заглушка на старте ----------
if not st.session_state.test_started and not st.session_state.test_finished:
    st.write("👈 Введите имя и выберите предмет слева, затем нажмите **«Начать тест»**.")
