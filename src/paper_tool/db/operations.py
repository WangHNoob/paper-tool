"""操作日志 CRUD"""

from __future__ import annotations

import json
from typing import Any

from .database import Database


def record_operation(db: Database, **kwargs: Any) -> int:
    """记录一条操作日志，返回自增 ID"""
    keys = [
        "original_path", "original_name", "new_path", "new_name",
        "category", "title", "authors", "year", "journal", "keywords",
        "confidence", "status", "error_message",
    ]
    values = {
        k: (
            json.dumps(kwargs.get(k, ""), ensure_ascii=False)
            if isinstance(kwargs.get(k), list)
            else kwargs.get(k, "")
        )
        for k in keys
    }
    placeholders = ", ".join(f":{k}" for k in keys)
    sql = f"INSERT INTO operations ({', '.join(keys)}) VALUES ({placeholders})"
    cursor = db.conn.execute(sql, values)
    db.conn.commit()
    return cursor.lastrowid


def list_operations(
    db: Database,
    *,
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """查询操作日志列表"""
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if category is not None:
        conditions.append("category = :category")
        params["category"] = category
    if status is not None:
        conditions.append("status = :status")
        params["status"] = status

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM operations {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    rows = db.conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def get_operation(db: Database, op_id: int) -> dict[str, Any] | None:
    """获取单条操作记录"""
    row = db.conn.execute(
        "SELECT * FROM operations WHERE id = ?", (op_id,)
    ).fetchone()
    return dict(row) if row else None
