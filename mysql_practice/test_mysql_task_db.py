"""真实 MySQL 集成测试。

需要本机运行 MySQL、且已配置好 mysql_practice/.env。
测试只操作标题以 D24_ 开头的数据，不使用 TRUNCATE，
也不影响 D23 或其他练习数据。
"""
import mysql.connector
import pytest

from mysql_config import load_config
import mysql_task_db

TITLE_PREFIX = "D24_"

pytestmark = pytest.mark.mysql_integration


def _cleanup(connection) -> None:
    """只删除标题以 D24_ 开头的测试任务。"""
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM tasks WHERE LEFT(title, %s) = %s",
            (len(TITLE_PREFIX), TITLE_PREFIX),
        )
        connection.commit()
    finally:
        cursor.close()


@pytest.fixture
def connection():
    config = load_config()
    conn = mysql.connector.connect(**config)
    _cleanup(conn)
    try:
        yield conn
    finally:
        _cleanup(conn)
        conn.close()


def test_crud_flow(connection):
    title = TITLE_PREFIX + "CRUD任务"

    task_id = mysql_task_db.create_task(connection, title, priority=2)
    assert isinstance(task_id, int)
    connection.commit()

    task = mysql_task_db.get_task(connection, task_id)
    assert task == {
        "id": task_id,
        "title": title,
        "completed": False,
        "priority": 2,
    }
    assert task["completed"] is False

    found = [
        row for row in mysql_task_db.list_tasks(connection) if row["id"] == task_id
    ]
    assert len(found) == 1

    assert mysql_task_db.update_completed(connection, task_id, True) is True
    assert mysql_task_db.get_task(connection, task_id)["completed"] is True
    connection.commit()

    assert mysql_task_db.delete_task(connection, task_id) is True
    assert mysql_task_db.get_task(connection, task_id) is None
    connection.commit()


def test_rollback_discards_insert(connection):
    title = TITLE_PREFIX + "回滚任务"

    task_id = mysql_task_db.create_task(connection, title, priority=3)
    assert mysql_task_db.get_task(connection, task_id) is not None

    connection.rollback()

    rows = mysql_task_db.list_tasks(connection)
    assert all(row["title"] != title for row in rows)
    assert mysql_task_db.get_task(connection, task_id) is None


def test_title_with_single_quote(connection):
    title = TITLE_PREFIX + "O'Reilly参数化测试"

    task_id = mysql_task_db.create_task(connection, title)
    connection.commit()

    task = mysql_task_db.get_task(connection, task_id)
    assert task["title"] == title


def test_update_same_value_returns_true(connection):
    task_id = mysql_task_db.create_task(
        connection,
        TITLE_PREFIX + "相同状态",
        completed=True,
    )
    connection.commit()

    assert mysql_task_db.update_completed(
        connection,
        task_id,
        True,
    ) is True


def test_list_tasks_filters_by_completed(connection):
    todo_id = mysql_task_db.create_task(
        connection,
        TITLE_PREFIX + "筛选未完成",
        completed=False,
    )
    done_id = mysql_task_db.create_task(
        connection,
        TITLE_PREFIX + "筛选已完成",
        completed=True,
    )
    connection.commit()

    todo_rows = mysql_task_db.list_tasks(connection, False)
    done_rows = mysql_task_db.list_tasks(connection, True)

    todo_ids = [row["id"] for row in todo_rows]
    done_ids = [row["id"] for row in done_rows]

    assert todo_id in todo_ids
    assert done_id not in todo_ids
    assert all(row["completed"] is False for row in todo_rows)

    assert done_id in done_ids
    assert todo_id not in done_ids
    assert all(row["completed"] is True for row in done_rows)


def test_missing_id_returns_none_or_false(connection):
    missing_id = 999999999

    assert mysql_task_db.get_task(connection, missing_id) is None
    assert mysql_task_db.update_completed(connection, missing_id, True) is False
    assert mysql_task_db.delete_task(connection, missing_id) is False


@pytest.mark.parametrize(
    "bad_priority, expect_exc",
    [
        (0, ValueError),
        (4, ValueError),
        ("2", TypeError),
        (True, TypeError),
    ],
)
def test_invalid_priority(connection, bad_priority, expect_exc):
    with pytest.raises(expect_exc):
        mysql_task_db.create_task(
            connection,
            TITLE_PREFIX + "非法优先级",
            priority=bad_priority,
        )


@pytest.mark.parametrize(
    "bad_title, expect_exc",
    [
        ("", ValueError),
        ("   ", ValueError),
        ("a" * 51, ValueError),
        (None, TypeError),
    ],
)
def test_invalid_title(connection, bad_title, expect_exc):
    with pytest.raises(expect_exc):
        mysql_task_db.create_task(connection, bad_title)


@pytest.mark.parametrize(
    "bad_id, expect_exc",
    [
        (True, TypeError),
        ("1", TypeError),
        (0, ValueError),
        (-1, ValueError),
    ],
)
def test_invalid_task_id(connection, bad_id, expect_exc):
    with pytest.raises(expect_exc):
        mysql_task_db.get_task(connection, bad_id)


def test_invalid_completed(connection):
    task_id = mysql_task_db.create_task(connection, TITLE_PREFIX + "非法状态")
    connection.commit()

    with pytest.raises(TypeError):
        mysql_task_db.update_completed(connection, task_id, 1)

    with pytest.raises(TypeError):
        mysql_task_db.list_tasks(connection, completed="true")
