"""学习周报工作流：查询任务 → 计算统计 → 生成文字 → 保存 Markdown。"""
from pathlib import Path
from typing import Callable

from task_db import list_tasks
from weekly_report import calculate_weekly_stats
from weekly_report_model import generate_weekly_report_text

EMPTY_REPORT = "# 学习周报\n\n本周暂无任务记录。"


def create_weekly_report(
    db_path: Path,
    output_path: Path,
    model_generate: Callable[[dict], str] = generate_weekly_report_text,
) -> str:
    """生成并保存学习周报，返回实际保存的内容。

    没有任务时不调用模型，直接使用固定内容。
    模型失败时异常继续向上抛出，且不会创建周报文件。
    """
    rows = list_tasks(db_path)
    stats = calculate_weekly_stats(rows)

    if stats["total"] == 0:
        report = EMPTY_REPORT
    else:
        report = model_generate(stats)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    return report
