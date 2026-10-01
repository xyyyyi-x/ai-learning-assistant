"""把周报统计数据交给模型，让模型组织成中文 Markdown 文字。

数字和标题由 Python 计算，模型只负责组织语言。
"""
import json

import requests

from model_config import get_model_config


SYSTEM_PROMPT = (
    "你是学习周报助手。"
    "只能依据提供的统计数据撰写周报，"
    "不得修改任务数量、完成率或任务标题，也不得编造数据里没有的任务。"
    "返回简洁的中文 Markdown，包含四个部分："
    "本周概况、已完成、待完成、下周建议。"
)


def build_weekly_report_messages(stats: dict) -> list[dict]:
    """把统计字典整理成模型消息，不发送请求。"""
    stats_json = json.dumps(stats, ensure_ascii=False)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"以下是本周的统计数据：\n{stats_json}\n\n请据此撰写周报。",
        },
    ]


def generate_weekly_report_text(stats: dict) -> str:
    """请求模型把统计数据写成周报文字，返回去掉首尾空白的字符串。"""
    messages = build_weekly_report_messages(stats)
    config = get_model_config()

    payload = {
        "model": config["model"],
        "messages": messages,
        "stream": False,
        "thinking": {"type": "disabled"},
        "max_tokens": 800,
    }

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url=config["base_url"].rstrip("/") + "/chat/completions",
        headers=headers,
        json=payload,
        timeout=(30, 60),
    )

    response.raise_for_status()
    data = response.json()

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice["finish_reason"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("模型响应结构异常") from exc

    if not isinstance(content, str):
        raise ValueError("模型返回正文不是字符串")

    content_stripped = content.strip()
    if not content_stripped:
        raise ValueError("模型返回正文为空")

    if finish_reason == "length":
        raise ValueError("周报被截断")
    if finish_reason != "stop":
        raise ValueError("模型非正常结束")

    return content_stripped
