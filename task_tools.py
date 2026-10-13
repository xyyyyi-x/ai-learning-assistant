from pathlib import Path
import task_db


def query_tasks(
    db_path: Path,
    completed: bool = False,
    title_query: str | None = None,
) -> list[dict]:
    """按完成状态查询任务，只读取数据库。"""

    if type(completed) is not bool:
        raise TypeError("completed必须是布尔值")

    if title_query is not None and not isinstance(title_query, str):
        raise TypeError("title_query必须是字符串")
    keyword = title_query.strip().lower() if title_query is not None else ""
    rows = task_db.list_tasks(db_path)
    result = []

    # 遍历、筛选、转字典
    for row in rows:
        task_completed = bool(row[2])
        if task_completed == completed and keyword in row[1].lower():
            task = {
                "id": row[0],
                "title": row[1],
                "completed": bool(row[2]),
                "priority": row[3],
            }
            result.append(task)

    return result
