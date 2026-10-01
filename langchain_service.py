# langchain_service.py
from pathlib import Path
from langchain_core.messages import AIMessage
from langchain_agent import create_task_agent
import requests
from openai import APITimeoutError, APIError
from langchain.agents.middleware.model_call_limit import (
    ModelCallLimitExceededError,
)

def run_langchain_assistant(goal: str, db_path: Path) -> str:
    """执行查询Agent，返回经过检查的最终回答。"""

    if not isinstance(goal, str):
        raise TypeError("学习目标必须是字符串")

    goal = goal.strip()
    if not goal:
        raise ValueError("学习目标不能为空")

    try:
        agent = create_task_agent(db_path)
        result = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": goal},
                ]
            }
        )
    except APITimeoutError as exc:
        raise requests.exceptions.Timeout(
            "模型服务请求超时"
        ) from exc
    except APIError as exc:
        raise requests.exceptions.RequestException(
            "模型服务请求失败"
        ) from exc
    except ModelCallLimitExceededError as exc:
        raise RuntimeError(
            "超过模型调用次数上限"
        ) from exc

    # 校验1：result必须是字典
    if not isinstance(result, dict):
        raise ValueError("Agent返回格式异常")

    # 校验2：取出messages，必须是非空列表
    messages = result.get("messages")
    if not isinstance(messages, list) or len(messages) == 0:
        raise ValueError("Agent未返回消息")

    # 校验3：最后一条消息必须是 AIMessage
    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        raise ValueError("Agent未返回最终模型消息")

    # 校验4：不能还有待执行的工具调用
    if last_msg.tool_calls:
        raise ValueError("Agent仍有未完成的工具调用")

    # 校验5：content去除空白后不为空
    answer = last_msg.content
    if not isinstance(answer, str) or len(answer.strip()) == 0:
        raise ValueError("Agent未返回有效回答")

    return answer.strip()
