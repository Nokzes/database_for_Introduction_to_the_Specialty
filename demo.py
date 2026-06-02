"""
Демонстрация работы базы данных АСОИУ «Аптека».
Запуск: python demo.py
"""

import os
from pharmacy_db import PharmacyDB, populate_sample_data

DB_FILE = "demo_pharmacy.db"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

db = PharmacyDB(DB_FILE)

print("=" * 57)
print("   АСОИУ «Аптека» — демонстрация базы данных")
print("=" * 57)

# ── Автозаполнение ────────────────────────────────────────
print("\n[0] Автозаполнение тестовыми данными...")
ids = populate_sample_data(db)
print(f"    Лекарств:   {len(ids['medicine_ids'])}")
print(f"    Поставщиков: {len(ids['supplier_ids'])}")
print(f"    Накладных:  {len(ids['invoice_ids'])}")
print(f"    Сотрудников: {len(ids['employee_ids'])}")
print(f"    Продаж:     {len(ids['sale_ids'])}")

# ── Каталог лекарств ──────────────────────────────────────
print("\n[1] Каталог лекарств")
for m in db.get_medicines():
    rx = " [Рецепт]" if m["requires_prescription"] else ""
    print(f"    {m['id']:2}. {m['name']:<35} {m['dosage_form']}{rx}")

# ── Реестр ЖНВЛП ──────────────────────────────────────────
print("\n[2] Реестр ЖНВЛП")
for row in db.get_jnvlp():
    print(f"    {row['medicine_name']:<35} предел {row['max_wholesale_price']:.2f} руб.")

# ── Склад ─────────────────────────────────────────────────
print("\n[3] Остатки на складе (только годные)")
for row in db.get_warehouse():
    jnvlp = " [ЖНВЛП]" if row["is_jnvlp"] else ""
    print(f"    {row['medicine_name']:<35} серия {row['series']}  "
          f"до {row['expiry_date']}  {row['quantity']:>4} уп.  "
          f"{row['retail_price']:.2f} руб.{jnvlp}")

# ── Поиск лекарства ───────────────────────────────────────
print("\n[4] Поиск по каталогу: «парацет»")
for m in db.search_medicines("парацет"):
    print(f"    Найдено: {m['name']} ({m['manufacturer']})")

# ── Проверка цены ЖНВЛП ───────────────────────────────────
print("\n[5] Проверка цены ЖНВЛП (Ибупрофен)")
m_ibu_id = ids["medicine_ids"][0]
for price, label in [(99.0, "99.00"), (999.0, "999.00")]:
    ok, limit = db.check_jnvlp_price(m_ibu_id, price)
    status = "OK" if ok else f"ПРЕВЫШЕНИЕ (макс. {limit} руб.)"
    print(f"    Цена {label} руб. — {status}")

# ── Аутентификация ────────────────────────────────────────
print("\n[6] Аутентификация сотрудников")
# Берём реальный логин из базы — populate_sample_data добавляет uid-суффикс
all_emps = db.get_employees()
emp1_login = next(e["login"] for e in all_emps if e["id"] == ids["employee_ids"][0])

emp = db.authenticate(emp1_login, "pass123")
print(f"    {emp1_login} / pass123  →  {emp['full_name']} ({emp['role']})")
emp_bad = db.authenticate(emp1_login, "wrong")
print(f"    {emp1_login} / wrong    →  {'доступ запрещён' if emp_bad is None else 'пропущен'}")

# ── Продажи ───────────────────────────────────────────────
print("\n[7] Последние продажи")
for sale in db.get_sales():
    print(f"    #{sale['id']}  {sale['receipt_number']}  "
          f"{sale['employee_name']:<25}  {sale['total_amount']:>8.2f} руб.  "
          f"{sale['payment_method']}")

print("\n[7] Детали первого чека")
sale, items = db.get_sale_details(ids["sale_ids"][0])
print(f"    Кассир: {sale['employee_name']},  итого: {sale['total_amount']:.2f} руб.")
for it in items:
    print(f"      • {it['medicine_name']:<35} x{it['quantity']}  "
          f"= {it['price'] * it['quantity']:.2f} руб.")

# ── Предупреждения ────────────────────────────────────────
print("\n[8] Предупреждения: истекающий срок (180 дней)")
for row in db.get_expiring_soon(days=180):
    print(f"    ⚠ {row['medicine_name']:<35} серия {row['series']}  "
          f"до {row['expiry_date']}  {row['quantity']} уп.")

print("\n[8] Предупреждения: просроченные товары")
for row in db.report_expired():
    print(f"    ✗ {row['medicine_name']:<35} серия {row['series']}  "
          f"истёк {row['expiry_date']}  {row['quantity']} уп.")

print("\n[8] Предупреждения: малый остаток (≤ 50 уп.)")
for row in db.get_low_stock(threshold=50):
    print(f"    ↓ {row['medicine_name']:<35} {row['quantity']} уп.")

# ── Отчёты ────────────────────────────────────────────────
print("\n[9] Топ продаваемых лекарств")
for i, row in enumerate(db.report_top_medicines(limit=5), 1):
    print(f"    {i}. {row['name']:<35} {row['total_sold']:>4} уп.  "
          f"{row['revenue']:.2f} руб.")

print("\n[9] Выручка по дням")
for row in db.report_revenue("2026-01-01", "2026-12-31"):
    print(f"    {row['day']}  чеков: {row['sales_count']}  "
          f"выручка: {row['revenue']:.2f} руб.")

print("\n" + "=" * 57)
print("   Демонстрация завершена.")
print("=" * 57)
