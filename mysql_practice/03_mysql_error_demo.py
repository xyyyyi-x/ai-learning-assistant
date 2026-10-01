r"""MySQL 错误分类演示。

依次演示：连接失败、SQL 语法错误、查无记录，以及失败事务的回滚。

运行：
    .\.venv\Scripts\python.exe .\mysql_practice\03_mysql_error_demo.py
"""
import mysql.connector

from mysql_config import load_config
import mysql_task_db

TITLE_PREFIX = "D24_"
ROLLBACK_TITLE = TITLE_PREFIX + "失败事务回滚"


def print_error(error, label: str) -> None:
    """打印异常分类信息。只输出分类字段，不涉及连接配置，避免泄露密码。"""
    print("异常类名：", type(error).__name__)
    print("errno：", getattr(error, "errno", None))
    print("sqlstate：", getattr(error, "sqlstate", None))
    print("错误类型：", label)


def demo_connect_error() -> None:
    print("=== 情况一：连接失败 ===")

    bad_config = load_config()
    bad_config["port"] = 1
    bad_config["connection_timeout"] = 1

    try:
        mysql.connector.connect(**bad_config)
        print("意外地连接成功了")
    except mysql.connector.Error as error:
        print_error(error, "连接失败")

    print()


def demo_sql_error() -> None:
    print("=== 情况二：SQL 语法错误 ===")

    connection = mysql.connector.connect(**load_config())
    cursor = connection.cursor()
    try:
        cursor.execute("SELEC id FROM tasks")
    except mysql.connector.Error as error:
        connection.rollback()
        print_error(error, "SQL执行失败")
    finally:
        cursor.close()
        connection.close()

    print()


def demo_missing_record() -> None:
    print("=== 情况三：查无记录 ===")

    connection = mysql.connector.connect(**load_config())
    try:
        result = mysql_task_db.get_task(connection, 999999999)
        print(f"查询结果：{result}")
        print("说明：这是正常业务结果，不是数据库异常")
    finally:
        connection.close()

    print()


def demo_failed_transaction_rollback() -> None:
    print("=== 失败事务回滚 ===")

    connection = mysql.connector.connect(**load_config())
    task_id = None

    try:
        # 先清掉上次可能残留的同名任务
        cursor = connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM tasks WHERE title = %s",
                (ROLLBACK_TITLE,),
            )
            connection.commit()
        finally:
            cursor.close()

        # 1. 显式开启事务
        connection.start_transaction()

        # 2. 创建任务，先不提交
        task_id = mysql_task_db.create_task(connection, ROLLBACK_TITLE, priority=2)
        print("事务内创建的任务ID：", task_id)

        # 3. 事务内能查到它
        inside = mysql_task_db.get_task(connection, task_id)
        print("事务内是否查到：", inside is not None)

        # 4. 执行一条故意写错的 SQL
        cursor = connection.cursor()
        try:
            cursor.execute("SELEC id FROM tasks")
        finally:
            cursor.close()

    except mysql.connector.Error as error:
        print_error(error, "SQL执行失败")

        # 5. 回滚，撤销事务里未提交的插入
        connection.rollback()
        print("已执行 rollback()")

    try:
        # 6. 回滚后再查一次，应当查不到
        if task_id is not None:
            after = mysql_task_db.get_task(connection, task_id)
            print(f"rollback 后再查：{after}")
            print("是否还存在：", after is not None)
    finally:
        # 清理 D24_ 开头的数据，保证脚本可以重复运行
        cleanup_cursor = connection.cursor()
        try:
            cleanup_cursor.execute(
                "DELETE FROM tasks WHERE LEFT(title, %s) = %s",
                (len(TITLE_PREFIX), TITLE_PREFIX),
            )
            connection.commit()
        finally:
            cleanup_cursor.close()
        connection.close()

    print()


def main() -> None:
    demo_connect_error()
    demo_sql_error()
    demo_missing_record()
    demo_failed_transaction_rollback()


if __name__ == "__main__":
    main()
