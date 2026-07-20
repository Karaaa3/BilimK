# Словарь переводов: английское название (как в базе) -> русское (для показа юзеру)
# Используется во всех функциях бота, где показываются товары/категории.

CATEGORIES_RU = {
    "Fruits": "Фрукты",
    "Berries": "Ягоды",
    "Dried fruits": "Сухофрукты",
    "Vegetables": "Овощи",
    "Legumes": "Бобовые",
    "Soy products": "Соевые",
    "Greens": "Зелень",
    "Spices": "Специи",
    "Grains": "Крупы",
    "Starches": "Крахмал",
}

PRODUCTS_RU = {
    # Фрукты
    "apple": "Яблоко", "banana": "Банан", "orange": "Апельсин", "lemon": "Лимон",
    "lime": "Лайм", "mandarin": "Мандарин", "grape": "Виноград", "watermelon": "Арбуз",
    "melon": "Дыня", "pear": "Груша", "peach": "Персик", "plum": "Слива",
    "apricot": "Абрикос", "kiwi": "Киви", "pomegranate": "Гранат", "mango": "Манго",
    "pineapple": "Ананас", "avocado": "Авокадо", "papaya": "Папайя",
    "persimmon": "Хурма", "grapefruit": "Грейпфрут", "fig": "Инжир",
    # Ягоды
    "strawberry": "Клубника", "blueberry": "Голубика", "raspberry": "Малина",
    "blackberry": "Ежевика", "cherry": "Вишня", "cranberry": "Клюква",
    "red currant": "Красная смородина", "black currant": "Чёрная смородина",
    # Сухофрукты
    "raisins": "Изюм", "dried apricot": "Курага", "dates": "Финики",
    "prunes": "Чернослив", "dried banana": "Сушёный банан",
    # Овощи
    "potato": "Картофель", "carrot": "Морковь", "beetroot": "Свёкла",
    "radish": "Редис", "turnip": "Репа", "ginger": "Имбирь", "onion": "Лук",
    "garlic": "Чеснок", "tomato": "Помидор", "bell pepper": "Болгарский перец",
    "eggplant": "Баклажан", "cucumber": "Огурец", "pumpkin": "Тыква",
    "broccoli": "Брокколи", "cauliflower": "Цветная капуста", "cabbage": "Капуста",
    "celery": "Сельдерей", "corn": "Кукуруза",
    # Бобовые
    "chickpeas": "Нут", "lentils": "Чечевица", "beans": "Фасоль", "peas": "Горох",
    "green peas": "Зелёный горошек", "peanuts": "Арахис", "green beans": "Стручковая фасоль",
    # Соевые
    "soybeans": "Соевые бобы", "tofu": "Тофу", "soy sauce": "Соевый соус",
    # Зелень
    "spinach": "Шпинат", "parsley": "Петрушка", "cilantro": "Кинза",
    "arugula": "Руккола", "basil": "Базилик", "mint": "Мята", "dill": "Укроп",
    "watercress": "Кресс-салат", "sorrel": "Щавель", "leek greens": "Зелень лука-порея",
    # Специи
    "chili pepper": "Перец чили", "black pepper": "Чёрный перец",
    "turmeric": "Куркума", "cinnamon": "Корица", "fenugreek seeds": "Пажитник",
    # Крупы
    "rice": "Рис", "oats": "Овёс", "wheat": "Пшеница", "quinoa": "Киноа", "barley": "Ячмень",
    # Крахмал
    "potato starch": "Картофельный крахмал", "corn starch": "Кукурузный крахмал",
}


def product_ru(name_en):
    """Русское название товара (если нет в словаре — вернёт английское)."""
    return PRODUCTS_RU.get(name_en, name_en)


def category_ru(name_en):
    """Русское название категории."""
    return CATEGORIES_RU.get(name_en, name_en)
