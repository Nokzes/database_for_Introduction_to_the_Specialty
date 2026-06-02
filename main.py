"""
АСОИУ «Аптека» — главное меню.
Запуск: python main.py
"""

import subprocess
import sys
import os

SCRIPTS = {
    "1": ("Демонстрация базы данных",  "demo.py"),
    "2": ("Поиск лекарств",            "search.py"),
    "3": ("Добавление данных",         "add_data.py"),
    "4": ("Удаление данных",           "delete_data.py"),
}

def run(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    subprocess.run([sys.executable, path])

def main():
    while True:
        print("\n╔══════════════════════════════════════╗")
        print("║     АСОИУ «Аптека» — Главное меню    ║")
        print("╠══════════════════════════════════════╣")
        for key, (label, _) in SCRIPTS.items():
            print(f"║  {key}. {label:<34}║")
        print("║  0. Выход                            ║")
        print("╚══════════════════════════════════════╝")

        choice = input("Ваш выбор: ").strip()

        if choice == "0":
            print("Выход.")
            break
        elif choice in SCRIPTS:
            _, filename = SCRIPTS[choice]
            print(f"\n{'─' * 40}")
            run(filename)
            print(f"{'─' * 40}")
            input("Нажмите Enter, чтобы вернуться в меню...")
        else:
            print("  Неверный выбор. Введите число от 0 до 4.")

if __name__ == "__main__":
    main()
