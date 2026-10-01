import json
import pytest
from pydantic import ValidationError

import task_db
from tool_messages import build_tool_reply


def test_build_tool_reply(tmp_path):
    """基础测试：正常查询，生成正确tool消息"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    task_id = task_db.create_task(
        db_path,
        "练习函数",
        completed=False,
    )

    reply = build_tool_reply(
        "call_001",
        "query_tasks",
        '{"completed": false}',
        db_path,
    )

    assert reply["role"] == "tool"
    assert reply["tool_call_id"] == "call_001"
    assert isinstance(reply["content"], str)

    tasks = json.loads(reply["content"])
    assert tasks == [
        {
            "id": task_id,
            "title": "练习函数",
            "completed": False,
            "priority": 1,
        }
    ]


def test_build_tool_reply_empty_result(tmp_path):
    """空查询结果：数据库无匹配任务，content解析后为空列表"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)
    # 不创建任何任务

    reply = build_tool_reply(
        "call_empty",
        "query_tasks",
        '{"completed": false}',
        db_path,
    )

    assert reply["tool_call_id"] == "call_empty"
    tasks = json.loads(reply["content"])
    assert tasks == []


def test_build_tool_reply_unknown_tool(tmp_path):
    """调用未知工具，抛出ValueError，包含'未知工具'"""
    db_path = tmp_path / "tasks.db"

    with pytest.raises(ValueError, match="未知工具"):
        build_tool_reply(
            "call_bad",
            "delete_tasks",
            "{}",
            db_path,
        )


def test_build_tool_reply_invalid_argument(tmp_path):
    """非法参数，抛出ValidationError"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    with pytest.raises(ValidationError):
        build_tool_reply(
            "call_bad_param",
            "query_tasks",
            '{"completed": null}',
            db_path,
        )
