import sqlite3
import pytest
from task_db import get_task,update_completed,delete_task
from task_db import init_db, create_task, list_tasks

@pytest.fixture
def db_path(tmp_path):
    path=tmp_path/"test_tasks.db"
    conn=sqlite3.connect(path)

    try:
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.executemany(
            "INSERT INTO tasks (id, title, completed, priority)"
            " VALUES (?, ?, ?, ?)",
            [
                (1,"任务A",0,1),
                (2,"任务B",0,3),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    return path

def test_get_task(db_path):
    assert get_task(db_path,1) ==(1,"任务A",0,1)
    assert get_task(db_path,-1) is None

def test_update_completed(db_path):
    # 更新任务1 completed=True，断言返回True
    ret = update_completed(db_path, 1, True)
    assert ret is True
    # 查询任务1，确认状态已变成1（SQLite存整数1代表True）
    task1 = get_task(db_path, 1)
    assert task1 == (1, "任务A", 1, 1)

    # 任务2保持不变
    task2 = get_task(db_path, 2)
    assert task2 == (2, "任务B", 0, 3)

    # 再改回 False，校验结果
    ret2 = update_completed(db_path, 1, False)
    assert ret2 is True
    task1_after = get_task(db_path, 1)
    assert task1_after == (1, "任务A", 0, 1)

def test_missing_and_invalid_update(db_path):
    # 更新不存在id=-1，返回False
    ret_not_exist = update_completed(db_path, -1, True)
    assert ret_not_exist is False

    # 传入非bool类型，应当抛出TypeError
    with pytest.raises(TypeError):
        update_completed(db_path, 1, "true")

    with pytest.raises(TypeError):
        update_completed(db_path, 1, 1)

    with pytest.raises(TypeError):
        update_completed(db_path, 1, None)

    # 全部非法操作跑完，统一查询确认1、2数据完全没改动
    t1 = get_task(db_path, 1)
    t2 = get_task(db_path, 2)
    assert t1 == (1, "任务A", 0, 1)
    assert t2 == (2, "任务B", 0, 3)

def test_delete_task(db_path):
    # 删除任务1，返回True
    del_ret1 = delete_task(db_path, 1)
    assert del_ret1 is True

    # 查询任务1已经不存在
    t1 = get_task(db_path, 1)
    assert t1 is None

    # 任务2内容不变
    t2 = get_task(db_path, 2)
    assert t2 == (2, "任务B", 0, 3)

    # 再次删除已经删掉的任务1，返回False
    del_ret2 = delete_task(db_path, 1)
    assert del_ret2 is False

def test_init_db_keeps_existing_data(tmp_path):
    path = tmp_path / "tasks.db"
    init_db(path)

    assert list_tasks(path) == []

    task_id = create_task(path, "保留这条任务")

    init_db(path)

    assert get_task(path, task_id) == (
        task_id, "保留这条任务", 0, 1
    )

def test_create_and_list(tmp_path):
    path = tmp_path / "tasks.db"
    init_db(path)

    id_a = create_task(path, "任务A")
    id_b = create_task(path, "任务B", completed=True, priority=3)

    # 编号是整数，且两个id不相等
    assert isinstance(id_a, int)
    assert isinstance(id_b, int)
    assert id_a != id_b

    tasks = list_tasks(path)
    # 按id升序，先A后B
    assert tasks == [
        (id_a, "任务A", 0, 1),
        (id_b, "任务B", 1, 3)
    ]

def test_invalid_create_keeps_data(tmp_path):
    path = tmp_path / "tasks.db"
    init_db(path)

    # 先创建合法任务A，保存快照
    task_id = create_task(path, "任务A")
    snapshot = list_tasks(path)

    # 各种非法输入，全部要抛出对应异常
    with pytest.raises(TypeError):
        create_task(path, title=None)

    with pytest.raises(ValueError):
        create_task(path, title="")

    with pytest.raises(ValueError):
        create_task(path, title="a" * 51)

    with pytest.raises(TypeError):
        create_task(path, "合法标题", completed=1)

    with pytest.raises(TypeError):
        create_task(path, "合法标题", priority=True)

    with pytest.raises(ValueError):
        create_task(path, "合法标题", priority=0)

    with pytest.raises(ValueError):
        create_task(path, "合法标题", priority=4)

    # 全部非法操作跑完，数据库数据不能变，和快照一致
    assert list_tasks(path) == snapshot
    assert get_task(path, task_id) == (task_id, "任务A", 0, 1)

def test_create_title_with_quote(tmp_path):
    path = tmp_path / "tasks.db"
    init_db(path)

    task_id = create_task(path, "学习 O'Reilly")
    row = get_task(path, task_id)
    assert row is not None
    assert row[1] == "学习 O'Reilly"


def test_list_tasks_no_priority(db_path):
    # 不传参数
    assert list_tasks(db_path) == [(1, "任务A", 0, 1), (2, "任务B", 0, 3)]
    # 显式传 None
    assert list_tasks(db_path, priority=None) == [(1, "任务A", 0, 1), (2, "任务B", 0, 3)]


def test_list_tasks_filter_priority(db_path):
    # 筛选优先级1，只返回任务A
    assert list_tasks(db_path, priority=1) == [(1, "任务A", 0, 1)]
    # 筛选优先级3，只返回任务B
    assert list_tasks(db_path, priority=3) == [(2, "任务B", 0, 3)]
    # 筛选优先级2，没有匹配任务，返回空列表
    assert list_tasks(db_path, priority=2) == []


def test_list_tasks_filter_multiple(db_path):
    # 再创建一条优先级1的任务
    new_id = create_task(db_path, "任务C", priority=1)
    # 筛选优先级1，现在有两条，按编号升序
    result = list_tasks(db_path, priority=1)
    assert result == [
        (1, "任务A", 0, 1),
        (new_id, "任务C", 0, 1),
    ]
    # 确认按编号升序（1 在前，new_id 在后）
    assert [row[0] for row in result] == [1, new_id]


def test_list_tasks_invalid_priority(db_path):
    # 非法类型 → TypeError
    for bad in ["1", 1.0, True]:
        with pytest.raises(TypeError):
            list_tasks(db_path, priority=bad)
    # 非法数值 → ValueError
    for bad in [0, 4]:
        with pytest.raises(ValueError):
            list_tasks(db_path, priority=bad)


def test_list_tasks_does_not_modify(db_path):
    # 执行各种筛选和非法查询
    list_tasks(db_path, priority=1)
    list_tasks(db_path, priority=3)
    list_tasks(db_path, priority=2)
    with pytest.raises(TypeError):
        list_tasks(db_path, priority="1")
    with pytest.raises(ValueError):
        list_tasks(db_path, priority=0)
    # 最后查全部任务，数据没有被修改
    assert list_tasks(db_path) == [(1, "任务A", 0, 1), (2, "任务B", 0, 3)]