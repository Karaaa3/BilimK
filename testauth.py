import httpx
 
# --- ВПИШИ СВОИ ДАННЫЕ ОТ X2POS.COM ---
EMAIL = "max847524@gmail.com"
PASSWORD = "bt!4205#g86L@"
 
BASE_URL = "https://x2pos.com"
 
 
 
def main():
    print("Отправляю запрос авторизации...")
 
    # ВАЖНО: /api/auth принимает form-data, поэтому data=, а не json=
    response = httpx.post(
        f"{BASE_URL}/api/auth",
        data={"user": EMAIL, "password": PASSWORD},
        timeout=30,
    )
 
    print("HTTP-статус:", response.status_code)
 
    if response.status_code != 200:
        print("Что-то пошло не так. Ответ сервера:")
        print(response.text)
        return
 
    data = response.json()
    token = data.get("token")
    company_id = data.get("company_id")
 
    if token:
        print("\nУСПЕХ! Авторизация прошла.")
        print("Company ID:", company_id)
        print("Токен:", token)
        print("\nСвязь с X2 POS работает. Токен получен.")
    else:
        print("\nТокен не пришёл. Полный ответ:")
        print(data)
 
 
if __name__ == "__main__":
    main()