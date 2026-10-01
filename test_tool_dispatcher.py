import pytest
from pydantic import ValidationError

import task_db
from tool_dispatcher import execute_tool

import tool_dispatcher


def test_execute_query_tasks(tmp_path):
    """正常查询：筛选未完成任务，成功案例"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    unfinished_id = task_db.create_task(
        db_path, "练习工具调用", completed=False
    )
    task_db.create_task(
        db_path, "复习JSON", completed=True
    )

    result = execute_tool(
        "query_tasks",
        '{"completed": false}',
        db_path,
    )

    assert result == [
        {
            "id": unfinished_id,
            "title": "练习工具调用",
            "completed": False,
            "priority": 1,
        }
    ]


def test_execute_query_tasks_default_args(tmp_path):
    """测试：参数 {}，使用模型默认参数，返回未完成任务"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)
    task_db.create_task(db_path, "任务A", completed=False)
    task_db.create_task(db_path, "任务B", completed=True)

    result = execute_tool(
        "query_tasks",
        "{}",
        db_path
    )
    # 未提供completed时，默认使用False，查询未完成任务
    assert len(result) == 1
    assert result[0]["title"] == "任务A"


def test_execute_unknown_tool(tmp_path):
    """测试：调用不存在的工具 delete_tasks，抛出ValueError:未知工具"""
    db_path = tmp_path / "tasks.db"
    with pytest.raises(ValueError, match="未知工具"):
        execute_tool(
            "delete_tasks",
            "{}",
            db_path
        )


def test_execute_query_tasks_invalid_param(tmp_path):
    """测试：参数类型错误 completed:"false"（字符串而不是布尔值）抛出ValidationError"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    with pytest.raises(ValidationError):
        execute_tool(
            "query_tasks",
            '{"completed": "false"}',
            db_path
        )


def test_invalid_args_do_not_call_query(tmp_path, monkeypatch):
    calls = []

    def fake_query(db_path, completed=False):
        calls.append(completed)
        return []

    monkeypatch.setitem(
        tool_dispatcher.TOOL_FUNCTIONS,
        "query_tasks",
        fake_query,
    )

    with pytest.raises(ValidationError):
        execute_tool(
            "query_tasks",
            '{"completed": "false"}',
            tmp_path / "tasks.db",
        )

    assert calls == []

def test_unknown_tool_does_not_call_query(tmp_path, monkeypatch):
    calls = []
    def fake_query(db_path, completed=False):
        calls.append(completed)
        return []

    monkeypatch.setitem(
        tool_dispatcher.TOOL_FUNCTIONS,
        "query_tasks",
        fake_query,
    )

    with pytest.raises(ValueError, match="未知工具"):
        execute_tool(
            "delete_tasks",
            "{}",
            tmp_path / "tasks.db",
        )
    # 未知工具，不会走到查询函数，calls保持空
    assert calls == []


def test_valid_args_call_query_once(tmp_path, monkeypatch):
    calls = []
    expected = [
        {
            "id": 7,
            "title": "复习工具调用",
            "completed": True,
            "priority": 1,
        }
    ]

    def fake_query(db_path, completed):
        calls.append(completed)
        return expected

    monkeypatch.setitem(
        tool_dispatcher.TOOL_FUNCTIONS,
        "query_tasks",
        fake_query,
    )

    result = execute_tool(
        "query_tasks",
        '{"completed": true}',
        tmp_path / "tasks.db",
    )
    # 校验参数正确，调用一次，参数正确，返回值原样传回
    assert calls == [True]
    assert result == expected
