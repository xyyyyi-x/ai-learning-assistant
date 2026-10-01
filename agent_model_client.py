import requests
from model_config import get_model_config
from tool_schemas import QueryTasksArgs
import logging
from time import perf_counter

logger = logging.getLogger(__name__)

def call_agent_model(messages: list[dict]) -> dict:
    """请求模型，返回普通回答或工具调用消息。"""
    config = get_model_config()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_tasks",
                "description": (
                    "查询用户的学习任务。"
                    "completed为false时查询未完成任务，"
                    "为true时查询已完成任务。"
                ),
                "parameters": QueryTasksArgs.model_json_schema(),
            },
        }
    ]

    system_message = {
        "role": "system",
        "content": (
            "你是学习任务助手。"
            "涉及用户实际任务时，先调用查询工具，以工具结果为依据回答。"
            "没有查到任务时如实说明，不要编造。"
            "普通问候可以直接回答。"
        ),
    }

    payload = {
        "model": config["model"],
        "messages": [system_message] + messages,
        "tools": tools,
        "stream": False,
        "thinking": {"type": "disabled"},
        "max_tokens": 800,
    }

    # 放在函数 call_agent_model 内部
    started = perf_counter()
    try:
        response = requests.post(
            url=config["base_url"].rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(30, 60),
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as exc:
        elapsed = perf_counter() - started
        logger.warning(
            "model_request_failed elapsed_seconds=%.3f error_type=%s",
            elapsed,
            type(exc).__name__,
        )
        raise  # 裸raise，继续向上抛出异常，不能吞掉错误
    # ========== 补齐：提取、检查并返回模型消息 ==========
    try:
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice["finish_reason"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("模型响应结构异常") from exc

    if not isinstance(message, dict):
        raise ValueError("模型消息格式异常")

    # 判断finish_reason
    if finish_reason == "stop":
        # 普通文字回答，允许直接返回message
        pass
    elif finish_reason == "tool_calls":
        # 模型发起工具调用，允许content=None
        pass
    elif finish_reason == "length":
        raise ValueError("模型回答被截断")
    else:
        raise ValueError("模型非正常结束")

    usage = data.get("usage") or {}
    elapsed = perf_counter() - started

    logger.info(
        "model_request_completed elapsed_seconds=%.3f "
        "finish_reason=%s prompt_tokens=%s "
        "completion_tokens=%s total_tokens=%s",
        elapsed,
        finish_reason,
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
        usage.get("total_tokens"),
    )

    return message
