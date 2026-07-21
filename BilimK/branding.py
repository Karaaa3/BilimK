# -*- coding: utf-8 -*-
"""
branding.py
-----------
Фирменный стиль BilimK, вынесенный отдельно от app.py, чтобы:
1. Не захламлять основную логику приложения HTML/CSS-строками.
2. Иметь одно место, где меняются цвета/шрифты/отступы, если бренд
   поменяется в будущем.

Фирменные цвета:
- Бирюзовый  #27A295 — кнопки, прогресс, успешные темы, ссылки, акценты
- Тёмно-лазурный #11547D — заголовки, текст меню, логотип
- Белый #FFFFFF — карточки и фон

Основной визуальный мотив бренда — ГОРА (эмблема сайта): используется
и в шапке, и в виде буквального "восхождения" на странице прогресса.
"""

TEAL = "#27A295"
NAVY = "#11547D"
WHITE = "#FFFFFF"
TEAL_SOFT = "#E6F5F3"   # мягкий бирюзовый фон для карточек/бейджей
NAVY_SOFT = "#EAF1F5"


def inject_custom_css():
    """
    Возвращает <style>-блок с общими классами для карточек, шапки,
    бейджа серии и статистических плашек. Вызывается один раз в начале
    app.py через st.markdown(branding.inject_custom_css(), unsafe_allow_html=True).
    """
    return f"""
    <style>
    /* Карточка общего назначения (фон/тень/скругление) */
    .bilimk-card {{
        background: {WHITE};
        border: 1px solid {NAVY_SOFT};
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 2px 10px rgba(17, 84, 125, 0.07);
        margin-bottom: 14px;
    }}

    /* Фирменная шапка с градиентом бренда */
    .bilimk-header {{
        background: linear-gradient(135deg, {NAVY} 0%, {TEAL} 100%);
        border-radius: 18px;
        padding: 26px 30px;
        color: {WHITE};
        margin-bottom: 18px;
    }}
    .bilimk-header h1 {{
        color: {WHITE} !important;
        margin: 0 0 4px 0;
        font-size: 2rem;
        font-weight: 800;
    }}
    .bilimk-header p {{
        color: {WHITE} !important;
        opacity: 0.92;
        margin: 0;
        font-size: 1.05rem;
    }}
    .bilimk-header .bilimk-subtitle {{
        opacity: 0.8;
        font-size: 0.92rem;
        margin-top: 6px;
    }}

    /* Плашка статистики (банк ошибок, дашборд) */
    .bilimk-stat {{
        background: {WHITE};
        border: 1px solid {NAVY_SOFT};
        border-radius: 14px;
        padding: 18px 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(17, 84, 125, 0.06);
    }}
    .bilimk-stat .value {{
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.1;
    }}
    .bilimk-stat .label {{
        color: {NAVY};
        opacity: 0.75;
        font-size: 0.85rem;
        margin-top: 4px;
    }}
    .bilimk-stat .icon {{ font-size: 1.4rem; }}

    /* Бейдж "серии" (streak) */
    .bilimk-streak-badge {{
        display: inline-block;
        background: {TEAL_SOFT};
        color: {NAVY};
        border-radius: 999px;
        padding: 6px 16px;
        font-weight: 700;
        font-size: 0.95rem;
    }}

    /* Мини-полоска прогресса внутри карточки рекомендации */
    .bilimk-mini-progress-track {{
        background: {NAVY_SOFT};
        border-radius: 999px;
        height: 10px;
        width: 100%;
        overflow: hidden;
        margin-top: 6px;
    }}
    .bilimk-mini-progress-fill {{
        background: {TEAL};
        height: 100%;
        border-radius: 999px;
    }}

    /* Цитата на пустом главном экране */
    .bilimk-quote {{
        border-left: 4px solid {TEAL};
        padding: 10px 18px;
        color: {NAVY};
        font-style: italic;
        opacity: 0.85;
        margin-top: 10px;
    }}

    /* Заголовки внутри контента */
    h2, h3 {{ color: {NAVY}; }}
    </style>
    """


def render_header(title: str, tagline: str, subtitle: str) -> str:
    """Фирменная шапка с градиентом: название, слоган, подзаголовок."""
    return f"""
    <div class="bilimk-header">
        <h1>🏔 {title}</h1>
        <p>{tagline}</p>
        <div class="bilimk-subtitle">{subtitle}</div>
    </div>
    """


def render_stat_card(icon: str, value, label: str, color: str = NAVY) -> str:
    """Одна плашка статистики (например, для банка ошибок или дашборда)."""
    return f"""
    <div class="bilimk-stat">
        <div class="icon">{icon}</div>
        <div class="value" style="color:{color};">{value}</div>
        <div class="label">{label}</div>
    </div>
    """


def render_streak_badge(days: int, label: str) -> str:
    """Бейдж 'серии' дней подряд."""
    return f'<span class="bilimk-streak-badge">🔥 {label}: {days}</span>'


def render_mini_progress(percent: int) -> str:
    """Мини-полоска прогресса (для карточки 'рекомендуется сегодня')."""
    percent = max(0, min(100, percent))
    return f"""
    <div class="bilimk-mini-progress-track">
        <div class="bilimk-mini-progress-fill" style="width:{percent}%;"></div>
    </div>
    """


def render_mountain_climb(percent: int, levels: int = 6) -> str:
    """
    Буквальная визуализация прогресса в виде восхождения на гору:
    точки поднимаются по склону слева направо, снизу вверх. Сколько
    точек "загорелось" бирюзовым - зависит от общего процента прогресса.
    На вершине - флаг (эмблема сайта), который "загорается", когда
    прогресс достигает 100%.

    Это задумано как визуальная "фишка" бренда (гора = эмблема BilimK),
    а не как точная научная диаграмма - поэтому просто и наглядно.
    """
    percent = max(0, min(100, percent))
    reached = round(percent / 100 * levels)

    width, height = 340, 200
    base_y = 175
    peak_x, peak_y = width * 0.55, 25

    # Точки идут по прямой от подножия (слева снизу) к вершине
    start_x, start_y = 40, base_y - 15
    dots = []
    for i in range(1, levels + 1):
        frac = i / levels
        x = start_x + (peak_x - start_x) * frac
        y = start_y + (peak_y - start_y) * frac
        filled = i <= reached
        color = TEAL if filled else "#D7E6E4"
        r = 8 if filled else 6
        dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}" '
                     f'stroke="{NAVY if filled else "#C7D8D6"}" stroke-width="1.5" />')

    flag = "🚩" if percent >= 100 else ""

    svg = f"""
    <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width:100%; max-width:420px;">
        <!-- Силуэт горы (второй план) -->
        <polygon points="10,{base_y} 110,60 180,{base_y}" fill="{NAVY}" opacity="0.15" />
        <!-- Главная вершина -->
        <polygon points="30,{base_y} {peak_x:.0f},{peak_y} {width-20},{base_y}" fill="{NAVY}" opacity="0.9" />
        <polygon points="{peak_x-35:.0f},{peak_y+55} {peak_x:.0f},{peak_y} {peak_x+35:.0f},{peak_y+55}" fill="{WHITE}" opacity="0.25" />
        {''.join(dots)}
        <text x="{peak_x:.0f}" y="{peak_y-8}" font-size="20" text-anchor="middle">{flag}</text>
    </svg>
    """
    return svg
