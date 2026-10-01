from pathlib import Path

from tool_messages import build_tool_reply


def run_assistant(
    goal: str,
    db_path: Path,
    model_call,
    max_turns: int = 3,
) -> str:
    """处理模型消息和工具调用，返回最终回答。"""
    messages = [
        {"role": "user", "content": goal},
    ]

    for _ in range(max_turns):
        response = model_call(messages)
        tool_calls = response.get("tool_calls", [])

        # A. 没有工具调用：检查并返回最终回答
        if not tool_calls:
            content = response.get("content")
            if not isinstance(content, str) or len(content.strip()) == 0:
                raise ValueError("模型未返回有效回答")
            return content.strip()

        # B. 有工具调用：先保存模型的调用消息
        messages.append(response)

        # C. 遍历工具调用，执行并保存每条工具回复
        for call in tool_calls:
            call_id = call["id"]
            tool_name = call["function"]["name"]
            arguments_json = call["function"]["arguments"]

            tool_reply_msg = build_tool_reply(
                call_id=call_id,
                tool_name=tool_name,
                arguments_json=arguments_json,
                db_path=db_path
            )
            messages.append(tool_reply_msg)

    # 循环耗尽，超出最大轮次
    raise RuntimeError("超过模型调用次数上限")
