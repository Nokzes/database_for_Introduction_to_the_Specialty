"""
АСОИУ «Аптека» — удаление данных.
Запуск: python delete_data.py
"""

from pharmacy_db import PharmacyDB

DB_FILE = "pharmacy.db"

ROLE_LABELS = {
    "pharmacist": "Фармацевт",
    "admin":      "Администратор",
    "sysadmin":   "Системный администратор",
}

# ─── Утилиты ввода ────────────────────────────────────────────────────────────

def choose(prompt, options):
    print(prompt)
    for i, label in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        raw = input("Ваш выбор: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Введите число от 1 до {len(options)}.")

def confirm(prompt):
    return input(prompt).strip().lower() == "y"

# ─── Удаление сотрудника ──────────────────────────────────────────────────────

def delete_employee(db):
    employees = db.get_employees()
    if not employees:
        print("  Сотрудников нет.")
        return

    print("\n── Список сотрудников ──")
    for e in employees:
        role = ROLE_LABELS.get(e["role"], e["role"])
        print(f"  [{e['id']}] {e['full_name']} — {role}, логин: {e['login']}")

    raw = input("\nВведите id сотрудника для удаления (или Enter для отмены): ").strip()
    if not raw:
        print("  Отменено.")
        return

    if not raw.isdigit():
        print("  Некорректный id.")
        return

    emp_id = int(raw)
    target = next((e for e in employees if e["id"] == emp_id), None)
    if not target:
        print(f"  Сотрудник с id={emp_id} не найден.")
        return

    print(f"\n  Будет удалён: [{target['id']}] {target['full_name']} ({target['login']})")
    if not confirm("  Подтвердить удаление? (y/n): "):
        print("  Отменено.")
        return

    with db._conn() as conn:
        conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    print(f"  Сотрудник [{emp_id}] удалён.")

# ─── Удаление лекарства ───────────────────────────────────────────────────────

def delete_medicine(db):
    medicines = db.get_medicines()
    if not medicines:
        print("  Лекарств нет.")
        return

    print("\n── Список лекарств ──")
    for m in medicines:
        rx = " [Рецепт]" if m["requires_prescription"] else ""
        mfr = f", {m['manufacturer']}" if m["manufacturer"] else ""
        print(f"  [{m['id']}] {m['name']}{mfr}{rx}")

    raw = input("\nВведите id лекарства для удаления (или Enter для отмены): ").strip()
    if not raw:
        print("  Отменено.")
        return

    if not raw.isdigit():
        print("  Некорректный id.")
        return

    med_id = int(raw)
    target = next((m for m in medicines if m["id"] == med_id), None)
    if not target:
        print(f"  Лекарство с id={med_id} не найдено.")
        return

    # Проверяем, есть ли остатки на складе
    with db._conn() as conn:
        stock = conn.execute(
            "SELECT SUM(quantity) as total FROM warehouse WHERE medicine_id = ?",
            (med_id,)
        ).fetchone()
    total_stock = stock["total"] or 0

    print(f"\n  Будет удалено: [{target['id']}] {target['name']}")
    if total_stock > 0:
        print(f"  Предупреждение: на складе {total_stock} уп. этого лекарства.")

    if not confirm("  Подтвердить удаление? (y/n): "):
        print("  Отменено.")
        return

    with db._conn() as conn:
        conn.execute("DELETE FROM warehouse WHERE medicine_id = ?", (med_id,))
        conn.execute("DELETE FROM jnvlp_registry WHERE medicine_id = ?", (med_id,))
        conn.execute("DELETE FROM medicines WHERE id = ?", (med_id,))
    print(f"  Лекарство [{med_id}] удалено.")

# ─── Удаление поставщика ──────────────────────────────────────────────────────

def delete_supplier(db):
    suppliers = db.get_suppliers()
    if not suppliers:
        print("  Поставщиков нет.")
        return

    print("\n── Список поставщиков ──")
    for s in suppliers:
        phone = f", {s['phone']}" if s["phone"] else ""
        print(f"  [{s['id']}] {s['name']}{phone}")

    raw = input("\nВведите id поставщика для удаления (или Enter для отмены): ").strip()
    if not raw:
        print("  Отменено.")
        return

    if not raw.isdigit():
        print("  Некорректный id.")
        return

    sup_id = int(raw)
    target = next((s for s in suppliers if s["id"] == sup_id), None)
    if not target:
        print(f"  Поставщик с id={sup_id} не найден.")
        return

    # Проверяем, есть ли накладные от этого поставщика
    with db._conn() as conn:
        inv_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM supply_invoices WHERE supplier_id = ?",
            (sup_id,)
        ).fetchone()["cnt"]

    print(f"\n  Будет удалён: [{target['id']}] {target['name']}")
    if inv_count > 0:
        print(f"  Предупреждение: у поставщика {inv_count} накладных в базе.")

    if not confirm("  Подтвердить удаление? (y/n): "):
        print("  Отменено.")
        return

    with db._conn() as conn:
        conn.execute("DELETE FROM suppliers WHERE id = ?", (sup_id,))
    print(f"  Поставщик [{sup_id}] удалён.")

# ─── Главный цикл ─────────────────────────────────────────────────────────────

ENTITIES = ["Сотрудник", "Лекарство", "Поставщик", "Выход"]

HANDLERS = {
    "Сотрудник": delete_employee,
    "Лекарство": delete_medicine,
    "Поставщик": delete_supplier,
}

def main():
    db = PharmacyDB(DB_FILE)
    print("=== АСОИУ «Аптека» — Удаление данных ===")

    while True:
        print()
        idx    = choose("Что удалить?", ENTITIES)
        entity = ENTITIES[idx]

        if entity == "Выход":
            print("Выход.")
            break

        HANDLERS[entity](db)

if __name__ == "__main__":
    main()
