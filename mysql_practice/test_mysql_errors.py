"""MySQL 错误分类与回滚的集成测试。

需要本机运行 MySQL、且已配置好 mysql_practice/.env。
测试只操作标题以 D24_ 开头的数据，不使用 TRUNCATE。
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
    conn = mysql.connector.connect(**load_config())
    _cleanup(conn)
    try:
        yield conn
    finally:
        _cleanup(conn)
        conn.close()


def test_bad_port_raises_connector_error():
    bad_config = load_config()
    bad_config["port"] = 1
    bad_config["connection_timeout"] = 1

    with pytest.raises(mysql.connector.Error):
        mysql.connector.connect(**bad_config)


def test_bad_sql_raises_programming_error(connection):
    cursor = connection.cursor()
    try:
        with pytest.raises(mysql.connector.ProgrammingError):
            cursor.execute("SELEC id FROM tasks")
    finally:
        cursor.close()

    connection.rollback()


def test_missing_task_returns_none(connection):
    result = mysql_task_db.get_task(connection, 999999999)
    assert result is None


def test_rollback_after_sql_error_discards_insert(connection):
    title = TITLE_PREFIX + "事务错误回滚"

    connection.start_transaction()
    task_id = mysql_task_db.create_task(connection, title, priority=2)
    assert mysql_task_db.get_task(connection, task_id) is not None

    cursor = connection.cursor()
    try:
        with pytest.raises(mysql.connector.Error):
            cursor.execute("SELEC id FROM tasks")
    finally:
        cursor.close()

    connection.rollback()

    assert mysql_task_db.get_task(connection, task_id) is None
