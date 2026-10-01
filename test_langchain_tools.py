import pytest
from pydantic import ValidationError

import task_db
from langchain_tools import create_query_tool


def test_query_uncompleted(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    unfinished_id = task_db.create_task(
        db_path, "练习工具调用", completed=False
    )
    task_db.create_task(
        db_path, "复习HTTP", completed=True
    )

    query_tool = create_query_tool(db_path)
    result = query_tool.invoke({"completed": False})

    assert query_tool.name == "query_tasks"
    assert result == [
        {
            "id": unfinished_id,
            "title": "练习工具调用",
            "completed": False,
            "priority": 1,
        }
    ]


def test_query_completed(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    task_db.create_task(
        db_path, "练习工具调用", completed=False
    )
    finished_id = task_db.create_task(
        db_path, "复习HTTP", completed=True
    )

    query_tool = create_query_tool(db_path)
    result = query_tool.invoke({"completed": True})

    assert query_tool.name == "query_tasks"
    assert result == [
        {
            "id": finished_id,
            "title": "复习HTTP",
            "completed": True,
            "priority": 1,
        }
    ]


def test_query_invalid_param_raise_validation_error(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)
    task_db.create_task(db_path, "练习工具调用", completed=False)

    query_tool = create_query_tool(db_path)

    # 传入字符串"false"，不是布尔值，触发Pydantic参数校验报错
    with pytest.raises(ValidationError):
        query_tool.invoke({"completed": "false"})
