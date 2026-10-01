from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_deepseek import ChatDeepSeek

from langchain_tools import create_query_tool
from model_config import get_model_config


def create_task_agent(db_path: Path):
    config = get_model_config()

    model = ChatDeepSeek(
        model=config["model"],
        api_key=config["api_key"],
        api_base=config["base_url"],
        timeout=60,
        max_retries=0,
        max_tokens=800,
        extra_body={"thinking": {"type": "disabled"}},
    )

    query_tool = create_query_tool(db_path)

    agent = create_agent(
        model=model,
        tools=[query_tool],
        system_prompt=(
            "你是学习任务助手。"
            "涉及用户实际任务时，先调用查询工具，"
            "以工具结果为依据回答，不要编造任务。"
            "当前只有只读查询功能，不能修改任务。"
            "普通问候可以直接回答。"
        ),
        middleware=[
            ModelCallLimitMiddleware(
                run_limit=3,
                exit_behavior="error",
            ),
        ],
    )

    return agent