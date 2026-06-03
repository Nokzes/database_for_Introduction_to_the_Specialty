"""
АСОИУ «Аптека» — модуль базы данных
Тема: Поступление и продажа лекарств
Библиотека: sqlite3 (стандартная библиотека Python)
"""

import sqlite3
import hashlib
from datetime import date, datetime, timedelta


DB_PATH = "pharmacy.db"


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=DB_PATH):
    """Создаёт все таблицы базы данных."""
    conn = get_connection(db_path)
    conn.executescript("""
        -- Каталог лекарств
        CREATE TABLE IF NOT EXISTS medicines (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT NOT NULL,
            manufacturer         TEXT,
            dosage_form          TEXT,          -- таблетки, капсулы, раствор и т.д.
            unit                 TEXT DEFAULT 'уп.',
            requires_prescription INTEGER DEFAULT 0,
            created_at           TEXT DEFAULT (datetime('now'))
        );

        -- Поставщики
        CREATE TABLE IF NOT EXISTS suppliers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            inn           TEXT UNIQUE,
            address       TEXT,
            phone         TEXT,
            email         TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        -- Реестр ЖНВЛП (жизненно необходимые и важнейшие лекарственные препараты)
        CREATE TABLE IF NOT EXISTS jnvlp_registry (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id          INTEGER NOT NULL,
            max_wholesale_price  REAL NOT NULL,   -- предельная отпускная цена производителя
            registered_date      TEXT NOT NULL,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        );

        -- Электронные накладные от поставщиков
        CREATE TABLE IF NOT EXISTS supply_invoices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id    INTEGER NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            invoice_date   TEXT NOT NULL,
            status         TEXT DEFAULT 'pending', -- pending / accepted / rejected
            created_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );

        -- Склад: каждая партия лекарства (серия + срок годности)
        CREATE TABLE IF NOT EXISTS warehouse (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id    INTEGER NOT NULL,
            invoice_id     INTEGER,
            series         TEXT NOT NULL,
            expiry_date    TEXT NOT NULL,
            quantity       INTEGER NOT NULL DEFAULT 0,
            purchase_price REAL NOT NULL,
            retail_price   REAL NOT NULL,
            marking_code   TEXT UNIQUE,    -- код «Честного Знака»
            is_jnvlp       INTEGER DEFAULT 0,
            created_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id),
            FOREIGN KEY (invoice_id)  REFERENCES supply_invoices(id)
        );

        -- Сотрудники: фармацевт, администратор, системный администратор
        CREATE TABLE IF NOT EXISTS employees (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT NOT NULL,
            role          TEXT NOT NULL,  -- pharmacist / admin / sysadmin
            login         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        -- Кассовые продажи
        CREATE TABLE IF NOT EXISTS sales (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id    INTEGER NOT NULL,
            receipt_number TEXT UNIQUE NOT NULL,
            sale_date      TEXT DEFAULT (datetime('now')),
            total_amount   REAL NOT NULL DEFAULT 0,
            payment_method TEXT DEFAULT 'cash',  -- cash / card
            status         TEXT DEFAULT 'completed',
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        );

        -- Позиции в чеке
        CREATE TABLE IF NOT EXISTS sale_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id      INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity     INTEGER NOT NULL,
            price        REAL NOT NULL,
            FOREIGN KEY (sale_id)      REFERENCES sales(id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouse(id)
        );

        -- Журнал операций с маркировкой «Честный Знак» / ИС МДЛП
        CREATE TABLE IF NOT EXISTS marking_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            marking_code   TEXT NOT NULL,
            operation_type TEXT NOT NULL,  -- receipt / sale / return / write_off
            operation_date TEXT DEFAULT (datetime('now')),
            reference_id   INTEGER,        -- id накладной или продажи
            reference_type TEXT            -- invoice / sale
        );
    """)
    conn.commit()
    conn.close()


class PharmacyDB:
    """Класс для работы с базой данных аптеки."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(db_path)

    def _conn(self):
        return get_connection(self.db_path)

    # ─────────────────────────── ЛЕКАРСТВА ───────────────────────────

    def add_medicine(self, name, manufacturer=None, dosage_form=None,
                     unit="уп.", requires_prescription=False):
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO medicines
                   (name, manufacturer, dosage_form, unit, requires_prescription)
                   VALUES (?,?,?,?,?)""",
                (name, manufacturer, dosage_form, unit, int(requires_prescription))
            )
            return cur.lastrowid

    def get_medicines(self):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM medicines").fetchall()

    def search_medicines(self, query, field="name"):
        """
        Поиск лекарств. field: name | manufacturer | dosage_form | prescription | all
        Для prescription query: 'да'/'рецепт' → рецептурные, 'нет' → безрецептурные.
        """
        q = query.lower().strip()
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM medicines").fetchall()

        if field == "prescription":
            rx = q in ("да", "рецепт", "рецептурный", "1", "yes")
            return [r for r in rows if bool(r["requires_prescription"]) == rx]

        field_map = {
            "name":         lambda r: r["name"] or "",
            "manufacturer": lambda r: r["manufacturer"] or "",
            "dosage_form":  lambda r: r["dosage_form"] or "",
            "all":          lambda r: " ".join(filter(None, [
                                r["name"], r["manufacturer"], r["dosage_form"]
                            ])),
        }
        get_text = field_map.get(field, field_map["name"])
        return [r for r in rows if q in get_text(r).lower()]

    def search_employees(self, query, field="full_name"):
        """
        Поиск сотрудников. field: full_name | role | login | all
        Для role можно вводить: фармацевт, администратор, сисадмин или en-значения.
        """
        q = query.lower().strip()
        role_aliases = {
            "фармацевт": "pharmacist", "pharmacist": "pharmacist",
            "администратор": "admin",  "admin": "admin",
            "системный": "sysadmin",   "сисадмин": "sysadmin", "sysadmin": "sysadmin",
        }
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, full_name, role, login, created_at FROM employees"
            ).fetchall()

        if field == "role":
            target = role_aliases.get(q, q)
            return [r for r in rows if target in r["role"].lower()]

        field_map = {
            "full_name": lambda r: r["full_name"] or "",
            "login":     lambda r: r["login"] or "",
            "all":       lambda r: " ".join(filter(None, [
                             r["full_name"], r["role"], r["login"]
                         ])),
        }
        get_text = field_map.get(field, field_map["full_name"])
        return [r for r in rows if q in get_text(r).lower()]

    def search_suppliers(self, query, field="name"):
        """
        Поиск поставщиков. field: name | inn | address | phone | email | all
        """
        q = query.lower().strip()
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM suppliers").fetchall()

        field_map = {
            "name":    lambda r: r["name"] or "",
            "inn":     lambda r: r["inn"] or "",
            "address": lambda r: r["address"] or "",
            "phone":   lambda r: r["phone"] or "",
            "email":   lambda r: r["email"] or "",
            "all":     lambda r: " ".join(filter(None, [
                           r["name"], r["inn"], r["address"],
                           r["phone"], r["email"]
                       ])),
        }
        get_text = field_map.get(field, field_map["name"])
        return [r for r in rows if q in get_text(r).lower()]

    def get_medicine_by_id(self, medicine_id):
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM medicines WHERE id = ?", (medicine_id,)
            ).fetchone()

    # ─────────────────────────── ПОСТАВЩИКИ ──────────────────────────

    def add_supplier(self, name, inn=None, address=None, phone=None, email=None):
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO suppliers (name, inn, address, phone, email) VALUES (?,?,?,?,?)",
                (name, inn, address, phone, email)
            )
            return cur.lastrowid

    def get_suppliers(self):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM suppliers").fetchall()

    # ─────────────────────────── ЖНВЛП ───────────────────────────────

    def add_jnvlp(self, medicine_id, max_wholesale_price, registered_date=None):
        if registered_date is None:
            registered_date = date.today().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO jnvlp_registry (medicine_id, max_wholesale_price, registered_date)
                   VALUES (?,?,?)""",
                (medicine_id, max_wholesale_price, registered_date)
            )
            return cur.lastrowid

    def get_jnvlp(self):
        with self._conn() as conn:
            return conn.execute("""
                SELECT j.*, m.name AS medicine_name
                FROM jnvlp_registry j
                JOIN medicines m ON j.medicine_id = m.id
            """).fetchall()

    def check_jnvlp_price(self, medicine_id, retail_price):
        """
        Проверяет, не превышает ли розничная цена допустимый предел для ЖНВЛП.
        Возвращает (ok: bool, max_allowed: float | None).
        """
        with self._conn() as conn:
            row = conn.execute(
                """SELECT max_wholesale_price FROM jnvlp_registry
                   WHERE medicine_id = ? ORDER BY registered_date DESC LIMIT 1""",
                (medicine_id,)
            ).fetchone()
        if row:
            # Упрощённая формула: розничная надбавка не более 32% (по законодательству РФ для ЖНВЛП)
            max_allowed = round(row["max_wholesale_price"] * 1.32, 2)
            return retail_price <= max_allowed, max_allowed
        return True, None  # не ЖНВЛП

    # ─────────────────────────── НАКЛАДНЫЕ ───────────────────────────

    def create_invoice(self, supplier_id, invoice_number, invoice_date=None):
        if invoice_date is None:
            invoice_date = date.today().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO supply_invoices (supplier_id, invoice_number, invoice_date)
                   VALUES (?,?,?)""",
                (supplier_id, invoice_number, invoice_date)
            )
            return cur.lastrowid

    def get_invoices(self):
        with self._conn() as conn:
            return conn.execute("""
                SELECT i.*, s.name AS supplier_name
                FROM supply_invoices i
                JOIN suppliers s ON i.supplier_id = s.id
                ORDER BY i.invoice_date DESC
            """).fetchall()

    # ─────────────────────────── СКЛАД / ПРИЁМКА ─────────────────────

    def receive_goods(self, invoice_id, medicine_id, series, expiry_date,
                      quantity, purchase_price, retail_price,
                      marking_code=None, is_jnvlp=False):
        """
        Принимает товар на склад по накладной.
        Для ЖНВЛП автоматически проверяет допустимость цены.
        """
        if is_jnvlp:
            ok, max_allowed = self.check_jnvlp_price(medicine_id, retail_price)
            if not ok:
                raise ValueError(
                    f"Цена {retail_price} руб. превышает предел ЖНВЛП ({max_allowed} руб.)"
                )

        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO warehouse
                   (medicine_id, invoice_id, series, expiry_date, quantity,
                    purchase_price, retail_price, marking_code, is_jnvlp)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (medicine_id, invoice_id, series, expiry_date, quantity,
                 purchase_price, retail_price, marking_code, int(is_jnvlp))
            )
            warehouse_id = cur.lastrowid

            if marking_code:
                conn.execute(
                    """INSERT INTO marking_log
                       (marking_code, operation_type, reference_id, reference_type)
                       VALUES (?, 'receipt', ?, 'invoice')""",
                    (marking_code, invoice_id)
                )

            conn.execute(
                "UPDATE supply_invoices SET status = 'accepted' WHERE id = ?",
                (invoice_id,)
            )
            return warehouse_id

    def get_warehouse(self, include_expired=False):
        """Возвращает остатки на складе."""
        today = date.today().isoformat()
        with self._conn() as conn:
            if include_expired:
                return conn.execute("""
                    SELECT w.*, m.name AS medicine_name
                    FROM warehouse w
                    JOIN medicines m ON w.medicine_id = m.id
                    WHERE w.quantity > 0
                    ORDER BY w.expiry_date
                """).fetchall()
            return conn.execute("""
                SELECT w.*, m.name AS medicine_name
                FROM warehouse w
                JOIN medicines m ON w.medicine_id = m.id
                WHERE w.quantity > 0 AND w.expiry_date >= ?
                ORDER BY w.expiry_date
            """, (today,)).fetchall()

    def get_expiring_soon(self, days=30):
        """Товары, у которых срок годности истекает в течение `days` дней."""
        today = date.today()
        threshold = (today + timedelta(days=days)).isoformat()
        with self._conn() as conn:
            return conn.execute("""
                SELECT w.*, m.name AS medicine_name
                FROM warehouse w
                JOIN medicines m ON w.medicine_id = m.id
                WHERE w.expiry_date BETWEEN ? AND ?
                  AND w.quantity > 0
                ORDER BY w.expiry_date
            """, (today.isoformat(), threshold)).fetchall()

    def get_low_stock(self, threshold=10):
        """Товары с малым остатком на складе."""
        with self._conn() as conn:
            return conn.execute("""
                SELECT w.*, m.name AS medicine_name
                FROM warehouse w
                JOIN medicines m ON w.medicine_id = m.id
                WHERE w.quantity <= ? AND w.quantity > 0
                ORDER BY w.quantity
            """, (threshold,)).fetchall()

    def write_off(self, warehouse_id, quantity, reason="expired"):
        """Списание товара (просрок, брак и т.д.)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT quantity, marking_code FROM warehouse WHERE id = ?",
                (warehouse_id,)
            ).fetchone()
            if not row:
                raise ValueError("Позиция склада не найдена")
            if row["quantity"] < quantity:
                raise ValueError(f"На складе только {row['quantity']} ед.")

            conn.execute(
                "UPDATE warehouse SET quantity = quantity - ? WHERE id = ?",
                (quantity, warehouse_id)
            )
            if row["marking_code"]:
                conn.execute(
                    """INSERT INTO marking_log
                       (marking_code, operation_type, reference_type)
                       VALUES (?, 'write_off', ?)""",
                    (row["marking_code"], reason)
                )

    # ─────────────────────────── СОТРУДНИКИ ──────────────────────────

    def add_employee(self, full_name, role, login, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO employees (full_name, role, login, password_hash)
                   VALUES (?,?,?,?)""",
                (full_name, role, login, password_hash)
            )
            return cur.lastrowid

    def authenticate(self, login, password):
        """Возвращает запись сотрудника при успешной аутентификации, иначе None."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM employees WHERE login = ? AND password_hash = ?",
                (login, password_hash)
            ).fetchone()

    def get_employees(self):
        with self._conn() as conn:
            return conn.execute(
                "SELECT id, full_name, role, login, created_at FROM employees"
            ).fetchall()

    # ─────────────────────────── ПРОДАЖИ ─────────────────────────────

    def create_sale(self, employee_id, items, payment_method="cash"):
        """
        Оформляет кассовую продажу и списывает остатки со склада.

        items — список словарей: [{"warehouse_id": int, "quantity": int}, ...]

        Возвращает (sale_id, receipt_number, total_amount).
        """
        receipt_number = f"RCP-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"

        with self._conn() as conn:
            total = 0.0
            enriched = []

            for item in items:
                row = conn.execute(
                    "SELECT quantity, retail_price, marking_code FROM warehouse WHERE id = ?",
                    (item["warehouse_id"],)
                ).fetchone()

                if not row:
                    raise ValueError(f"Склад id={item['warehouse_id']} не найден")
                if row["quantity"] < item["quantity"]:
                    raise ValueError(
                        f"Недостаточно товара (склад id={item['warehouse_id']}): "
                        f"нужно {item['quantity']}, доступно {row['quantity']}"
                    )

                line_total = row["retail_price"] * item["quantity"]
                total += line_total
                enriched.append({**item, "price": row["retail_price"],
                                  "marking_code": row["marking_code"]})

            cur = conn.execute(
                """INSERT INTO sales (employee_id, receipt_number, total_amount, payment_method)
                   VALUES (?,?,?,?)""",
                (employee_id, receipt_number, round(total, 2), payment_method)
            )
            sale_id = cur.lastrowid

            for item in enriched:
                conn.execute(
                    """INSERT INTO sale_items (sale_id, warehouse_id, quantity, price)
                       VALUES (?,?,?,?)""",
                    (sale_id, item["warehouse_id"], item["quantity"], item["price"])
                )
                conn.execute(
                    "UPDATE warehouse SET quantity = quantity - ? WHERE id = ?",
                    (item["quantity"], item["warehouse_id"])
                )
                if item["marking_code"]:
                    conn.execute(
                        """INSERT INTO marking_log
                           (marking_code, operation_type, reference_id, reference_type)
                           VALUES (?, 'sale', ?, 'sale')""",
                        (item["marking_code"], sale_id)
                    )

        return sale_id, receipt_number, round(total, 2)

    def get_sales(self, date_from=None, date_to=None):
        with self._conn() as conn:
            if date_from and date_to:
                return conn.execute("""
                    SELECT s.*, e.full_name AS employee_name
                    FROM sales s
                    JOIN employees e ON s.employee_id = e.id
                    WHERE s.sale_date BETWEEN ? AND ?
                    ORDER BY s.sale_date DESC
                """, (date_from, date_to)).fetchall()
            return conn.execute("""
                SELECT s.*, e.full_name AS employee_name
                FROM sales s
                JOIN employees e ON s.employee_id = e.id
                ORDER BY s.sale_date DESC
            """).fetchall()

    def get_sale_details(self, sale_id):
        """Возвращает (sale, [items]) — заголовок и позиции чека."""
        with self._conn() as conn:
            sale = conn.execute("""
                SELECT s.*, e.full_name AS employee_name
                FROM sales s
                JOIN employees e ON s.employee_id = e.id
                WHERE s.id = ?
            """, (sale_id,)).fetchone()

            items = conn.execute("""
                SELECT si.quantity, si.price,
                       m.name AS medicine_name,
                       w.series, w.expiry_date, w.marking_code
                FROM sale_items si
                JOIN warehouse w ON si.warehouse_id = w.id
                JOIN medicines m ON w.medicine_id = m.id
                WHERE si.sale_id = ?
            """, (sale_id,)).fetchall()

        return sale, items

    # ─────────────────────────── ОТЧЁТЫ ──────────────────────────────

    def report_revenue(self, date_from, date_to):
        """Выручка по дням за период."""
        with self._conn() as conn:
            return conn.execute("""
                SELECT DATE(sale_date) AS day,
                       COUNT(*)        AS sales_count,
                       SUM(total_amount) AS revenue
                FROM sales
                WHERE sale_date BETWEEN ? AND ?
                GROUP BY DATE(sale_date)
                ORDER BY day
            """, (date_from, date_to)).fetchall()

    def report_top_medicines(self, limit=10):
        """Топ продаваемых лекарств."""
        with self._conn() as conn:
            return conn.execute("""
                SELECT m.name,
                       SUM(si.quantity)          AS total_sold,
                       SUM(si.quantity * si.price) AS revenue
                FROM sale_items si
                JOIN warehouse w ON si.warehouse_id = w.id
                JOIN medicines m ON w.medicine_id = m.id
                GROUP BY m.id
                ORDER BY total_sold DESC
                LIMIT ?
            """, (limit,)).fetchall()

    def report_expired(self):
        """Просроченные остатки на складе."""
        today = date.today().isoformat()
        with self._conn() as conn:
            return conn.execute("""
                SELECT w.*, m.name AS medicine_name
                FROM warehouse w
                JOIN medicines m ON w.medicine_id = m.id
                WHERE w.expiry_date < ? AND w.quantity > 0
                ORDER BY w.expiry_date
            """, (today,)).fetchall()


# ─────────────────────────────────────────────────────────────────────────────
# АВТОЗАПОЛНЕНИЕ ТЕСТОВЫМИ ДАННЫМИ
# ─────────────────────────────────────────────────────────────────────────────

def populate_sample_data(db: PharmacyDB):
    """
    Добавляет в базу данных набор тестовых данных:
      - 12 лекарств (часть — ЖНВЛП, часть — рецептурные)
      - 3 поставщика
      - 2 накладные с партиями (в т.ч. одна с просроченным товаром)
      - 3 сотрудника
      - 8 кассовых продаж

    Безопасно вызывать повторно — каждый вызов добавляет новый
    независимый набор записей, не затрагивая существующие данные.
    Возвращает словарь с id всех созданных сущностей.
    """
    # Уникальный суффикс для полей с UNIQUE-ограничением,
    # чтобы повторные вызовы не конфликтовали с уже существующими записями.
    uid = datetime.now().strftime("%H%M%S%f")

    today = date.today()

    # ── Лекарства ────────────────────────────────────────────────────────────
    medicines = [
        # (name, manufacturer, dosage_form, requires_prescription)
        ("Ибупрофен 400мг",            "Фармстандарт",  "таблетки",  False),
        ("Парацетамол 500мг",          "Renewal",        "таблетки",  False),
        ("Аскорбиновая кислота 500мг", "Renewal",        "таблетки",  False),
        ("Нурофен Экспресс 200мг",     "Reckitt",        "капсулы",   False),
        ("Амоксициллин 500мг",         "Биосинтез",      "капсулы",   True),
        ("Азитромицин 500мг",          "Озон",           "таблетки",  True),
        ("Метформин 1000мг",           "Озон",           "таблетки",  True),
        ("Эналаприл 10мг",             "Фармстандарт",  "таблетки",  True),
        ("Омепразол 20мг",             "КРКА",           "капсулы",   False),
        ("Лоратадин 10мг",             "Акрихин",        "таблетки",  False),
        ("Валидол",                    "Нижфарм",        "таблетки",  False),
        ("Активированный уголь 250мг", "Фармстандарт",  "таблетки",  False),
    ]
    med_ids = []
    for name, mfr, form, rx in medicines:
        med_ids.append(db.add_medicine(name, mfr, form, requires_prescription=rx))

    # ── ЖНВЛП ────────────────────────────────────────────────────────────────
    jnvlp_data = [
        (0,  85.00),   # Ибупрофен
        (1,  45.00),   # Парацетамол
        (4, 120.00),   # Амоксициллин
        (5, 180.00),   # Азитромицин
        (6, 210.00),   # Метформин
        (7,  95.00),   # Эналаприл
        (8,  90.00),   # Омепразол
    ]
    for idx, max_price in jnvlp_data:
        db.add_jnvlp(med_ids[idx], max_price,
                     registered_date=(today - timedelta(days=180)).isoformat())

    # ── Поставщики (ИНН уникален — добавляем суффикс uid) ────────────────────
    sup1 = db.add_supplier("ООО СИА Интернейшнл",
                           inn=f"7718830903-{uid}",
                           address="г. Москва, ул. Профсоюзная, 3",
                           phone="+7-495-933-51-61")
    sup2 = db.add_supplier("ЗАО Протек-СПб",
                           inn=f"7736289532-{uid}",
                           address="г. Санкт-Петербург, Московский пр., 12",
                           phone="+7-812-320-20-20")
    sup3 = db.add_supplier("ООО Катрен",
                           inn=f"5408117593-{uid}",
                           address="г. Новосибирск, ул. Кирова, 86",
                           phone="+7-383-289-90-00")

    # ── Накладная 1: основной приход (свежие товары) ─────────────────────────
    inv1 = db.create_invoice(sup1, f"НК-2026-047-{uid}",
                             (today - timedelta(days=5)).isoformat())

    # (med_idx, series, expiry_offset_days, qty, purchase, retail, marking, is_jnvlp)
    batch1 = [
        (0,  "АА1234", 545,  120, 70.00,  99.00,  f"MC001AAA111-{uid}", True),   # Ибупрофен
        (1,  "АБ5678", 730,  200, 32.00,  52.00,  f"MC002BBB222-{uid}", True),   # Парацетамол
        (2,  "АВ9012", 365,  150, 22.00,  45.00,  f"MC003CCC333-{uid}", False),  # Аскорбинка
        (4,  "АГ3456", 545,   60, 95.00, 138.00,  f"MC004DDD444-{uid}", True),   # Амоксициллин
        (5,  "АД7890", 730,   40, 145.00,210.00,  f"MC005EEE555-{uid}", True),   # Азитромицин
        (6,  "АЕ2345", 730,   80, 175.00,240.00,  None,                  True),   # Метформин
        (7,  "АЖ6789", 365,  100, 72.00,  98.00,  None,                  True),   # Эналаприл
        (8,  "АЗ0123", 545,   90, 68.00,  95.00,  f"MC008HHH888-{uid}", True),   # Омепразол
        (9,  "АИ4567", 365,  110, 55.00,  89.00,  f"MC009III999-{uid}", False),  # Лоратадин
        (11, "АК8901", 365,  300, 8.00,   18.00,  None,                  False),  # Уголь
    ]
    w_ids_1 = []
    for med_i, series, exp_days, qty, buy, sell, mark, jnvlp in batch1:
        exp = (today + timedelta(days=exp_days)).isoformat()
        wid = db.receive_goods(inv1, med_ids[med_i], series, exp,
                               qty, buy, sell, mark, jnvlp)
        w_ids_1.append(wid)

    # ── Накладная 2: другой поставщик + просроченная партия ──────────────────
    inv2 = db.create_invoice(sup2, f"НК-2026-031-{uid}",
                             (today - timedelta(days=30)).isoformat())

    batch2 = [
        (3,  "БА1111", 180,   50, 190.00, 280.00, f"MC010JJJ000-{uid}", False),  # Нурофен
        (10, "ББ2222", 730,  200, 12.00,  28.00,  None,                  False),  # Валидол
        # Просроченная партия Ибупрофена (срок истёк 10 дней назад)
        (0,  "БВ3333", -10,   15, 68.00,  95.00,  f"MC012LLL222-{uid}", True),   # просрок
    ]
    w_ids_2 = []
    for med_i, series, exp_days, qty, buy, sell, mark, jnvlp in batch2:
        exp = (today + timedelta(days=exp_days)).isoformat()
        wid = db.receive_goods(inv2, med_ids[med_i], series, exp,
                               qty, buy, sell, mark, jnvlp)
        w_ids_2.append(wid)

    # ── Сотрудники (login уникален — добавляем суффикс uid) ──────────────────
    emp1 = db.add_employee("Иванова Мария Петровна",   "pharmacist", f"ivanova-{uid}",   "pass123")
    emp2 = db.add_employee("Смирнов Алексей Иванович", "admin",      f"smirnov-{uid}",   "admin456")
    emp3 = db.add_employee("Петров Никита Олегович",   "sysadmin",   f"petrov-{uid}",    "dev789")

    # ── Продажи за последние 7 дней ─────────────────────────────────────────
    # Каждая продажа — список позиций (warehouse_id из batch1, количество)
    # w_ids_1 порядок: Ибупрофен, Парацетамол, Аскорбинка, Амоксициллин,
    #                  Азитромицин, Метформин, Эналаприл, Омепразол,
    #                  Лоратадин, Уголь
    sales_data = [
        (emp1, [{"warehouse_id": w_ids_1[0], "quantity": 3},
                {"warehouse_id": w_ids_1[1], "quantity": 2}], "card"),
        (emp1, [{"warehouse_id": w_ids_1[2], "quantity": 5},
                {"warehouse_id": w_ids_1[9], "quantity": 2}], "cash"),
        (emp2, [{"warehouse_id": w_ids_1[3], "quantity": 1},
                {"warehouse_id": w_ids_1[7], "quantity": 2}], "card"),
        (emp1, [{"warehouse_id": w_ids_1[4], "quantity": 1}],             "cash"),
        (emp1, [{"warehouse_id": w_ids_1[5], "quantity": 2},
                {"warehouse_id": w_ids_1[6], "quantity": 1}], "card"),
        (emp2, [{"warehouse_id": w_ids_1[8], "quantity": 3},
                {"warehouse_id": w_ids_2[1], "quantity": 1}], "cash"),
        (emp1, [{"warehouse_id": w_ids_1[0], "quantity": 2},
                {"warehouse_id": w_ids_1[2], "quantity": 4}], "card"),
        (emp1, [{"warehouse_id": w_ids_1[9], "quantity": 10},
                {"warehouse_id": w_ids_1[1], "quantity": 3}], "cash"),
    ]
    sale_ids = []
    for emp, items, method in sales_data:
        sid, rcp, total = db.create_sale(emp, items, method)
        sale_ids.append(sid)

    return {
        "medicine_ids": med_ids,
        "supplier_ids": [sup1, sup2, sup3],
        "invoice_ids":  [inv1, inv2],
        "warehouse_ids": w_ids_1 + w_ids_2,
        "employee_ids": [emp1, emp2, emp3],
        "sale_ids":     sale_ids,
    }
