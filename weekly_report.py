"""学习周报的统计部分。

只做确定性统计：不读取数据库、不调用模型、不写文件。
"""


def calculate_weekly_stats(rows: list[tuple]) -> dict:
    """根据任务元组列表计算周报统计值。

    每条任务的结构是 (id, title, completed, priority)，
    其中 completed 是从 SQLite 读出的整数 0 或 1。
    """
    total = len(rows)

    completed_titles = [row[1] for row in rows if row[2] == 1]
    pending_titles = [row[1] for row in rows if row[2] != 1]

    completed = len(completed_titles)
    pending = len(pending_titles)

    if total == 0:
        completion_rate = 0.0
    else:
        completion_rate = round(completed / total * 100, 1)

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "completed_titles": completed_titles,
        "pending_titles": pending_titles,
    }
