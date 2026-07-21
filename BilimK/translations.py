# -*- coding: utf-8 -*-
"""
translations.py
----------------
Все текстовые строки интерфейса на двух языках (ru / kz).

Использование в app.py:
    from translations import t
    st.title(t("app_title"))

Функция t(key) сама достаёт текущий язык из st.session_state.lang
(по умолчанию "ru", если ещё не выбран).
"""

import streamlit as st

TRANSLATIONS = {
    "ru": {
        "language_selector_label": "Язык интерфейса / Тіл",
        "app_title": "📘 Персональный ИИ-тьютор",
        "app_caption": "Пробный тест + разбор ошибок для учеников 8–11 классов",
        "login_caption": "Войдите в аккаунт, чтобы сохранять свой прогресс между занятиями",
        "tab_login": "Вход",
        "tab_register": "Регистрация",
        "login_field": "Логин",
        "password_field": "Пароль",
        "login_button": "Войти",
        "login_error": "Неверный логин или пароль.",
        "register_login_field": "Придумайте логин",
        "register_password_field": "Придумайте пароль (от 4 символов)",
        "register_button": "Зарегистрироваться",
        "register_success_suffix": "Теперь войдите во вкладке «Вход».",
        "greeting": "👋 Привет, **{username}**!",
        "logout_button": "Выйти",
        "menu_label": "Что хотите сделать?",
        "page_test": "📝 Пройти тест",
        "page_diagnostic": "🩺 Диагностика по всем предметам",
        "page_progress": "🗺️ Мой прогресс",
        "page_mistakes": "🗂️ Банк ошибок",
        "diag_never_done": (
            "👋 Вы ещё не проходили общую диагностику. Рекомендуем начать с неё — "
            "выберите «{page_diagnostic}» в меню слева, чтобы сразу увидеть карту "
            "своих сильных и слабых сторон по всем предметам."
        ),
        "diag_week_passed": (
            "📅 С последней диагностики прошло {days} дн. Рекомендуем пройти её снова, "
            "чтобы отследить прогресс за неделю."
        ),
        "settings_header": "Настройки теста",
        "grade_label": "Выберите класс",
        "grade_format": "{grade} класс",
        "subject_label": "Выберите предмет",
        "start_test_button": "▶️ Начать тест",
        "test_subheader": "Тест по предмету: {subject} ({grade} класс)",
        "questions_count": "Вопросов в тесте: {count}",
        "no_questions_warning": "Для этого предмета пока нет вопросов на выбранный класс.",
        "finish_test_button": "✅ Завершить тест",
        "answer_all_warning": "Пожалуйста, ответьте на все вопросы перед завершением теста.",
        "ai_spinner": "ИИ-тьютор анализирует ваши ответы...",
        "result_subheader": "📊 Результат теста",
        "correct_answers_metric": "Правильных ответов",
        "summary_label": "**Общая рекомендация:** {summary}",
        "plan_subheader": "📚 Персональный план обучения",
        "review_subheader": "🔍 Разбор ответов",
        "correct_expander": "✅ {prefix}Вопрос {num} — верно",
        "wrong_expander": "❌ {prefix}Вопрос {num} — есть над чем поработать",
        "question_label": "**Вопрос:** {text}",
        "your_answer_label": "Ваш ответ: _{answer}_",
        "correct_answer_label": "Правильный ответ: **{answer}**",
        "tutor_explanation_label": "🧑‍🏫 **Объяснение тьютора:**\n\n{explanation}",
        "retry_test_button": "🔁 Пройти другой тест",
        "test_idle_hint": "👈 Выберите класс и предмет слева, затем нажмите **«Начать тест»**.",
        "diag_header": "Диагностика",
        "diag_grade_label": "Ваш класс",
        "start_diag_button": "▶️ Начать диагностику",
        "diag_subheader": "Диагностический тест — {grade} класс, все предметы",
        "diag_caption": "{count} вопросов — по одному из каждого предмета",
        "finish_diag_button": "✅ Завершить диагностику",
        "answer_all_diag_warning": "Пожалуйста, ответьте на все вопросы.",
        "diag_spinner": "ИИ-тьютор анализирует результаты диагностики...",
        "diag_result_subheader": "📊 Результат диагностики",
        "diag_plan_subheader": "📚 Общий план обучения по итогам диагностики",
        "diag_review_subheader": "🔍 Разбор по предметам",
        "retry_diag_button": "🔁 Пройти диагностику заново",
        "diag_idle_hint": (
            "👈 Выберите класс слева и нажмите **«Начать диагностику»** — "
            "это займёт всего пару минут и покажет карту по всем предметам сразу."
        ),
        "progress_subheader": "🗺️ Карта прогресса",
        "progress_empty": (
            "Пока нет данных о прогрессе — пройдите хотя бы один тест "
            "или диагностику, и здесь появится карта ваших тем."
        ),
        "status_mastered": "✅ Освоено",
        "status_review": "⚠️ Нужно повторить",
        "status_weak": "❌ Слабое место",
        "col_subject": "Предмет", "col_topic": "Тема", "col_correct": "Верно",
        "col_total": "Всего", "col_percent": "Процент", "col_status": "Статус",
        "weak_topics_warning": "⚠️ Слабых мест сейчас: {count}. Пройдите тест по этим темам ещё раз, чтобы закрыть пробелы.",
        "no_weak_topics": "🎉 Явных слабых мест не найдено — отличная работа!",
        "mistakes_subheader": "🗂️ Банк ошибок",
        "mistakes_caption": (
            "Здесь автоматически собираются все ваши неверные ответы со всех "
            "пройденных тестов и диагностик - ничего вручную сохранять не нужно."
        ),
        "mistakes_empty": (
            "Пока ошибок не накопилось — либо вы ещё не проходили тесты, "
            "либо ответили на всё верно. Отличный результат!"
        ),
        "top_weak_label": "**Чаще всего ошибки встречаются в темах:**",
        "top_weak_item": "- {subject} → {topic} ({count} ошибок)",
        "filter_by_subject": "Показать ошибки по предмету:",
        "all_subjects_option": "Все предметы",
        "mistake_expander": "❌ [{subject}, {grade} класс] {topic} — {date}",
    },
    "kz": {
        "language_selector_label": "Язык интерфейса / Тіл",
        "app_title": "📘 Жеке ИИ-тьютор",
        "app_caption": "8–11 сынып оқушыларына арналған сынама тест және қателерді талдау",
        "login_caption": "Прогресіңізді сақтау үшін аккаунтқа кіріңіз",
        "tab_login": "Кіру",
        "tab_register": "Тіркелу",
        "login_field": "Логин",
        "password_field": "Құпия сөз",
        "login_button": "Кіру",
        "login_error": "Логин немесе құпия сөз қате.",
        "register_login_field": "Логин ойлап табыңыз",
        "register_password_field": "Құпия сөз ойлап табыңыз (кемінде 4 таңба)",
        "register_button": "Тіркелу",
        "register_success_suffix": "Енді «Кіру» қойындысында кіріңіз.",
        "greeting": "👋 Сәлем, **{username}**!",
        "logout_button": "Шығу",
        "menu_label": "Не істегіңіз келеді?",
        "page_test": "📝 Тест тапсыру",
        "page_diagnostic": "🩺 Барлық пәндер бойынша диагностика",
        "page_progress": "🗺️ Менің прогресім",
        "page_mistakes": "🗂️ Қателер банкі",
        "diag_never_done": (
            "👋 Сіз әлі жалпы диагностика тапсырмадыңыз. Одан бастауды ұсынамыз — "
            "сол жақтағы мәзірден «{page_diagnostic}» тармағын таңдаңыз, барлық пәндер "
            "бойынша күшті және әлсіз жақтарыңыздың картасын бірден көресіз."
        ),
        "diag_week_passed": (
            "📅 Соңғы диагностикадан бері {days} күн өтті. Аптадағы прогресті "
            "бақылау үшін оны қайта тапсыруды ұсынамыз."
        ),
        "settings_header": "Тест баптаулары",
        "grade_label": "Сыныпты таңдаңыз",
        "grade_format": "{grade} сынып",
        "subject_label": "Пәнді таңдаңыз",
        "start_test_button": "▶️ Тестті бастау",
        "test_subheader": "{subject} пәні бойынша тест ({grade} сынып)",
        "questions_count": "Тесттегі сұрақтар саны: {count}",
        "no_questions_warning": "Бұл пән бойынша таңдалған сыныпқа сұрақтар әзірге жоқ.",
        "finish_test_button": "✅ Тестті аяқтау",
        "answer_all_warning": "Тестті аяқтамас бұрын барлық сұрақтарға жауап беріңіз.",
        "ai_spinner": "ИИ-тьютор жауаптарыңызды талдап жатыр...",
        "result_subheader": "📊 Тест нәтижесі",
        "correct_answers_metric": "Дұрыс жауаптар",
        "summary_label": "**Жалпы ұсыныс:** {summary}",
        "plan_subheader": "📚 Жеке оқу жоспары",
        "review_subheader": "🔍 Жауаптарды талдау",
        "correct_expander": "✅ {prefix}Сұрақ {num} — дұрыс",
        "wrong_expander": "❌ {prefix}Сұрақ {num} — қайталау керек",
        "question_label": "**Сұрақ:** {text}",
        "your_answer_label": "Сіздің жауабыңыз: _{answer}_",
        "correct_answer_label": "Дұрыс жауап: **{answer}**",
        "tutor_explanation_label": "🧑‍🏫 **Тьютордың түсіндірмесі:**\n\n{explanation}",
        "retry_test_button": "🔁 Басқа тест тапсыру",
        "test_idle_hint": "👈 Сол жақтан сынып пен пәнді таңдап, **«Тестті бастау»** батырмасын басыңыз.",
        "diag_header": "Диагностика",
        "diag_grade_label": "Сіздің сыныбыңыз",
        "start_diag_button": "▶️ Диагностиканы бастау",
        "diag_subheader": "Диагностикалық тест — {grade} сынып, барлық пәндер",
        "diag_caption": "{count} сұрақ — әр пәннен бір-бірден",
        "finish_diag_button": "✅ Диагностиканы аяқтау",
        "answer_all_diag_warning": "Барлық сұрақтарға жауап беріңіз.",
        "diag_spinner": "ИИ-тьютор диагностика нәтижелерін талдап жатыр...",
        "diag_result_subheader": "📊 Диагностика нәтижесі",
        "diag_plan_subheader": "📚 Диагностика қорытындысы бойынша жалпы оқу жоспары",
        "diag_review_subheader": "🔍 Пәндер бойынша талдау",
        "retry_diag_button": "🔁 Диагностиканы қайта тапсыру",
        "diag_idle_hint": (
            "👈 Сол жақтан сыныпты таңдап, **«Диагностиканы бастау»** батырмасын басыңыз — "
            "бұл небәрі бірнеше минут алады және барлық пәндер бойынша картаны бірден көрсетеді."
        ),
        "progress_subheader": "🗺️ Прогресс картасы",
        "progress_empty": (
            "Прогресс туралы деректер әлі жоқ — кемінде бір тест немесе диагностика "
            "тапсырыңыз, сонда осында тақырыптарыңыздың картасы пайда болады."
        ),
        "status_mastered": "✅ Меңгерілген",
        "status_review": "⚠️ Қайталау керек",
        "status_weak": "❌ Әлсіз тұс",
        "col_subject": "Пән", "col_topic": "Тақырып", "col_correct": "Дұрыс",
        "col_total": "Барлығы", "col_percent": "Пайыз", "col_status": "Статус",
        "weak_topics_warning": "⚠️ Қазіргі әлсіз тұстар саны: {count}. Пробелдерді жабу үшін осы тақырыптар бойынша тестті қайта тапсырыңыз.",
        "no_weak_topics": "🎉 Айқын әлсіз тұстар табылған жоқ — керемет жұмыс!",
        "mistakes_subheader": "🗂️ Қателер банкі",
        "mistakes_caption": (
            "Мұнда барлық тапсырылған тесттер мен диагностикалардан барлық қате "
            "жауаптарыңыз автоматты түрде жиналады - қолмен ештеңе сақтаудың қажеті жоқ."
        ),
        "mistakes_empty": (
            "Әзірге қателер жиналған жоқ — не сіз әлі тест тапсырмадыңыз, "
            "не барлығына дұрыс жауап бердіңіз. Тамаша нәтиже!"
        ),
        "top_weak_label": "**Қателер жиі кездесетін тақырыптар:**",
        "top_weak_item": "- {subject} → {topic} ({count} қате)",
        "filter_by_subject": "Пән бойынша қателерді көрсету:",
        "all_subjects_option": "Барлық пәндер",
        "mistake_expander": "❌ [{subject}, {grade} сынып] {topic} — {date}",
    },
}


def t(key: str, **kwargs) -> str:
    """
    Возвращает переведённую строку для текущего языка интерфейса
    (берётся из st.session_state.lang, по умолчанию "ru").
    Поддерживает подстановку через .format(**kwargs).
    """
    lang = st.session_state.get("lang", "ru")
    template = TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
