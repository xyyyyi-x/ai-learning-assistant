# 15_langchain_live_demo.py
from pathlib import Path
from tempfile import TemporaryDirectory
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage

import task_db
from langchain_agent import create_task_agent


def main():
    # 加载 .env，脚本所在目录下的.env，沿用override=True, encoding="utf-8-sig"
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        raise ValueError("缺少week2/.env配置文件")

    load_dotenv(
        env_path,
        override=True,
        encoding="utf-8-sig",
    )

    # 使用临时目录创建临时数据库
    with TemporaryDirectory(prefix="langchain-agent-demo-") as temp_dir:
        db_path = Path(temp_dir) / "tasks.db"
        task_db.init_db(db_path)

        # 创建两条任务
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

        # 框架调用部分
        agent = create_task_agent(db_path)
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "请查询我还没完成的学习任务，并列出标题。",
                    }
                ]
            }
        )
        messages = result["messages"]
        for message in messages:
            if isinstance(message, AIMessage):
                print("模型提出的工具调用：", message.tool_calls)
                print("模型回答内容：", message.content)
                print("Token用量：", message.usage_metadata)
            elif isinstance(message, ToolMessage):
                print("工具回复编号：", message.tool_call_id)
                print("工具执行结果：", message.content)

        print("\n最后一条消息的内容：")
        print(messages[-1].content)


if __name__ == "__main__":
    main()
