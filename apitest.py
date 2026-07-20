import httpx
 
# --- ВПИШИ СВОИ ДАННЫЕ ОТ X2POS.COM ---
EMAIL = "max847524@gmail.com"
PASSWORD = "bt!4205#g86L@"
 
BASE_URL = "https://x2pos.com"

def get_token():
    r = httpx.post(
        f"{BASE_URL}/api/auth",
        data={"user": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["token"]

def main():
    token = get_token()
    headers = {"API-KEY": token}
 
    # 1. Узнаём branch_id (филиал)
    emp = httpx.get(f"{BASE_URL}/api/employee", headers=headers, timeout=30).json()
    branch_id = emp.get("current_branch_id") or emp.get("branches", [None])[0]
    print("Филиал (branch_id):", branch_id)
    print("=" * 50)
 
    # 2. Получаем список товаров
    print("ТОВАРЫ:")
    products = httpx.get(f"{BASE_URL}/api/products", headers=headers, timeout=30).json()
 
    # 3. Получаем остатки по филиалу
    stock = httpx.get(f"{BASE_URL}/api/stock?branch_id={branch_id}", headers=headers, timeout=30).json()
 
    # stock - это словарь {variation_id: {quantity: ...}}
    for p in products:
        name = p.get("product_name", "?")
        category = p.get("category_name", "?")
        variations = p.get("variations", {})
 
        # у товара могут быть разновидности - берём первую
        for var_id, var in variations.items():
            price = var.get("retail_price", "?")
            # ищем остаток этой разновидности
            qty = "?"
            if str(var_id) in stock:
                qty = stock[str(var_id)].get("quantity", "?")
            print(f"  {name} ({category}) - цена {price}, остаток {qty}")
 
    print("=" * 50)
    print(f"Всего товаров: {len(products)}")
 
 
if __name__ == "__main__":
    main()