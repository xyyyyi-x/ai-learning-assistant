import json
from pathlib import Path

from tool_dispatcher import execute_tool


def build_tool_reply(
    call_id: str,
    tool_name: str,
    arguments_json: str,
    db_path: Path,
) -> dict:
    """执行工具，将查询结果包装成工具回复消息。"""
    # 1. 调用execute_tool，取得任务列表
    result = execute_tool(tool_name, arguments_json, db_path)
    # 2. 把任务列表转换成JSON字符串
    content = json.dumps(result, ensure_ascii=False)
    # 3. 返回包含role、tool_call_id、content的字典
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": content,
    }
