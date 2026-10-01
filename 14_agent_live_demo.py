import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import logging

from dotenv import load_dotenv

import task_db
from agent_loop import run_assistant
from agent_model_client import call_agent_model


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        raise ValueError("缺少 .env 配置文件")

    load_dotenv(
        env_path,
        override=True,
        encoding="utf-8-sig",
    )

    goal = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "请查询我还没完成的学习任务，并列出标题。"
    )

    model_calls = 0

    def traced_model_call(messages):
        nonlocal model_calls
        model_calls += 1
        print(f"\n第{model_calls}次请求模型")

        # 打印本轮提交的工具结果，便于核对真实查询数据
        for message in messages:
            if message["role"] == "tool":
                print("提交的工具结果：", message["content"])

        response = call_agent_model(messages)

        tool_calls = response.get("tool_calls") or []
        for call in tool_calls:
            print("模型请求工具：", call["function"]["name"])
            print("工具参数：", call["function"]["arguments"])

        if not tool_calls:
            print("模型返回普通回答")

        return response

    with TemporaryDirectory(prefix="agent-demo-") as temp_dir:
        db_path = Path(temp_dir) / "tasks.db"
        task_db.init_db(db_path)

        task_db.create_task(
            db_path,
            "练习工具调用",
            completed=False,
        )
        task_db.create_task(
            db_path,
            "复习HTTP",
            completed=True,
        )

        answer = run_assistant(
            goal=goal,
            db_path=db_path,
            model_call=traced_model_call,
            max_turns=3,
        )

        print("\n最终回答：")
        print(answer)
        print("模型请求次数：", model_calls)


if __name__ == "__main__":
    main()