"""
АСОИУ «Аптека» — расширенный поиск.
Запуск: python search.py
"""

from pharmacy_db import PharmacyDB, populate_sample_data

DB_FILE = "pharmacy.db"

ROLE_LABELS = {
    "pharmacist": "Фармацевт",
    "admin":      "Администратор",
    "sysadmin":   "Системный администратор",
}

# ─── Конфигурация критериев ───────────────────────────────────────────────────

MEDICINE_FIELDS = {
    "1": ("name",         "По названию"),
    "2": ("manufacturer", "По производителю"),
    "3": ("dosage_form",  "По форме выпуска"),
    "4": ("prescription", "По рецептурности  (введите: да / нет)"),
    "5": ("all",          "По всем полям"),
}

EMPLOYEE_FIELDS = {
    "1": ("full_name", "По ФИО"),
    "2": ("role",      "По роли  (фармацевт / администратор / сисадмин)"),
    "3": ("login",     "По логину"),
    "4": ("all",       "По всем полям"),
}

SUPPLIER_FIELDS = {
    "1": ("name",    "По названию"),
    "2": ("inn",     "По ИНН"),
    "3": ("address", "По адресу"),
    "4": ("phone",   "По телефону"),
    "5": ("email",   "По email"),
    "6": ("all",     "По всем полям"),
}

# ─── Форматированный вывод результатов ───────────────────────────────────────

def print_medicines(rows):
    if not rows:
        print("  Ничего не найдено.\n")
        return
    print(f"  Найдено: {len(rows)}\n")
    for m in rows:
        rx   = " [Рецепт]"  if m["requires_prescription"] else ""
        mfr  = f", {m['manufacturer']}" if m["manufacturer"] else ""
        form = f", {m['dosage_form']}"  if m["dosage_form"]  else ""
        print(f"  [{m['id']:>3}] {m['name']}{mfr}{form}{rx}")
    print()


def print_employees(rows):
    if not rows:
        print("  Ничего не найдено.\n")
        return
    print(f"  Найдено: {len(rows)}\n")
    for e in rows:
        role = ROLE_LABELS.get(e["role"], e["role"])
        print(f"  [{e['id']:>3}] {e['full_name']:<30} {role:<28} логин: {e['login']}")
    print()


def print_suppliers(rows):
    if not rows:
        print("  Ничего не найдено.\n")
        return
    print(f"  Найдено: {len(rows)}\n")
    for s in rows:
        inn   = f", ИНН {s['inn']}"      if s["inn"]     else ""
        phone = f", {s['phone']}"         if s["phone"]   else ""
        addr  = f"\n       {s['address']}" if s["address"] else ""
        print(f"  [{s['id']:>3}] {s['name']}{inn}{phone}{addr}")
    print()

# ─── Выбор критерия ───────────────────────────────────────────────────────────

def pick_field(fields_dict):
    """Показывает меню критериев и возвращает field-ключ."""
    print("\n  Критерий поиска:")
    for key, (_, label) in fields_dict.items():
        print(f"    {key}. {label}")
    while True:
        choice = input("  Выбор: ").strip()
        if choice in fields_dict:
            return fields_dict[choice][0]
        print(f"  Введите число от 1 до {len(fields_dict)}.")

# ─── Блоки поиска ─────────────────────────────────────────────────────────────

def search_medicines_loop(db):
    print("\n── Поиск лекарств ──────────────────────────────")
    field = pick_field(MEDICINE_FIELDS)
    while True:
        query = input("\n  Запрос (Enter — выход): ").strip()
        if not query:
            break
        print_medicines(db.search_medicines(query, field))


def search_employees_loop(db):
    print("\n── Поиск сотрудников ───────────────────────────")
    field = pick_field(EMPLOYEE_FIELDS)
    while True:
        query = input("\n  Запрос (Enter — выход): ").strip()
        if not query:
            break
        print_employees(db.search_employees(query, field))


def search_suppliers_loop(db):
    print("\n── Поиск поставщиков ───────────────────────────")
    field = pick_field(SUPPLIER_FIELDS)
    while True:
        query = input("\n  Запрос (Enter — выход): ").strip()
        if not query:
            break
        print_suppliers(db.search_suppliers(query, field))

# ─── Главный цикл ─────────────────────────────────────────────────────────────

SECTIONS = {
    "1": ("Лекарства",   search_medicines_loop),
    "2": ("Сотрудники",  search_employees_loop),
    "3": ("Поставщики",  search_suppliers_loop),
}

def main():
    db = PharmacyDB(DB_FILE)

    with db._conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    if count == 0:
        print("База пустая — добавляем тестовые данные...\n")
        populate_sample_data(db)

    print("=== АСОИУ «Аптека» — Поиск ===")
    print("Для выхода из раздела нажмите Enter на пустом запросе.\n")

    while True:
        print("Что искать?")
        for key, (label, _) in SECTIONS.items():
            print(f"  {key}. {label}")
        print("  0. Выход")

        choice = input("Выбор: ").strip()
        if choice == "0":
            print("Выход.")
            break
        if choice in SECTIONS:
            _, handler = SECTIONS[choice]
            handler(db)
        else:
            print("  Неверный выбор.\n")

if __name__ == "__main__":
    main()
