"""SQLite 儲存：每個群組同時最多一張進行中的團購單。"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id         INTEGER NOT NULL,
    platform        TEXT NOT NULL,
    restaurant      TEXT NOT NULL,
    url             TEXT,
    organizer_id    INTEGER NOT NULL,
    organizer_name  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',  -- open / closed / cancelled
    created_at      REAL NOT NULL,
    closed_at       REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_session_per_chat
    ON sessions(chat_id) WHERE status = 'open';

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL,
    user_name   TEXT NOT NULL,
    name        TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    unit_price  REAL,
    note        TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS items_by_session ON items(session_id);
"""


class StorageError(Exception):
    pass


@dataclass
class Session:
    id: int
    chat_id: int
    platform: str
    restaurant: str
    url: str | None
    organizer_id: int
    organizer_name: str
    status: str


@dataclass
class Item:
    id: int
    session_id: int
    user_id: int
    user_name: str
    name: str
    quantity: int
    unit_price: float | None
    note: str

    @property
    def subtotal(self) -> float | None:
        return None if self.unit_price is None else self.unit_price * self.quantity


class Storage:
    def __init__(self, path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # --- sessions ---------------------------------------------------------

    def open_session(
        self,
        chat_id: int,
        platform: str,
        restaurant: str,
        url: str | None,
        organizer_id: int,
        organizer_name: str,
    ) -> Session:
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO sessions (chat_id, platform, restaurant, url,"
                    " organizer_id, organizer_name, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (chat_id, platform, restaurant, url, organizer_id,
                     organizer_name, time.time()),
                )
        except sqlite3.IntegrityError as exc:
            raise StorageError("這個群組已經有進行中的團購單") from exc
        return self.get_session(cur.lastrowid)

    def get_session(self, session_id: int) -> Session:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise StorageError("找不到團購單")
        return _session(row)

    def current_session(self, chat_id: int) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? AND status = 'open'",
            (chat_id,),
        ).fetchone()
        return _session(row) if row else None

    def last_session(self, chat_id: int) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        return _session(row) if row else None

    def set_status(self, session_id: int, status: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET status = ?, closed_at = ? WHERE id = ?",
                (status, time.time(), session_id),
            )

    def reopen(self, session_id: int) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE sessions SET status = 'open', closed_at = NULL"
                    " WHERE id = ?",
                    (session_id,),
                )
        except sqlite3.IntegrityError as exc:
            raise StorageError("這個群組已經有進行中的團購單") from exc

    # --- items ------------------------------------------------------------

    def add_item(
        self,
        session_id: int,
        user_id: int,
        user_name: str,
        name: str,
        quantity: int,
        unit_price: float | None,
        note: str,
    ) -> Item:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO items (session_id, user_id, user_name, name,"
                " quantity, unit_price, note, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, user_id, user_name, name, quantity, unit_price,
                 note, time.time()),
            )
        row = self.conn.execute(
            "SELECT * FROM items WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return _item(row)

    def items(self, session_id: int, user_id: int | None = None) -> list[Item]:
        sql = "SELECT * FROM items WHERE session_id = ?"
        args: tuple = (session_id,)
        if user_id is not None:
            sql += " AND user_id = ?"
            args += (user_id,)
        rows = self.conn.execute(sql + " ORDER BY id", args).fetchall()
        return [_item(r) for r in rows]

    def remove_item(self, session_id: int, item_id: int, user_id: int | None) -> bool:
        """刪除品項；user_id 為 None 時（團主）可刪除任何人的品項。"""
        sql = "DELETE FROM items WHERE session_id = ? AND id = ?"
        args: tuple = (session_id, item_id)
        if user_id is not None:
            sql += " AND user_id = ?"
            args += (user_id,)
        with self.conn:
            cur = self.conn.execute(sql, args)
        return cur.rowcount > 0

    def clear_user_items(self, session_id: int, user_id: int) -> int:
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM items WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
        return cur.rowcount


def _session(row: sqlite3.Row) -> Session:
    return Session(**{k: row[k] for k in Session.__dataclass_fields__})


def _item(row: sqlite3.Row) -> Item:
    return Item(**{k: row[k] for k in Item.__dataclass_fields__})
