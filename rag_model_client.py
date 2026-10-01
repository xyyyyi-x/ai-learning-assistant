import requests

from model_config import get_model_config
from rag_prompt import build_rag_messages


def generate_rag_answer(
    question: str,
    chunks: list[dict],
) -> str:
    """根据问题与参考资料请求模型，返回回答字符串。"""

    messages = build_rag_messages(question, chunks)
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
        raise ValueError("回答被截断")
    if finish_reason != "stop":
        raise ValueError("模型非正常结束")

    return content_stripped
