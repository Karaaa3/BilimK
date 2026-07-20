from openai import OpenAI
import streamlit as st

# Инициализируем клиент OpenRouter и вставляем ключ прямо в код
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="твой_ключ_сюда",  # Замени эту строку на свой секретный ключ
)

st.title("🎓 ИИ-Тьютор для хакатона")

user_prompt = st.text_input("Задай вопрос по учебе:")

if user_prompt:
  with st.spinner("ИИ думает..."):
    try:
      completion = client.chat.completions.create(
          model="anthropic/claude-sonnet-5",
          messages=[{"role": "user", "content": user_prompt}],
      )
      st.write(completion.choices[0].message.content)
    except Exception as e:
      st.error(
          "Произошла ошибка (проверь правильность ключа и баланс на"
          f" счете): {e}"
      )