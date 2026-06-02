"""
АСОИУ «Аптека» — интерактивное добавление данных.
Запуск: python add_data.py
"""

import random
import string
from datetime import datetime
from faker import Faker
import requests
from deep_translator import GoogleTranslator
from pharmacy_db import PharmacyDB

DB_FILE = "pharmacy.db"
fake = Faker("ru_RU")

# ─── Реальные данные для автозаполнения ──────────────────────────────────────

REAL_MEDICINES = [
    # ── Обезболивающие и жаропонижающие ─────────────────────────────────────
    ("Аспирин Кардио 100мг",       "Bayer",              "таблетки",  False),
    ("Нурофен Экспресс 200мг",     "Reckitt",            "капсулы",   False),
    ("Цитрамон П",                 "Фармстандарт",       "таблетки",  False),
    ("Пенталгин",                  "Отисифарм",          "таблетки",  False),
    ("Нимесил 100мг",              "Berlin-Chemie",      "гранулы",   False),
    ("Кетанов 10мг",               "Ranbaxy",            "таблетки",  True),
    ("Найз 100мг",                 "Dr. Reddy's",        "таблетки",  False),
    ("Диклофенак 75мг",            "Биосинтез",          "раствор",   True),
    ("Мелоксикам 15мг",            "Озон",               "таблетки",  True),
    ("Кетопрофен 100мг",           "Биосинтез",          "капсулы",   False),

    # ── Спазмолитики ─────────────────────────────────────────────────────────
    ("Но-шпа 40мг",                "Sanofi",             "таблетки",  False),
    ("Дротаверин 40мг",            "Фармстандарт",       "таблетки",  False),
    ("Папаверин 40мг",             "Биосинтез",          "таблетки",  False),

    # ── ЖКТ ──────────────────────────────────────────────────────────────────
    ("Фестал",                     "Sanofi",             "таблетки",  False),
    ("Мезим Форте",                "Berlin-Chemie",      "таблетки",  False),
    ("Смекта",                     "Ipsen",              "порошок",   False),
    ("Линекс Форте",               "Sandoz",             "капсулы",   False),
    ("Лоперамид 2мг",              "Акрихин",            "капсулы",   False),
    ("Де-Нол 120мг",               "Astellas",           "таблетки",  True),
    ("Нольпаза 40мг",              "KRKA",               "таблетки",  True),
    ("Омез 20мг",                  "Dr. Reddy's",        "капсулы",   True),
    ("Мотилиум 10мг",              "Johnson & Johnson",  "таблетки",  False),
    ("Церукал 10мг",               "AWD Pharma",         "таблетки",  True),
    ("Активированный уголь 250мг", "Фармстандарт",       "таблетки",  False),
    ("Энтеросгель",                "Силма",              "паста",     False),
    ("Полисорб",                   "Полисорб",           "порошок",   False),
    ("Хилак Форте",                "Ratiopharm",         "капли",     False),
    ("Дюфалак",                    "Solvay Pharma",      "сироп",     False),
    ("Бифиформ",                   "Ferrosan",           "капсулы",   False),

    # ── Антибиотики ──────────────────────────────────────────────────────────
    ("Флемоксин Солютаб 500мг",    "Astellas",           "таблетки",  True),
    ("Амоксиклав 875мг",           "Sandoz",             "таблетки",  True),
    ("Аугментин 875мг",            "GlaxoSmithKline",    "таблетки",  True),
    ("Сумамед 500мг",              "Teva",               "таблетки",  True),
    ("Азитрокс 500мг",             "Фармстандарт",       "капсулы",   True),
    ("Доксициклин 100мг",          "Биосинтез",          "капсулы",   True),
    ("Цефтриаксон 1г",             "Биохимик",           "порошок",   True),
    ("Ципрофлоксацин 500мг",       "Озон",               "таблетки",  True),
    ("Метронидазол 500мг",         "Озон",               "таблетки",  True),
    ("Бисептол 480мг",             "Polpharma",          "таблетки",  True),
    ("Флюкостат 150мг",            "Фармстандарт",       "капсулы",   True),
    ("Клацид 500мг",               "Abbott",             "таблетки",  True),

    # ── Антигистаминные ───────────────────────────────────────────────────────
    ("Супрастин 25мг",             "Egis",               "таблетки",  False),
    ("Зиртек 10мг",                "UCB",                "таблетки",  False),
    ("Кларитин 10мг",              "Bayer",              "таблетки",  False),
    ("Эриус 5мг",                  "Schering-Plough",    "таблетки",  False),
    ("Тавегил 1мг",                "Novartis",           "таблетки",  False),
    ("Фенистил",                   "Novartis",           "капли",     False),

    # ── Нос и горло ──────────────────────────────────────────────────────────
    ("Нафтизин 0.1%",              "Фармстандарт",       "капли",     False),
    ("Аквамарис",                  "Jadran",             "спрей",     False),
    ("Отривин 0.1%",               "Novartis",           "спрей",     False),
    ("Ринонорм 0.1%",              "Berlin-Chemie",      "спрей",     False),
    ("Стрепсилс",                  "Reckitt",            "таблетки",  False),
    ("Гексорал",                   "Johnson & Johnson",  "спрей",     False),
    ("Тантум Верде",               "Angelini",           "спрей",     False),
    ("Фарингосепт",                "Sopharma",           "таблетки",  False),
    ("Биопарокс",                  "Servier",            "спрей",     True),

    # ── Сердечно-сосудистые ───────────────────────────────────────────────────
    ("Конкор 5мг",                 "Merck",              "таблетки",  True),
    ("Лизиноприл 10мг",            "Фармстандарт",       "таблетки",  True),
    ("Эналаприл 10мг",             "Фармстандарт",       "таблетки",  True),
    ("Амлодипин 5мг",              "Озон",               "таблетки",  True),
    ("Верошпирон 25мг",            "Gedeon Richter",     "таблетки",  True),
    ("Гипотиазид 25мг",            "Chinoin",            "таблетки",  True),
    ("Валидол",                    "Нижфарм",            "таблетки",  False),
    ("Корвалол",                   "Фармстандарт",       "капли",     False),
    ("Нитроглицерин 0.5мг",        "Биосинтез",          "таблетки",  True),
    ("Кардиомагнил 75мг",          "Takeda",             "таблетки",  False),
    ("Варфарин 2.5мг",             "Озон",               "таблетки",  True),
    ("Клопидогрел 75мг",           "Канонфарма",         "таблетки",  True),

    # ── Холестерин и сахарный диабет ──────────────────────────────────────────
    ("Аторвастатин 20мг",          "Озон",               "таблетки",  True),
    ("Розувастатин 10мг",          "Канонфарма",         "таблетки",  True),
    ("Глюкофаж 1000мг",            "Merck",              "таблетки",  True),
    ("Сиофор 850мг",               "Berlin-Chemie",      "таблетки",  True),
    ("Галвус Мет 50/1000мг",       "Novartis",           "таблетки",  True),

    # ── Нервная система ───────────────────────────────────────────────────────
    ("Мидокалм 150мг",             "Gedeon Richter",     "таблетки",  True),
    ("Пирацетам 800мг",            "Фармстандарт",       "капсулы",   True),
    ("Глицин 100мг",               "Биотики",            "таблетки",  False),
    ("Афобазол 10мг",              "Отисифарм",          "таблетки",  False),
    ("Тенотен",                    "Материа Медика",     "таблетки",  False),
    ("Персен Форте",               "Sandoz",             "капсулы",   False),
    ("Ново-Пассит",                "Teva",               "таблетки",  False),
    ("Фенибут 250мг",              "Олайнфарм",          "таблетки",  True),
    ("Донормил 15мг",              "Sanofi",             "таблетки",  False),

    # ── Витамины и минералы ───────────────────────────────────────────────────
    ("Аскорбиновая кислота 500мг", "Renewal",            "таблетки",  False),
    ("Витамин Д3 2000МЕ",          "Solgar",             "капсулы",   False),
    ("Магне В6",                   "Sanofi",             "таблетки",  False),
    ("Кальций Д3 Никомед",         "Takeda",             "таблетки",  False),
    ("Компливит",                  "Фармстандарт",       "таблетки",  False),
    ("Мультитабс Иммуно",          "Ferrosan",           "таблетки",  False),
    ("Алфавит Классик",            "Внешторг Фарма",     "таблетки",  False),
    ("Витрум",                     "Unipharm",           "таблетки",  False),
    ("Омега-3 1000мг",             "Doppelherz",         "капсулы",   False),

    # ── Глаза и уши ───────────────────────────────────────────────────────────
    ("Визин Классик",              "Johnson & Johnson",  "капли",     False),
    ("Тобрадекс",                  "Alcon",              "капли",     True),
    ("Офлоксацин 0.3%",            "Промед",             "капли",     True),
    ("Отипакс",                    "Biocodex",           "капли",     False),
    ("Отофа",                      "Bouchard",           "капли",     True),

    # ── Кожа ─────────────────────────────────────────────────────────────────
    ("Акридерм",                   "Акрихин",            "мазь",      True),
    ("Бепантен",                   "Bayer",              "мазь",      False),
    ("Пантенол",                   "Нижфарм",            "спрей",     False),
    ("Левомеколь",                 "Нижфарм",            "мазь",      False),
    ("Банеоцин",                   "Sandoz",             "порошок",   False),
    ("Цинковая мазь",              "Фармстандарт",       "мазь",      False),
    ("Клотримазол 1%",             "Акрихин",            "мазь",      False),
    ("Экзодерил",                  "Sandoz",             "раствор",   False),

    # ── Гормональные и щитовидная железа ─────────────────────────────────────
    ("Эутирокс 100мкг",            "Merck",              "таблетки",  True),
    ("Л-Тироксин 100мкг",          "Berlin-Chemie",      "таблетки",  True),
    ("Преднизолон 5мг",            "Никомед",            "таблетки",  True),
    ("Дексаметазон 0.5мг",         "Биосинтез",          "таблетки",  True),
]

REAL_SUPPLIERS = [
    ("ООО Протек",           "7736289532", "г. Москва, ул. Беговая, 3а",               "+7-495-788-12-12", "info@protek.ru"),
    ("ООО СИА Интернейшнл",  "7718830903", "г. Москва, ул. Профсоюзная, 3",            "+7-495-933-51-61", "info@sia.ru"),
    ("ООО Катрен",           "5408117593", "г. Новосибирск, ул. Кирова, 86",            "+7-383-289-90-00", "katren@katren.ru"),
    ("ООО Пульс",            "7714643628", "г. Москва, ул. Электрозаводская, 21",      "+7-495-787-40-04", "pulse@pulsefarm.ru"),
    ("ООО Империя-Фарма",    "7802388551", "г. Санкт-Петербург, Петергофское ш., 73",  "+7-812-334-04-44", "info@imperiya.spb.ru"),
    ("ООО ФК Здоровье",      "6164298124", "г. Ростов-на-Дону, ул. Малиновского, 25",  "+7-863-279-00-00", "zdorovye@fkz.ru"),
    ("АО Р-Фарм",            "7725548221", "г. Москва, ул. Ярославская, 14",           "+7-495-775-81-05", "rfarm@r-pharm.com"),
    ("ООО Биотэк",           "7709355111", "г. Москва, Варшавское ш., 125",            "+7-495-781-02-02", "biotec@biotec.ru"),
    ("ООО Фармкомплект",     "7811096234", "г. Санкт-Петербург, ул. Савушкина, 83",   "+7-812-449-00-11", "fk@pharmkomp.ru"),
    ("ООО Самсон-Фарма",     "7726152360", "г. Москва, Варшавское ш., 47к4",           "+7-495-740-11-00", "info@samson-med.ru"),
]

ROLES = ["pharmacist", "admin", "sysadmin"]
ROLE_LABELS = {
    "pharmacist": "Фармацевт",
    "admin":      "Администратор",
    "sysadmin":   "Системный администратор",
}

TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
    'з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
    'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def translit(text):
    return "".join(TRANSLIT.get(c, c) for c in text.lower())

def make_login(full_name):
    parts = full_name.strip().split()
    return translit(parts[0])[:10] if parts else "user"

def make_password(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

# ─── Утилиты ввода ────────────────────────────────────────────────────────────

def choose(prompt, options):
    """Показывает нумерованное меню и возвращает выбранный индекс (0-based)."""
    print(prompt)
    for i, label in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        raw = input("Ваш выбор: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Введите число от 1 до {len(options)}.")

def confirm(prompt="  Добавить? (y/n): "):
    return input(prompt).strip().lower() == "y"

# ─── Сотрудники ───────────────────────────────────────────────────────────────

def add_employee_manual(db):
    print("\n── Добавление сотрудника (вручную) ──")
    full_name = input("ФИО: ").strip()
    if not full_name:
        print("  ФИО не может быть пустым.")
        return

    role_idx  = choose("Роль:", [ROLE_LABELS[r] for r in ROLES])
    role      = ROLES[role_idx]
    suggested = make_login(full_name)
    login     = input(f"Логин [{suggested}]: ").strip() or suggested
    password  = input("Пароль: ").strip()
    if not password:
        print("  Пароль не может быть пустым.")
        return

    emp_id = db.add_employee(full_name, role, login, password)
    print(f"\n  Добавлен: [{emp_id}] {full_name} ({ROLE_LABELS[role]}), логин: {login}")


def add_employee_auto(db):
    full_name = fake.name()
    role      = random.choice(ROLES)
    login     = make_login(full_name) + str(random.randint(10, 99))
    password  = make_password()

    print("\n  Сгенерированные данные:")
    print(f"    ФИО:    {full_name}")
    print(f"    Роль:   {ROLE_LABELS[role]}")
    print(f"    Логин:  {login}")
    print(f"    Пароль: {password}")

    if confirm():
        emp_id = db.add_employee(full_name, role, login, password)
        print(f"  Добавлен с id={emp_id}.")
    else:
        print("  Отменено.")

# ─── Лекарства ────────────────────────────────────────────────────────────────

def add_medicine_manual(db):
    print("\n── Добавление лекарства (вручную) ──")
    name = input("Название: ").strip()
    if not name:
        print("  Название не может быть пустым.")
        return

    manufacturer = input("Производитель: ").strip() or None
    dosage_form  = input("Форма (таблетки / капсулы / спрей / …): ").strip() or None
    rx           = input("Рецептурный? (y/n): ").strip().lower() == "y"

    med_id = db.add_medicine(name, manufacturer, dosage_form, requires_prescription=rx)
    print(f"\n  Добавлено: [{med_id}] {name}")


_DOSAGE_FORM_MAP = {
    "tablet":              "таблетки",
    "tablets":             "таблетки",
    "capsule":             "капсулы",
    "capsules":            "капсулы",
    "solution":            "раствор",
    "spray":               "спрей",
    "cream":               "крем",
    "gel":                 "гель",
    "ointment":            "мазь",
    "powder":              "порошок",
    "syrup":               "сироп",
    "drops":               "капли",
    "injection":           "раствор для инъекций",
    "suppository":         "суппозитории",
    "patch":               "пластырь",
    "suspension":          "суспензия",
    "granules":            "гранулы",
    "film-coated tablet":  "таблетки п/о",
    "chewable tablet":     "жевательные таблетки",
}

_translator = GoogleTranslator(source="en", target="ru")

def _translate(text):
    """Переводит текст с английского на русский. При ошибке возвращает оригинал."""
    try:
        return _translator.translate(text)
    except Exception:
        return text


def fetch_medicine_from_api():
    """
    Получает случайный препарат из OpenFDA (база данных FDA США).
    Не требует API-ключа.
    Возвращает словарь с оригиналом (en) и переведёнными (ru) полями, или None.
    Документация: https://open.fda.gov/apis/drug/label/
    """
    try:
        skip = random.randint(0, 5000)
        url = (
            "https://api.fda.gov/drug/label.json"
            f"?search=openfda.brand_name:*+AND+openfda.manufacturer_name:*"
            f"&limit=1&skip={skip}"
        )
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        data = resp.json()

        openfda = data["results"][0].get("openfda", {})

        name_en         = openfda.get("brand_name", [""])[0].title()
        manufacturer_en = openfda.get("manufacturer_name", [""])[0]
        product_type    = openfda.get("product_type", ["OTC"])[0].lower()
        rx              = "prescription" in product_type

        raw_form    = openfda.get("dosage_form", ["tablet"])[0].lower()
        dosage_form = _DOSAGE_FORM_MAP.get(raw_form, raw_form)

        if not name_en or not manufacturer_en:
            return None

        return {
            "name_en":         name_en,
            "manufacturer_en": manufacturer_en[:60],
            "dosage_form":     dosage_form,
            "rx":              rx,
        }

    except Exception:
        return None


def _print_preview(label, name, manufacturer, dosage_form, rx):
    print(f"\n  ── {label} {'─' * max(1, 34 - len(label))}")
    print(f"    Название:      {name}")
    print(f"    Производитель: {manufacturer}")
    print(f"    Форма:         {dosage_form}")
    print(f"    Рецептурный:   {'да' if rx else 'нет'}")


def add_medicine_auto(db):
    print("  Запрос к OpenFDA API...", end=" ", flush=True)
    api_result = fetch_medicine_from_api()

    if api_result:
        print("получено.\n")
        name_en         = api_result["name_en"]
        manufacturer_en = api_result["manufacturer_en"]
        dosage_form     = api_result["dosage_form"]
        rx              = api_result["rx"]
        source          = "OpenFDA API"
    else:
        print("недоступен, используем локальный список.\n")
        name_en, manufacturer_en, dosage_form, rx = random.choice(REAL_MEDICINES)
        source = "локальный список"

    # Показываем оригинал
    _print_preview("Оригинал (английский)", name_en, manufacturer_en, dosage_form, rx)

    # Предлагаем перевести
    print()
    translate_choice = input("  Перевести на русский? (y/n): ").strip().lower()

    if translate_choice == "y":
        print("  Перевод...", end=" ", flush=True)
        name_ru         = _translate(name_en)
        manufacturer_ru = manufacturer_en
        print("готово.")

        # Показываем оба варианта
        _print_preview("Оригинал (английский)", name_en,  manufacturer_en, dosage_form, rx)
        _print_preview("Перевод  (русский)",    name_ru,  manufacturer_ru, dosage_form, rx)

        print()
        idx = choose("Какой вариант добавить?", [
            "Английский оригинал",
            "Русский перевод",
            "Отмена",
        ])
        if idx == 0:
            name, manufacturer = name_en, manufacturer_en
        elif idx == 1:
            name, manufacturer = name_ru, manufacturer_ru
        else:
            print("  Отменено.")
            return
    else:
        name, manufacturer = name_en, manufacturer_en
        if not confirm("\n  Добавить? (y/n): "):
            print("  Отменено.")
            return

    med_id = db.add_medicine(name, manufacturer, dosage_form, requires_prescription=rx)
    print(f"  Добавлено с id={med_id}: {name} ({source}).")

# ─── Поставщики ───────────────────────────────────────────────────────────────

def add_supplier_manual(db):
    print("\n── Добавление поставщика (вручную) ──")
    name = input("Название организации: ").strip()
    if not name:
        print("  Название не может быть пустым.")
        return

    inn     = input("ИНН: ").strip() or None
    address = input("Адрес: ").strip() or None
    phone   = input("Телефон: ").strip() or None
    email   = input("Email: ").strip() or None

    sup_id = db.add_supplier(name, inn, address, phone, email)
    print(f"\n  Добавлен: [{sup_id}] {name}")


def add_supplier_auto(db):
    name, inn, address, phone, email = random.choice(REAL_SUPPLIERS)
    inn_unique = f"{inn}-{datetime.now().strftime('%f')}"

    print("\n  Сгенерированные данные:")
    print(f"    Название: {name}")
    print(f"    ИНН:      {inn_unique}")
    print(f"    Адрес:    {address}")
    print(f"    Телефон:  {phone}")
    print(f"    Email:    {email}")

    if confirm():
        sup_id = db.add_supplier(name, inn_unique, address, phone, email)
        print(f"  Добавлен с id={sup_id}.")
    else:
        print("  Отменено.")

# ─── Главный цикл ─────────────────────────────────────────────────────────────

ENTITIES = ["Сотрудник", "Лекарство", "Поставщик", "Выход"]
FILL     = ["Ручное заполнение", "Автоматическое заполнение"]

HANDLERS = {
    ("Сотрудник", "Ручное заполнение"):          add_employee_manual,
    ("Сотрудник", "Автоматическое заполнение"):  add_employee_auto,
    ("Лекарство", "Ручное заполнение"):          add_medicine_manual,
    ("Лекарство", "Автоматическое заполнение"):  add_medicine_auto,
    ("Поставщик", "Ручное заполнение"):          add_supplier_manual,
    ("Поставщик", "Автоматическое заполнение"):  add_supplier_auto,
}

def main():
    db = PharmacyDB(DB_FILE)
    print("=== АСОИУ «Аптека» — Добавление данных ===")

    while True:
        print()
        entity_idx = choose("Что добавить?", ENTITIES)
        entity     = ENTITIES[entity_idx]

        if entity == "Выход":
            print("Выход.")
            break

        fill_idx = choose("Способ заполнения:", FILL)
        fill     = FILL[fill_idx]

        HANDLERS[(entity, fill)](db)

if __name__ == "__main__":
    main()
