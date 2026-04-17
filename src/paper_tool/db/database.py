"""SQLite 连接管理 + schema 初始化"""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS operations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path   TEXT NOT NULL,
    original_name   TEXT NOT NULL,
    new_path        TEXT NOT NULL,
    new_name        TEXT NOT NULL,
    category        TEXT NOT NULL,
    title           TEXT DEFAULT '',
    authors         TEXT DEFAULT '',
    year            TEXT DEFAULT '',
    journal         TEXT DEFAULT '',
    keywords        TEXT DEFAULT '',
    confidence      REAL DEFAULT 0.0,
    status          TEXT NOT NULL DEFAULT 'success',
    error_message   TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rolled_back_at  TIMESTAMP DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_operations_original ON operations(original_path);
CREATE INDEX IF NOT EXISTS idx_operations_category ON operations(category);
CREATE INDEX IF NOT EXISTS idx_operations_created ON operations(created_at DESC);
"""


class Database:
    """SQLite 数据库管理器 (WAL 模式)"""

    def __init__(self, db_path: str | Path):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """建立数据库连接"""
        self._conn = sqlite3.connect(
            str(self._path),
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("数据库尚未连接，请先调用 connect()")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
