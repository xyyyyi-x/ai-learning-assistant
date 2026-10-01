import requests
from model_config import get_model_config
from suggestion_parser import parse_suggestions

def generate_suggestions(goal: str) -> list[str]:
    """
    根据学习目标生成建议，返回经过校验的任务标题列表。

    Args:
        goal: 学习目标文本

    Returns:
        list[str]: 包含1到5个任务标题的列表，
            每个标题已去除首尾空白，长度为1到50个字符。

    Raises:
        TypeError: goal 不是字符串
        ValueError: goal为空、响应结构异常、正文为空、回答截断、模型非正常结束
        requests.exceptions.RequestException: HTTP错误、超时、网络异常直接向外抛出
    """
    # 参数校验
    if not isinstance(goal, str):
        raise TypeError("学习目标必须是字符串")

    goal = goal.strip()
    if not goal:
        raise ValueError("学习目标不能为空")

    config = get_model_config()

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": "你是一名学习助手。根据用户的学习目标生成3条具体、可执行的练习任务。"
                            "仅返回一个合法JSON对象，不要Markdown代码块，不要额外解释。"
                            '格式为：{"suggestions":[{"title":"任务标题"}]}。'
                            "每个title必须是字符串，去掉首尾空白后长度为1到50个字符。"
            },
            {
                "role": "user",
                "content": goal
            }
        ],
        "stream": False,
        "thinking": {"type": "disabled"},
        "max_tokens": 400,
    }

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url=config["base_url"].rstrip("/") + "/chat/completions",
        headers=headers,
        json=payload,
        timeout=(30, 60),
    )

    # HTTP异常直接抛出requests原生异常，不捕获
    response.raise_for_status()
    data = response.json()

    # 仅包裹JSON字段提取，不包含网络请求部分
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice["finish_reason"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("模型响应结构异常") from exc

    # 校验正文类型与非空
    if not isinstance(content, str):
        raise ValueError("模型返回正文不是字符串")

    content_stripped = content.strip()
    if not content_stripped:
        raise ValueError("模型返回正文为空")

    # finish_reason校验
    if finish_reason == "length":
        raise ValueError("回答被截断")
    if finish_reason != "stop":
        raise ValueError(f"模型非正常结束，finish_reason={finish_reason}")

    return parse_suggestions(content_stripped)
