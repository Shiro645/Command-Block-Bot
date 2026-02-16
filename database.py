# database.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Tuple

DB_PATH = Path("economy.db")

# --- constants ---
BLOCK_TYPES = ("cobblestone", "gravel", "deepslate", "bedrock")
BLOCK_VALUES = {"cobblestone": 1, "gravel": 3, "deepslate": 5, "bedrock": 10}

ALLOWED_MATERIALS = ("none", "gold", "iron", "diamond", "netherite")
GEAR_ITEMS = ("sword", "pickaxe", "axe", "shovel", "hoe", "helmet", "chestplate", "leggings", "boots")
TALENT_BRANCHES = ("miner", "trader", "lucky", "efficiency")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        # USERS (economy + xp + talents)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,

                emeralds INTEGER NOT NULL DEFAULT 0 CHECK (emeralds >= 0),

                xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
                level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),

                talent_points INTEGER NOT NULL DEFAULT 0 CHECK (talent_points >= 0),
                miner_points INTEGER NOT NULL DEFAULT 0 CHECK (miner_points >= 0),
                trader_points INTEGER NOT NULL DEFAULT 0 CHECK (trader_points >= 0),
                lucky_points INTEGER NOT NULL DEFAULT 0 CHECK (lucky_points >= 0),
                efficiency_points INTEGER NOT NULL DEFAULT 0 CHECK (efficiency_points >= 0)
            );
            """
        )

        # BLOCKS
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                user_id    INTEGER NOT NULL,
                block_type TEXT    NOT NULL CHECK (block_type IN ('cobblestone','gravel','deepslate','bedrock')),
                amount     INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
                PRIMARY KEY (user_id, block_type),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_blocks_user ON blocks(user_id);")

        # ITEMS (stackable)
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

        # GEAR (non-stackable)
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
    init_db()
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?);", (user_id,))
        for b in BLOCK_TYPES:
            conn.execute(
                "INSERT OR IGNORE INTO blocks(user_id, block_type, amount) VALUES(?, ?, 0);",
                (user_id, b),
            )


# ---------------- economy: emeralds ----------------
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


# ---------------- economy: blocks ----------------
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


# ---------------- economy: items ----------------
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


# ---------------- economy: gear ----------------
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


# ---------------- XP / Talents ----------------
def xp_required_for_level(level: int) -> int:
    return 100 + (level - 1) * 25


def get_progress(user_id: int) -> dict:
    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?;", (user_id,)).fetchone()
        return dict(row) if row else {}


def add_xp(user_id: int, amount: int) -> dict:
    ensure_user(user_id)
    if amount <= 0:
        return get_progress(user_id)

    with _connect() as conn:
        row = conn.execute("SELECT xp, level, talent_points FROM users WHERE user_id=?;", (user_id,)).fetchone()
        xp = int(row["xp"]) + amount
        level = int(row["level"])
        talent_points = int(row["talent_points"])

        while xp >= xp_required_for_level(level):
            xp -= xp_required_for_level(level)
            level += 1
            if level % 5 == 0:
                talent_points += 1

        conn.execute(
            "UPDATE users SET xp=?, level=?, talent_points=? WHERE user_id=?;",
            (xp, level, talent_points, user_id),
        )

    return get_progress(user_id)


def set_xp_level(user_id: int, xp: int | None = None, level: int | None = None) -> dict:
    ensure_user(user_id)
    with _connect() as conn:
        if xp is not None:
            conn.execute("UPDATE users SET xp=? WHERE user_id=?;", (max(0, int(xp)), user_id))
        if level is not None:
            conn.execute("UPDATE users SET level=? WHERE user_id=?;", (max(1, int(level)), user_id))
    return get_progress(user_id)


def add_talent_points(user_id: int, delta: int) -> dict:
    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute("SELECT talent_points FROM users WHERE user_id=?;", (user_id,)).fetchone()
        new_val = max(0, int(row["talent_points"]) + int(delta))
        conn.execute("UPDATE users SET talent_points=? WHERE user_id=?;", (new_val, user_id))
    return get_progress(user_id)


def reset_talents(user_id: int) -> dict:
    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE users SET
                miner_points=0,
                trader_points=0,
                lucky_points=0,
                efficiency_points=0
            WHERE user_id=?;
            """,
            (user_id,),
        )
    return get_progress(user_id)


def spend_talent_point(user_id: int, branch: str, points: int = 1) -> dict | None:
    branch = branch.lower().strip()
    if branch not in TALENT_BRANCHES:
        return None
    points = max(1, int(points))

    ensure_user(user_id)

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT talent_points, miner_points, trader_points, lucky_points, efficiency_points
            FROM users WHERE user_id=?;
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            return None

        have = int(row["talent_points"])
        if have < points:
            return None

        col = f"{branch}_points"
        conn.execute(
            f"""
            UPDATE users
            SET talent_points = talent_points - ?,
                {col} = {col} + ?
            WHERE user_id=?;
            """,
            (points, points, user_id),
        )

    return get_progress(user_id)
