"""回滚逻辑"""

import logging
import shutil
from pathlib import Path

from .database import Database
from .operations import get_operation

logger = logging.getLogger(__name__)


def rollback_operation(db: Database, op_id: int) -> bool:
    """回滚指定操作，将文件移回原始位置。

    Args:
        db: 数据库实例
        op_id: 操作记录 ID

    Returns:
        True 回滚成功，False 回滚失败
    """
    op = get_operation(db, op_id)
    if op is None:
        logger.error("操作记录 %d 不存在", op_id)
        return False

    if op.get("rolled_back_at") is not None:
        logger.warning("操作记录 %d 已经被回滚过", op_id)
        return False

    if op["status"] != "success":
        logger.error("操作记录 %d 状态为 %s，无法回滚", op_id, op["status"])
        return False

    new_path = Path(op["new_path"])
    original_path = Path(op["original_path"])

    if not new_path.exists():
        logger.error("文件不存在，无法回滚: %s", new_path)
        return False

    try:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(new_path), str(original_path))
        db.conn.execute(
            "UPDATE operations SET rolled_back_at = CURRENT_TIMESTAMP WHERE id = ?",
            (op_id,),
        )
        db.conn.commit()
        logger.info("回滚成功: %s -> %s", new_path, original_path)
        return True
    except OSError as e:
        logger.error("回滚失败: %s", e)
        return False
