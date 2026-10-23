"""
StockSense — Database layer
Supports multi-user authentication with per-user data isolation.
"""

import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

DB = Path(__file__).resolve().parent / 'stocksense.db'


# ──────────────────────────────────────────────
# CONNECTION
# ──────────────────────────────────────────────

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


# ──────────────────────────────────────────────
# INITIALISATION  (safe — idempotent)
# ──────────────────────────────────────────────

def init():
    with connect() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name   TEXT    NOT NULL,
                store_name  TEXT    NOT NULL DEFAULT '',
                email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT  NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sales (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                date         TEXT    NOT NULL,
                product_id   TEXT    NOT NULL,
                product_name TEXT    NOT NULL,
                quantity_sold REAL   NOT NULL,
                unit_price   REAL    NOT NULL,
                unit_cost    REAL
            );

            CREATE TABLE IF NOT EXISTS products (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER NOT NULL REFERENCES users(id),
                product_id         TEXT    NOT NULL,
                product_name       TEXT    NOT NULL DEFAULT '',
                category           TEXT    NOT NULL DEFAULT '',
                unit               TEXT    NOT NULL DEFAULT 'units',
                current_stock      REAL    NOT NULL DEFAULT 0,
                incoming_stock     REAL    NOT NULL DEFAULT 0,
                lead_time_days     INTEGER NOT NULL DEFAULT 7,
                review_period_days INTEGER NOT NULL DEFAULT 7,
                shelf_life_days    INTEGER NOT NULL DEFAULT 365,
                min_order_qty      INTEGER NOT NULL DEFAULT 1,
                pack_size          INTEGER NOT NULL DEFAULT 1,
                unit_cost          REAL,
                stock_age_days     INTEGER,
                supplier_name      TEXT    NOT NULL DEFAULT '',
                expiry_date        TEXT,
                UNIQUE(user_id, product_id)
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id        INTEGER NOT NULL REFERENCES users(id),
                key            TEXT    NOT NULL,
                value          TEXT    NOT NULL DEFAULT '',
                PRIMARY KEY (user_id, key)
            );
        """)

        # Insert default settings rows for any user that is missing them
        # (runs at startup — harmless if already present)
        for k, v in [
            ('service_level', '0.95'),
            ('default_review_period', '7'),
            ('budget_limit', ''),
        ]:
            c.execute("""
                INSERT OR IGNORE INTO user_settings (user_id, key, value)
                SELECT id, ?, ? FROM users
            """, (k, v))

        # ── Safe migration: migrate legacy products table with product_id PRIMARY KEY ──
        prod_sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'").fetchone()
        if prod_sql and 'product_id TEXT PRIMARY KEY' in prod_sql[0]:
            c.execute("ALTER TABLE products RENAME TO _products_legacy")
            c.execute("""
                CREATE TABLE products (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id            INTEGER NOT NULL REFERENCES users(id),
                    product_id         TEXT    NOT NULL,
                    product_name       TEXT    NOT NULL DEFAULT '',
                    category           TEXT    NOT NULL DEFAULT '',
                    unit               TEXT    NOT NULL DEFAULT 'units',
                    current_stock      REAL    NOT NULL DEFAULT 0,
                    incoming_stock     REAL    NOT NULL DEFAULT 0,
                    lead_time_days     INTEGER NOT NULL DEFAULT 7,
                    review_period_days INTEGER NOT NULL DEFAULT 7,
                    shelf_life_days    INTEGER NOT NULL DEFAULT 365,
                    min_order_qty      INTEGER NOT NULL DEFAULT 1,
                    pack_size          INTEGER NOT NULL DEFAULT 1,
                    unit_cost          REAL,
                    stock_age_days     INTEGER,
                    supplier_name      TEXT    NOT NULL DEFAULT '',
                    UNIQUE(user_id, product_id)
                )
            """)
            c.execute("""
                INSERT INTO products
                    (user_id, product_id, product_name, category, unit, current_stock,
                     incoming_stock, lead_time_days, review_period_days, shelf_life_days,
                     min_order_qty, pack_size, unit_cost, stock_age_days, supplier_name)
                SELECT
                    COALESCE(user_id, 1), product_id, COALESCE(product_name, product_id),
                    COALESCE(category, ''), COALESCE(unit, 'units'), COALESCE(current_stock, 0),
                    COALESCE(incoming_stock, 0), COALESCE(lead_time_days, 7),
                    COALESCE(review_period_days, 7), COALESCE(shelf_life_days, 365),
                    COALESCE(min_order_qty, 1), COALESCE(pack_size, 1), unit_cost,
                    stock_age_days, COALESCE(supplier_name, '')
                FROM _products_legacy
            """)
            c.execute("DROP TABLE _products_legacy")

        # ── Safe migration: add user_id column to legacy tables if absent ──
        # This handles databases created before the auth upgrade.
        _ensure_column(c, 'sales',    'user_id', 'INTEGER NOT NULL DEFAULT 1')
        _ensure_column(c, 'products', 'user_id', 'INTEGER NOT NULL DEFAULT 1')
        _ensure_column(c, 'products', 'product_name', "TEXT NOT NULL DEFAULT ''")
        _ensure_column(c, 'products', 'category',     "TEXT NOT NULL DEFAULT ''")
        _ensure_column(c, 'products', 'unit',         "TEXT NOT NULL DEFAULT 'units'")
        _ensure_column(c, 'products', 'supplier_name', "TEXT NOT NULL DEFAULT ''")
        _ensure_column(c, 'products', 'expiry_date', 'TEXT')

        # Legacy id column on products
        _ensure_column(c, 'products', 'id', 'INTEGER PRIMARY KEY AUTOINCREMENT')

        # Create unique constraint index so ON CONFLICT(user_id, product_id) works on existing DBs
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_user_prod ON products(user_id, product_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_user ON sales(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_user_date ON sales(user_id, date)")


def _ensure_column(conn, table, column, definition):
    """Add a column to a table if it does not already exist."""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except Exception:
            pass   # Column already exists or table doesn't exist yet


# ──────────────────────────────────────────────
# USER AUTH
# ──────────────────────────────────────────────

def create_user(full_name: str, store_name: str, email: str, password: str) -> int:
    """Create a new user. Returns the new user id. Raises ValueError on duplicate."""
    pw_hash = generate_password_hash(password)
    try:
        with connect() as c:
            cur = c.execute(
                "INSERT INTO users (full_name, store_name, email, password_hash) "
                "VALUES (?, ?, ?, ?)",
                (full_name.strip(), store_name.strip(), email.strip().lower(), pw_hash)
            )
            user_id = cur.lastrowid
            # Create default settings for this new user
            for k, v in [
                ('service_level', '0.95'),
                ('default_review_period', '7'),
                ('budget_limit', ''),
            ]:
                c.execute(
                    "INSERT OR IGNORE INTO user_settings (user_id, key, value) VALUES (?,?,?)",
                    (user_id, k, v)
                )
            return user_id
    except sqlite3.IntegrityError:
        raise ValueError("An account with that email address already exists.")


def get_user_by_email(email: str):
    """Return a user row dict or None."""
    with connect() as c:
        row = c.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    """Return a user row dict or None."""
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def delete_user(user_id: int):
    """Safely delete user and all associated records (foreign-key safe)."""
    with connect() as c:
        c.execute("DELETE FROM sales WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM products WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))


def delete_user_by_email(email: str):
    user = get_user_by_email(email)
    if user:
        delete_user(user['id'])


def verify_password(user: dict, password: str) -> bool:
    return check_password_hash(user['password_hash'], password)


def update_user(user_id: int, full_name: str, store_name: str):
    with connect() as c:
        c.execute(
            "UPDATE users SET full_name=?, store_name=? WHERE id=?",
            (full_name.strip(), store_name.strip(), user_id)
        )


# ──────────────────────────────────────────────
# SETTINGS  (per-user)
# ──────────────────────────────────────────────

def settings(user_id: int) -> dict:
    """Return complete settings, repairing missing defaults for older accounts."""
    defaults = {
        'service_level': '0.95',
        'default_review_period': '7',
        'budget_limit': '',
        'theme': 'neon-dark',
        'language': 'en',
    }
    with connect() as c:
        # Guard against stale sessions or legacy data referencing a user that no
        # longer exists. The auth decorator normally redirects these sessions.
        if c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            return defaults.copy()
        # Older databases/accounts may not have every settings row. Add defaults
        # safely without overwriting values the user has already saved.
        c.executemany(
            "INSERT OR IGNORE INTO user_settings (user_id, key, value) VALUES (?,?,?)",
            [(user_id, key, value) for key, value in defaults.items()],
        )
        rows = c.execute(
            "SELECT key, value FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchall()
    result = defaults.copy()
    result.update({r['key']: r['value'] for r in rows})
    return result


def set_settings(d: dict, user_id: int):
    with connect() as c:
        for k, v in d.items():
            c.execute(
                "INSERT INTO user_settings (user_id, key, value) VALUES (?,?,?) "
                "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
                (user_id, k, str(v))
            )


# ──────────────────────────────────────────────
# SALES  (per-user)
# ──────────────────────────────────────────────

def sales(user_id: int):
    import pandas as pd
    with connect() as c:
        return pd.read_sql_query(
            "SELECT date, product_id, product_name, quantity_sold, unit_price, unit_cost "
            "FROM sales WHERE user_id = ?",
            c, params=(user_id,)
        )


def replace_sales(rows, user_id: int):
    """Delete all sales for this user and insert new rows."""
    with connect() as c:
        c.execute("DELETE FROM sales WHERE user_id = ?", (user_id,))
        c.executemany(
            "INSERT INTO sales (user_id, date, product_id, product_name, "
            "quantity_sold, unit_price, unit_cost) VALUES (?,?,?,?,?,?,?)",
            [(user_id,) + tuple(r) for r in rows]
        )


def append_sales(rows, user_id: int):
    """Append sales rows, skipping exact duplicates (date+product+qty+price)."""
    with connect() as c:
        c.executemany(
            "INSERT OR IGNORE INTO sales (user_id, date, product_id, product_name, "
            "quantity_sold, unit_price, unit_cost) VALUES (?,?,?,?,?,?,?)",
            [(user_id,) + tuple(r) for r in rows]
        )


def sales_records_page(user_id: int, page: int = 1, per_page: int = 50,
                       search: str = '', product_filter: str = '') -> dict:
    """Return paginated sales records for the UI table."""
    offset = (page - 1) * per_page
    clauses = ["user_id = ?"]
    params: list = [user_id]

    if search:
        clauses.append("(product_name LIKE ? OR product_id LIKE ?)")
        params += [f'%{search}%', f'%{search}%']
    if product_filter:
        clauses.append("product_id = ?")
        params.append(product_filter)

    where = " AND ".join(clauses)

    with connect() as c:
        total = c.execute(
            f"SELECT COUNT(*) FROM sales WHERE {where}", params
        ).fetchone()[0]

        rows = c.execute(
            f"SELECT date, product_id, product_name, quantity_sold, unit_price, unit_cost "
            f"FROM sales WHERE {where} ORDER BY date DESC, product_name LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, -(-total // per_page)),   # ceiling division
        'rows': [dict(r) for r in rows]
    }


def sales_product_list(user_id: int) -> list:
    """Return distinct (product_id, product_name) pairs for filter dropdown."""
    with connect() as c:
        rows = c.execute(
            "SELECT DISTINCT product_id, product_name FROM sales WHERE user_id = ? "
            "ORDER BY product_name",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# PRODUCTS  (per-user)
# ──────────────────────────────────────────────

def products(user_id: int) -> list:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM products WHERE user_id = ? ORDER BY product_name, product_id",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_product(user_id: int, product_id: str):
    with connect() as c:
        row = c.execute(
            "SELECT * FROM products WHERE user_id=? AND product_id=?",
            (user_id, product_id)
        ).fetchone()
    return dict(row) if row else None


DEFAULT_PROD = {
    'product_name': '',
    'category': '',
    'unit': 'units',
    'current_stock': 0.0,
    'incoming_stock': 0.0,
    'lead_time_days': 7,
    'review_period_days': 7,
    'shelf_life_days': 365,
    'min_order_qty': 1,
    'pack_size': 1,
    'unit_cost': None,
    'stock_age_days': None,
    'supplier_name': '',
    'expiry_date': None,
}


def upsert_product(data: dict, user_id: int):
    """Insert or update a product record for this user."""
    params = {**DEFAULT_PROD, **data, 'user_id': user_id}
    with connect() as c:
        c.execute("""
            INSERT INTO products
                (user_id, product_id, product_name, category, unit,
                 current_stock, incoming_stock, lead_time_days, review_period_days,
                 shelf_life_days, min_order_qty, pack_size, unit_cost,
                 stock_age_days, supplier_name, expiry_date)
            VALUES
                (:user_id,:product_id,:product_name,:category,:unit,
                 :current_stock,:incoming_stock,:lead_time_days,:review_period_days,
                 :shelf_life_days,:min_order_qty,:pack_size,:unit_cost,
                 :stock_age_days,:supplier_name,:expiry_date)
            ON CONFLICT(user_id, product_id) DO UPDATE SET
                product_name   = excluded.product_name,
                category       = excluded.category,
                unit           = excluded.unit,
                current_stock  = excluded.current_stock,
                incoming_stock = excluded.incoming_stock,
                lead_time_days = excluded.lead_time_days,
                review_period_days = excluded.review_period_days,
                shelf_life_days = excluded.shelf_life_days,
                min_order_qty  = excluded.min_order_qty,
                pack_size      = excluded.pack_size,
                unit_cost      = excluded.unit_cost,
                stock_age_days = excluded.stock_age_days,
                supplier_name  = excluded.supplier_name,
                expiry_date    = excluded.expiry_date
        """, params)


def replace_products(rows, user_id: int):
    """Replace all products for this user (used by CSV upload and demo loader)."""
    with connect() as c:
        c.execute("DELETE FROM products WHERE user_id = ?", (user_id,))
        c.executemany(
            "INSERT INTO products "
            "(user_id, product_id, product_name, category, unit, current_stock, incoming_stock, "
            "lead_time_days, review_period_days, shelf_life_days, min_order_qty, pack_size, "
            "unit_cost, stock_age_days, supplier_name, expiry_date) VALUES "
            "(:user_id,:product_id,:product_name,:category,:unit,:current_stock,:incoming_stock,"
            ":lead_time_days,:review_period_days,:shelf_life_days,:min_order_qty,:pack_size,"
            ":unit_cost,:stock_age_days,:supplier_name,:expiry_date)",
            [{**DEFAULT_PROD, **r, 'user_id': user_id,
              'product_name': r.get('product_name', r.get('product_id', ''))} for r in rows]
        )
