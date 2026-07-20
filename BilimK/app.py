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

import streamlit as st

import db
import ai_tutor
from questions import get_subjects, get_questions

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
    subject = st.selectbox("Выберите предмет", get_subjects())

    if st.button("▶️ Начать тест", use_container_width=True):
        st.session_state.test_started = True
        st.session_state.test_finished = False
        st.session_state.results = None
        st.session_state.current_subject = subject
        st.session_state.current_student = student_name


# ---------- ШАГ 2: прохождение теста ----------
if st.session_state.test_started and not st.session_state.test_finished:
    subject = st.session_state.current_subject
    student_name = st.session_state.current_student
    questions = get_questions(subject)

    st.subheader(f"Тест по предмету: {subject}")
    st.write(f"Вопросов в тесте: {len(questions)}")

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
                answer_records = []
                correct_count = 0
                wrong_topics = []

                for q, user_choice in zip(questions, user_answers):
                    correct_option = q["options"][q["correct_index"]]
                    is_correct = (user_choice == correct_option)

                    explanation = None
                    if is_correct:
                        correct_count += 1
                    else:
                        # ---- КЛЮЧЕВОЙ МОМЕНТ ИИ-ТЬЮТОРА ----
                        # Вызываем LLM только для неверных ответов.
                        # Мы передаём модели уже известный правильный ответ,
                        # чтобы она не "угадывала" его заново, а объясняла разницу.
                        explanation = ai_tutor.get_ai_explanation(
                            question_text=q["question"],
                            topic=q["topic"],
                            student_answer=user_choice,
                            correct_answer=correct_option,
                        )
                        wrong_topics.append(q["topic"])

                    answer_records.append({
                        "question_text": q["question"],
                        "topic": q["topic"],
                        "student_answer": user_choice,
                        "correct_answer": correct_option,
                        "is_correct": is_correct,
                        "ai_explanation": explanation,
                    })

                # Сохраняем результат теста в SQLite
                db.save_test_result(
                    student_name=student_name,
                    subject=subject,
                    total_questions=len(questions),
                    correct_answers=correct_count,
                    answer_records=answer_records,
                )

                # Общая рекомендация по итогам теста (опционально, одна доп. LLM-вызов)
                summary = ai_tutor.get_summary_feedback(subject, wrong_topics)

            st.session_state.results = {
                "correct_count": correct_count,
                "total": len(questions),
                "answer_records": answer_records,
                "summary": summary,
            }
            st.session_state.test_finished = True
            st.rerun()


# ---------- ШАГ 3: показ результатов и объяснений ----------
if st.session_state.test_finished and st.session_state.results:
    results = st.session_state.results

    st.subheader("📊 Результат теста")
    st.metric("Правильных ответов", f"{results['correct_count']} / {results['total']}")

    st.info(f"**Общая рекомендация:** {results['summary']}")

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
