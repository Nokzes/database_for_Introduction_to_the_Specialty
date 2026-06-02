from pharmacy_db import PharmacyDB, populate_sample_data

db = PharmacyDB("pharmacy.db")

# Заполняем базу, если она пустая
with db._conn() as conn:
    count = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
if count == 0:
    print("База пустая — добавляем тестовые данные...\n")
    populate_sample_data(db)

print("=== Поиск лекарств ===")
print("Для выхода введите 'выход' или нажмите Ctrl+C\n")

while True:
    query = input("Введите название лекарства: ").strip()

    if query.lower() in ("выход", "exit", "quit"):
        print("Выход.")
        break

    if not query:
        print("Запрос не может быть пустым.\n")
        continue

    results = db.search_medicines(query)

    if not results:
        print(f"  Ничего не найдено по запросу «{query}».\n")
        continue

    print(f"  Найдено: {len(results)}\n")
    for m in results:
        rx = " [Рецепт]" if m["requires_prescription"] else ""
        print(f"  [{m['id']}] {m['name']} — {m['manufacturer']}, {m['dosage_form']}{rx}")
    print()
