"""周报工作流测试。

使用临时 SQLite 数据库和假模型函数，不读取真实数据库、不调用真实模型。
"""
import requests
import pytest

from task_db import create_task, init_db
from weekly_report_service import create_weekly_report


def _prepare_db(db_path, tasks):
    """建库并写入任务；tasks 是 (标题, 是否完成) 的列表。"""
    init_db(db_path)
    for title, completed in tasks:
        create_task(db_path, title, completed=completed)


def test_report_with_tasks(tmp_path):
    db_path = tmp_path / "tasks.db"
    output_path = tmp_path / "reports" / "weekly.md"

    _prepare_db(db_path, [("已完成任务", True), ("未完成任务", False)])

    received = []

    def fake_model(stats):
        received.append(stats)
        return "# 学习周报\n\n测试周报正文"

    report = create_weekly_report(db_path, output_path, model_generate=fake_model)

    # 模型只调用一次，且收到的是 Python 算出来的统计值
    assert len(received) == 1
    assert received[0]["total"] == 2
    assert received[0]["completed"] == 1
    assert received[0]["pending"] == 1

    assert report == "# 学习周报\n\n测试周报正文"
    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8") == report


def test_empty_database(tmp_path):
    db_path = tmp_path / "tasks.db"
    output_path = tmp_path / "reports" / "weekly.md"

    init_db(db_path)  # 只建表，不创建任何任务

    def fake_model(stats):
        raise AssertionError("空任务不应该调用模型")

    report = create_weekly_report(db_path, output_path, model_generate=fake_model)

    assert report == "# 学习周报\n\n本周暂无任务记录。"
    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8") == report


def test_model_failure(tmp_path):
    db_path = tmp_path / "tasks.db"
    output_path = tmp_path / "reports" / "weekly.md"

    _prepare_db(db_path, [("一条任务", False)])

    def fake_model(stats):
        raise requests.exceptions.Timeout("模拟模型超时")

    with pytest.raises(requests.exceptions.Timeout):
        create_weekly_report(db_path, output_path, model_generate=fake_model)

    assert not output_path.exists()
