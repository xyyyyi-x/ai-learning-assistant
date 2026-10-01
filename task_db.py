import sqlite3
from pathlib import Path

def update_completed(
        db_path:Path,
        task_id:int,
        completed:bool,
)->bool:
    """
    更新完成状态：找到任务返回True，不存在返回False。
    :param db_path:
    :param task_id:
    :param completed:
    :return:
    """
    if type(completed)!=bool:
        raise TypeError("completed必须是布尔值")

    conn=sqlite3.connect(db_path)
    try:
        cursor=conn.execute(
            "UPDATE tasks SET completed = ? WHERE id = ?",
            (int(completed),task_id),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()
def get_task(db_path: Path, task_id: int) -> tuple | None:
    """返回完整任务元组(id, title, completed, priority)，不存在返回None。"""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, title, completed, priority FROM tasks WHERE id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        return row
    finally:
        conn.close()
def delete_task(db_path: Path, task_id: int) -> bool:
    """删除任务；找到并删除返回True，不存在返回False。"""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        conn.commit()
        # rowcount：被删除的行数，等于1代表确实删到了记录
        return cursor.rowcount == 1
    finally:
        conn.close()

def init_db(db_path: Path) -> None:
    """创建任务表；表已存在时保留已有数据。"""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
    finally:
        conn.close()

from pathlib import Path
import sqlite3

def create_task(
    db_path: Path,
    title: str,
    completed: bool = False,
    priority: int = 1,
) -> int:
    """创建任务并返回数据库分配的编号。"""
    # 类型校验（类型检查放最前面）
    if not isinstance(title, str):
        raise TypeError("title必须是字符串")
    if type(completed) is not bool:
        raise TypeError("completed必须是布尔值")
    if not isinstance(priority, int) or type(priority) is bool:
        raise TypeError("priority必须是整数，不能是布尔值")

    # 值校验
    if not (1 <= len(title) <= 50):
        raise ValueError("title长度必须在1～50之间")
    if not (1 <= priority <= 3):
        raise ValueError("priority必须在1～3之间")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (title, completed, priority) VALUES (?, ?, ?)",
            (title, int(completed), priority),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_tasks(db_path: Path, priority: int | None = None) -> list[tuple]:
    """按编号id升序返回任务元组列表；priority 为 None 时返回全部，否则只返回该优先级的任务。"""
    if priority is not None:
        if not isinstance(priority, int) or type(priority) is bool:
            raise TypeError("priority必须是整数，不能是布尔值")
        if not (1 <= priority <= 3):
            raise ValueError("priority必须在1～3之间")

    conn = sqlite3.connect(db_path)
    try:
        if priority is None:
            cursor = conn.execute(
                "SELECT id, title, completed, priority FROM tasks ORDER BY id"
            )
        else:
            cursor = conn.execute(
                "SELECT id, title, completed, priority FROM tasks WHERE priority = ? ORDER BY id",
                (priority,),
            )
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
