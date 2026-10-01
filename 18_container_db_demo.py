import argparse
import os
from pathlib import Path

import task_db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "read", "complete"])
    parser.add_argument("--id", type=int)
    args = parser.parse_args()

    db_path = Path(os.environ["TASK_DB_PATH"])
    print("数据库路径：", db_path)

    if args.action == "create":
        task_db.init_db(db_path)
        task_id = task_db.create_task(
            db_path,
            title="验证容器中的SQLite持久化",
            priority=2,
        )
        print("创建的任务编号：", task_id)

    elif args.action == "read":
        rows = task_db.list_tasks(db_path)
        for row in rows:
            print(row)

    elif args.action == "complete":
        if args.id is None:
            parser.error("complete需要--id")
        ok = task_db.update_completed(db_path, args.id, True)
        if ok:
            print(f"任务 {args.id} 已标记为完成")
        else:
            print(f"未找到任务 {args.id}")


if __name__ == "__main__":
    main()
