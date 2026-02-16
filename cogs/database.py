# database.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Tuple

DB_PATH = Path("economy.db")

BLOCK_TYPES = ("cobblestone", "gravel", "deepslate", "bedrock")
BLOCK_VALUES = {"cobblestone": 1, "gravel": 3, "deepslate": 5, "bedrock": 10}

ALLOWED_MATERIALS = ("none", "gold", "iron", "diamond", "netherite")
ALLOWED_ITEMS = (
    "sword", "pickaxe", "axe", "shovel", "hoe",
    "helmet", "chestplate", "leggings", "boots",
    "ingot", "stick"
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY,
                emeralds  INTEGER NOT NULL DEFAULT 0 CHECK (emeralds >= 0)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                user_id     INTEGER NOT NULL,
                block_type  TEXT    NOT NULL CHECK (block_type IN ('cobblestone','gravel','deepslate','bedrock')),
                amount      INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
                PRIMARY KEY (user_id, block_type),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_blocks_user ON blocks(user_id);")

        # NEW: items inventory (for admin + later market/craft)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                user_id   INTEGER NOT NULL,
                item      TEXT    NOT NULL,
                material  TEXT    NOT NULL,
                amount    INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
                PRIMARY KEY (user_id, item, material),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id);")


# NEW: gear inventory (non-stackable)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS gear (
        gear_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        item       TEXT    NOT NULL,
        material   TEXT    NOT NULL,
        created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """
)
conn.execute("CREATE INDEX IF NOT EXISTS idx_gear_user ON gear(user_id);")



def ensure_user(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id, emeralds) VALUES(?, 0);", (user_id,))
        for b in BLOCK_TYPES:
            conn.execute(
                "INSERT OR IGNORE INTO blocks(user_id, block_type, amount) VALUES(?, ?, 0);",
                (user_id, b),
            )


# ---------- emeralds ----------
def get_emeralds(user_id: int) -> int:
    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute("SELECT emeralds FROM users WHERE user_id=?;", (user_id,)).fetchone()
        return int(row["emeralds"]) if row else 0


def add_emeralds(user_id: int, delta: int) -> int:
    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET emeralds = CASE WHEN emeralds + ? < 0 THEN 0 ELSE emeralds + ? END
            WHERE user_id = ?;
            """,
            (delta, delta, user_id),
        )
    return get_emeralds(user_id)


# ---------- blocks ----------
def get_blocks(user_id: int) -> Dict[str, int]:
    ensure_user(user_id)
    inv = {b: 0 for b in BLOCK_TYPES}
    with _connect() as conn:
        rows = conn.execute(
            "SELECT block_type, amount FROM blocks WHERE user_id=?;",
            (user_id,),
        ).fetchall()
        for r in rows:
            inv[str(r["block_type"])] = int(r["amount"])
    return inv


def add_blocks(user_id: int, block_type: str, delta: int) -> int:
    if block_type not in BLOCK_VALUES:
        raise ValueError(f"Unknown block_type: {block_type}")

    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO blocks(user_id, block_type, amount)
            VALUES(?, ?, 0)
            ON CONFLICT(user_id, block_type) DO NOTHING;
            """,
            (user_id, block_type),
        )
        conn.execute(
            """
            UPDATE blocks
            SET amount = CASE WHEN amount + ? < 0 THEN 0 ELSE amount + ? END
            WHERE user_id=? AND block_type=?;
            """,
            (delta, delta, user_id, block_type),
        )
        row = conn.execute(
            "SELECT amount FROM blocks WHERE user_id=? AND block_type=?;",
            (user_id, block_type),
        ).fetchone()
        return int(row["amount"]) if row else 0


def sell_all_blocks(user_id: int) -> Tuple[int, Dict[str, int]]:
    ensure_user(user_id)
    inv = get_blocks(user_id)

    gained = 0
    sold: Dict[str, int] = {}
    for b, amt in inv.items():
        if amt <= 0:
            continue
        gained += amt * BLOCK_VALUES[b]
        sold[b] = amt

    if gained == 0:
        return 0, {}

    with _connect() as conn:
        conn.execute("UPDATE blocks SET amount=0 WHERE user_id=?;", (user_id,))
        conn.execute("UPDATE users SET emeralds = emeralds + ? WHERE user_id=?;", (gained, user_id))

    return gained, sold


# ---------- items ----------
def get_items(user_id: int) -> Dict[tuple[str, str], int]:
    ensure_user(user_id)
    out: Dict[tuple[str, str], int] = {}
    with _connect() as conn:
        rows = conn.execute(
            "SELECT item, material, amount FROM items WHERE user_id=?;",
            (user_id,),
        ).fetchall()
        for r in rows:
            out[(str(r["item"]), str(r["material"]))] = int(r["amount"])
    return out


def add_item(user_id: int, item: str, material: str, delta: int) -> int:
    ensure_user(user_id)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO items(user_id, item, material, amount)
            VALUES(?, ?, ?, 0)
            ON CONFLICT(user_id, item, material) DO NOTHING;
            """,
            (user_id, item, material),
        )
        conn.execute(
            """
            UPDATE items
            SET amount = CASE WHEN amount + ? < 0 THEN 0 ELSE amount + ? END
            WHERE user_id=? AND item=? AND material=?;
            """,
            (delta, delta, user_id, item, material),
        )
        row = conn.execute(
            "SELECT amount FROM items WHERE user_id=? AND item=? AND material=?;",
            (user_id, item, material),
        ).fetchone()
        return int(row["amount"]) if row else 0

def get_item_amount(user_id: int, item: str, material: str) -> int:
    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT amount FROM items WHERE user_id=? AND item=? AND material=?;",
            (user_id, item, material),
        ).fetchone()
        return int(row["amount"]) if row else 0


def remove_item_checked(user_id: int, item: str, material: str, amount: int) -> bool:
    """
    Removes amount if user has enough. Returns True if removed, False otherwise.
    """
    if amount <= 0:
        return True

    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT amount FROM items WHERE user_id=? AND item=? AND material=?;",
            (user_id, item, material),
        ).fetchone()

        current = int(row["amount"]) if row else 0
        if current < amount:
            return False

        conn.execute(
            "UPDATE items SET amount = amount - ? WHERE user_id=? AND item=? AND material=?;",
            (amount, user_id, item, material),
        )
        return True

def add_gear(user_id: int, item: str, material: str) -> None:
    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO gear(user_id, item, material) VALUES(?, ?, ?);",
            (user_id, item, material),
        )

def get_gear(user_id: int) -> list[tuple[str, str]]:
    ensure_user(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT item, material FROM gear WHERE user_id=? ORDER BY gear_id;",
            (user_id,),
        ).fetchall()
    return [(str(r["item"]), str(r["material"])) for r in rows]

def remove_gear(user_id: int, item: str, material: str, count: int = 1) -> int:
    """Remove up to 'count' gear pieces. Returns how many were removed."""
    ensure_user(user_id)
    if count <= 0:
        return 0
    with _connect() as conn:
        rows = conn.execute(
            "SELECT gear_id FROM gear WHERE user_id=? AND item=? AND material=? ORDER BY gear_id LIMIT ?;",
            (user_id, item, material, count),
        ).fetchall()
        ids = [int(r["gear_id"]) for r in rows]
        for gid in ids:
            conn.execute("DELETE FROM gear WHERE gear_id=?;", (gid,))
    return len(ids)
