import pytest
import task_db
from task_tools import query_tasks
from tool_schemas import QueryTasksArgs

def test_query_empty_database(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)
    assert query_tasks(db_path) == []


def test_query_uncompleted(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    # 创建：1条未完成，1条已完成
    id_unfinished = task_db.create_task(db_path, "练习函数", completed=False, priority=1)
    id_finished = task_db.create_task(db_path, "复习HTTP", completed=True, priority=2)

    # 校验查询前后数据不变（验证只读，没有修改数据库）
    before = task_db.list_tasks(db_path)
    task_list = query_tasks(db_path)
    after = task_db.list_tasks(db_path)
    assert before == after

    # 只返回未完成任务
    assert len(task_list) == 1
    assert task_list[0] == {
        "id": id_unfinished,
        "title": "练习函数",
        "completed": False,
        "priority": 1,
    }


def test_query_completed(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    id_unfinished = task_db.create_task(db_path, "练习函数", completed=False, priority=1)
    id_finished = task_db.create_task(db_path, "复习HTTP", completed=True, priority=2)

    task_list = query_tasks(db_path, completed=True)
    assert len(task_list) == 1
    assert task_list[0] == {
        "id": id_finished,
        "title": "复习HTTP",
        "completed": True,
        "priority": 2,
    }


def test_reject_invalid_completed(tmp_path):
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    # 传字符串、数字0、None，都要抛TypeError
    with pytest.raises(TypeError):
        query_tasks(db_path, completed="false")

    with pytest.raises(TypeError):
        query_tasks(db_path, completed=0)

    with pytest.raises(TypeError):
        query_tasks(db_path, completed=None)


def test_query_with_validated_args(tmp_path):
    # 1. 创建临时数据库并初始化
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    # 2. 创建一条未完成任务、一条已完成任务
    id_unfinished = task_db.create_task(db_path, "练习函数", completed=False, priority=1)
    id_finished = task_db.create_task(db_path, "复习HTTP", completed=True, priority=2)

    # 3. 校验参数JSON字符串
    args = QueryTasksArgs.model_validate_json('{"completed": true}')

    # 4. 把校验后的参数传给query_tasks执行查询
    result = query_tasks(
        db_path,
        completed=args.completed,
    )

    # 5. 断言：只返回已完成任务，核对完整字典
    assert len(result) == 1
    assert result[0] == {
        "id": id_finished,
        "title": "复习HTTP",
        "completed": True,
        "priority": 2,
    }
