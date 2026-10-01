"""用参数化 SQL 操作 MySQL 的练习脚本。

连接配置从同目录的 .env 读取，使用练习账户而不是 root。
所有 SQL 的值都通过 %s 占位符传参，不在字符串里拼接。
"""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
TITLE = "复习 Python 的 'with' 用法"

REQUIRED_KEYS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
]


def load_config() -> dict:
    """读取同目录 .env，缺少必需项时抛出清晰异常。"""
    env_path = BASE_DIR / ".env"
    if not env_path.is_file():
        raise FileNotFoundError(f"缺少配置文件：{env_path}")

    load_dotenv(env_path, override=True, encoding="utf-8-sig")

    config = {}
    for key in REQUIRED_KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            raise ValueError(f"缺少配置：{key}")
        config[key] = value

    return config


def fetch_priority(cursor, title: str) -> int:
    """参数化查询指定标题的优先级，找不到就报错。"""
    cursor.execute(
        "SELECT priority FROM tasks WHERE title = %s",
        (title,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"没有找到任务：{title}")
    return row[0]


def main() -> None:
    config = load_config()

    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(
            host=config["MYSQL_HOST"],
            port=int(config["MYSQL_PORT"]),
            user=config["MYSQL_USER"],
            password=config["MYSQL_PASSWORD"],
            database=config["MYSQL_DATABASE"],
            # 当前安装的 26.7.0 版本 C 扩展在本机连接时报
            # "RuntimeError: Failed raising error."，改用纯 Python 实现。
            use_pure=True,
        )
        cursor = connection.cursor()

        # 先删掉上次练习留下的同名任务，保证脚本可以重复运行
        cursor.execute("DELETE FROM tasks WHERE title = %s", (TITLE,))
        connection.commit()

        # 参数化插入，标题里带单引号也不需要转义
        cursor.execute(
            "INSERT INTO tasks (title, completed, priority) VALUES (%s, %s, %s)",
            (TITLE, False, 2),
        )
        connection.commit()

        print("插入并查询到的priority：", fetch_priority(cursor, TITLE))

        # 结束上面查询隐式开启的事务。
        # autocommit=False 时任何语句都会开启事务，不先结束的话，
        # 下面的 start_transaction() 会报 "Transaction already in progress"，
        # 也就无法证明 UPDATE 位于本次主动开启的事务里。
        connection.commit()

        # 明确开始本次回滚演示的事务
        connection.start_transaction()
        cursor.execute(
            "UPDATE tasks SET priority = %s WHERE title = %s",
            (3, TITLE),
        )
        print("事务内priority：", fetch_priority(cursor, TITLE))

        # 回滚，撤销事务内未提交的修改
        connection.rollback()
        print("回滚后priority：", fetch_priority(cursor, TITLE))

    except mysql.connector.Error:
        # 数据库出错时先回滚，再把异常继续抛出去
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
