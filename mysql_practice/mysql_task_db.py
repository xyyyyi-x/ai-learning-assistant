"""MySQL 版任务 CRUD。

所有函数接收调用方传入的 connection，内部不调用 commit()，
由调用方决定提交还是回滚。找不到记录时返回 None 或 False，
不抛出 HTTP 异常。
"""


def _validate_title(title) -> str:
    if not isinstance(title, str):
        raise TypeError("title 必须是字符串")

    stripped = title.strip()
    if not (1 <= len(stripped) <= 50):
        raise ValueError("title 去掉首尾空白后长度必须在 1～50 之间")

    return stripped


def _validate_completed(completed) -> bool:
    if type(completed) is not bool:
        raise TypeError("completed 必须是布尔值")

    return completed


def _validate_priority(priority) -> int:
    if not isinstance(priority, int) or type(priority) is bool:
        raise TypeError("priority 必须是整数，不能是布尔值")

    if not (1 <= priority <= 3):
        raise ValueError("priority 必须在 1～3 之间")

    return priority


def _validate_task_id(task_id) -> int:
    if not isinstance(task_id, int) or type(task_id) is bool:
        raise TypeError("task_id 必须是整数，不能是布尔值")

    if task_id <= 0:
        raise ValueError("task_id 必须是正整数")

    return task_id


def create_task(connection, title, completed=False, priority=1) -> int:
    """插入任务，返回新编号；不提交，由调用方决定。"""
    title = _validate_title(title)
    completed = _validate_completed(completed)
    priority = _validate_priority(priority)

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO tasks (title, completed, priority) VALUES (%s, %s, %s)",
            (title, completed, priority),
        )
        return cursor.lastrowid
    finally:
        cursor.close()


def get_task(connection, task_id) -> dict | None:
    """返回任务字典；不存在时返回 None。"""
    task_id = _validate_task_id(task_id)

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, title, completed, priority FROM tasks WHERE id = %s",
            (task_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()

    if row is None:
        return None

    row["completed"] = bool(row["completed"])
    return row


def list_tasks(connection, completed=None) -> list[dict]:
    """completed 为 None 时返回全部，否则只返回对应状态的任务。"""
    if completed is not None:
        completed = _validate_completed(completed)

    cursor = connection.cursor(dictionary=True)
    try:
        if completed is None:
            cursor.execute(
                "SELECT id, title, completed, priority FROM tasks ORDER BY id"
            )
        else:
            cursor.execute(
                "SELECT id, title, completed, priority FROM tasks"
                " WHERE completed = %s ORDER BY id",
                (completed,),
            )
        rows = cursor.fetchall()
    finally:
        cursor.close()

    for row in rows:
        row["completed"] = bool(row["completed"])

    return rows


def update_completed(connection, task_id, completed) -> bool:
    """更新完成状态；找到返回 True，不存在返回 False。"""
    task_id = _validate_task_id(task_id)
    completed = _validate_completed(completed)

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "UPDATE tasks SET completed = %s WHERE id = %s",
            (completed, task_id),
        )

        if cursor.rowcount == 1:
            return True

        # rowcount 为 0 有两种可能：记录不存在，或者新值与旧值相同
        # （MySQL 默认按"实际改变的行数"计数）。再查一次才能区分。
        cursor.execute(
            "SELECT 1 AS exists_flag FROM tasks WHERE id = %s",
            (task_id,),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def delete_task(connection, task_id) -> bool:
    """删除任务；找到并删除返回 True，不存在返回 False。"""
    task_id = _validate_task_id(task_id)

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cursor.rowcount == 1
    finally:
        cursor.close()
