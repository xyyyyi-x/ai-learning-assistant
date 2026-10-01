from pathlib import Path
import task_db


def query_tasks(
    db_path: Path,
    completed: bool = False,
) -> list[dict]:
    """按完成状态查询任务，只读取数据库。"""

    if type(completed) is not bool:
        raise TypeError("completed必须是布尔值")

    rows = task_db.list_tasks(db_path)
    result = []

    # 遍历、筛选、转字典
    for row in rows:
        task_completed = bool(row[2])
        if task_completed == completed:
            task = {
                "id": row[0],
                "title": row[1],
                "completed": bool(row[2]),
                "priority": row[3],
            }
            result.append(task)

    return result
